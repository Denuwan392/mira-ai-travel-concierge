import { expect, test } from "@playwright/test";

const workspace = "/workspace/index.html";
test("published guide, verified quote, booking and private staff trace", async ({ page, request }) => {
  await page.goto(workspace + "#/tours");
  await page.getByRole("heading", { name: "Sigiriya and Minneriya Day Tour from Kandy" }).click();
  await page.locator('input[type="date"]').fill("2027-01-10");
  await page.getByRole("button", { name: "Get verified quote" }).click();
  const quote = page.getByRole("region", { name: "Verified quote" });
  await expect(quote).toContainText("USD 315");
  const saved = await page.request.get("/api/quotes");
  const [{ quote: record, current }] = await saved.json();
  expect(current).toBe(true);
  expect(record.total).toBe(315);
  expect(record.deposit).toBe(315);
  await page.getByRole("combobox").selectOption("declined");
  await page.getByRole("button", { name: "Try mock booking" }).click();
  await expect(page.getByRole("status")).toContainText("declined");
  await page.getByRole("combobox").selectOption("success");
  await page.getByRole("button", { name: "Try mock booking" }).click();
  await expect(page.getByRole("status")).toContainText("confirmed");
  await page.reload();
  await expect(quote).toContainText("USD 315");
  expect((await request.get("/api/staff/enquiries")).status()).toBe(401);
  const headers = { Authorization: "Bearer " + process.env.MIRA_STAFF_TOKEN };
  const rows = await (await request.get("/api/staff/enquiries", { headers })).json();
  const row = rows.find((r: {quote:string}) => r.quote === record.id);
  expect(row).toBeTruthy();
  const detail = await (await request.get("/api/staff/enquiries/" + row.id, { headers })).json();
  expect(detail.finance.total).toBe(record.total);
  expect(detail.events.map((e: {stage:string}) => e.stage)).toContain("pricing");
  await page.goto(workspace + "#/enquiry/" + row.id);
  await expect(page.getByText("Status: new")).toBeVisible();
  expect((await request.get("/api/enquiries/" + row.id)).status()).toBe(401);
});

test("mobile discovery, retry, and missing rates", async ({ page }) => {
  await page.setViewportSize({ width:390, height:844 });
  await page.route("**/api/guide", route => route.fulfill({ status:503, body:"" }), {times:1});
  await page.goto(workspace);
  await page.getByRole("button", {name:"Retry"}).click();
  await page.getByRole("button", {name:"Find a day trip"}).click();
  await expect(page.locator("[data-a2ui-version]")).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.getByPlaceholder("Tell Mira what you're looking for...").fill("Sigiriya day tour for two adults on 10 January 2029");
  await page.getByRole("button", {name:"Send message"}).click();
  await page.getByRole("button", {name:"View enquiry status"}).click();
  await expect(page.getByText("Status: new")).toBeVisible();
});

test("staff account reviews the evaluated build through the production proxy", async ({page}) => {
  test.skip(!process.env.MIRA_TEST_STAFF_PASSWORD, "Requires isolated staff fixture");
  await page.goto("/staff");
  await page.getByLabel("Staff Email").fill("console@example.test");
  await page.getByLabel("Password").fill(process.env.MIRA_TEST_STAFF_PASSWORD!);
  await page.getByRole("button", {name:"Sign In to Staff Console"}).click();
  const report = page.getByRole("link", {name:"View evaluation results"});
  await expect(report).toBeVisible();
  const result = await page.request.get("/api/staff/evaluation");
  expect(result.ok()).toBe(true);
  expect((await result.json()).summary.total_cases).toBeGreaterThanOrEqual(40);
  await page.getByRole("button", {name:"Enquiries", exact:true}).click();
  await expect(page.getByText(/verified_quote|Verified quote saved/i).first()).toBeVisible();
});

test("consented returning traveller resumes the verified quote and recovers an expired session", async ({page,context}) => {
  await page.goto(workspace + "#/mira");
  const remember = page.getByRole("checkbox", {name:/Remember this journey/});
  await remember.click();
  await expect(remember).toBeChecked();
  await page.getByPlaceholder("Tell Mira what you're looking for...").fill("Sigiriya day trip for two adults on 10 January 2027");
  await page.getByRole("button", {name:"Send message"}).click();
  await expect(page.getByRole("region", {name:"Verified quote"})).toBeVisible();
  const returning = await context.newPage();
  await returning.goto(workspace + "#/mira");
  await expect(returning.getByRole("region", {name:"Verified quote"})).toContainText("USD 315");
  await returning.getByRole("checkbox").click();
  await expect(returning.getByRole("checkbox")).not.toBeChecked();
  await context.clearCookies();
  await returning.getByPlaceholder("Tell Mira what you're looking for...").fill("Show me a day tour");
  await returning.getByRole("button", {name:"Send message"}).click();
  await expect(returning.getByRole("alert")).toContainText("expired");
  await returning.getByRole("button", {name:"Retry"}).click();
  await expect(returning.getByRole("button", {name:"Find a day tour"})).toBeEnabled();
  await expect(returning.getByRole("region", {name:"Verified quote"})).toHaveCount(0);
});

