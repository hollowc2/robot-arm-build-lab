import * as THREE from "three";
import { wristPosition } from "./assembly.ts";

export type JointAngles = {
  base: number;
  shoulder: number;
  elbow: number;
  wrist: number;
  gripper: number;
};
export type JointName = keyof JointAngles;

export const homePose: JointAngles = { base: 0, shoulder: 0, elbow: 0, wrist: 0, gripper: 0 };
export const jointLimits: Record<JointName, [number, number]> = {
  base: [0, 360],
  shoulder: [-130, 130],
  elbow: [-135, 135],
  wrist: [-150, 18],
  gripper: [0, 40],
};
// Real hardware will vary; keep these two limits per joint easy to calibrate.
export const jointMotion: Record<JointName, { maxSpeed: number; acceleration: number }> = {
  base: { maxSpeed: 90, acceleration: 180 },
  shoulder: { maxSpeed: 70, acceleration: 140 },
  elbow: { maxSpeed: 80, acceleration: 160 },
  wrist: { maxSpeed: 100, acceleration: 200 },
  gripper: { maxSpeed: 16, acceleration: 32 },
};
export const jointNames = Object.keys(homePose) as JointName[];
export const armJoints = ["base", "shoulder", "elbow", "wrist"] as const;

// Installed joint offsets (mm) shared by the rendered arm and the planning model.
export const shoulderPosition: [number, number, number] = [0, 0, 162.03];
export const elbowPosition: [number, number, number] = [0, 0, 175.35];
// The centre of the mouth, between the finger pads, in the wrist frame.
export const gripPointPosition: [number, number, number] = [0, 124, 14];

export function clampJoint(name: JointName, value: number) {
  const [min, max] = jointLimits[name];
  return Math.max(min, Math.min(max, value));
}

export const normalizeBase = (value: number) => (value % 360 + 360) % 360;

// Signed shortest difference for the continuous base joint, plain difference otherwise.
export function jointDelta(name: JointName, from: number, to: number) {
  return name === "base" ? ((to - from + 540) % 360) - 180 : to - from;
}

export function applyJointRotations(
  pose: JointAngles,
  groups: { base: THREE.Object3D; shoulder: THREE.Object3D; elbow: THREE.Object3D; wrist: THREE.Object3D },
) {
  groups.base.rotation.z = THREE.MathUtils.degToRad(-pose.base);
  groups.shoulder.rotation.x = THREE.MathUtils.degToRad(-pose.shoulder);
  groups.elbow.rotation.x = THREE.MathUtils.degToRad(pose.elbow);
  groups.wrist.rotation.x = THREE.MathUtils.degToRad(-pose.wrist);
}

export type ArmModel = ReturnType<typeof createArmModel>;

