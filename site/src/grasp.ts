import * as THREE from "three";

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
  const intersects = (travel: number) => jaws.some(({ geometry, side }) => {
    const vertices = geometry.getAttribute("position");
    const indices = geometry.index;
    const count = indices?.count ?? vertices.count;
    for (let index = 0; index < count; index += 3) {
      [triangle.a, triangle.b, triangle.c].forEach((vertex, corner) => {
        vertex.fromBufferAttribute(vertices, indices ? indices.getX(index + corner) : index + corner);
        vertex.x += side * travel / 2;
        vertex.sub(position).applyQuaternion(inverse);
      });
      if (box ? box.intersectsTriangle(triangle)
        : triangle.closestPointToPoint(nearest.set(0, 0, 0), nearest).lengthSq() <= (shape as { radius: number }).radius ** 2) return true;
    }
    return false;
  });
  if (intersects(maximum)) return null; // The object cannot fit between fully open jaws.
  if (!intersects(0)) return null; // It is outside the finger contact area.
  let closed = 0;
  let open = maximum;
  for (let iteration = 0; iteration < 12; iteration += 1) {
    const middle = (closed + open) / 2;
    if (intersects(middle)) closed = middle;
    else open = middle;
  }
  return open + 0.05;
}
