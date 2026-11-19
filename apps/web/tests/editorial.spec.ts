import { expect, test } from "@playwright/test";

test("homepage forwards a traveller's own words through the price workflow", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Plan with Mira").fill("Sigiriya day trip for two adults on 10 January 2027");
  const submit = page.getByRole("button", { name: "Start planning", exact: true });
  await submit.hover();
  const border = await submit.evaluate(el => {
    const css = getComputedStyle(el, "::before");
    return [css.pointerEvents, css.animationDuration];
  });
  expect(border).toEqual(["none", "0.17s"]);
  await submit.click();
  await expect(page.getByRole("region", { name: "Verified quote" })).toContainText("USD 315");
});

test("journey selectors and manual landscapes respond to keyboard input", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Next landscape" }).press("Enter");
  await expect(page.locator(".scene-count")).toContainText("02");
  await page.getByRole("button", { name: "Next journey" }).press("Enter");
  await expect(page.getByRole("button", { name: /Highlights of Sri Lanka/ })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Previous journey" }).click();
  await page.getByRole("button", { name: "Plan this journey" }).click();
  await expect(page.getByRole("heading", { name: "Your travel details" })).toBeVisible();
});

test("mobile navigation, static focus border and responsive gallery", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const menu = page.getByRole("button", { name: "Open menu" });
  await menu.click();
  await expect(page.getByRole("link", { name: "My trips" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(menu).toBeFocused();
  const submit = page.getByRole("button", { name: "Start planning", exact: true });
  await submit.focus();
  expect(await submit.evaluate(el => getComputedStyle(el, "::before").animationName)).toBe("none");
  for (const width of [320, 390, 768, 1280, 1920]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    await expect(page.getByRole("button", { name: "Explore by compass" })).toHaveCount(0);
  }
});

test("a browser without WebGL keeps the photographic tour controls", async ({ page }) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
      value: function (this: HTMLCanvasElement, kind: string, ...args: unknown[]) {
        return kind.includes("webgl") ? null : Reflect.apply(original, this, [kind, ...args]);
      },
    });
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.getByRole("button", { name: "Explore by compass" }).click();
  await expect(page.getByRole("button", { name: "Close compass" })).toHaveCount(0);
  await page.getByRole("button", { name: "Next journey" }).click();
  await expect(page.getByRole("button", { name: /Highlights of Sri Lanka/ })).toHaveAttribute("aria-pressed", "true");
});