// A mesh-free copy of the kinematic chain used for planning, reach and validation.
export function createArmModel(lift = 0) {
  const root = new THREE.Group();
  const base = new THREE.Group();
  const shoulder = new THREE.Group();
  const elbow = new THREE.Group();
  const wrist = new THREE.Group();
  const grip = new THREE.Object3D();
  root.position.z = lift;
  shoulder.position.set(...shoulderPosition);
  elbow.position.set(...elbowPosition);
  wrist.position.set(...wristPosition);
  grip.position.set(...gripPointPosition);
  root.add(base);
  base.add(shoulder);
  shoulder.add(elbow);
  elbow.add(wrist);
  wrist.add(grip);

  const probePosition = new THREE.Vector3();
  const probeJoint = new THREE.Vector3();
  const probe = (pose: JointAngles) => {
    applyJointRotations(pose, { base, shoulder, elbow, wrist });
    root.updateMatrixWorld(true);
    return probePosition.setFromMatrixPosition(grip.matrixWorld);
  };
  // Position error plus two soft preferences: the gripper points straight down, and the
  // elbow and wrist housings stay well clear of the table.
  const cost = (pose: JointAngles, target: THREE.Vector3) => {
    const error = probe(pose).distanceToSquared(target);
    const tilt = downTilt(pose);
    const elbowClearance = Math.max(0, 90 - probeJoint.setFromMatrixPosition(elbow.matrixWorld).z);
    const wristClearance = Math.max(0, 90 - probeJoint.setFromMatrixPosition(wrist.matrixWorld).z);
    return { error, cost: error + 2 * tilt ** 2 + elbowClearance ** 2 + wristClearance ** 2 };
  };
  // Seed from the previous pose and, among accurate solutions, prefer the one with the least
  // joint travel so consecutive steps stay on the same elbow branch instead of flipping.
  const solve = (target: THREE.Vector3, gripper: number, previous: JointAngles): JointAngles => {
    const baseAngle = normalizeBase(THREE.MathUtils.radToDeg(Math.atan2(target.x, target.y)));
    const solutions: { pose: JointAngles; error: number; cost: number; travel: number }[] = [];
    for (const seed of [[previous.shoulder, previous.elbow, previous.wrist], [45, -110, -48], [30, -130, -66], [-125, 125, -100]]) {
      let candidate: JointAngles = { base: baseAngle, shoulder: seed[0], elbow: seed[1], wrist: seed[2], gripper };
      for (const step of [24, 8, 2, 0.5, 0.1, 0.02]) {
        for (let round = 0; round < 12; round += 1) {
          let improved = false;
          for (const joint of armJoints) {
            let best = candidate;
            let bestCost = cost(candidate, target).cost;
            for (const delta of [-step, step]) {
              const value = joint === "base" ? normalizeBase(candidate[joint] + delta) : clampJoint(joint, candidate[joint] + delta);
              const next = { ...candidate, [joint]: value };
              const { cost: nextCost } = cost(next, target);
              if (nextCost < bestCost) {
                best = next;
                bestCost = nextCost;
                improved = true;
              }
            }
            candidate = best;
          }
          if (!improved) break;
        }
      }
      const travel = (["shoulder", "elbow", "wrist"] as const)
        .reduce((sum, joint) => sum + Math.abs(candidate[joint] - previous[joint]), 0);
      solutions.push({ pose: candidate, ...cost(candidate, target), travel });
    }
    const accurate = solutions.filter((solution) => solution.error < 4);
    const rank = (solution: (typeof solutions)[number]) => (accurate.length ? solution.cost + 0.1 * solution.travel : solution.cost);
    const chosen = (accurate.length ? accurate : solutions).reduce((best, solution) => (rank(solution) < rank(best) ? solution : best)).pose;
    // Coordinate descent stalls a fraction of a millimetre short in narrow valleys. Close the gap
    // exactly on the branch it chose, as long as that stays within limits and clear of the table.
    const exact = solveStraightDown(target, gripper, root.position.z, Math.sign(chosen.elbow) || -1);
    if (exact && armJoints.every((joint) => Math.abs(jointDelta(joint, chosen[joint], exact[joint])) < 6) && cost(exact, target).cost <= cost(chosen, target).cost) {
      return exact;
    }
    return chosen;
  };

  const gripQuaternion = (pose: JointAngles, out = new THREE.Quaternion()) => {
    probe(pose);
    return grip.getWorldQuaternion(out);
  };
  const gripMatrix = (pose: JointAngles, out = new THREE.Matrix4()) => {
    probe(pose);
    return out.copy(grip.matrixWorld);
  };

  return { root, base, shoulder, elbow, wrist, grip, probe, solve, gripQuaternion, gripMatrix, setLift: (z: number) => { root.position.z = z; } };
}

// Closed-form pose that puts the grip point on the target with the fingers vertical. With the
// wrist fixed at -90° to the world, shoulder and elbow form a planar two-link chain in the
// base's YZ plane; the wrist's sideways offset only shifts the base angle.
export function solveStraightDown(target: THREE.Vector3, gripper: number, lift: number, elbowSign: number): JointAngles | null {
  const side = wristPosition[0];
  const radial = Math.sqrt(target.x ** 2 + target.y ** 2 - side ** 2);
  if (!Number.isFinite(radial)) return null;
  const base = normalizeBase(THREE.MathUtils.radToDeg(Math.atan2(target.x, target.y) - Math.atan2(side, radial)));
  const upper = elbowPosition[2];
  const fore = wristPosition[2];
  // Grip point sits (z, -y) of the wrist joint once the fingers point down.
  const dy = radial - gripPointPosition[2];
  const dz = target.z - lift + gripPointPosition[1] - shoulderPosition[2];
  const cosElbow = (dy ** 2 + dz ** 2 - upper ** 2 - fore ** 2) / (2 * upper * fore);
  if (Math.abs(cosElbow) > 1) return null;
  const elbow = elbowSign * Math.acos(cosElbow);
  const upperAngle = Math.atan2(dz, dy) - Math.atan2(fore * Math.sin(elbow), upper + fore * Math.cos(elbow));
  const shoulder = 90 - THREE.MathUtils.radToDeg(upperAngle);
  const elbowDegrees = THREE.MathUtils.radToDeg(elbow);
  const pose = { base, shoulder, elbow: elbowDegrees, wrist: -shoulder + elbowDegrees + 90, gripper };
  return armJoints.every((joint) => joint === "base" || clampJoint(joint, pose[joint]) === pose[joint]) ? pose : null;
}

// Degrees the fingers lean away from pointing straight down.
export function downTilt(pose: JointAngles) {
  return ((-pose.shoulder + pose.elbow - pose.wrist + 90 + 540) % 360) - 180;
}
