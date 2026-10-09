import * as THREE from "three";
import { downTilt, homePose, solveStraightDown, type ArmModel, type JointAngles } from "./arm.ts";
import { brickHeight, type BuildPreset, type PresetBrick } from "./bricks.ts";
import { gripAboveCenter, openTravel, stageVerbs, type BuildPlan, type BuildStage, type BuildStep, type PlannedBrick } from "./buildPlan.ts";

export const sortColors = ["red", "blue", "yellow", "green"] as const;
export const sortCount = sortColors.length * 2;
export const sortZoneAngle = (color: number) => 45 + color * 90;
export function radialPoint(angle: number, radius: number, z: number) {
  const radians = THREE.MathUtils.degToRad(angle);
  return new THREE.Vector3(-Math.sin(radians) * radius, Math.cos(radians) * radius, z);
}

// Shuffle colors between clear pickup slots; a little angular jitter changes each round.
// Keeping the objects upright lets the arm without wrist roll grasp them squarely.
export function planSort(arm: ArmModel, random = Math.random): BuildPlan {
  const colors = [...sortColors, ...sortColors];
  for (let i = colors.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [colors[i], colors[j]] = [colors[j], colors[i]];
  }
  const entries: PresetBrick[] = colors.map((color, index) => ({ type: "2x2", color, cell: [index * 4, 0, 0], rotation: 0 }));
  const preset: BuildPreset = { id: "sort", name: "Color sorting", blurb: "Eight scattered objects · four color zones", bricks: entries };
  const bricks: PlannedBrick[] = [];
  const steps: BuildStep[] = [];
  const problems: string[] = [];
  const counts = new Map<string, number>();
  let previous: JointAngles = { ...homePose };
  entries.forEach((entry, index) => {
    const colorIndex = sortColors.indexOf(entry.color as typeof sortColors[number]);
    const slot = counts.get(entry.color) ?? 0;
    counts.set(entry.color, slot + 1);
    const supplyCenter = radialPoint(index * 45 + (random() - 0.5) * 8, 240, brickHeight / 2);
    const targetCenter = radialPoint(sortZoneAngle(colorIndex) + (slot ? 8 : -8), 300, brickHeight / 2);
    const pick = supplyCenter.clone().add(new THREE.Vector3(0, 0, gripAboveCenter));
    const place = targetCenter.clone().add(new THREE.Vector3(0, 0, gripAboveCenter));
    let from: THREE.Vector3 | null = null;
    const label = `${entry.color} object`;
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
    bricks.push({ index, entry, label, size: new THREE.Vector3(19.8, 19.8, brickHeight), studs: { u: 2, v: 2 },
      supply: { position: supplyCenter, quaternion: supplyQuaternion },
      target: { position: targetCenter, quaternion: targetQuaternion },
    });
  });
  steps.push({ brick: sortCount - 1, stage: "park", label: "Returning home", target: { ...homePose, gripper: openTravel }, dwell: 0 });
  return { preset, bricks, steps, problems };
}
