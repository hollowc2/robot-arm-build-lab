import * as THREE from "three";
import { solveStraightDown } from "./arm.ts";
import type { BuildStage, BuildStep } from "./buildPlan.ts";

// Keep the finger pads above the lower edge of a held block during pickup and release.
export const gripAboveCenter = 9;
// Additional jaw travel while approaching and releasing.
export const openTravel = 30;
export const stageVerbs: Record<BuildStage, string> = {
  approach: "Approaching",
  lower: "Lowering onto",
  grip: "Gripping",
  lift: "Lifting",
  carry: "Carrying",
  align: "Aligning",
  place: "Placing",
  release: "Releasing",
  retract: "Retracting from",
  park: "Returning home",
};

// Joint poses along a step's straight line, for ArmDriver.moveTo. Closed-form IK keeps this cheap
// enough to evaluate every fixed step.
export function followLine(step: BuildStep, lift: number) {
  if (!step.line) return undefined;
  const [from, to] = step.line;
  const point = new THREE.Vector3();
  const elbowSign = Math.sign(step.target.elbow) || -1;
  return (progress: number) => (progress >= 1
    ? step.target
    : solveStraightDown(point.lerpVectors(from, to, progress), step.target.gripper, lift, elbowSign) ?? step.target);
}
