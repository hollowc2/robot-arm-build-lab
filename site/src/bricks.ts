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

export type BrickType = "1x1" | "1x2" | "1x3" | "1x4" | "1x6" | "2x2" | "2x3" | "2x4" | "2x6";
// Width (along the jaw axis) x length (along the build line) in studs at rotation 0.
export const brickTypes: Record<BrickType, { width: number; length: number }> = {
  "1x1": { width: 1, length: 1 },
  "1x2": { width: 1, length: 2 },
  "1x3": { width: 1, length: 3 },
  "1x4": { width: 1, length: 4 },
  "1x6": { width: 1, length: 6 },
  "2x2": { width: 2, length: 2 },
  "2x3": { width: 2, length: 3 },
  "2x4": { width: 2, length: 4 },
  "2x6": { width: 2, length: 6 },
};

export const brickColors = {
  red: "#8f1209",
  blue: "#0f4f9e",
  yellow: "#e8b412",
  green: "#1d6b37",
  white: "#d9d8d2",
  orange: "#d2600f",
  tan: "#c2a66a",
  gray: "#66717b",
  brown: "#58331f",
  glass: "#9cd7e8",
} as const;
export type BrickColor = keyof typeof brickColors;

export type PresetBrick = {
  type: BrickType;
  color: BrickColor;
  // Grid cell of the brick's lowest corner: [along the build line, across it, layer].
  cell: [u: number, v: number, layer: number];
  // Quarter turns about the vertical axis; 90 swaps width and length.
  rotation: 0 | 90;
  // Roof wedges rise toward the centre of the building across the depth axis.
  slope?: 1 | -1;
};

export type BuildPreset = {
  id: string;
  name: string;
  blurb: string;
  // Listed in assembly order.
  bricks: PresetBrick[];
};

// Three open bays preserve a deep silhouette while leaving 40 mm finger lanes.
// All pickups present a two-stud face. Courses are assembled from the inside out
// at each height, never descending beside an already finished tall wall.
function architecture(id: string, name: string, blurb: string): BuildPreset {
  const bricks: PresetBrick[] = [];
  const add = (u: number, v: number, layer: number, length: 2 | 3 | 4 | 6, color: BrickColor) =>
    bricks.push({ type: `2x${length}` as BrickType, color, cell: [u, v, layer], rotation: 0 });
  const lanes = [0, -6, 6];
  const height = id === "skyline" ? 12 : id === "citadel" ? 9 : 8;
  for (let layer = 0; layer < height; layer++) for (const v of lanes) {
    if (id === "pavilion") {
      if (layer === 0) { add(0, v, layer, 4, "gray"); add(4, v, layer, 6, "gray"); }
      else if (layer < 4) { add(0, v, layer, 2, layer === 2 ? "glass" : "tan"); add(8, v, layer, 2, layer === 2 ? "glass" : "tan"); }
      else if (layer === 4) { add(0, v, layer, 4, "white"); add(4, v, layer, 6, "white"); }
      else { const inset = layer - 5; add(inset, v, layer, 4, "green"); add(inset + 4, v, layer, (layer === 7 ? 2 : 4), "green"); }
    } else if (id === "terraces") {
      const inset = Math.floor(layer / 2);
      const color = layer % 2 ? "orange" : "tan";
      if (inset === 0) { add(0, v, layer, 4, color); add(4, v, layer, 6, color); }
      else if (inset === 1) { add(1, v, layer, 4, color); add(5, v, layer, 4, color); }
      else if (inset === 2) { add(2, v, layer, 3, color); add(5, v, layer, 3, color); }
      else add(3, v, layer, 4, "yellow");
    } else if (id === "skyline") {
      const towerHeight = v === 0 ? 12 : v < 0 ? 8 : 10;
      if (layer >= towerHeight) continue;
      const color = layer === towerHeight - 1 ? "yellow" : layer % 3 === 2 ? "white" : layer % 3 === 1 ? "glass" : "blue";
      add(v === 0 ? 2 : 0, v, layer, 4, color);
      if (v !== 0) add(6, v, layer, 4, color);
    } else {
      if (layer === 0 || layer === 4 || layer === 6) { add(0, v, layer, 4, layer === 0 ? "gray" : "tan"); add(4, v, layer, 6, "tan"); }
      else if (layer < 7) { add(0, v, layer, 2, "white"); add(8, v, layer, 2, "white"); }
      else { add(0, v, layer, 2, "tan"); add(4, v, layer, 2, "tan"); add(8, v, layer, 2, "tan"); }
    }
  }
  return { id, name, blurb, bricks };
}

export const buildPresets: BuildPreset[] = [
  architecture("pavilion", "Garden pavilion", "Open glazed colonnade · ivory lintels · stepped green gables"),
  architecture("terraces", "Terraced monument", "Four receding terraces · sandstone bands · terracotta steps"),
  architecture("skyline", "City skyline", "Five staggered towers · glazed façades · gold crowns"),
  architecture("citadel", "Grand citadel", "Triple gate arcade · stone towers · raised battlements"),
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
