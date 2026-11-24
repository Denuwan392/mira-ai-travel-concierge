import { writeFile } from "node:fs/promises";
import { expect, test, type Page } from "@playwright/test";

interface TurnComponent {
  type: string;
  quote?: {
    id: string;
    source: string;
    date: string;
    adults: number;
    ages: number[];
    total: number;
    deposit: number;
    enquiry: string;
    enquiry_reference: string;
  };
  public_reference?: string;
  reference?: string;
  outcome?: string;
  reason_code?: string;
  tour_id?: string;
}

interface TraceEvent {
  stage: string;
  rate_digest?: string;
}

const sigiriya = "/workspace/index.html#/tours/sigiriya-minneriya-day-tour-from-kandy";
const colombo = "/workspace/index.html#/tours/colombo-city-tour";
const date = "2027-01-10";

test.skip(!process.env.MIRA_PRICING_TEST_PASSWORD, "Requires the isolated live pricing fixture");

async function requestQuote(page: Page) {
  const response = page.waitForResponse(r => new URL(r.url()).pathname === "/api/agent");
  await page.getByRole("button", { name: /^(Get verified quote|Recalculate quote)$/ }).click();
  const result = await response;
  expect(result.status()).toBe(200);
  const data = (await result.text()).split("\n")
    .filter(line => line.startsWith("data: "))
    .map(line => JSON.parse(line.slice(6)));
  const snapshot = data.findLast(event => event.type === "STATE_SNAPSHOT" && event.snapshot?.turn);
  expect(snapshot?.snapshot.surface).toBeTruthy();
  return { ...snapshot.snapshot, request: result.request().postDataJSON().messages.at(-1).content };
}

