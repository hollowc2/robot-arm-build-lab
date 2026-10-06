import * as THREE from "three";

// Fixed post and linkage centers from sg90_parallel_gripper.py (mm).
export const jawPivotY = 74.5;
export const jawPivotX = 11.5;
const tipLength = 61;
const tipInward = 5;
const hornY = 49.5;
const hornRadius = Math.hypot(6, 15.5);
const rodLength = Math.hypot(2.5, 26.5);

export function jawAngle(travel: number, side: -1 | 1): number {
  // Travel is the increase in tip gap, preserving the existing mm control.
  const radius = Math.hypot(tipLength, tipInward);
  return -side * (Math.asin((travel / 2 - tipInward) / radius) + Math.atan2(tipInward, tipLength));
}

export function jawMatrix(travel: number, side: -1 | 1): THREE.Matrix4 {
  const pivotX = side * jawPivotX;
  return new THREE.Matrix4().makeTranslation(pivotX, jawPivotY, 0)
    .multiply(new THREE.Matrix4().makeRotationZ(jawAngle(travel, side)))
    .multiply(new THREE.Matrix4().makeTranslation(-pivotX, -jawPivotY, 0));
}

export function linkagePose(travel: number, side: -1 | 1) {
  // Solve the rigid horn / pushrod circle intersection on the installed branch.
  const drive = new THREE.Vector3(side * 15, 91.5, 0).applyMatrix4(jawMatrix(travel, side));
  const shaft = new THREE.Vector3(side * jawPivotX, hornY, 0);
  const delta = drive.clone().sub(shaft);
  const distance = delta.length();
  const along = (hornRadius ** 2 - rodLength ** 2 + distance ** 2) / (2 * distance);
  const height = Math.sqrt(Math.max(0, hornRadius ** 2 - along ** 2));
  const hornEnd = shaft.clone().addScaledVector(delta, along / distance)
    .add(new THREE.Vector3(delta.y, -delta.x, 0).multiplyScalar(side * height / distance));
  const hornAngle = Math.atan2(hornEnd.y - hornY, hornEnd.x - shaft.x) - Math.atan2(15.5, side * 6);
  const rodAngle = Math.atan2(drive.y - hornEnd.y, drive.x - hornEnd.x) - Math.atan2(26.5, -side * 2.5);
  return { drive, hornEnd, hornAngle, rodAngle };
}

// Keep release reachable when contact occurs near the fully open stop.
export function releaseTravel(contact: number, maximum: number): number {
  return Math.min(contact + 2, maximum);
}
