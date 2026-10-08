import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import * as THREE from "three";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import { createArmModel, jointMotion, jointNames } from "../src/arm.ts";
import { brickHeight, buildPresets, studHeight, validateLayout } from "../src/bricks.ts";
import { boxesOverlap, brickBox, followLine, gripperBoxes, openTravel, planBuild, supplyBatch, supplyBatchSize } from "../src/buildPlan.ts";
import { ArmDriver, BuildSequencer } from "../src/buildRunner.ts";
import { graspTravel } from "../src/grasp.ts";
import { smallBuildFixtures } from "./small-build-fixtures.ts";
import { releaseTravel } from "../src/gripper.ts";
import { SimClock, simStep } from "../src/simClock.ts";

const loader = new STLLoader();
const load = (name) => {
  const bytes = fs.readFileSync(new URL(`../public/generated/models/simulator_${name}.stl`, import.meta.url));
  return loader.parse(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength));
};
const jaws = [{ geometry: load("gripper_left"), side: -1 }, { geometry: load("gripper_right"), side: 1 }];
// Matches the simulator, which grounds the arm on its lowest CAD support (asserted in grasp.test).
const arm = createArmModel(46);
const regressionPresets = [...smallBuildFixtures, ...buildPresets];
const plans = new Map(regressionPresets.map((preset) => [preset.id, planBuild(preset, arm)]));

// Where a brick sits in the wrist frame, which is what the simulator hands to graspTravel.
function inWristFrame(pose, brickPose) {
  arm.probe(pose);
  const wristPosition = arm.wrist.getWorldPosition(new THREE.Vector3());
  const inverse = arm.wrist.getWorldQuaternion(new THREE.Quaternion()).invert();
  return {
    position: brickPose.position.clone().sub(wristPosition).applyQuaternion(inverse),
    quaternion: brickPose.quaternion.clone().premultiply(inverse),
  };
}

test("presets are supported, in a buildable order and squeezable across the jaws", () => {
  assert.deepEqual(buildPresets.map((preset) => preset.id), ["pavilion", "terraces", "skyline", "citadel"]);
  for (const preset of buildPresets) {
    assert.deepEqual(validateLayout(preset), [], preset.name);
    assert.ok(preset.bricks.length >= 6 && preset.bricks.length <= 250, `${preset.name} has ${preset.bricks.length} bricks`);
  }
});

test("large sculptures span three dimensions at 50, 100, 150 and 250 bricks", () => {
  const large = buildPresets.filter((preset) => preset.bricks.length >= 50);
  assert.deepEqual(large.map((preset) => preset.bricks.length), [50, 100, 150, 250]);
  for (const preset of large) {
    for (let axis = 0; axis < 3; axis += 1) assert.ok(new Set(preset.bricks.map((brick) => brick.cell[axis])).size > 1);
  }
});

test("large builds reuse a bounded tray without overlapping waiting bricks", () => {
  for (const plan of plans.values()) {
    for (let start = 0; start < plan.bricks.length; start += supplyBatchSize) {
      const waiting = plan.bricks.slice(start, start + supplyBatchSize);
      for (let i = 0; i < waiting.length; i += 1) {
        const brick = waiting[i];
        assert.ok(brick.supply.position.length() < 260);
        for (const other of waiting.slice(i + 1)) assert.equal(boxesOverlap(brickBox(brick, brick.supply), brickBox(other, other.supply)), false);
        if (start > 0) assert.ok(brick.supply.position.distanceTo(plan.bricks[i].supply.position) < 1e-9);
      }
    }
  }
});

