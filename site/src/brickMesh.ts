import * as THREE from "three";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { studHeight, studPitch, studRadius } from "./bricks";

// Body plus studs, centred on the body so it shares an origin with the physics box.
export function brickGeometry(size: THREE.Vector3, studs: { u: number; v: number }, slope?: 1 | -1) {
  if (slope) {
    const x = size.x / 2, y = size.y / 2, z = size.z / 2;
    const low = -z + 1.5;
    const vertices = [
      [-x, -y, -z], [x, -y, -z], [x, y, -z], [-x, y, -z],
      [-x, -y, slope === 1 ? low : z], [x, -y, slope === 1 ? z : low],
      [x, y, slope === 1 ? z : low], [-x, y, slope === 1 ? low : z],
    ];
    const triangles = [0, 2, 1, 0, 3, 2, 4, 5, 6, 4, 6, 7, 0, 1, 5, 0, 5, 4, 1, 2, 6, 1, 6, 5, 2, 3, 7, 2, 7, 6, 3, 0, 4, 3, 4, 7];
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(triangles.flatMap((index) => vertices[index]), 3));
    geometry.computeVertexNormals();
    return geometry;
  }
  const body = new RoundedBoxGeometry(size.x, size.y, size.z, 2, 0.35);
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
  const merged = mergeGeometries(parts.map((part) => part.index ? part.toNonIndexed() : part.clone()));
  parts.forEach((part) => part.dispose());
  return merged;
}

export function brickMaterial(color: string) {
  return new THREE.MeshPhysicalMaterial({ color, roughness: color === "#9cd7e8" ? 0.12 : 0.3, metalness: 0, clearcoat: 0.45, clearcoatRoughness: 0.2, ...(color === "#9cd7e8" ? { transparent: true, opacity: 0.48, depthWrite: false } : {}) });
}

export function ghostMaterial(color: string) {
  return new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.13, depthWrite: false });
}
