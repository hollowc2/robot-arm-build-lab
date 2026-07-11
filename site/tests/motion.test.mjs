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
