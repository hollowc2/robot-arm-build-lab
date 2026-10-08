import * as THREE from "three";
import { downTilt, homePose, solveStraightDown, type ArmModel, type JointAngles } from "./arm.ts";
import { wristPosition } from "./assembly.ts";
import {
  brickHeight,
  brickLabel,
  brickPlay,
  footprint,
  studHeight,
  studPitch,
  validateLayout,
  type BuildPreset,
  type PresetBrick,
} from "./bricks.ts";

// The grip point (centre of the finger pads) sits this far above a held brick's centre, so the
// fingertips stay above the brick's lower edge and clear of the studs on the layer beneath.
export const gripAboveCenter = 9;
// Jaw travel used while approaching and releasing: 3 mm of air either side of a 20 mm brick.
export const openTravel = 30;
// The brick hovers this far above its studs before the final press.
export const alignHeight = 5;
// Carry the held brick at least this far above everything already built.
export const carryClearance = 16;

// Bricks are built along a line the gripper can follow with the base held still, so every
// brick keeps the same yaw relative to the jaws and lands square on the grid. Angles follow the
// base joint: degrees clockwise from +Y, seen from above.
export const buildSite = { baseAngle: 222, start: 175 };
// Supply bricks wait on two arcs in front of the arm, picked in assembly order.
export const supplyLayout = { centerAngle: 138, radii: [190, 255], spacing: 42 };
// Replenish this bounded tray between batches instead of wrapping hundreds of
// simultaneously waiting bricks around the arm and through the build site.
export const supplyBatchSize = 12;
export const supplyBatch = (index: number) => Math.floor(index / supplyBatchSize);

export type BuildStage = "approach" | "lower" | "grip" | "lift" | "carry" | "align" | "place" | "release" | "retract" | "park";
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

export type BrickPose = { position: THREE.Vector3; quaternion: THREE.Quaternion };
export type PlannedBrick = {
  index: number;
  entry: PresetBrick;
  label: string;
  // Full body size in the brick frame: x across the build line, y along it, z up (no studs).
  size: THREE.Vector3;
  studs: { u: number; v: number };
  supply: BrickPose;
  target: BrickPose;
};
export type BuildStep = {
  brick: number;
  stage: BuildStage;
  label: string;
  target: JointAngles;
  dwell: number;
  // Vertical moves follow this straight line of grip points instead of a joint-space line.
  line?: [THREE.Vector3, THREE.Vector3];
};
export type BuildPlan = { preset: BuildPreset; bricks: PlannedBrick[]; steps: BuildStep[]; problems: string[] };

// Upright boxes only ever rotate about Z here, which keeps overlap tests to a 2D SAT check.
export type UprightBox = { center: THREE.Vector3; yaw: number; half: THREE.Vector3 };

export function boxesOverlap(a: UprightBox, b: UprightBox, margin = 0.05) {
  if (Math.abs(a.center.z - b.center.z) >= a.half.z + b.half.z - margin) return false;
  const dx = b.center.x - a.center.x;
  const dy = b.center.y - a.center.y;
  for (const yaw of [a.yaw, a.yaw + Math.PI / 2, b.yaw, b.yaw + Math.PI / 2]) {
    const ax = Math.cos(yaw);
    const ay = Math.sin(yaw);
    const reach = (box: UprightBox) => box.half.x * Math.abs(Math.cos(box.yaw) * ax + Math.sin(box.yaw) * ay)
      + box.half.y * Math.abs(-Math.sin(box.yaw) * ax + Math.cos(box.yaw) * ay);
    if (Math.abs(dx * ax + dy * ay) >= reach(a) + reach(b) - margin) return false;
  }
  return true;
}

const yawOf = (quaternion: THREE.Quaternion) => {
  const axis = new THREE.Vector3(1, 0, 0).applyQuaternion(quaternion);
  return Math.atan2(axis.y, axis.x);
};

// A brick's solid, including the studs on top, as an upright box.
export function brickBox(brick: Pick<PlannedBrick, "size">, pose: BrickPose): UprightBox {
  const half = brick.size.clone().multiplyScalar(0.5);
  half.z += studHeight / 2;
  return { center: pose.position.clone().add(new THREE.Vector3(0, 0, studHeight / 2)), yaw: yawOf(pose.quaternion), half };
}

// Conservative envelopes of the gripper below the wrist, measured from the CAD fingers at
// up to 30 mm of travel, in grip-point offsets: across the jaws, along the arm, and vertical.
const gripperEnvelopes = [
  { across: [10.2, 28.5], along: [-4, 5], vertical: [-12.7, 29] }, // each finger
  { across: [-27, 27], along: [-30, 2.5], vertical: [34, 140] }, // servo body and linkage
] as const;

