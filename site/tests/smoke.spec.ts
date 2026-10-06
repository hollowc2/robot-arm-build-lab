import { expect, type Locator, test } from "@playwright/test";

test("landing page runs the brick builder and part viewer", async ({ page }) => {
  // Loads ~12 MB of meshes and runs physics on software WebGL in CI.
  test.setTimeout(180_000);
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: /Robot Arm/ })).toBeVisible();

  const hero = page.locator("#simulator");
  await expect(hero).toHaveAttribute("data-meshes", "35", { timeout: 30_000 });
  await expect(hero).toHaveAttribute("data-mode", "autopilot");
  await expect(hero).toHaveAttribute("data-build", "running");
  await expect(hero.locator(".build-headline")).toHaveText("Placing brick 1 of 13");
  await expect(hero.getByRole("radio", { name: /Little house/ })).toHaveAttribute("aria-checked", "true");

  // Manual takeover stops the automated build cleanly.
  const readouts = hero.locator("#dock-panel-joints .joint-readout");
  await hero.getByRole("tab", { name: "Joints" }).click();
  await hero.getByRole("button", { name: "Home" }).click();
  await expect(hero).toHaveAttribute("data-mode", "manual");
  await expect(hero).toHaveAttribute("data-build", "stopped");
  await expect(readouts.nth(1)).toHaveText("0°", { timeout: 15_000 });
  await expect(readouts.nth(2)).toHaveText("0°", { timeout: 15_000 });
  await page.getByLabel("Shoulder").fill("45");
  await expect(readouts.nth(1)).toHaveText("45°", { timeout: 15_000 });

  // Switching structures resets to the new build, ready to start.
  await hero.getByRole("tab", { name: "Build" }).click();
  await hero.getByRole("radio", { name: /Pyramid/ }).click();
  await expect(hero).toHaveAttribute("data-preset", "pyramid");
  await expect(hero).toHaveAttribute("data-build", "idle");
  await expect(hero).toHaveAttribute("data-placed", "0");
  await expect(hero.locator(".build-headline")).toHaveText("Ready to build");

  await page.getByLabel("Simulation speed").fill("4");
  await expect(hero).toHaveAttribute("data-speed", "4");
  await hero.getByRole("button", { name: "Start" }).click();
  await expect(hero).toHaveAttribute("data-mode", "autopilot");
  await expect(hero).toHaveAttribute("data-held", "tan 2×4", { timeout: 60_000 });

  // Pause freezes the arm with the brick still in the jaws.
  await hero.getByRole("button", { name: "Pause" }).click();
  await expect(hero).toHaveAttribute("data-paused", "true");
  const frozen = { stage: await hero.getAttribute("data-stage"), joints: await readouts.allTextContents() };
  await page.waitForTimeout(1500);
  expect({ stage: await hero.getAttribute("data-stage"), joints: await readouts.allTextContents() }).toEqual(frozen);
  await expect(hero).toHaveAttribute("data-held", "tan 2×4");
  await hero.getByRole("button", { name: "Resume" }).click();
  await expect(hero).toHaveAttribute("data-placed", "1", { timeout: 60_000 });

  // Reset mid-build clears the structure and restores the supply.
  await expect(hero).toHaveAttribute("data-held", "tan 2×2", { timeout: 60_000 });
  await hero.getByRole("button", { name: "Reset" }).click();
  await expect(hero).toHaveAttribute("data-build", "idle");
  await expect(hero).toHaveAttribute("data-placed", "0");
  await expect(hero).toHaveAttribute("data-held", "");

  // Manual grip still stops on a held brick and opening drops it.
  await hero.getByRole("button", { name: "Start" }).click();
  await expect(hero).toHaveAttribute("data-held", "tan 2×4", { timeout: 60_000 });
  await hero.getByRole("button", { name: "Pause" }).click();
  await hero.getByRole("tab", { name: "Joints" }).click();
  // The build's own grip target is already closed, so squeeze to a different value to take over.
  await page.getByLabel("Grip", { exact: true }).fill("5");
  await expect(hero).toHaveAttribute("data-paused", "false");
  await expect(hero).toHaveAttribute("data-build", "stopped");
  await expect.poll(async () => Number.parseFloat(await readouts.nth(4).innerText())).toBeGreaterThan(10);
  await expect(hero).toHaveAttribute("data-held", "tan 2×4");
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
