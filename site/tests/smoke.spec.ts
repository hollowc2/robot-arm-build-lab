import { expect, type Locator, test } from "@playwright/test";

test("landing page runs the simulator and part viewer", async ({ page }) => {
  // Loads ~12 MB of meshes and runs physics on software WebGL in CI.
  test.setTimeout(150_000);
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: /Robot Arm/ })).toBeVisible();

  const hero = page.locator("#simulator");
  await expect(hero).toHaveAttribute("data-meshes", "35", { timeout: 30_000 });
  await expect(hero).toHaveAttribute("data-mode", "autopilot");

  const readouts = hero.locator(".joint-readout");
  await hero.getByRole("button", { name: "Home" }).click();
  await expect(hero).toHaveAttribute("data-mode", "manual");
  await expect(readouts.nth(1)).toHaveText("0°", { timeout: 15_000 });
  await expect(readouts.nth(2)).toHaveText("0°", { timeout: 15_000 });
  await page.getByLabel("Shoulder").fill("45");
  await expect(readouts.nth(1)).toHaveText("45°", { timeout: 15_000 });

  await hero.getByRole("button", { name: "Reset blocks" }).click();
  await hero.getByRole("button", { name: "Run autopilot" }).click();
  await expect(hero).toHaveAttribute("data-mode", "autopilot");
  await expect(hero.getByText("Opening the gripper")).toBeVisible();

  await expect(hero).toHaveAttribute("data-held", "orange block", { timeout: 75_000 });
  await hero.getByRole("button", { name: "Pause autopilot" }).click();
  await page.getByLabel("Grip", { exact: true }).fill("0");
  await expect.poll(async () => Number.parseFloat(await readouts.nth(4).innerText())).toBeGreaterThan(10);
  await expect(hero).toHaveAttribute("data-held", "orange block");
  await page.getByLabel("Grip", { exact: true }).fill("40");
  await expect(hero).toHaveAttribute("data-held", "", { timeout: 10_000 });

  const parts = page.locator("#parts");
  await parts.scrollIntoViewIfNeeded();
  const stage = parts.locator(".part-stage");
  await expect(stage).toHaveAttribute("data-state", "stl", { timeout: 15_000 });
  await expect.poll(() => countRenderedPixels(parts.locator("canvas"))).toBeGreaterThan(0);

  await parts.getByRole("button", { name: /SG90 Parallel Gripper/ }).click();
  await expect(parts.getByRole("heading", { name: "SG90 Parallel Gripper" })).toBeVisible();
  await expect(stage).toHaveAttribute("data-state", "stl", { timeout: 15_000 });
});

test("old simulator URL lands on the main page", async ({ page }) => {
  await page.goto("simulator/");
  await expect(page).toHaveURL(/\/robot-arm\/#simulator$/);
  await expect(page.locator("#simulator")).toBeVisible();
});

async function countRenderedPixels(canvas: Locator) {
  return canvas.evaluate((node) => {
    const canvasNode = node as HTMLCanvasElement;
    const context = canvasNode.getContext("webgl2") || canvasNode.getContext("webgl");
    if (!context) return 0;

    const sampleWidth = 8;
    const sampleHeight = 8;
    const pixels = new Uint8Array(sampleWidth * sampleHeight * 4);
    context.readPixels(
      Math.max(Math.floor(canvasNode.width / 2 - sampleWidth / 2), 0),
      Math.max(Math.floor(canvasNode.height / 2 - sampleHeight / 2), 0),
      sampleWidth,
      sampleHeight,
      context.RGBA,
      context.UNSIGNED_BYTE,
      pixels,
    );

    let lit = 0;
    for (let index = 0; index < pixels.length; index += 4) {
      if (pixels[index] + pixels[index + 1] + pixels[index + 2] > 60) lit += 1;
    }
    return lit;
  });
}