export function gripperBoxes(gripPosition: THREE.Vector3, gripQuaternion: THREE.Quaternion, extendUp = 0): UprightBox[] {
  const across = new THREE.Vector3(1, 0, 0).applyQuaternion(gripQuaternion).setZ(0).normalize();
  const along = new THREE.Vector3(0, 0, 1).applyQuaternion(gripQuaternion).setZ(0).normalize();
  const yaw = Math.atan2(across.y, across.x);
  const box = (acrossRange: readonly number[], alongRange: readonly number[], vertical: readonly number[]): UprightBox => {
    const top = vertical[1] + extendUp;
    return {
      center: gripPosition.clone()
        .addScaledVector(across, (acrossRange[0] + acrossRange[1]) / 2)
        .addScaledVector(along, (alongRange[0] + alongRange[1]) / 2)
        .add(new THREE.Vector3(0, 0, (vertical[0] + top) / 2)),
      yaw,
      half: new THREE.Vector3((acrossRange[1] - acrossRange[0]) / 2, (alongRange[1] - alongRange[0]) / 2, (top - vertical[0]) / 2),
    };
  };
  const [finger, body] = gripperEnvelopes;
  return [
    box(finger.across, finger.along, finger.vertical),
    box([-finger.across[1], -finger.across[0]], finger.along, finger.vertical),
    box(body.across, body.along, body.vertical),
  ];
}

const siteAxes = () => {
  const angle = THREE.MathUtils.degToRad(buildSite.baseAngle);
  return {
    along: new THREE.Vector3(Math.sin(angle), Math.cos(angle), 0),
    across: new THREE.Vector3(Math.cos(angle), -Math.sin(angle), 0),
  };
};

// The gripper is centered over the base axis (master_assembly.py), so the grip point follows the
// base's radial line. Keep this in step with the wrist's sideways position.
const armSideOffset = wristPosition[0];

export function targetPose(entry: PresetBrick): BrickPose {
  const { along, across } = siteAxes();
  const studs = footprint(entry);
  const [u, v, layer] = entry.cell;
  const position = new THREE.Vector3()
    .addScaledVector(across, armSideOffset + ((v + studs.v / 2) - 1) * studPitch)
    .addScaledVector(along, buildSite.start + (u + studs.u / 2) * studPitch)
    .setZ(layer * brickHeight + brickHeight / 2);
  const quaternion = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), Math.atan2(across.y, across.x));
  return { position, quaternion };
}

function supplySlots(count: number) {
  const capacity = Math.min(count, supplyBatchSize);
  const inner = Math.ceil(capacity / 2);
  return Array.from({ length: count }, (_, index) => {
    const trayIndex = index % capacity;
    const ring = trayIndex < inner ? 0 : 1;
    const slots = ring === 0 ? inner : capacity - inner;
    const slot = ring === 0 ? trayIndex : trayIndex - inner;
    const radius = supplyLayout.radii[ring];
    const step = THREE.MathUtils.radToDeg(supplyLayout.spacing / radius);
    const angle = THREE.MathUtils.degToRad(supplyLayout.centerAngle + (slot - (slots - 1) / 2) * step);
    const across = new THREE.Vector3(Math.cos(angle), -Math.sin(angle), 0);
    const along = new THREE.Vector3(Math.sin(angle), Math.cos(angle), 0);
    return across.multiplyScalar(armSideOffset).addScaledVector(along, radius).setZ(brickHeight / 2);
  });
}