test("live quote, preview, history and enquiry identity", async ({ page, playwright }, testInfo) => {
  const staff = await playwright.request.newContext({ baseURL: testInfo.project.use.baseURL });
  try {
    const login = await staff.post("/api/auth/login", { data: {
      email: "pricing-audit@example.test",
      password: process.env.MIRA_PRICING_TEST_PASSWORD,
    } });
    expect(login.status()).toBe(200);

    await page.goto(sigiriya);
    const verified = page.getByRole("region", { name: "Verified quote" });
    const specialist = page.getByRole("region", { name: "Specialist confirmation required" });
    await expect(verified).toHaveCount(0);
    await expect(specialist).toHaveCount(0);

    const check = async (tourId: string, adults: number, childAges: number[], total: number, label: string) => {
      const result = await requestQuote(page);
      expect(JSON.parse(result.request).payload).toEqual({ tourId, date, adults, childAges });
      const quote = (result.turn.components as TurnComponent[]).find((c) => c.type === "PriceBreakdown")?.quote;
      if (!quote) throw new Error("Expected PriceBreakdown quote");
      expect(quote).toMatchObject({ source: tourId, date, adults, ages: childAges, total, deposit: total });
      await expect(verified).toContainText("USD " + quote.total);
      const preview = await staff.post("/api/staff/pricing/preview", {
        data: { tour_id: tourId, date, adults, child_ages: childAges, infants: 0 },
      });
      expect(preview.status()).toBe(200);
      const data = await preview.json();
      expect(data).toMatchObject({ outcome: "PRICE_VERIFIED", total_usd: quote.total, deposit_usd: quote.deposit });
      const enquiry = await page.request.get("/api/enquiries/" + quote.enquiry);
      expect(enquiry.status()).toBe(200);
      const saved = await enquiry.json();
      expect(saved).toMatchObject({ id: quote.enquiry, quote: quote.id, tour_id: tourId, reference: quote.enquiry_reference });
      expect(quote.enquiry_reference).toMatch(/^ENQ-/);
      const byReference = await page.request.get("/api/enquiries/" + saved.reference);
      expect((await byReference.json()).id).toBe(saved.id);
      const trace = await staff.get("/api/staff/enquiries/" + saved.id);
      expect(trace.status()).toBe(200);
      expect(((await trace.json()).events as TraceEvent[]).find((e) => e.stage === "pricing")?.rate_digest).toBe(data.rate_digest);
      const evidence = JSON.stringify({
        request: JSON.parse(result.request), status: 200, evaluated_config: data.evaluated_config,
        outcome: data.outcome, total: quote.total, deposit: quote.deposit, rate_digest: data.rate_digest,
        enquiry_reference: "[redacted]", component: "PriceBreakdown",
      }, null, 2);
      await testInfo.attach(label, { contentType: "application/json", body: evidence });
      if (process.env.MIRA_PRICING_CAPTURE && ["sigiriya-two", "sigiriya-four", "colombo-six-children", "sigiriya-mobile"].includes(label)) {
        const path = process.env.MIRA_PRICING_CAPTURE + "/" + label;
        await writeFile(path + ".redacted.json", evidence + "\n");
        await page.screenshot({ path: path + ".png", fullPage: true });
      }
      return saved.id;
    };

    const two = await check("T01", 2, [], 315, "sigiriya-two");
    await page.reload();
    await expect(verified).toContainText("USD 315");
    const increase = page.getByRole("button", { name: "Increase adults" });
    await increase.click();
    await expect(verified).toHaveCount(0);
    await expect(page.getByRole("region", { name: "Outdated quote" })).toBeVisible();
    await increase.click();
    const four = await check("T01", 4, [], 540, "sigiriya-four");
    expect(four).not.toBe(two);
    expect(await check("T01", 4, [], 540, "sigiriya-repeat")).toBe(four);

    await page.goto(colombo);
    await expect(verified).toHaveCount(0);
    await expect(specialist).toHaveCount(0);
    for (let i = 0; i < 6; i++) await page.getByRole("button", { name: "Increase children" }).click();
    await check("T03", 2, [7, 7, 7, 7, 7, 7], 265, "colombo-six-children");

    await page.locator('input[type="date"]').fill("2029-01-10");
    const unavailable = await requestQuote(page);
    const notice = (unavailable.turn.components as TurnComponent[]).find((c) => c.type === "EnquiryNotice");
    if (!notice?.public_reference) throw new Error("Expected EnquiryNotice public_reference");
    expect(notice).toMatchObject({ outcome: "PRICE_UNAVAILABLE", reason_code: "date_or_fx_expired", tour_id: "T03" });
    await expect(specialist).toContainText("outside the valid pricing window");
    await expect(specialist).toContainText(notice.public_reference);
    const enquiry = await page.request.get("/api/enquiries/" + notice.public_reference);
    expect((await enquiry.json()).id).toBe(notice.reference);
    if (process.env.MIRA_PRICING_CAPTURE) {
      await page.screenshot({ path: process.env.MIRA_PRICING_CAPTURE + "/unavailable.png", fullPage: true });
    }

    await page.goto("/workspace/index.html#/tours/instafamous-sri-lanka");
    const missing = await requestQuote(page);
    expect((missing.turn.components as TurnComponent[]).find((c) => c.type === "EnquiryNotice")).toMatchObject({
      outcome: "PRICE_UNAVAILABLE", reason_code: "tour_rate", tour_id: "T10",
    });
    await expect(specialist).toContainText("does not have an automated package rate");

    await page.goto(sigiriya);
    await expect(specialist).toHaveCount(0);
    await expect(page.getByText(notice.public_reference)).toHaveCount(0);
    await page.route("**/api/agent?*", route => route.fulfill({ status: 503 }), { times: 1 });
    await page.getByRole("button", { name: "Get verified quote" }).click();
    await expect(page.getByRole("alert")).toContainText("Could not calculate quote");
    await expect(specialist).toHaveCount(0);
    await expect(verified).toHaveCount(0);

    await page.setViewportSize({ width: 390, height: 844 });
    await check("T01", 2, [], 315, "sigiriya-mobile");
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  } finally {
    await staff.dispose();
  }
});

test("changing traveller inputs discards an older response", async ({ page }) => {
  await page.goto(sigiriya);
  let release: () => void;
  const hold = new Promise<void>(resolve => { release = resolve; });
  let observed: () => void;
  const older = new Promise<void>(resolve => { observed = resolve; });
  await page.route("**/api/agent?*", async route => {
    const response = await route.fetch();
    observed();
    await hold;
    await route.fulfill({ response }).catch(() => {});
  }, { times: 1 });
  await page.getByRole("button", { name: "Get verified quote" }).click();
  await older;
  try {
    const increase = page.getByRole("button", { name: "Increase adults" });
    await increase.click();
    await increase.click();
    await requestQuote(page);
    await expect(page.getByRole("region", { name: "Verified quote" })).toContainText("USD 540");
  } finally {
    release!();
  }
  await expect(page.getByRole("region", { name: "Verified quote" })).toContainText("USD 540");
});
