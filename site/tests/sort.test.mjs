import assert from "node:assert/strict";
import test from "node:test";
import * as THREE from "three";
import { createArmModel } from "../src/arm.ts";
import { planSort, sortColors } from "../src/sortPlan.ts";
import { boxesOverlap, brickBox } from "../src/buildPlan.ts";

test("random sorting rounds remain reachable and separate every pickup and color destination", () => {
  const arm = createArmModel(46);
  let seed = 1234;
  const random = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 2 ** 32);
  const layouts = new Set();
  for (let round = 0; round < 20; round++) {
    const plan = planSort(arm, random);
    assert.deepEqual(plan.problems, []);
    layouts.add(plan.bricks.map((brick) => brick.entry.color).join(","));
    for (const color of sortColors) {
      const group = plan.bricks.filter((brick) => brick.entry.color === color);
      assert.equal(group.length, 2);
      assert.ok(group[0].target.position.distanceTo(group[1].target.position) < 85);
    }
    for (const brick of plan.bricks) {
      for (const pose of [brick.supply, brick.target]) assert.ok(new THREE.Vector3(0, 0, 1).applyQuaternion(pose.quaternion).distanceTo(new THREE.Vector3(0, 0, 1)) < 1e-6);
      for (const other of plan.bricks.filter((other) => other.index !== brick.index)) {
        for (const pose of [brick.supply, brick.target]) {
          for (const otherPose of [other.supply, other.target]) assert.equal(boxesOverlap(brickBox(brick, pose), brickBox(other, otherPose)), false);
        }
      }
      // The carried object must have the same local pose at each end of the journey.
      const local = (stage, objectPose) => {
        const pose = plan.steps.find((step) => step.brick === brick.index && step.stage === stage).target;
        return arm.gripMatrix(pose, new THREE.Matrix4()).clone().invert().multiply(new THREE.Matrix4().compose(objectPose.position, objectPose.quaternion, new THREE.Vector3(1, 1, 1)));
      };
      const a = local("grip", brick.supply).elements;
      const b = local("place", brick.target).elements;
      assert.ok(a.every((value, i) => Math.abs(value - b[i]) < 0.01));
    }
  }
  assert.ok(layouts.size > 15);
});
