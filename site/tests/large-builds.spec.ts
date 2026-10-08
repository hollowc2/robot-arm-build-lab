import { expect, test } from "@playwright/test";

test("architectural builds refill the tray and reset cleanly", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "One browser validates the shared supply physics");
  test.setTimeout(240_000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(String(error)));
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  await page.goto("/");
  const hero = page.locator("#simulator");
  await expect(hero).toHaveAttribute("data-meshes", "48", { timeout: 60_000 });
  for (const [name, count] of [["Grand citadel", 250], ["City skyline", 150], ["Terraced monument", 100], ["Garden pavilion", 50]] as const) {
    await hero.getByRole("radio", { name: new RegExp(name) }).click();
    await expect(hero.getByRole("progressbar")).toHaveAttribute("aria-valuemax", String(count));
    await expect(hero).toHaveAttribute("data-build", "idle");
    await expect(hero).toHaveAttribute("data-supply", "12");
    const bounds = await hero.evaluate((node) => ({
      heroBottom: node.getBoundingClientRect().bottom,
      controlsBottom: node.querySelector(".dock")!.getBoundingClientRect().bottom,
    }));
    expect(bounds.controlsBottom).toBeLessThanOrEqual(bounds.heroBottom);
  }
  await page.getByLabel("Simulation speed").fill("4");
  await hero.getByRole("button", { name: "Start" }).click();
  await expect.poll(async () => Number(await hero.getAttribute("data-placed")), { timeout: 180_000 }).toBeGreaterThanOrEqual(13);
  await expect(hero).toHaveAttribute("data-build", "running");
  // The second batch physically arrived and produced a placement.
  expect(Number(await hero.getAttribute("data-supply"))).toBeGreaterThan(0);
  await hero.getByRole("button", { name: "Reset" }).click();
  await expect(hero).toHaveAttribute("data-build", "idle");
  await expect(hero).toHaveAttribute("data-placed", "0");
  await expect(hero).toHaveAttribute("data-held", "");
  await expect(hero).toHaveAttribute("data-supply", "12");
  expect(errors).toEqual([]);
});
