import type { BuildPreset, PresetBrick, BrickType, BrickColor } from "./bricks";
const brick = (type: BrickType, color: BrickColor, u: number, layer: number, rotation: 0 | 90 = 0, v = 0): PresetBrick => ({type, color, cell: [u, v, layer], rotation});
// Layouts with clearance for the plain CAD jaws.
export const plainGripperPresets: BuildPreset[] = [
  {
    id: "wall",
    name: "Small wall",
    blurb: "Running bond, four courses",
    bricks: [
      brick("2x4", "red", 0, 0), brick("2x4", "red", 4, 0),
      brick("2x2", "orange", 0, 1), brick("2x4", "orange", 2, 1), brick("2x2", "orange", 6, 1),
      brick("2x4", "red", 0, 2), brick("2x4", "red", 4, 2),
      brick("2x2", "orange", 0, 3), brick("2x4", "orange", 2, 3), brick("2x2", "orange", 6, 3),
    ],
  },
  {
    id: "stairs",
    name: "Staircase",
    blurb: "Five steps up",
    bricks: [
      brick("2x4", "blue", 0, 0), brick("2x4", "blue", 4, 0), brick("2x2", "blue", 8, 0),
      brick("2x4", "blue", 2, 1), brick("2x4", "blue", 6, 1),
      brick("2x2", "blue", 4, 2), brick("2x4", "blue", 6, 2),
      brick("2x4", "white", 6, 3),
      brick("1x2", "white", 8, 4, 90), brick("1x2", "white", 9, 4, 90),
    ],
  },
  {
    id: "pyramid",
    name: "Pyramid",
    blurb: "Stepped, five layers",
    bricks: [
      brick("2x4", "tan", 0, 0), brick("2x2", "tan", 4, 0), brick("2x4", "tan", 6, 0),
      brick("2x4", "yellow", 1, 1), brick("2x4", "yellow", 5, 1),
      brick("2x3", "orange", 2, 2), brick("2x3", "orange", 5, 2),
      brick("2x4", "red", 3, 3),
      brick("2x2", "red", 4, 4),
    ],
  },
  {
    id: "house",
    name: "Little house",
    blurb: "Doorway, lintel and gable",
    bricks: [
      brick("2x4", "white", 0, 0), brick("2x4", "white", 6, 0),
      brick("2x4", "white", 0, 1), brick("2x4", "white", 6, 1),
      brick("2x3", "white", 0, 2), brick("2x4", "tan", 3, 2), brick("2x3", "white", 7, 2),
      brick("2x4", "red", 1, 3), brick("2x4", "red", 5, 3),
      brick("2x3", "red", 2, 4), brick("2x3", "red", 5, 4),
      brick("2x4", "red", 3, 5),
      brick("2x2", "green", 4, 6),
    ],
  },
];
