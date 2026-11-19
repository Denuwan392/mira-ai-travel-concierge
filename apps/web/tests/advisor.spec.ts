import { expect, test } from "@playwright/test";

test("Ella conversation opens published journeys and keeps earlier results available", async ({
  page,
}) => {
  await page.goto("/plan");
  await page.getByRole("button", { name: "Ella trip", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Ella journeys" }),
  ).toBeVisible();
  const guide = page.getByRole("region", { name: "Interactive journey guide" });
  await expect(
    guide.getByRole("heading", { name: "Instafamous Sri Lanka" }),
  ).toBeVisible();
  await guide
    .getByRole("button", { name: "Shortlist Instafamous Sri Lanka" })
    .click();
  await guide
    .getByRole("button", { name: "Shortlist (1)", exact: true })
    .click();
  await expect(guide.locator(".guide-card")).toHaveCount(1);
  await page.getByRole("button", { name: "Explore these results" }).click();
  await guide.getByRole("button", { name: "Explore", exact: true }).click();
  await guide.getByRole("button", { name: "Galle on map" }).click();
  await expect(
    guide.getByRole("heading", { name: "Galle journeys" }),
  ).toBeVisible();
  await guide.getByRole("button", { name: "Ask Mira about Galle" }).click();
  await expect(
    page.getByRole("heading", { name: "Galle journeys" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Explore these results" }),
  ).toHaveCount(2);
  await page
    .getByRole("button", { name: "Explore these results" })
    .first()
    .click();
  await expect(
    guide.getByRole("heading", { name: "Ella journeys" }),
  ).toBeVisible();
});

test("day filters show published sections and two saved comparison choices", async ({
  page,
}) => {
  await page.goto("/plan");
  const board = page.getByRole("region", { name: "Interactive journey guide" });
  await board.getByRole("button", { name: "Compare", exact: true }).click();
  await board.getByRole("button", { name: "Compare tour" }).nth(0).click();
  await board.getByRole("button", { name: "Compare tour" }).nth(1).click();
  await expect(board.locator(".compare-pair article")).toHaveCount(2);
  await board.getByRole("button", { name: "Explore", exact: true }).click();
  await board
    .locator(".guide-card")
    .filter({ hasText: "Highlights of Sri Lanka" })
    .getByRole("button", { name: "View itinerary" })
    .click();
  await board.getByRole("button", { name: "Day 2", exact: true }).click();
  await expect(board.locator(".trip-day")).toHaveCount(1);
  await expect(board.locator(".trip-day")).toContainText("Sigiriya");
  await board.getByRole("button", { name: "Tour details" }).click();
  await expect(page.getByRole("dialog")).toContainText(
    "Highlights of Sri Lanka",
  );
});

test("phone exposes the map and updates the tour list without horizontal scrolling", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/plan");
  await page.getByRole("button", { name: "Journey", exact: true }).click();
  await page.getByRole("button", { name: "Map", exact: true }).click();
  await page.getByRole("button", { name: "Ella on map" }).click();
  await expect(
    page.getByRole("heading", { name: "Ella journeys" }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
});

test("Compare these tours reuses the two Ella results in the next agent turn", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Ella trip", exact: true }).click();
  await page
    .getByRole("button", { name: "Compare these tours", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Compare journeys" }),
  ).toBeVisible();
  const cards = page.locator(".compare-pair");
  await expect(cards).toContainText("Instafamous Sri Lanka");
  await expect(cards).toContainText("Treasures of Sri Lanka");
});
