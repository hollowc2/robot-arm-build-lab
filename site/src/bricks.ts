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

// Each course is a real plan in both horizontal axes. Empty interior cells remain
// empty; floors and roof courses tie the four walls together by stud overlap.
type BuildingStyle = { id: string; name: string; blurb: string; wall: BrickColor; roof: BrickColor; stories: number; pitched: boolean };
function building(style: BuildingStyle): BuildPreset {
  const bricks: PresetBrick[] = [];
  const width = 10, depth = 8;
  const eaves = 1 + style.stories * 4;
  const roofLayers = style.pitched ? 4 : 2;
  for (let layer = 0; layer < eaves + roofLayers; layer += 1) {
    const cells = new Map<string, BrickColor>();
    const set = (u: number, v: number, color: BrickColor) => cells.set(`${u},${v}`, color);
    if (layer === 0 || (layer > 1 && layer < eaves && (layer - 1) % 4 === 0)) {
      // Complete floor slabs, including the interior, in alternating bonded courses.
      for (let v = 0; v < depth; v++) for (let u = 0; u < width; u++) set(u, v, layer === 0 ? "gray" : "tan");
    } else if (layer < eaves) {
      for (let v = 0; v < depth; v++) for (let u = 0; u < width; u++) {
        if (u !== 0 && u !== width - 1 && v !== 0 && v !== depth - 1) continue;
        const local = (layer - 1) % 4;
        let color: BrickColor = local === 3 ? "white" : style.wall;
        // Glazed windows on all four elevations, with solid piers and white sills.
        const window = (v === 0 || v === depth - 1) ? (u === 2 || u === 3 || u === 6 || u === 7) : (v === 2 || v === 3 || v === 5);
        if (window && (local === 1 || local === 2)) color = "glass";
        if (window && local === 0) color = "white";
        // Two-stud entrance, inset behind the front wall; white lintel above.
        if (v === 0 && (u === 4 || u === 5) && layer <= 3) continue;
        set(u, v, color);
      }
      if (layer <= 3) {
        set(4, 1, "brown"); set(5, 1, layer === 3 ? "glass" : "brown");
      }
    } else {
      const roofLevel = layer - eaves;
      if (style.pitched) {
        // The first course spans the room; successive roof courses recede to a ridge.
        for (let v = roofLevel; v < depth - roofLevel; v++) for (let u = 0; u < width; u++) set(u, v, style.roof);
      } else if (roofLevel === 0) {
        for (let v = 0; v < depth; v++) for (let u = 0; u < width; u++) set(u, v, "gray");
      } else {
        for (let v = 0; v < depth; v++) for (let u = 0; u < width; u++) {
          if (u === 0 || u === width - 1 || v === 0 || v === depth - 1) {
            if (style.id !== "citadel" || (u + v) % 3 !== 1) set(u, v, style.roof);
          }
        }
      }
    }
    // Pack same-colour cells into a varied inventory, shifting seams every course.
    // Long pieces bridge the room from its supported side walls on the first roof course.
    for (let v = 0; v < depth; v++) for (let u = 0; u < width;) {
      const color = cells.get(`${u},${v}`);
      if (!color) { u++; continue; }
      const choices = (layer === 0 || layer === eaves || (layer > 1 && layer < eaves && (layer - 1) % 4 === 0)) ? [6, 4, 3, 2, 1] : (layer + v) % 2 ? [3, 1, 4, 2] : [4, 2, 3, 1];
      const length = choices.find((n) => u + n <= width && Array.from({ length: n }, (_, i) => cells.get(`${u + i},${v}`)).every((c) => c === color))!;
      const roofEdge = style.pitched && layer >= eaves && layer < eaves + roofLayers - 1 && (v === layer - eaves || v === depth - (layer - eaves) - 1);
      const wide = !(layer % 2 === 1 && v === 0) && !roofEdge && (length > 1 || (layer + v) % 2 === 0) && v + 1 < depth && Array.from({ length }, (_, i) => cells.get(`${u + i},${v + 1}`)).every((c) => c === color);
      const rotated = wide && length === 1;
      const type = rotated ? "1x2" : `${wide ? 2 : 1}x${length}` as BrickType;
      bricks.push({ type, color, cell: [u, v, layer], rotation: rotated ? 90 : 0, ...(roofEdge ? { slope: v < depth / 2 ? 1 as const : -1 as const } : {}) });
      for (let i = 0; i < length; i++) {
        cells.delete(`${u + i},${v}`);
        if (wide) cells.delete(`${u + i},${v + 1}`);
      }
      u += length;
    }
  }
  return { ...style, bricks };
}

export const buildPresets: BuildPreset[] = [
  building({ id: "pavilion", name: "Garden pavilion", blurb: "Four glazed walls · recessed entrance · green pitched roof", wall: "tan", roof: "green", stories: 1, pitched: true }),
  building({ id: "terraces", name: "Terraced monument", blurb: "Two-storey townhouse · ivory window frames · terracotta roof", wall: "yellow", roof: "orange", stories: 2, pitched: true }),
  building({ id: "skyline", name: "City skyline", blurb: "Three-storey corner building · glazed windows · gold parapet", wall: "blue", roof: "yellow", stories: 3, pitched: false }),
  building({ id: "citadel", name: "Grand citadel", blurb: "Stone gatehouse · inset oak door · four-sided battlements", wall: "white", roof: "tan", stories: 2, pitched: false }),
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
