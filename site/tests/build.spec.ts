import { expect, test, type Page } from "@playwright/test";
import { buildPresets } from "../src/bricks.ts";

// Real-time builds take minutes each, so this matrix is opt-in:
//   BUILD_MATRIX=1 npx playwright test tests/build.spec.ts --project=desktop --workers=4
// It needs a GPU-backed browser; software WebGL drops frames and runs the clock slower than real time.
test.skip(!process.env.BUILD_MATRIX, "Set BUILD_MATRIX=1 to build every preset at every speed.");
test.use({ launchOptions: { args: ["--enable-gpu", "--use-angle=gl"] } });

// Simulated seconds per build at 1x, rounded up from the headless runs in build.test.mjs.
const buildSeconds = 160;

async function openBuilder(page: Page, presetName: string, speed: number) {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(String(error)));
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  await page.goto("/");
  const hero = page.locator("#simulator");
  await expect(hero).toHaveAttribute("data-meshes", "35", { timeout: 60_000 });
  await hero.getByRole("radio", { name: new RegExp(presetName) }).click();
  await expect(hero).toHaveAttribute("data-build", "idle");
  await page.getByLabel("Simulation speed").fill(String(speed));
  await expect(hero).toHaveAttribute("data-speed", String(speed));
  return { hero, errors };
}

for (const preset of buildPresets) {
  for (const speed of [0.5, 1, 4]) {
    test(`${preset.name} completes at ${speed}x`, async ({ page }, info) => {
      test.skip(info.project.name !== "desktop", "Desktop only");
      const budget = (buildSeconds / speed) * 1000 * 1.5;
      test.setTimeout(budget + 90_000);
      const { hero, errors } = await openBuilder(page, preset.name, speed);
      const started = Date.now();
      await hero.getByRole("button", { name: "Start" }).click();
      await expect(hero).toHaveAttribute("data-build", "complete", { timeout: budget });
      await expect(hero).toHaveAttribute("data-placed", String(preset.bricks.length));
      await expect(hero.locator(".build-headline")).toHaveText(`${preset.name} complete`);
      info.annotations.push({ type: "wall-clock", description: `${((Date.now() - started) / 1000).toFixed(1)} s` });
      expect(errors).toEqual([]);
    });
  }
}

test("speed changes mid-grip and mid-carry keep the build on track", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "Desktop only");
  test.setTimeout(400_000);
  const { hero, errors } = await openBuilder(page, "Little house", 1);
  const speed = page.getByLabel("Simulation speed");
  await hero.getByRole("button", { name: "Start" }).click();
  for (const [stage, value] of [["Gripping", "4"], ["Carrying", "0.5"], ["Aligning", "2"], ["Gripping", "0.75"], ["Carrying", "4"]] as const) {
    await expect(hero).toHaveAttribute("data-stage", new RegExp(`^${stage}`), { timeout: 120_000 });
    await speed.fill(value);
    await expect(hero).toHaveAttribute("data-speed", value);
    await expect(hero).toHaveAttribute("data-build", "running");
  }
  await expect(hero).toHaveAttribute("data-build", "complete", { timeout: 240_000 });
  await expect(hero).toHaveAttribute("data-placed", "13");
  expect(errors).toEqual([]);
});
