import { expect, type Locator, test } from "@playwright/test";

test("landing page runs only the sorting factory, manual controls, and part viewer", async ({ page }) => {
  test.setTimeout(180_000);
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: /Robot Arm/ })).toBeVisible();
  const hero = page.locator("#simulator");
  await expect(hero).toHaveAttribute("data-meshes", "48", { timeout: 30_000 });
  await expect(hero.getByRole("tab")).toHaveText(["Factory", "Joints"]);
  await expect(hero.getByRole("tab", { name: "Build", exact: true })).toHaveCount(0);
  await expect(hero.locator("#dock-panel-build")).toHaveCount(0);
  await expect(hero.getByRole("radio")).toHaveCount(0);
  await expect(hero).toHaveAttribute("data-mode", "autopilot");
  const readouts = hero.locator("#dock-panel-joints .joint-readout");
  await hero.getByRole("tab", { name: "Joints" }).click();
  await hero.getByRole("button", { name: "Home" }).click();
  await expect(hero).toHaveAttribute("data-mode", "manual");
  await expect(hero).toHaveAttribute("data-build", "stopped");
  await expect(readouts.nth(1)).toHaveText("0°", { timeout: 15_000 });
  await expect(readouts.nth(2)).toHaveText("0°", { timeout: 15_000 });
  await page.getByLabel("Shoulder").fill("45");
  await expect(readouts.nth(1)).toHaveText("45°", { timeout: 15_000 });
  await hero.getByRole("tab", { name: "Factory" }).click();
  await page.getByLabel("Simulation speed").fill("4");
  await hero.getByRole("button", { name: "Shuffle & sort" }).click();
  await pauseOnPickup(hero, "foam block");
  const held = await hero.getAttribute("data-held");
  await expect(hero).toHaveAttribute("data-paused", "true");
  const frozen = { stage: await hero.getAttribute("data-stage"), joints: await readouts.allTextContents() };
  await page.waitForTimeout(1500);
  expect({ stage: await hero.getAttribute("data-stage"), joints: await readouts.allTextContents() }).toEqual(frozen);
  await expect(hero).toHaveAttribute("data-held", held!);
  await hero.getByRole("button", { name: "Resume" }).click();
  await expect.poll(async () => Number(await hero.getAttribute("data-placed")), { timeout: 60_000 }).toBeGreaterThanOrEqual(1);

  // Shuffle mid-batch clears the previous deliveries and restores six pickup slots.
  await hero.getByRole("button", { name: "Shuffle & sort" }).click();
  await expect(hero).toHaveAttribute("data-sort-round", "3");
  await expect(hero).toHaveAttribute("data-placed", "0");
  await expect(hero).toHaveAttribute("data-supply", "6");
  await pauseOnPickup(hero, "foam block");
  await hero.getByRole("tab", { name: "Joints" }).click();
  await page.getByLabel("Grip", { exact: true }).fill("2");
  await expect(hero).toHaveAttribute("data-paused", "false");
  await expect(hero).toHaveAttribute("data-build", "stopped");
  await expect.poll(async () => Number.parseFloat(await readouts.nth(4).innerText())).toBeGreaterThan(5);
  await expect(hero).toHaveAttribute("data-held", /foam block/);
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

test("mobile controls keep the factory moving with the canvas off screen", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile", "Mobile controls sit below the canvas");
  test.setTimeout(90_000);
  // A slow or missing font must not change whether the controls can run the arm.
  await page.route("**/*.woff2", (route) => route.abort());
  await page.goto("/");
  const hero = page.locator("#simulator");
  await expect(hero).toHaveAttribute("data-meshes", "48", { timeout: 30_000 });
  await page.getByLabel("Simulation speed").fill("4");

  // Leave the controls visible while moving the canvas beyond the visibility margin.
  await hero.locator(".hero-stage").evaluate((canvas) => {
    window.scrollBy({ top: canvas.getBoundingClientRect().bottom + 160, behavior: "instant" });
  });
  const bounds = await hero.evaluate((element) => ({
    canvasBottom: element.querySelector(".hero-stage")!.getBoundingClientRect().bottom,
    controlsBottom: element.querySelector(".dock")!.getBoundingClientRect().bottom,
    controlsTop: element.querySelector(".dock")!.getBoundingClientRect().top,
    viewportHeight: window.innerHeight,
  }));
  expect(bounds.canvasBottom).toBeLessThan(-120);
  expect(bounds.controlsBottom).toBeGreaterThan(0);
  expect(bounds.controlsTop).toBeLessThan(bounds.viewportHeight);
  await expect(hero).toHaveAttribute("data-held", /foam block/, { timeout: 60_000 });
});

test("old simulator URL lands on the main page", async ({ page }) => {
  await page.goto("simulator/");
  await expect(page).toHaveURL(/\/robot-arm\/#simulator$/);
  await expect(page.locator("#simulator")).toBeVisible();
});

// A 4x pickup can finish while Playwright scrolls to Pause. Invoke the real
// control when React publishes the held brick, before another frame advances.
async function pauseOnPickup(hero: Locator, label: string) {
  await hero.evaluate((node, heldLabel) => new Promise<void>((resolve, reject) => {
    const observer = new MutationObserver(check);
    const timer = window.setTimeout(() => {
      observer.disconnect();
      reject(new Error(`No pickup of ${heldLabel} within 60 seconds`));
    }, 60_000);
    function check() {
      if (!new RegExp(heldLabel).test(node.getAttribute("data-held") ?? "")) return;
      const pause = [...node.querySelectorAll<HTMLButtonElement>("button")]
        .find((button) => button.textContent?.trim() === "Pause" && !button.disabled);
      if (!pause) return;
      pause.click();
      observer.disconnect();
      window.clearTimeout(timer);
      resolve();
    }
    observer.observe(node, { attributes: true, attributeFilter: ["data-held"] });
    check();
  }), label);
}

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