export function planBuild(preset: BuildPreset, arm: ArmModel): BuildPlan {
  const problems = validateLayout(preset);
  const up = (point: THREE.Vector3, height: number) => point.clone().setZ(height);
  const gripAt = (center: THREE.Vector3) => center.clone().add(new THREE.Vector3(0, 0, gripAboveCenter));
  let previous: JointAngles = { ...homePose };
  const solve = (point: THREE.Vector3, gripper: number, what: string) => {
    // Most build moves use the same straight-down elbow branch. The exact IK
    // avoids numerical searches for thousands of poses in a large preset.
    const pose = solveStraightDown(point, gripper, arm.root.position.z, Math.sign(previous.elbow) || -1)
      ?? arm.solve(point, gripper, previous);
    const miss = arm.probe(pose).distanceTo(point);
    if (miss > 0.05 || Math.abs(downTilt(pose)) > 0.05) problems.push(`${what} is out of reach (${miss.toFixed(1)} mm short)`);
    previous = pose;
    return pose;
  };

  const slots = supplySlots(preset.bricks.length);
  const bricks: PlannedBrick[] = [];
  const steps: BuildStep[] = [];
  const placed: UprightBox[] = [];
  const gripPosition = new THREE.Vector3();
  const pickQuaternion = new THREE.Quaternion();
  const placeQuaternion = new THREE.Quaternion();

  preset.bricks.forEach((entry, index) => {
    const label = brickLabel(entry);
    const name = `${preset.name} brick ${index + 1} (${label})`;
    const studs = footprint(entry);
    const size = new THREE.Vector3(studs.v * studPitch - 2 * brickPlay, studs.u * studPitch - 2 * brickPlay, brickHeight);
    const target = targetPose(entry);
    const supplyCenter = slots[index];
    const top = Math.max(studHeight + brickHeight, ...placed.map((box) => box.center.z + box.half.z), target.position.z + brickHeight / 2 + studHeight);
    const travel = top + carryClearance + brickHeight / 2 + gripAboveCenter;

    const pick = gripAt(supplyCenter);
    const place = gripAt(target.position);
    let from: THREE.Vector3 | null = null;
    const add = (stage: BuildStage, point: THREE.Vector3, gripper: number, dwell = 0) => {
      const pose = solve(point, gripper, `${name} ${stage}`);
      const what = stage === "retract" ? "the structure" : `the ${label}`;
      const vertical = from && from.distanceTo(point) > 0 && Math.hypot(from.x - point.x, from.y - point.y) < 1e-6;
      steps.push({ brick: index, stage, label: `${stageVerbs[stage]} ${what}`, target: pose, dwell, ...(vertical ? { line: [from!, point.clone()] as [THREE.Vector3, THREE.Vector3] } : {}) });
      from = point.clone();
      return pose;
    };
    add("approach", up(pick, travel), openTravel);
    const pickPose = add("lower", pick, openTravel, 0.1);
    add("grip", pick, 0, 0.35);
    add("lift", up(pick, travel), 0);
    add("carry", up(place, travel), 0);
    add("align", up(place, place.z + alignHeight), 0, 0.25);
    const placePose = add("place", place, 0, 0.15);
    add("release", place, openTravel, 0.2);
    add("retract", up(place, travel), openTravel);

    // No wrist roll: the brick keeps its yaw relative to the jaws, so the supply brick is laid
    // out pre-turned by however far the base swings between picking and placing.
    arm.gripQuaternion(pickPose, pickQuaternion);
    arm.gripQuaternion(placePose, placeQuaternion);
    const supply: BrickPose = {
      position: supplyCenter,
      quaternion: pickQuaternion.clone().multiply(placeQuaternion.clone().invert()).multiply(target.quaternion),
    };
    const planned: PlannedBrick = { index, entry, label, size, studs, supply, target };
    bricks.push(planned);

    // Check the vertical corridor the held brick and open fingers drop through at each end.
    arm.probe(placePose);
    arm.grip.getWorldPosition(gripPosition);
    // The studs beneath slot into the brick's hollow underside, so start the corridor above them.
    const corridor = brickBox(planned, target);
    const corridorBottom = target.position.z - brickHeight / 2 + studHeight;
    const corridorTop = travel - gripAboveCenter + brickHeight / 2 + studHeight;
    corridor.center.z = (corridorBottom + corridorTop) / 2;
    corridor.half.z = (corridorTop - corridorBottom) / 2;
    const placeBlockers = placed.filter((box) => boxesOverlap(box, corridor)
      || gripperBoxes(gripPosition, placeQuaternion, travel - place.z).some((part) => boxesOverlap(box, part)));
    if (placeBlockers.length) problems.push(`${name}: the gripper would hit ${placeBlockers.length} placed brick(s) on the way down`);
    placed.push(brickBox(planned, target));
  });

  // Pickups have to clear every brick still waiting in the supply.
  bricks.forEach((brick, index) => {
    const pickStep = steps.find((step) => step.brick === index && step.stage === "lower")!;
    arm.probe(pickStep.target);
    arm.grip.getWorldPosition(gripPosition);
    arm.grip.getWorldQuaternion(pickQuaternion);
    const fingers = gripperBoxes(gripPosition, pickQuaternion, 200);
    const hits = bricks.slice(index + 1).filter((other) => supplyBatch(other.index) === supplyBatch(index)
      && fingers.some((part) => boxesOverlap(part, brickBox(other, other.supply))));
    if (hits.length) problems.push(`${preset.name} brick ${index + 1}: the open fingers would hit supply brick ${hits[0].index + 1}`);
  });

  steps.push({ brick: preset.bricks.length - 1, stage: "park", label: stageVerbs.park, target: { ...homePose, gripper: 0 }, dwell: 0 });
  return { preset, bricks, steps, problems };
}

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
