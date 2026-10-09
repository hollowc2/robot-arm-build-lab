import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import * as THREE from "three";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import { hornArm, hornPin, hornRadius, hornY, jawDrive, jawMatrix, jawPivotX, jawPivotY, linkagePose, releaseTravel, rodLength } from "../src/gripper.ts";
import { graspTravel } from "../src/grasp.ts";
import { elbowPivotZ, wristPosition, wristMeshOffset } from "../src/assembly.ts";

const loader = new STLLoader();
const load = (name) => {
  const bytes = fs.readFileSync(new URL(`../public/generated/models/simulator_${name}.stl`, import.meta.url));
  return loader.parse(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength));
};
const jaws = [{ geometry: load("gripper_left"), side: -1 }, { geometry: load("gripper_right"), side: 1 }];
const block = { halfExtents: new THREE.Vector3(12, 11, 11) };
const ball = { radius: 9 };

test("CAD fingers stop on both a block and a ball, with different openings", () => {
  const blockTravel = graspTravel(jaws, new THREE.Vector3(0, 131, 12.5), new THREE.Quaternion(), block, 40);
  const ballTravel = graspTravel(jaws, new THREE.Vector3(0, 133, 12.5), new THREE.Quaternion(), ball, 40);
  assert.ok(blockTravel > 10 && blockTravel < 40, `block travel ${blockTravel}`);
  assert.ok(ballTravel > 0 && ballTravel < blockTravel, `ball travel ${ballTravel}`);
  // Independently verify every finger triangle clears the solid at the returned opening.
  for (const [shape, position, travel] of [[block, new THREE.Vector3(0, 131, 12.5), blockTravel], [ball, new THREE.Vector3(0, 133, 12.5), ballTravel]]) {
    const bounds = new THREE.Box3(new THREE.Vector3(-12, -11, -11), new THREE.Vector3(12, 11, 11));
    for (const { geometry, side } of jaws) {
      const vertices = geometry.attributes.position;
      for (let i = 0; i < vertices.count; i += 3) {
        const points = [0, 1, 2].map((offset) => new THREE.Vector3().fromBufferAttribute(vertices, i + offset).applyMatrix4(jawMatrix(travel, side)).sub(position));
        const triangle = new THREE.Triangle(...points);
        if ("radius" in shape) assert.ok(triangle.closestPointToPoint(new THREE.Vector3(), new THREE.Vector3()).length() > shape.radius);
        else assert.equal(bounds.intersectsTriangle(triangle), false);
      }
    }
  }
});

test("contact accounts for block rotation and rejects objects outside the mouth", () => {
  const position = new THREE.Vector3(0, 131, 12.5);
  const straight = graspTravel(jaws, position, new THREE.Quaternion(), block, 40);
  const rotated = graspTravel(jaws, position, new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), Math.PI / 4), block, 40);
  assert.ok(straight !== null && rotated !== null);
  // Pivoting changes the contact angle as well as the mouth width.
  assert.ok(Math.abs(rotated - straight) > 0.5);
  assert.equal(graspTravel(jaws, new THREE.Vector3(0, 180, 12.5), new THREE.Quaternion(), ball, 40), null);
  assert.equal(graspTravel(jaws, position, new THREE.Quaternion(), { radius: 60 }, 40), null);
});

test("the full assembly can be grounded from the fixed CAD support's lowest point", () => {
  const fixed = load("base_fixed");
  fixed.computeBoundingBox();
  const lift = -fixed.boundingBox.min.z;
  assert.equal(lift, 46);
  assert.equal(fixed.boundingBox.clone().translate(new THREE.Vector3(0, 0, lift)).min.z, 0);
});


test("wrist pulley and gripper stay on the CAD shaft throughout wrist rotation", () => {
  const pulley = load("wrist_driven");
  pulley.computeBoundingBox();
  const cadAxis = pulley.boundingBox.getCenter(new THREE.Vector3());
  // X is the shaft axis; the pulley sits beside the centered gripper tongue.
  const localAxis = cadAxis.clone().add(new THREE.Vector3(...wristMeshOffset));
  assert.ok(Math.abs(localAxis.y) < 0.001);
  assert.ok(Math.abs(localAxis.z) < 0.001, `pulley is ${localAxis.z} mm off the wrist pivot`);
  assert.ok(Math.abs(elbowPivotZ + wristPosition[2] - cadAxis.z) < 0.001);
  for (const degrees of [-150, -90, -45, 0, 18]) {
    const wrist = new THREE.Group();
    wrist.position.set(...wristPosition);
    wrist.rotation.x = THREE.MathUtils.degToRad(-degrees);
    wrist.updateMatrixWorld(true);
    const rotatingAxis = wrist.localToWorld(localAxis.clone());
    assert.ok(Math.abs(rotatingAxis.y - wrist.position.y) < 0.001);
    assert.ok(Math.abs(rotatingAxis.z - wrist.position.z) < 0.001);
  }
});


test("fingers stay on fixed posts and rigid links remain attached throughout travel", () => {
  for (const side of [-1, 1]) {
    for (let travel = 0; travel <= 40; travel += 1) {
      const transform = jawMatrix(travel, side);
      const pivot = new THREE.Vector3(side * jawPivotX, jawPivotY, 0);
      assert.ok(pivot.clone().applyMatrix4(transform).distanceTo(pivot) < 1e-9);
      const { drive, hornEnd, hornAngle, rodAngle } = linkagePose(travel, side);
      assert.ok(Math.abs(hornEnd.distanceTo(new THREE.Vector3(side * jawPivotX, hornY, 0)) - hornRadius) < 1e-9);
      assert.ok(Math.abs(hornEnd.distanceTo(drive) - rodLength) < 1e-9);
      const hornTip = new THREE.Vector3(side * hornArm.outboard, hornArm.forward, 0).applyAxisAngle(new THREE.Vector3(0, 0, 1), hornAngle).add(new THREE.Vector3(side * jawPivotX, hornY, 0));
      const rodTip = new THREE.Vector3(side * (jawPivotX + jawDrive.outboard), jawPivotY + jawDrive.forward, 0).sub(hornPin(side)).applyAxisAngle(new THREE.Vector3(0, 0, 1), rodAngle).add(hornEnd);
      assert.ok(hornTip.distanceTo(hornEnd) < 1e-9);
      assert.ok(rodTip.distanceTo(drive) < 1e-9);
    }
  }
});


test("objects contacting near maximum opening can still be released", () => {
  assert.equal(releaseTravel(39, 40), 40);
  assert.equal(releaseTravel(20, 40), 22);
});


test("a pinch rejects missing or one-sided finger contact", () => {
  const position = new THREE.Vector3(0, 131, 12.5);
  assert.equal(graspTravel([jaws[0]], position, new THREE.Quaternion(), block, 40), null);
  assert.equal(graspTravel(jaws, position.clone().setX(5), new THREE.Quaternion(), block, 40), null);
});
