import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { studHeight, studPitch, studRadius } from "./bricks";

// Body plus studs, centred on the body so it shares an origin with the physics box.
export function brickGeometry(size: THREE.Vector3, studs: { u: number; v: number }) {
  const body = new THREE.BoxGeometry(size.x, size.y, size.z);
  const parts: THREE.BufferGeometry[] = [body];
  for (let across = 0; across < studs.v; across += 1) {
    for (let along = 0; along < studs.u; along += 1) {
      const stud = new THREE.CylinderGeometry(studRadius, studRadius, studHeight, 20);
      stud.rotateX(Math.PI / 2);
      stud.translate((across + 0.5 - studs.v / 2) * studPitch, (along + 0.5 - studs.u / 2) * studPitch, size.z / 2 + studHeight / 2);
      parts.push(stud);
    }
  }
  // Non-indexed copies give the box and cylinders the same attribute layout for merging.
  const merged = mergeGeometries(parts.map((part) => part.toNonIndexed()));
  parts.forEach((part) => part.dispose());
  return merged;
}

export function brickMaterial(color: string) {
  return new THREE.MeshStandardMaterial({ color, roughness: 0.72, metalness: 0 });
}

export function ghostMaterial(color: string) {
  return new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.13, depthWrite: false });
}