test("layout validation catches bad assembly orders, overlaps and floating bricks", () => {
  const wall = smallBuildFixtures.find((preset) => preset.id === "wall");
  // Upper course listed before the course it rests on.
  const reordered = { ...wall, bricks: [wall.bricks[2], ...wall.bricks.slice(0, 2), ...wall.bricks.slice(3)] };
  assert.match(validateLayout(reordered).join("\n"), /nothing placed beneath it/);
  // A brick slipped in under one that is already there.
  const underneath = { ...wall, bricks: [...wall.bricks.slice(0, 3), { ...wall.bricks[1], cell: [8, 0, 0] }, { ...wall.bricks[0], cell: [8, 0, 1] }] };
  assert.deepEqual(validateLayout(underneath), []);
  const late = { ...wall, bricks: [wall.bricks[0], { ...wall.bricks[0], cell: [0, 0, 1] }, { ...wall.bricks[0], cell: [2, 0, 0] }] };
  assert.match(validateLayout(late).join("\n"), /overlaps brick 1/);
  const tucked = { ...wall, bricks: [{ ...wall.bricks[0], cell: [0, 0, 1] }] };
  assert.match(validateLayout(tucked).join("\n"), /nothing placed beneath it/);
  const sideways = { ...wall, bricks: [{ ...wall.bricks[0], rotation: 90 }] };
  assert.match(validateLayout(sideways).join("\n"), /wider than the gripper/);
  const buried = { ...wall, bricks: [wall.bricks[0], { ...wall.bricks[0], cell: [0, 0, 1] }, { type: "2x2", color: "red", cell: [0, 0, 0], rotation: 0 }] };
  assert.match(validateLayout(buried).join("\n"), /overlaps|placed first/);
});

test("every placement and pickup is reachable and clear of other bricks", () => {
  for (const plan of plans.values()) {
    assert.deepEqual(plan.problems, [], plan.preset.name);
    const stages = plan.steps.filter((step) => step.stage !== "park").map((step) => step.stage);
    assert.equal(stages.length, plan.bricks.length * 9);
    assert.deepEqual(stages.slice(0, 9), ["approach", "lower", "grip", "lift", "carry", "align", "place", "release", "retract"]);
  }
});

test("the CAD fingers clear every supply brick when open and close on it squarely", () => {
  for (const plan of plans.values()) {
    for (const brick of plan.bricks) {
      const pickPose = plan.steps.find((step) => step.brick === brick.index && step.stage === "grip").target;
      const placePose = plan.steps.find((step) => step.brick === brick.index && step.stage === "place").target;
      const atPick = inWristFrame(pickPose, brick.supply);
      const atPlace = inWristFrame(placePose, brick.target);
      // The brick rides in the same spot in the jaws from pickup to placement.
      assert.ok(atPick.position.distanceTo(atPlace.position) < 0.01, `${plan.preset.name} ${brick.label}`);
      assert.ok(atPick.quaternion.angleTo(atPlace.quaternion) < 1e-4);
      const contact = graspTravel(jaws, atPick.position, atPick.quaternion, { halfExtents: brick.size.clone().multiplyScalar(0.5) }, openTravel);
      assert.ok(contact !== null && contact > 5 && contact < openTravel - 3, `${plan.preset.name} ${brick.label} contact ${contact}`);
    }
  }
});

