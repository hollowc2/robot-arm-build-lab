import { expect, test } from "@playwright/test";
import { buildPresets } from "../src/bricks.ts";

test("finished buildings can be inspected without changing assembly progress", async ({ page }) => {
  test.setTimeout(120_000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(String(error)));
  await page.goto("/");
  const hero = page.locator("#simulator");
  await expect(hero).toHaveAttribute("data-meshes", "54", { timeout: 60_000 });
  for (const preset of buildPresets) {
    await hero.getByRole("radio", { name: new RegExp(preset.name) }).click();
    await hero.getByRole("button", { name: "View building", exact: true }).click();
    await expect(hero).toHaveAttribute("data-preview", "true");
    await expect(hero).toHaveAttribute("data-placed", "0");
    await expect(hero.locator(".build-headline")).toHaveText(`${preset.name} preview`);
    if (preset.id === "pavilion") await page.screenshot({ path: "/tmp/lego-building-final.png" });
    await hero.getByRole("button", { name: "Return to build", exact: true }).click();
    await expect(hero).toHaveAttribute("data-preview", "false");
    await expect(hero).toHaveAttribute("data-build", "idle");
  }
  expect(errors).toEqual([]);
});
