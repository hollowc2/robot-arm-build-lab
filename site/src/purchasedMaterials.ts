import * as THREE from "three";

export const nema17Finishes = ["motor_case", "motor_stack", "motor_connector", "steel"] as const;
export const byj48Finishes = ["byj_can", "brass", "byj_blue", "wire_blue", "wire_pink", "wire_yellow", "wire_orange", "wire_red"] as const;
export const sg90Finishes = ["servo_blue", "nylon", "servo_label", "wire_brown", "wire_red", "wire_orange"] as const;
export type Finish = typeof nema17Finishes[number] | typeof byj48Finishes[number] | typeof sg90Finishes[number];

export function purchasedMaterials(reflections: THREE.Texture): Record<Finish, THREE.MeshStandardMaterial> {
  const metal = (color: string, roughness: number, metalness = 1) => new THREE.MeshStandardMaterial({ color, roughness, metalness, envMap: reflections });
  const plastic = (color: string, roughness = 0.4) => new THREE.MeshStandardMaterial({ color, roughness, metalness: 0, envMap: reflections, envMapIntensity: 0.4 });
  const label = document.createElement("canvas");
  label.width = 512;
  label.height = 320;
  const ctx = label.getContext("2d")!;
  ctx.fillStyle = "#151717";
  ctx.fillRect(0, 0, 512, 320);
  ctx.strokeStyle = "#ccb165";
  ctx.lineWidth = 9;
  ctx.strokeRect(12, 12, 488, 296);
  ctx.fillStyle = "#ead797";
  ctx.textAlign = "center";
  ctx.font = "bold 64px Arial";
  ctx.fillText("TOWER PRO", 256, 90);
  ctx.font = "36px Arial";
  ctx.fillText("Micro Servo 9g", 256, 155);
  ctx.font = "bold 94px Arial";
  ctx.fillText("SG90", 256, 263);
  const map = new THREE.CanvasTexture(label);
  map.colorSpace = THREE.SRGBColorSpace;
  return {
    motor_case: Object.assign(metal("#1c1e21", 0.42, 0.6), { envMapIntensity: 0.7 }),
    motor_stack: metal("#aeb3b8", 0.36, 0.9),
    motor_connector: plastic("#eee8d8", 0.6),
    steel: Object.assign(metal("#eef1f4", 0.16), { envMapIntensity: 1.2 }),
    byj_can: metal("#c4cad0", 0.32, 0.85),
    brass: metal("#c6a05a", 0.25),
    byj_blue: plastic("#1765b5", 0.32),
    // Glossy blue moulding with clearcoat highlights on the gearbox lid.
    servo_blue: new THREE.MeshPhysicalMaterial({ color: "#1559d1", roughness: 0.23, metalness: 0, clearcoat: 0.7, clearcoatRoughness: 0.2, envMap: reflections }),
    nylon: plastic("#f4efe1", 0.48),
    servo_label: new THREE.MeshStandardMaterial({ map, roughness: 0.48, metalness: 0 }),
    wire_blue: plastic("#2275ce"),
    wire_pink: plastic("#ef82b4"),
    wire_yellow: plastic("#f4cb36"),
    wire_orange: plastic("#ed761b"),
    wire_red: plastic("#c92b30"),
    wire_brown: plastic("#613e2c"),
  };
}

export function prepareFinishGeometry(geometry: THREE.BufferGeometry, finish: Finish) {
  if (finish !== "servo_label") return;
  // Sticker plates lie on the case's +/-X faces. Y/Z share the same range for both installed servos.
  geometry.computeBoundingBox();
  const box = geometry.boundingBox!;
  const position = geometry.getAttribute("position");
  const normal = geometry.getAttribute("normal");
  const uv = new Float32Array(position.count * 2);
  for (let i = 0; i < position.count; i++) {
    const u = (position.getY(i) - box.min.y) / (box.max.y - box.min.y);
    uv[i * 2] = normal.getX(i) < 0 ? u : 1 - u;
    uv[i * 2 + 1] = (position.getZ(i) - box.min.z) / (box.max.z - box.min.z);
  }
  geometry.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
}