// Runs a whole build on the shared clock, driver and sequencer, standing in for cannon-es with an
// ideal grasp at the CAD contact travel. Every fixed step is checked for collisions.
function runBuild(plan, speedForFrame = () => 1, frameSeconds = 1 / 60, recordPoses = true) {
  const clock = new SimClock();
  const driver = new ArmDriver();
  const sequencer = new BuildSequencer(plan);
  const poses = [];
  const placed = new Set();
  const bricks = plan.bricks.map((brick) => ({ ...brick, pose: { position: brick.supply.position.clone(), quaternion: brick.supply.quaternion.clone() } }));
  const contacts = plan.bricks.map((brick) => {
    const grip = plan.steps.find((step) => step.brick === brick.index && step.stage === "grip").target;
    const local = inWristFrame(grip, brick.supply);
    return graspTravel(jaws, local.position, local.quaternion, { halfExtents: brick.size.clone().multiplyScalar(0.5) }, openTravel);
  });
  let held = null;
  let heldTravel = null;
  let relative = null;
  let collisions = [];
  let worstDrift = 0;
  const gripMatrix = new THREE.Matrix4();
  const gripPosition = new THREE.Vector3();
  const gripQuaternion = new THREE.Quaternion();

  const first = sequencer.start();
  driver.moveTo(first.target, followLine(first, 46));
  let frame = 0;
  while (sequencer.status === "running" && clock.elapsed < Math.max(600, plan.bricks.length * 20)) {
    clock.setSpeed(speedForFrame(frame, sequencer.step));
    clock.advance(frameSeconds, (seconds) => {
      if (sequencer.status !== "running") return;
      const previous = { ...driver.pose };
      driver.step(seconds);
      // Jaws stop on the brick they are squeezing.
      if (held !== null && driver.pose.gripper < heldTravel) driver.pose.gripper = heldTravel;
      for (const joint of jointNames) {
        const change = Math.abs(((driver.pose[joint] - previous[joint] + 540) % 360) - 180);
        assert.ok(change <= jointMotion[joint].maxSpeed * seconds + 1e-6, `${joint} jumped ${change}`);
      }
      if (recordPoses) poses.push(Object.values(driver.pose).join(","));
      const step = sequencer.step;
      if (held === null && step.stage === "grip" && driver.pose.gripper <= contacts[step.brick]) {
        held = step.brick;
        heldTravel = contacts[step.brick];
        arm.gripMatrix(driver.pose, gripMatrix);
        relative = gripMatrix.clone().invert().multiply(new THREE.Matrix4().compose(bricks[held].pose.position, bricks[held].pose.quaternion, new THREE.Vector3(1, 1, 1)));
      }
      arm.gripMatrix(driver.pose, gripMatrix);
      gripMatrix.decompose(gripPosition, gripQuaternion, new THREE.Vector3());
      if (held !== null) {
        new THREE.Matrix4().multiplyMatrices(gripMatrix, relative).decompose(bricks[held].pose.position, bricks[held].pose.quaternion, new THREE.Vector3());
        if (step.stage === "align" || step.stage === "place") {
          const target = plan.bricks[held].target.position;
          worstDrift = Math.max(worstDrift, Math.hypot(bricks[held].pose.position.x - target.x, bricks[held].pose.position.y - target.y));
        }
        if (driver.pose.gripper >= releaseTravel(heldTravel, 40)) {
          const target = plan.bricks[held].target;
          assert.ok(bricks[held].pose.position.distanceTo(target.position) < 0.05, "released off its studs");
          bricks[held].pose = { position: target.position.clone(), quaternion: target.quaternion.clone() };
          placed.add(held);
          held = null;
          heldTravel = null;
        }
      }
      // Nothing the arm carries may pass through placed bricks or bricks still waiting.
      // The active brick intentionally touches the pads. Its exact STL contact
      // is checked above; the conservative tool boxes check other obstacles.
      const obstacles = bricks.filter((brick) => brick.index !== held
        && (plan.bricks.length < 50 || brick.index !== step.brick)
        && (placed.has(brick.index) || supplyBatch(brick.index) === supplyBatch(step.brick)));
      const tools = gripperBoxes(gripPosition, gripQuaternion);
      if (held !== null) {
        const carried = brickBox(bricks[held], bricks[held].pose);
        // Studs below may enter the hollow underside, so start the carried solid above them.
        carried.center.z += studHeight / 2;
        carried.half.z -= studHeight / 2;
        tools.push(carried);
      }
      for (const obstacle of obstacles) {
        const box = brickBox(obstacle, obstacle.pose);
        // Broad phase before the SAT check; most bricks are nowhere near the tool.
        if (Math.abs(box.center.z - gripPosition.z) > box.half.z + 150) continue;
        if (Math.hypot(box.center.x - gripPosition.x, box.center.y - gripPosition.y) > 90) continue;
        if (tools.some((tool) => boxesOverlap(tool, box))) collisions.push(`${step.label} hit ${obstacle.label} #${obstacle.index + 1}`);
      }
      const next = sequencer.update(seconds, driver.arrived(heldTravel), held, (index) => placed.has(index));
      if (next) driver.moveTo(next.target, followLine(next, 46));
    });
    frame += 1;
  }
  return { sequencer, poses, placed, elapsed: clock.elapsed, collisions: [...new Set(collisions)], worstDrift, bricks };
}

