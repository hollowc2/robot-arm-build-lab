import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import { graspTravel } from "../src/grasp.ts";
import * as THREE from "three";
import { createArmModel } from "../src/arm.ts";
import { insideSortBin, planSort, sortColors } from "../src/sortPlan.ts";
import { boxesOverlap, brickBox, gripperBoxes, openTravel } from "../src/buildPlan.ts";

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


test("foam blocks fit the actual CAD fingers at pickup and release, with clear tray access", () => {
  const loader = new STLLoader();
  const jaws = [-1, 1].map((side) => {
    const bytes = fs.readFileSync(new URL(`../public/generated/models/simulator_gripper_${side < 0 ? "left" : "right"}.stl`, import.meta.url));
    return { side, geometry: loader.parse(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength)) };
  });
  const arm = createArmModel(46);
  const plan = planSort(arm, () => 0.5);
  const next = planSort(arm, () => 0.1);
  assert.equal(plan.bricks.length, 6);
  for (const block of plan.bricks) {
    assert.deepEqual(block.studs, { u: 0, v: 0 });
    assert.deepEqual(block.size.toArray(), [24, 24, 24]);
    assert.ok(block.supply.position.distanceTo(next.bricks[block.index].supply.position) < 1e-9, "pickup slots stay fixed across shuffles");
    for (const [stage, object] of [["grip", block.supply], ["place", block.target]]) {
      const pose = plan.steps.find((step) => step.brick === block.index && step.stage === stage).target;
      arm.probe(pose);
      const wrist = arm.wrist.getWorldPosition(new THREE.Vector3());
      const inverse = arm.wrist.getWorldQuaternion(new THREE.Quaternion()).invert();
      const contact = graspTravel(jaws, object.position.clone().sub(wrist).applyQuaternion(inverse), object.quaternion.clone().premultiply(inverse), { halfExtents: block.size.clone().multiplyScalar(0.5) }, openTravel);
      assert.ok(contact !== null && contact > 0 && contact < openTravel - 2, `${stage} contact for ${block.label}: ${contact}`);
      // The low 4 mm tray rim remains below the fingers on final placement.
      const envelopes = gripperBoxes(arm.probe(pose), arm.gripQuaternion(pose));
      assert.ok(envelopes.every((box) => box.center.z - box.half.z > 4));
      for (const other of plan.bricks.filter((other) => other.index !== block.index)) {
        for (const otherPose of [other.supply, other.target]) {
          assert.ok(envelopes.every((box) => !boxesOverlap(box, brickBox(other, otherPose))), `${stage} clears ${other.label}`);
        }
      }
    }
  }
  jaws.forEach(({ geometry }) => geometry.dispose());
});


test("delivery accepts loose placement in the matching bin and rejects wrong or outside bins", () => {
  const arm = createArmModel(46);
  const plan = planSort(arm, () => 0.5);
  for (const block of plan.bricks) {
    const yaw = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), 0.1);
    const rotation = block.target.quaternion.clone().multiply(yaw);
    const position = block.target.position.clone().add(new THREE.Vector3(3, 0, 0));
    assert.equal(insideSortBin(block.entry.color, position, rotation, block.size), true);
    assert.equal(insideSortBin(sortColors.find((color) => color !== block.entry.color), position, rotation, block.size), false);
    assert.equal(insideSortBin(block.entry.color, block.supply.position, rotation, block.size), false);
    assert.equal(insideSortBin(block.entry.color, position.clone().setZ(70), rotation, block.size), false);
    assert.equal(insideSortBin(block.entry.color, position.clone().multiplyScalar(2), rotation, block.size), false);
  }
});
