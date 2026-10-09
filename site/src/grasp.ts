import * as THREE from "three";
import { jawMatrix } from "./gripper.ts";

export type GraspShape = { halfExtents: THREE.Vector3 } | { radius: number };
export type JawSurface = { geometry: THREE.BufferGeometry; side: -1 | 1 };

// Test the CAD triangles against the solid in its own coordinate system. This includes
// the curved noses and serrated pads, which are narrower than the nominal pad gap.
export function graspTravel(
  jaws: JawSurface[],
  position: THREE.Vector3,
  quaternion: THREE.Quaternion,
  shape: GraspShape,
  maximum: number,
): number | null {
  const inverse = quaternion.clone().invert();
  const triangle = new THREE.Triangle();
  const nearest = new THREE.Vector3();
  const box = "halfExtents" in shape
    ? new THREE.Box3(shape.halfExtents.clone().negate(), shape.halfExtents)
    : null;
  const intersects = (travel: number, surfaces = jaws) => surfaces.some(({ geometry, side }) => {
    const transform = jawMatrix(travel, side);
    const vertices = geometry.getAttribute("position");
    const indices = geometry.index;
    const count = indices?.count ?? vertices.count;
    for (let index = 0; index < count; index += 3) {
      [triangle.a, triangle.b, triangle.c].forEach((vertex, corner) => {
        vertex.fromBufferAttribute(vertices, indices ? indices.getX(index + corner) : index + corner);
        vertex.applyMatrix4(transform);
        vertex.sub(position).applyQuaternion(inverse);
      });
      if (box ? box.intersectsTriangle(triangle)
        : triangle.closestPointToPoint(nearest.set(0, 0, 0), nearest).lengthSq() <= (shape as { radius: number }).radius ** 2) return true;
    }
    return false;
  });
  // A pinch needs opposing fingers. A single-sided hit cannot hold a brick.
  if (jaws.length !== 2 || new Set(jaws.map((jaw) => jaw.side)).size !== 2) return null;
  if (intersects(maximum)) return null;
  const contacts = jaws.map((jaw) => {
    if (!intersects(0, [jaw])) return null;
    let closed = 0;
    let open = maximum;
    for (let iteration = 0; iteration < 12; iteration += 1) {
      const middle = (closed + open) / 2;
      if (intersects(middle, [jaw])) closed = middle;
      else open = middle;
    }
    return open + 0.05;
  });
  if (contacts.some((contact) => contact === null)) return null;
  const [left, right] = contacts as number[];
  // Reject off-centre poses instead of treating one finger as a hidden grip.
  if (Math.abs(left - right) > 0.75) return null;
  return Math.max(left, right);
}
