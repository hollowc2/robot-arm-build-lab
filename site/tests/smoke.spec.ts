import { expect, test } from "@playwright/test";

test("dashboard loads a non-empty viewer", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Billy Bitcoin's Robot Arm" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Robot Arm Master Assembly" })).toBeVisible();
  const canvas = page.locator("canvas").first();
  await expect(canvas).toBeVisible();

  const renderedPixels = await canvas.evaluate((node) => {
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
  expect(renderedPixels).toBeGreaterThan(0);
});
