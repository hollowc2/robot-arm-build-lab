import * as THREE from "three";
import { downTilt, homePose, solveStraightDown, type ArmModel, type JointAngles } from "./arm.ts";
import type { BuildPreset, PresetBrick } from "./bricks.ts";
import type { BuildPlan, BuildStage, BuildStep, PlannedBrick } from "./buildPlan.ts";
import { gripAboveCenter, openTravel, stageVerbs } from "./waypoints.ts";

export const sortColors = ["red", "blue", "yellow"] as const;
export const sortPalette: Record<string, string> = { red: "#8f1209", blue: "#0f4f9e", yellow: "#e8b412" };
export const sortBlockSize = 24;
export const sortCount = sortColors.length * 2;
export const sortZoneAngle = (color: number) => 60 + color * 120;
export function radialPoint(angle: number, radius: number, z: number) {
  const radians = THREE.MathUtils.degToRad(angle);
  return new THREE.Vector3(-Math.sin(radians) * radius, Math.cos(radians) * radius, z);
}

// Delivery checks use the clear interior of the actual receiving tray, allowing
// a loose block to settle at any yaw rather than requiring a LEGO stud alignment.
export function insideSortBin(color: string, position: THREE.Vector3, quaternion: THREE.Quaternion, size: THREE.Vector3): boolean {
  const index = sortColors.indexOf(color as typeof sortColors[number]);
  if (index < 0) return false;
  const inverse = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), -THREE.MathUtils.degToRad(sortZoneAngle(index)));
  const local = position.clone().sub(radialPoint(sortZoneAngle(index), 300, 0)).applyQuaternion(inverse);
  const rotation = new THREE.Matrix4().makeRotationFromQuaternion(inverse.multiply(quaternion));
  const e = rotation.elements;
  const half = size.clone().multiplyScalar(0.5);
  const extentX = Math.abs(e[0]) * half.x + Math.abs(e[4]) * half.y + Math.abs(e[8]) * half.z;
  const extentY = Math.abs(e[1]) * half.x + Math.abs(e[5]) * half.y + Math.abs(e[9]) * half.z;
  return Math.abs(local.x) + extentX <= 64 && Math.abs(local.y) + extentY <= 34
    && local.z >= half.z - 2 && local.z <= half.z + 5;
}

// Shuffle colors between six fixed, evenly spaced pickup slots.
// Keeping the objects upright lets the arm without wrist roll grasp them squarely.
export function planSort(arm: ArmModel, random = Math.random): BuildPlan {
  const colors = [...sortColors, ...sortColors];
  for (let i = colors.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [colors[i], colors[j]] = [colors[j], colors[i]];
  }
  const entries: PresetBrick[] = colors.map((color, index) => ({ type: "2x2", color, cell: [index * 4, 0, 0], rotation: 0 }));
  const preset: BuildPreset = { id: "sort", name: "Sorting factory", blurb: "Six foam blocks · three color bins", bricks: entries };
  const bricks: PlannedBrick[] = [];
  const steps: BuildStep[] = [];
  const problems: string[] = [];
  const counts = new Map<string, number>();
  let previous: JointAngles = { ...homePose };
  entries.forEach((entry, index) => {
    const colorIndex = sortColors.indexOf(entry.color as typeof sortColors[number]);
    const slot = counts.get(entry.color) ?? 0;
    counts.set(entry.color, slot + 1);
    const supplyCenter = radialPoint(index * 60, 240, sortBlockSize / 2);
    const targetCenter = radialPoint(sortZoneAngle(colorIndex) + (slot ? 8 : -8), 300, sortBlockSize / 2);
    const pick = supplyCenter.clone().add(new THREE.Vector3(0, 0, gripAboveCenter));
    const place = targetCenter.clone().add(new THREE.Vector3(0, 0, gripAboveCenter));
    let from: THREE.Vector3 | null = null;
    const label = `${entry.color} foam block`;
    const add = (stage: BuildStage, point: THREE.Vector3, gripper: number, dwell = 0) => {
      const pose = solveStraightDown(point, gripper, arm.root.position.z, -1) ?? arm.solve(point, gripper, previous);
      if (arm.probe(pose).distanceTo(point) > 0.05 || Math.abs(downTilt(pose)) > 0.05) problems.push(`${label}: ${stage} is out of reach`);
      previous = pose;
      const vertical = from && from.distanceTo(point) > 0 && Math.hypot(from.x - point.x, from.y - point.y) < 1e-6;
      steps.push({ brick: index, stage, label: `${stageVerbs[stage]} ${label}`, target: pose, dwell, ...(vertical ? { line: [from!, point.clone()] as [THREE.Vector3, THREE.Vector3] } : {}) });
      from = point.clone();
      return pose;
    };
    const high = (point: THREE.Vector3) => point.clone().setZ(70);
    add("approach", high(pick), openTravel);
    const pickPose = add("lower", pick, openTravel, 0.1);
    add("grip", pick, 0, 0.35);
    add("lift", high(pick), 0);
    add("carry", high(place), 0);
    add("align", place.clone().add(new THREE.Vector3(0, 0, 5)), 0, 0.15);
    const placePose = add("place", place, 0, 0.15);
    add("release", place, openTravel, 0.2);
    add("retract", high(place), openTravel);
    const targetQuaternion = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), -THREE.MathUtils.degToRad(placePose.base));
    const supplyQuaternion = arm.gripQuaternion(pickPose).multiply(arm.gripQuaternion(placePose).invert()).multiply(targetQuaternion);
    bricks.push({ index, entry, label, size: new THREE.Vector3(sortBlockSize, sortBlockSize, sortBlockSize), studs: { u: 0, v: 0 },
      supply: { position: supplyCenter, quaternion: supplyQuaternion },
      target: { position: targetCenter, quaternion: targetQuaternion },
    });
  });
  steps.push({ brick: sortCount - 1, stage: "park", label: "Returning home", target: { ...homePose, gripper: openTravel }, dwell: 0 });
  return { preset, bricks, steps, problems };
}
