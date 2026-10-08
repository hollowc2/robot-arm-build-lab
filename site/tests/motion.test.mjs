import assert from "node:assert/strict";
import test from "node:test";
import { advanceMotion } from "../src/motion.ts";

test("joint motion accelerates, brakes, and stops on target", () => {
  let position = 0;
  let velocity = 0;
  const speeds = [];
  for (let frame = 0; frame < 300 && position !== 90; frame += 1) {
    [position, velocity] = advanceMotion(position, velocity, 90, 60, 120, 1 / 60);
    speeds.push(velocity);
  }
  assert.ok(speeds[1] > speeds[0]);
  assert.ok(speeds.at(-2) < Math.max(...speeds));
  assert.deepEqual([position, velocity], [90, 0]);
});

// Targets, braking inertia and curved automatic paths all obey the same stops.
test("elbow stops constrain manual tracking and automatic paths in both directions", async () => {
  const { ArmDriver } = await import("../src/buildRunner.ts");
  const { homePose, jointLimits } = await import("../src/arm.ts");
  for (const sign of [-1, 1]) {
    const limit = sign < 0 ? jointLimits.elbow[0] : jointLimits.elbow[1];
    const driver = new ArmDriver({ ...homePose, elbow: limit - sign * 0.01 });
    driver.velocities.elbow = sign * 80;
    driver.targets.elbow = sign * 135;
    for (let frame = 0; frame < 120; frame += 1) {
      driver.step(1 / 120);
      assert.ok(driver.pose.elbow >= jointLimits.elbow[0] && driver.pose.elbow <= jointLimits.elbow[1]);
    }
    assert.equal(driver.pose.elbow, limit);
    driver.moveTo({ ...homePose, elbow: sign * 135 }, () => ({ ...homePose, elbow: sign * 140 }));
    driver.step(1 / 120);
    assert.equal(driver.targets.elbow, limit);
    assert.equal(driver.pose.elbow, limit);
  }
});
