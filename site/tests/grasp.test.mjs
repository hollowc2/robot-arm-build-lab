import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import * as THREE from "three";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import { graspTravel } from "../src/grasp.ts";

const loader = new STLLoader();
const load = (name) => {
  const bytes = fs.readFileSync(new URL(`../public/generated/models/simulator_${name}.stl`, import.meta.url));
  return loader.parse(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength));
};
const jaws = [{ geometry: load("gripper_left"), side: -1 }, { geometry: load("gripper_right"), side: 1 }];
const block = { halfExtents: new THREE.Vector3(12, 11, 11) };
const ball = { radius: 9 };

test("CAD fingers stop on both a block and a ball, with different openings", () => {
  const blockTravel = graspTravel(jaws, new THREE.Vector3(0, 131, 14), new THREE.Quaternion(), block, 40);
  const ballTravel = graspTravel(jaws, new THREE.Vector3(0, 133, 14), new THREE.Quaternion(), ball, 40);
  assert.ok(blockTravel > 10 && blockTravel < 40, `block travel ${blockTravel}`);
  assert.ok(ballTravel > 0 && ballTravel < blockTravel, `ball travel ${ballTravel}`);
  // Independently verify every finger triangle clears the solid at the returned opening.
  for (const [shape, position, travel] of [[block, new THREE.Vector3(0, 131, 14), blockTravel], [ball, new THREE.Vector3(0, 133, 14), ballTravel]]) {
    const bounds = new THREE.Box3(new THREE.Vector3(-12, -11, -11), new THREE.Vector3(12, 11, 11));
    for (const { geometry, side } of jaws) {
      const vertices = geometry.attributes.position;
      for (let i = 0; i < vertices.count; i += 3) {
        const points = [0, 1, 2].map((offset) => new THREE.Vector3().fromBufferAttribute(vertices, i + offset).add(new THREE.Vector3(side * travel / 2, 0, 0)).sub(position));
        const triangle = new THREE.Triangle(...points);
        if ("radius" in shape) assert.ok(triangle.closestPointToPoint(new THREE.Vector3(), new THREE.Vector3()).length() > shape.radius);
        else assert.equal(bounds.intersectsTriangle(triangle), false);
      }
    }
  }
});

test("contact accounts for block rotation and rejects objects outside the mouth", () => {
  const position = new THREE.Vector3(0, 131, 14);
  const straight = graspTravel(jaws, position, new THREE.Quaternion(), block, 40);
  const rotated = graspTravel(jaws, position, new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), Math.PI / 4), block, 40);
  assert.ok(rotated > straight);
  assert.equal(graspTravel(jaws, new THREE.Vector3(0, 180, 14), new THREE.Quaternion(), ball, 40), null);
  assert.equal(graspTravel(jaws, position, new THREE.Quaternion(), { radius: 60 }, 40), null);
});

test("the full assembly can be grounded from the fixed CAD support's lowest point", () => {
  const fixed = load("base_fixed");
  fixed.computeBoundingBox();
  const lift = -fixed.boundingBox.min.z;
  assert.equal(lift, 46);
  assert.equal(fixed.boundingBox.clone().translate(new THREE.Vector3(0, 0, lift)).min.z, 0);
});
