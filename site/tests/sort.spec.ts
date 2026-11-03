import { expect, test } from "@playwright/test";

test("factory opens by default, sorts six foam blocks, reshuffles, and supports manual takeover", async ({ page }) => {
  test.setTimeout(300_000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  const hero = page.locator("#simulator");
  await expect(hero.getByRole("tab", { name: "Factory", exact: true })).toBeEnabled({ timeout: 30_000 });
  await expect(hero.getByRole("tab", { name: "Factory", exact: true })).toHaveAttribute("aria-selected", "true");
  await page.getByLabel("Simulation speed").fill("4");
  await expect(hero).toHaveAttribute("data-workspace", "sort");
  await expect(hero).toHaveAttribute("data-supply", "6");
  await expect(hero).toHaveAttribute("data-build", "running");
  await expect(hero).toHaveAttribute("data-held", /foam block/, { timeout: 30_000 });
  await hero.getByRole("button", { name: "Pause", exact: true }).click();
  await expect(hero).toHaveAttribute("data-paused", "true");
  await page.screenshot({ path: `/tmp/robot-sort-${test.info().project.name}.png` });
  await hero.getByRole("button", { name: "Shuffle & sort" }).click();
  await expect(hero).toHaveAttribute("data-sort-round", "2");
  await expect(hero).toHaveAttribute("data-paused", "false");
  await expect(hero).toHaveAttribute("data-placed", "0");
  await expect(hero).toHaveAttribute("data-build", "complete", { timeout: 150_000 });
  await expect(hero).toHaveAttribute("data-placed", "6");
  for (const color of ["red", "blue", "yellow"]) await expect(hero.locator(`.sort-color[data-color="${color}"]`)).toHaveAttribute("data-sorted", "2");
  await hero.getByRole("button", { name: "Shuffle & sort" }).click();
  await expect(hero).toHaveAttribute("data-sort-round", "3");
  await expect(hero).toHaveAttribute("data-build", "running");
  await hero.getByRole("tab", { name: "Joints", exact: true }).click();
  await hero.getByRole("button", { name: "Home", exact: true }).click();
  await expect(hero).toHaveAttribute("data-build", "stopped");
  await hero.getByRole("tab", { name: "Factory", exact: true }).click();
  await expect(hero.getByRole("button", { name: "Start sorting" })).toBeVisible();
  await expect(hero.getByRole("tab")).toHaveText(["Factory", "Joints"]);
  await expect(hero.getByRole("radio")).toHaveCount(0);
  expect(errors).toEqual([]);
});


test("reduced motion waits for an explicit start", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  const hero = page.locator("#simulator");
  await expect(hero).toHaveAttribute("data-meshes", "48", { timeout: 30_000 });
  await expect(hero).toHaveAttribute("data-workspace", "sort");
  await expect(hero).toHaveAttribute("data-build", "idle");
  await expect(hero).toHaveAttribute("data-placed", "0");
  await hero.getByRole("button", { name: "Start sorting" }).click();
  await expect(hero).toHaveAttribute("data-build", "running");
});
