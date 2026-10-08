// Interlocking-brick presets as plain data, plus the rules every layout has to satisfy.
//
// Bricks are 1.25x the classic toy-brick module so a two-stud brick (20 mm) fits the SG90
// gripper's mouth with about 3 mm to spare on each side when the jaws are opened to 30 mm.

export const studPitch = 10; // mm between stud centres
export const brickHeight = 12; // mm, without studs
export const studRadius = 3;
export const studHeight = 2;
// Real bricks are a hair under their nominal size so neighbours slide past each other.
export const brickPlay = 0.1;
// The jaws can only squeeze a brick across this many studs.
export const maxGripStuds = 2;

export type BrickType = "1x2" | "2x2" | "2x3" | "2x4";
// Width (along the jaw axis) x length (along the build line) in studs at rotation 0.
export const brickTypes: Record<BrickType, { width: number; length: number }> = {
  "1x2": { width: 1, length: 2 },
  "2x2": { width: 2, length: 2 },
  "2x3": { width: 2, length: 3 },
  "2x4": { width: 2, length: 4 },
};

export const brickColors = {
  red: "#8f1209",
  blue: "#0f4f9e",
  yellow: "#e8b412",
  green: "#1d6b37",
  white: "#d9d8d2",
  orange: "#d2600f",
  tan: "#c2a66a",
} as const;
export type BrickColor = keyof typeof brickColors;

export type PresetBrick = {
  type: BrickType;
  color: BrickColor;
  // Grid cell of the brick's lowest corner: [along the build line, across it, layer].
  cell: [u: number, v: number, layer: number];
  // Quarter turns about the vertical axis; 90 swaps width and length.
  rotation: 0 | 90;
};

export type BuildPreset = {
  id: string;
  name: string;
  blurb: string;
  // Listed in assembly order.
  bricks: PresetBrick[];
};

const brick = (type: BrickType, color: BrickColor, u: number, layer: number, rotation: 0 | 90 = 0, v = 0): PresetBrick => ({
  type, color, cell: [u, v, layer], rotation,
});

// Open rows leave room for the real finger pads. Each column clutches the course
// below; the baseplate ties the rows together. These are volumetric structures,
// with depth as well as height, rather than longer versions of the small wall.
function sculpture(id: string, name: string, blurb: string, heights: number[][], colors: BrickColor[]): BuildPreset {
  const bricks: PresetBrick[] = [];
  const layers = Math.max(...heights.flat());
  for (let layer = 0; layer < layers; layer += 1) {
    heights.forEach((row, v) => row.forEach((height, u) => {
      if (layer < height) bricks.push(brick("2x2", colors[layer % colors.length], u * 2, layer, 0, (v - (heights.length - 1) / 2) * 4));
    }));
  }
  return { id, name, blurb, bricks };
}

export const buildPresets: BuildPreset[] = [
  sculpture("pavilion", "Garden pavilion", "Two open colonnades · five courses", [
    [5, 5, 5, 5, 5], [5, 5, 5, 5, 5],
  ], ["white", "tan", "green"]),
  sculpture("terraces", "Terraced monument", "Four stepped terraces with finger-clearance lanes", [
    [4, 4, 5, 4, 4], [5, 6, 7, 6, 5], [5, 6, 7, 6, 5], [4, 4, 5, 4, 4],
  ], ["tan", "yellow", "orange", "red"]),
  sculpture("skyline", "City skyline", "Three streets of rising towers", [
    [7, 9, 12, 9, 7], [10, 12, 18, 12, 10], [7, 9, 12, 9, 7],
  ], ["blue", "white"]),
  sculpture("citadel", "Grand citadel", "Five open avenues around a central keep", [
    [10, 10, 10, 10, 10], [9, 10, 12, 10, 9], [8, 10, 14, 10, 8],
    [9, 10, 12, 10, 9], [10, 10, 10, 10, 10],
  ], ["white", "blue", "blue", "tan", "tan"]),
];

// Studs along (u) and across (v) the build line once the rotation is applied.
export function footprint({ type, rotation }: Pick<PresetBrick, "type" | "rotation">) {
  const { width, length } = brickTypes[type];
  return rotation === 90 ? { u: width, v: length } : { u: length, v: width };
}

export function brickLabel({ type, color }: Pick<PresetBrick, "type" | "color">) {
  return `${color} ${type.replace("x", "×")}`;
}

export function brickCells(entry: PresetBrick) {
  const { u, v } = footprint(entry);
  const cells: string[] = [];
  for (let du = 0; du < u; du += 1) {
    for (let dv = 0; dv < v; dv += 1) cells.push(`${entry.cell[0] + du},${entry.cell[1] + dv},${entry.cell[2]}`);
  }
  return cells;
}

// Grid-level rules: whole studs, no overlaps, every brick clutches something placed before
// it (or the baseplate), nothing is placed beneath an existing brick, and every brick can be
// squeezed across the jaws. Reach and clearance depend on the arm and are checked by the planner.
export function validateLayout(preset: BuildPreset): string[] {
  const problems: string[] = [];
  const occupied = new Map<string, number>();
  preset.bricks.forEach((entry, index) => {
    const name = `${preset.name} brick ${index + 1} (${brickLabel(entry)})`;
    const [u, v, layer] = entry.cell;
    if (!brickTypes[entry.type]) problems.push(`${name}: unknown brick type`);
    if (![u, v, layer].every(Number.isInteger) || layer < 0) problems.push(`${name}: must sit on whole studs at layer 0 or above`);
    if (footprint(entry).v > maxGripStuds) problems.push(`${name}: ${footprint(entry).v} studs across is wider than the gripper can squeeze`);
    const cells = brickCells(entry);
    for (const cell of cells) {
      const other = occupied.get(cell);
      if (other !== undefined) problems.push(`${name}: overlaps brick ${other + 1}`);
    }
    if (layer > 0) {
      const below = cells.map((cell) => cell.replace(/,(\d+)$/, `,${layer - 1}`));
      if (!below.some((cell) => occupied.has(cell))) problems.push(`${name}: nothing placed beneath it to clutch`);
    }
    const above = cells.map((cell) => cell.replace(/,(\d+)$/, `,${layer + 1}`));
    const blocker = above.map((cell) => occupied.get(cell)).find((other) => other !== undefined);
    if (blocker !== undefined) problems.push(`${name}: brick ${blocker + 1} above it was placed first`);
    cells.forEach((cell) => occupied.set(cell, index));
  });
  return problems;
}
