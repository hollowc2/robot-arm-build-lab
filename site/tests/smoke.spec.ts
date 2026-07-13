import { expect, type Locator, test } from "@playwright/test";

test("dashboard loads a non-empty viewer", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Billy Bitcoin's Robot Arm" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Robot Arm Master Assembly" })).toBeVisible();
  const canvas = page.locator("canvas").first();
  await expect(canvas).toBeVisible();
  await expect(page.getByText("STL loaded").first()).toBeVisible();

  const renderedPixels = await countRenderedPixels(canvas);
  expect(renderedPixels).toBeGreaterThan(0);

  await page.getByRole("button", { name: /Geared Base Stator/ }).first().click();
  await expect(page.getByRole("heading", { name: "Geared Base Stator" })).toBeVisible();
  await expect(page.getByText("STL loaded").first()).toBeVisible();
  await expect.poll(() => countRenderedPixels(canvas)).toBeGreaterThan(0);

  await page.getByRole("link", { name: "Open Simulator" }).click();
  await expect(page.getByRole("heading", { name: "Master Assembly Simulator" })).toBeVisible();
  await expect(page.getByText("17/17 CAD and drivetrain meshes loaded")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/5 physics objects ready/)).toBeVisible();
  await page.getByRole("button", { name: "Reset physics objects" }).click();
  await page.getByLabel("Shoulder").fill("45");
  await expect(page.getByText("45°")).toBeVisible();
  await page.getByRole("button", { name: "Demo" }).click();
  await expect(page.getByText("Demo: opening gripper")).toBeVisible();
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

    let nonBlack = 0;
    for (let index = 0; index < pixels.length; index += 4) {
      if (pixels[index] + pixels[index + 1] + pixels[index + 2] > 12) nonBlack += 1;
    }
    return nonBlack;
  });
}
