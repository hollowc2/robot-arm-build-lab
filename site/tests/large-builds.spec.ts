import { expect, test } from "@playwright/test";

test("architectures stay playable with the plain gripper", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "One browser validates the shared supply physics");
  test.setTimeout(240_000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(String(error)));
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  await page.goto("/");
  const hero = page.locator("#simulator");
  await expect(hero).toHaveAttribute("data-meshes", "54", { timeout: 60_000 });
  for (const [name, count] of [["Grand citadel", 60], ["City skyline", 48], ["Terraced monument", 42], ["Garden pavilion", 48]] as const) {
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
  await hero.getByRole("button", { name: "View building" }).click();
  await expect(hero).toHaveAttribute("data-preview", "true");
  await page.screenshot({ path: "/tmp/lego-building-preview.png" });
  await hero.getByRole("button", { name: "Return to build" }).click();
  await expect(hero).toHaveAttribute("data-preview", "false");
  await expect(hero.getByRole("button", { name: "Start", exact: true })).toBeEnabled();
  await expect(hero.locator(".build-headline")).toHaveText("Ready to build");
  expect(errors).toEqual([]);
});