const baselines = new Map();
for (const plan of [...plans.values()].filter((plan) => plan.bricks.length < 50)) {
  test(`${plan.preset.name} builds to completion at 0.5x, 1x and 4x along one trajectory`, () => {
    const runs = [0.5, 1, 4].map((speed) => runBuild(plan, () => speed));
    for (const run of runs) {
      assert.equal(run.sequencer.status, "complete", run.sequencer.failure ?? "");
      assert.equal(run.placed.size, plan.bricks.length);
      assert.deepEqual(run.collisions, []);
      // Sliding down beside a neighbour leaves no room for sideways wander.
      assert.ok(run.worstDrift < 0.05, `drifted ${run.worstDrift} mm while placing`);
      for (const brick of run.bricks) assert.ok(brick.pose.position.distanceTo(brick.target.position) < 1e-9);
    }
    // Fixed steps: speed changes how fast simulated time passes, not what happens in it.
    assert.deepEqual(runs[1].poses, runs[0].poses);
    assert.deepEqual(runs[2].poses, runs[0].poses);
    assert.ok(Math.abs(runs[2].elapsed - runs[0].elapsed) < 0.1);
    baselines.set(plan.preset.id, runs[0]);
    // Keep demos watchable: a couple of minutes at 1x.
    assert.ok(runs[0].elapsed < 240, `${plan.preset.name} takes ${runs[0].elapsed.toFixed(0)} s`);
  });
}

for (const plan of [...plans.values()].filter((plan) => plan.bricks.length >= 50)) {
  test(`${plan.preset.name} completes every pickup, placement and tray refill without collisions`, () => {
    const run = runBuild(plan, () => 4, 1 / 60, false);
    assert.equal(run.sequencer.status, "complete", run.sequencer.failure ?? "");
    assert.equal(run.placed.size, plan.bricks.length);
    assert.deepEqual(run.collisions, []);
    assert.ok(run.worstDrift < 0.05, `drifted ${run.worstDrift} mm while placing`);
    for (const brick of run.bricks) assert.ok(brick.pose.position.distanceTo(brick.target.position) < 1e-9);
  });
}

test("changing speed while gripping and carrying keeps the same path", () => {
  const plan = plans.get("house");
  const steady = baselines.get("house") ?? runBuild(plan);
  const speeds = { grip: 4, lift: 0.5, carry: 3.25, align: 0.75, place: 2 };
  const changing = runBuild(plan, (frame, step) => speeds[step.stage] ?? (frame % 7 === 0 ? 4 : 1));
  assert.equal(changing.sequencer.status, "complete");
  assert.deepEqual(changing.poses, steady.poses);
});

test("odd display frame rates still land on identical fixed steps", () => {
  const plan = plans.get("pyramid");
  const steady = baselines.get("pyramid") ?? runBuild(plan);
  const ragged = runBuild(plan, () => 1, 1 / 144);
  assert.deepEqual(ragged.poses, steady.poses);
});

test("a paused clock runs no steps and resuming continues where it left off", () => {
  const clock = new SimClock();
  let ticks = 0;
  clock.advance(1 / 60, () => { ticks += 1; });
  const before = ticks;
  clock.paused = true;
  for (let frame = 0; frame < 120; frame += 1) clock.advance(1 / 60, () => { ticks += 1; });
  assert.equal(ticks, before);
  clock.paused = false;
  clock.setSpeed(4);
  clock.advance(1 / 60, () => { ticks += 1; });
  assert.equal(ticks - before, Math.round((4 / 60) / simStep));
});

test("speed is clamped to 0.5x-4x and a long hitch is not replayed in a burst", () => {
  const clock = new SimClock();
  clock.setSpeed(10);
  assert.equal(clock.speed, 4);
  clock.setSpeed(0.1);
  assert.equal(clock.speed, 0.5);
  clock.setSpeed(4);
  let ticks = 0;
  clock.advance(5, () => { ticks += 1; });
  assert.ok(ticks <= Math.ceil(0.4 / simStep));
});

test("stacked brick tops line up with whole layers", () => {
  for (const plan of plans.values()) {
    for (const brick of plan.bricks) {
      const layer = (brick.target.position.z - brickHeight / 2) / brickHeight;
      assert.ok(Math.abs(layer - brick.entry.cell[2]) < 1e-9);
    }
  }
});
