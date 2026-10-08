import { armJoints, clampJoint, homePose, jointDelta, jointMotion, jointNames, type JointAngles } from "./arm.ts";
import { advanceMotion, planJointMove, stepJointMove, type JointMove } from "./motion.ts";
import type { BuildPlan, BuildStep } from "./buildPlan.ts";

type ArmJoint = (typeof armJoints)[number];
const pickArm = (pose: JointAngles) => Object.fromEntries(armJoints.map((joint) => [joint, pose[joint]])) as Record<ArmJoint, number>;

// Drives the joints one fixed step at a time: coordinated moves for the build sequence, and
// independent per-joint tracking for sliders and the gamepad. The gripper always tracks its own
// target so it can stop on contact with a brick.
export class ArmDriver {
  pose: JointAngles;
  velocities: JointAngles = { ...homePose };
  targets: JointAngles;
  private move: JointMove<ArmJoint> | null = null;
  private along: ((progress: number) => JointAngles) | null = null;

  constructor(pose: JointAngles = homePose) {
    this.pose = { ...pose };
    for (const joint of jointNames) this.pose[joint] = clampJoint(joint, this.pose[joint]);
    this.targets = { ...this.pose };
  }

  // Coordinated move to the target. `along` optionally bends the joint-space line into some other
  // path between the same two poses (a straight Cartesian drop), sampled by shared progress.
  moveTo(target: JointAngles, along?: (progress: number) => JointAngles) {
    this.targets = { ...target };
    for (const joint of jointNames) this.targets[joint] = clampJoint(joint, this.targets[joint]);
    const move = planJointMove<ArmJoint>(pickArm(this.pose), pickArm(this.targets), jointMotion, ["base"]);
    // A curved path asks a little more of some joints mid-way than the end points suggest.
    if (along) {
      // Curved Cartesian moves can demand more joint travel in the middle than
      // their endpoints imply, especially beside tall structures. Bound speed
      // by the steepest sampled joint derivative instead of a fixed discount.
      const samples = 128;
      let previous = along(0);
      for (let i = 1; i <= samples; i += 1) {
        const pose = along(i / samples);
        for (const joint of armJoints) {
          const derivative = Math.abs(jointDelta(joint, previous[joint], pose[joint])) * samples;
          if (derivative > 0) move.limits.maxSpeed = Math.min(move.limits.maxSpeed, jointMotion[joint].maxSpeed / derivative);
        }
        previous = pose;
      }
      move.limits.maxSpeed *= 0.8;
      move.limits.acceleration *= 0.6;
    }
    this.move = move;
    this.along = along ?? null;
  }

  // Hand the current targets to per-joint tracking, keeping the arm's current velocity.
  track() {
    this.move = null;
    this.along = null;
  }

  hold() {
    this.move = null;
    this.along = null;
    this.targets = { ...this.pose };
    this.velocities = { ...homePose };
  }

  step(seconds: number) {
    for (const joint of jointNames) this.targets[joint] = clampJoint(joint, this.targets[joint]);
    if (this.move) {
      const before = pickArm(this.pose);
      stepJointMove(this.move, seconds, this.pose, this.velocities, ["base"]);
      if (this.along) {
        const point = this.along(this.move.progress);
        for (const joint of armJoints) {
          this.pose[joint] = point[joint];
          this.velocities[joint] = jointDelta(joint, before[joint], point[joint]) / seconds;
        }
      }
    } else {
      for (const joint of armJoints) {
        [this.pose[joint], this.velocities[joint]] = advanceMotion(
          this.pose[joint], this.velocities[joint], this.targets[joint],
          jointMotion[joint].maxSpeed, jointMotion[joint].acceleration, seconds, joint === "base",
        );
      }
    }
    [this.pose.gripper, this.velocities.gripper] = advanceMotion(
      this.pose.gripper, this.velocities.gripper, this.targets.gripper,
      jointMotion.gripper.maxSpeed, jointMotion.gripper.acceleration, seconds,
    );
    // Reversing a target can leave outward velocity while braking. Enforce the
    // physical stops on the pose as well as targets and curved path samples.
    for (const joint of jointNames) {
      if (joint === "base") continue;
      const bounded = clampJoint(joint, this.pose[joint]);
      if (bounded !== this.pose[joint]) {
        this.pose[joint] = bounded;
        this.velocities[joint] = 0;
      }
    }
  }

  // A held brick stops the jaws short of a closing target; that counts as arrived.
  arrived(heldTravel: number | null) {
    const gripperTarget = heldTravel === null ? this.targets.gripper : Math.max(this.targets.gripper, heldTravel);
    const armDone = this.move
      ? this.move.progress === 1
      : armJoints.every((joint) => Math.abs(jointDelta(joint, this.pose[joint], this.targets[joint])) < 0.05 && Math.abs(this.velocities[joint]) < 0.01);
    return armDone && Math.abs(this.pose.gripper - gripperTarget) < 0.05;
  }
}

export type BuildStatus = "idle" | "running" | "complete" | "stopped" | "failed";
// Simulated seconds any one step may take before the build gives up.
const stepTimeout = 20;

// Walks the plan's steps. Each step finishes once the arm has arrived and dwelt there, and the
// grip and release steps also confirm that the right brick was picked up or snapped into place.
export class BuildSequencer {
  status: BuildStatus = "idle";
  index = 0;
  failure: string | null = null;
  readonly plan: BuildPlan;
  private settled = 0;
  private stepTime = 0;

  constructor(plan: BuildPlan) {
    this.plan = plan;
  }

  get step(): BuildStep {
    return this.plan.steps[Math.min(this.index, this.plan.steps.length - 1)];
  }

  start() {
    this.status = "running";
    this.index = 0;
    this.failure = null;
    this.settled = 0;
    this.stepTime = 0;
    return this.step;
  }

  stop() {
    if (this.status === "running") this.status = "stopped";
  }

  fail(reason: string) {
    this.status = "failed";
    this.failure = reason;
  }

  // Called once per fixed simulation step. Returns the next step when the sequence advances.
  update(seconds: number, arrived: boolean, held: number | null, isPlaced: (brick: number) => boolean): BuildStep | null {
    if (this.status !== "running") return null;
    const step = this.step;
    this.stepTime += seconds;
    if (this.stepTime > stepTimeout) {
      this.fail(`Stalled while ${step.label.toLowerCase()}`);
      return null;
    }
    if (!arrived) {
      this.settled = 0;
      return null;
    }
    this.settled += seconds;
    if (this.settled + 1e-9 < step.dwell) return null;
    const brick = this.plan.bricks[step.brick];
    if (step.stage === "grip" && held !== step.brick) {
      this.fail(`Missed the ${brick.label}`);
      return null;
    }
    if (step.stage === "release" && !isPlaced(step.brick)) {
      this.fail(`The ${brick.label} missed its studs`);
      return null;
    }
    this.index += 1;
    this.settled = 0;
    this.stepTime = 0;
    if (this.index === this.plan.steps.length) {
      this.status = "complete";
      return null;
    }
    return this.step;
  }

  // Bricks finished so far, and the one being worked on (1-based) while running.
  progress() {
    const current = this.status === "complete" ? this.plan.bricks.length : this.step.brick + 1;
    return { current, total: this.plan.bricks.length };
  }
}
