import { expect, test } from "@playwright/test";

const capture = process.env.MIRA_SCREENSHOTS === "1";

test("desktop lands, asks for details, prices, saves and simulates booking", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Your island. Your story." })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Highlights of Sri Lanka" })).toBeVisible();
  if (capture) await page.screenshot({ path: "../../docs/screenshots/desktop-home.png", fullPage: true });
  await page.getByRole("button", { name: "A Sigiriya day trip" }).click();
  await expect(page).toHaveURL(/\/plan$/);
  await expect(page.getByRole("heading", { name: "Your travel details" })).toBeVisible({ timeout: 15000 });
  await page.getByRole("button", { name: "Tour details" }).click();
  await expect(page.getByRole("dialog")).toContainText("Sigiriya and Minneriya");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page.getByLabel("Travel date").fill("2027-01-10");
  await page.getByRole("button", { name: "Check rates" }).click();
  const quote = page.getByRole("region", { name: "Verified quote" });
  await expect(quote.getByText("USD 315").first()).toBeVisible({ timeout: 15000 });
  if (capture) {
    await page.evaluate(() => window.scrollTo({top: 0, behavior: "instant"}));
    await page.screenshot({ path: "../../docs/screenshots/desktop-quote.png", fullPage: true });
  }
  await page.getByLabel("Simulation").selectOption("declined");
  await page.getByRole("button", { name: "Try demo booking" }).click();
  await expect(page.getByText(/mock payment was declined/)).toBeVisible();
  await page.getByLabel("Simulation").selectOption("success");
  await page.getByRole("button", { name: "Try demo booking" }).click();
  await expect(page.getByText(/Demo booking confirmed/)).toBeVisible();
  await page.getByRole("link", { name: "My trips" }).click();
  await expect(page.getByRole("region", { name: "Verified quote" })).toContainText("USD 315");
});

test("mobile switches between conversation and a non-priced enquiry", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Highlights of Sri Lanka" })).toBeVisible();
  if (capture) await page.screenshot({ path: "../../docs/screenshots/mobile-home.png", fullPage: true });
  await page.getByRole("button", { name: "Design a custom journey" }).click();
  await expect(page.getByText(/saved a private enquiry/)).toBeVisible({ timeout: 15000 });
  await page.getByRole("button", { name: "Journey", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Specialist confirmation required" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Verified quote" })).toHaveCount(0);
  if (capture) await page.screenshot({ path: "../../docs/screenshots/mobile-journey.png", fullPage: true });
  for (const width of [375, 390, 768, 1280]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
  }
});
