const { chromium } = require("../../web/node_modules/playwright");
const assert = require("node:assert/strict");
(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.MIRA_CHROME,
    headless: true,
  });
  try {
    for (const width of [1440, 390]) {
      const page = await browser.newPage({
        viewport: { width, height: 900 },
        reducedMotion: "reduce",
      });
      page.setDefaultTimeout(80000);
      const errors = [];
      page.on("pageerror", (e) => errors.push(e.message));
      page.on("console", (m) => {
        if (m.type() === "error") console.log("CONSOLE", m.text().slice(0, 190));
      });
      await page.goto(process.env.COMPASS_URL || "http://127.0.0.1:5175", {
        waitUntil: "domcontentloaded",
      });
      await page.locator('header[data-theme="hero"]').waitFor();
      await page.locator(".company-logo").first().waitFor();
      assert.ok(
        await page
          .locator(".cinema-hero")
          .evaluate((e) => parseFloat(getComputedStyle(e).borderBottomLeftRadius) > 0),
      );
      if (process.env.MIRA_SCREENSHOTS === "1")
        await page.screenshot({
          path: "docs/screenshots/notebook-home-" + width + ".jpg",
          quality: 75,
        });
      const notes = page.locator(".notes-spread");
      assert.equal(await notes.locator("article").count(), 2);
      await notes.scrollIntoViewIfNeeded();
      for (const photo of await notes.locator("img").all()) {
        await photo.evaluate((img) => img.decode());
      }
      if (process.env.MIRA_SCREENSHOTS === "1")
        await notes.screenshot({ path: "docs/screenshots/island-notes-" + width + ".jpg" });
      await page
        .locator("#mira-prompt")
        .fill("Sigiriya day trip for two adults on 10 January 2027");
      await page.locator("#mira-prompt").press("Enter");
      if (width === 390)
        await page.getByRole("button", { name: "Your journey", exact: true }).click();
      await page.locator(".live-total").waitFor();
      assert.equal(await page.locator(".live-total").textContent(), "USD 315");
      if (process.env.MIRA_SCREENSHOTS === "1")
        await page.screenshot({
          path: "docs/screenshots/notebook-quote-" + width + ".jpg",
          quality: 75,
        });
      await page.locator('select[name="scenario"]').selectOption("declined");
      await page.getByRole("button", { name: "Try mock booking" }).click();
      await page.getByText(/Simulation: declined/).waitFor();
      await page.reload({ waitUntil: "domcontentloaded" });
      if (width === 390)
        await page.getByRole("button", { name: "Your journey", exact: true }).click();
      await page.locator(".live-total").waitFor();
      await page.locator(".canvas-head").getByRole("link").click();
      await page.locator(".trip-link").first().click();
      if (width === 390)
        await page.getByRole("button", { name: "Your journey", exact: true }).click();
      await page.locator(".live-total").waitFor();
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), width);
      assert.deepEqual(errors, []);
      if (width === 1440) {
        await page.goto(process.env.COMPASS_URL || "http://127.0.0.1:5175");
        await page.locator("#mira-prompt").fill("We have six days for nature, trains and beaches");
        await page.locator("#mira-prompt").press("Enter");
        await page.getByText(/Proposed itinerary · 6 days/).waitFor();
        await page.getByRole("button", { name: "Day 2", exact: true }).click();
        await page.getByRole("button", { name: "Day 2", exact: true, pressed: true }).waitFor();
        await page.getByLabel("Proposed departure").fill("2027-03-12");
        await page.getByText(/updated your proposed departure to 2027-03-12/).waitFor();
        await page.getByLabel("Message Mira").fill("Add another day in Ella");
        await page.getByLabel("Message Mira").press("Enter");
        await page.getByText(/Proposed itinerary · 7 days/).waitFor();
        if (process.env.MIRA_SCREENSHOTS === "1")
          await page.screenshot({ path: "docs/screenshots/notebook-route-1440.jpg", quality: 75 });
        assert.deepEqual(errors, []);
      }
      console.log(width, "passed hero, workbook quote, mock decline, refresh and My Trips");
      await page.goto(new URL("/plan?id=00000000-0000-4000-8000-000000000000", page.url()).href);
      await page.getByText("This trip is unavailable in this browser session.", {exact:false}).first().waitFor();
      await page.getByRole("link", {name:"Start a new trip"}).click();
      await page.waitForFunction(() => !document.querySelector('[aria-label="Message Mira"]')?.disabled && new URL(location.href).searchParams.has("id"));
      assert.equal(await page.getByRole("alert").count(), 0);
      await page.close();
    }
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
