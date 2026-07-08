import { expect, test } from "@playwright/test";

test("dashboard loads a non-empty viewer", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Billy Bitcoin's Robot Arm Build Lab" })).toBeVisible();
  const canvas = page.locator("canvas").first();
  await expect(canvas).toBeVisible();

  const pixels = await canvas.evaluate((node) => {
    const canvasNode = node as HTMLCanvasElement;
    const context = canvasNode.getContext("webgl2") || canvasNode.getContext("webgl");
    return context ? canvasNode.width * canvasNode.height : 0;
  });
  expect(pixels).toBeGreaterThan(0);
});