test("conversation selects a published tour, renders itinerary and prices the picker", async ({page}) => {
  await page.goto(workspace + "#/mira");
  const chat = page.getByPlaceholder("Tell Mira what you're looking for...");
  await chat.fill("Hi! What can you do?");
  await page.getByRole("button", {name:"Send message"}).click();
  const card = page.locator('[data-tour-id="T01"]').first();
  await card.getByRole("button", {name:/Explore itinerary/}).click();
  const picker = page.locator("form").filter({has:page.getByRole("button", {name:"Check rates"})});
  await picker.getByLabel("Travel date").fill("2027-01-10");
  await picker.getByLabel("Adults").fill("2");
  await picker.getByLabel("Child ages, separated by commas").fill("1");
  await picker.getByRole("button", {name:"Check rates"}).click();
  await expect(page.getByRole("region", {name:"Verified quote"})).toContainText("USD 315");
  await page.getByRole("button", {name:"View enquiry status"}).first().click();
  await expect(page.getByText("Status: new")).toBeVisible();
  await page.goto(workspace + "#/mira");
  await chat.fill("Design a custom six-day journey across Kandy and Ella for a family of four");
  await page.getByRole("button", {name:"Send message"}).click();
  await expect(page.locator(".day-tabs button").first()).toBeVisible();
  await expect(page.getByRole("region", {name:"Verified quote"})).toHaveCount(0);
  await page.getByRole("button", {name:"View enquiry status"}).click();
  await expect(page.getByText("Status: new")).toBeVisible();
});

test("staff draft stays private through review and appears in discovery after Approver publication", async ({page, request}) => {
  const password = process.env.MIRA_TEST_STAFF_PASSWORD!;
  test.skip(!password, "Requires isolated staff fixture");
  const email = "reviewer@example.test";
  const newUser = await request.post("/api/auth/register", {data:{email,password,full_name:"Demo Reviewer"}});
  const {id} = await newUser.json();
  await page.goto("/staff");
  await page.getByLabel("Staff Email").fill("console@example.test");
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", {name:"Sign In to Staff Console"}).click();
  await expect(page.getByRole("button", {name:"Content Review"})).toBeVisible();
  expect((await page.request.patch("/api/admin/users/"+id,{data:{role:"approver"}})).ok()).toBe(true);
  await page.getByRole("button", {name:"Content Review"}).click();
  await page.getByPlaceholder(/Prepare a private Hill Country/).fill("Prepare a private itinerary using published Ella material");
  await page.getByRole("button", {name:"Create Draft"}).click();
  await expect(page.getByText(/Draft created/)).toBeVisible();
  const [draft] = await (await page.request.get("/api/staff/drafts")).json();
  expect((await request.get("/api/sources/"+draft.id)).status()).toBe(404);
  await expect(page.getByRole("button", {name:/Approve & Publish/})).toHaveCount(0);
  await page.request.post("/api/auth/logout");
  await page.reload();
  await page.getByLabel("Staff Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", {name:"Sign In to Staff Console"}).click();
  await page.getByRole("button", {name:"Content Review"}).click();
  await page.getByRole("button", {name:new RegExp(draft.title)}).click();
  await page.getByRole("button", {name:"Approve Content"}).click();
  await expect(page.getByText(/Draft status updated/)).toBeVisible();
  expect((await request.get("/api/sources/"+draft.id)).status()).toBe(404);
  await page.getByRole("button", {name:/Approve & Publish/}).click();
  await expect(page.getByText(/Draft published!/)).toBeVisible();
  await page.goto(workspace + "#/tours");
  await expect(page.getByRole("heading", {name:draft.title})).toBeVisible();
});

test("Test A & B & C: Four-adult quotation, quote invalidation, and tour switching", async ({ page, request }) => {
  await page.goto(workspace + "#/tours");
  // Select Sigiriya and Minneriya Day Tour (T01)
  await page.getByRole("heading", { name: "Sigiriya and Minneriya Day Tour from Kandy" }).click();
  await page.locator('input[type="date"]').fill("2027-01-10");
  
  // Increase adults from 2 to 4 (2 clicks)
  await page.getByRole("button", { name: "Increase adults" }).click();
  await page.getByRole("button", { name: "Increase adults" }).click();

  // Click "Get verified quote"
  await page.getByRole("button", { name: /Get verified quote|Recalculate quote/ }).click();
  const quote = page.getByRole("region", { name: "Verified quote" });
  await expect(quote).toContainText("USD 540");
  await expect(quote).toContainText("4 adults");

  // Verify backend quotes API
  const saved = await page.request.get("/api/quotes");
  const quotesList = await saved.json();
  const latestQuote = quotesList.find((q: any) => q.current);
  expect(latestQuote).toBeTruthy();
  expect(latestQuote.quote.adults).toBe(4);
  expect(latestQuote.quote.total).toBe(540);

  // Test B: Invalidation when changing adult count
  await page.getByRole("button", { name: "Decrease adults" }).click(); // Now 3 adults
  // Expect outdated warning / recalculate indicator
  await expect(page.getByText('Quote Outdated')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Recalculate quote', exact: true })).toBeVisible();

  // Test C: Tour switching clears quote
  await page.goto(workspace + "#/tours");
  await page.getByRole("heading", { name: "Kandy City Tour" }).click();
  await expect(page.getByText("USD 540")).toHaveCount(0);
});

test("Test D: Internal command leakage prevention in traveller chat", async ({ page }) => {
  await page.goto(workspace + "#/mira");
  const chat = page.getByPlaceholder("Tell Mira what you're looking for...");
  await chat.fill("Sigiriya day trip for two adults on 10 January 2027");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.getByRole("region", { name: "Verified quote" })).toBeVisible();

  // Ensure no machine commands like @trip or @tour appear in visible chat bubbles
  const bodyText = await page.locator("main").innerText();
  expect(bodyText).not.toMatch(/@trip\s+T\d+/);
  expect(bodyText).not.toMatch(/@tour\s+T\d+/);
});
