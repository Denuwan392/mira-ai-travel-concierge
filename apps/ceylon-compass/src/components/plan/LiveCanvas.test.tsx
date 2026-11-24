import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { LiveCanvas } from "./LiveCanvas";
import type { Entry } from "@/lib/live/service";

// Mock ResultSurface to render children directly for fast isolated component unit testing
vi.mock("./AgentSurface", () => ({
  ResultSurface: ({
    turn,
    render: renderComponent,
    guide,
  }: {
    turn: { components: unknown[] };
    render: (c: unknown) => React.ReactNode;
    guide?: React.ReactNode;
  }) => (
    <div data-testid="result-surface">
      {turn.components.map((c, i) => (
        <div key={i}>{renderComponent(c)}</div>
      ))}
      {guide}
    </div>
  ),
}));

describe("LiveCanvas Production-Grade Rendering & Deduplication", () => {
  const baseEntry: Entry = {
    prompt: "Sigiriya day trip for two adults on 10 January 2027",
    turn: {
      catalog_version: 1,
      trace: "11111111-1111-4111-8111-111111111111",
      text: "I’ve verified the quote for your travel date and group.",
      sources: ["T01"],
      components: [
        {
          type: "PriceBreakdown",
          quote: {
            id: "22222222-2222-4222-8222-222222222222",
            source: "T01",
            title: "Sigiriya and Minneriya Day Tour from Kandy",
            date: "2027-01-10",
            adults: 2,
            ages: [],
            currency: "USD",
            total: 315,
            deposit: 315,
            balance: 0,
          },
        },
        {
          type: "TourCard",
          id: "T01",
          source: "T01",
          title: "Sigiriya and Minneriya Day Tour from Kandy",
          duration: "1 day",
          category: "Day tour",
          start: "Your hotel in Kandy",
          summary: "A long, rewarding day from Kandy into the Cultural Triangle.",
        },
        {
          type: "BookingForm",
          quote: "22222222-2222-4222-8222-222222222222",
        },
        {
          type: "ConfirmationPanel",
          source: "T01",
          heading: "Quote saved",
          text: "Your private enquiry is available to the travel team.",
        },
        {
          type: "SourceReference",
          source: "T01",
          heading: "From the travel library",
          text: "Sigiriya and Minneriya Day Tour from Kandy",
        },
      ],
    },
    surface: [
      {
        version: "v0.9",
        createSurface: { surfaceId: "journey", catalogId: "urn:ceylon-compass:mira:1" },
      },
      {
        version: "v0.9",
        updateComponents: {
          surfaceId: "journey",
          components: [
            { id: "root", component: "JourneyColumn", children: ["item-0", "item-1", "item-2", "item-3"] },
            { id: "item-0", component: "PriceBreakdown", index: 0 },
            { id: "item-1", component: "TourCard", index: 1 },
            { id: "item-2", component: "BookingForm", index: 2 },
            { id: "item-3", component: "ConfirmationPanel", index: 3 },
          ],
        },
      },
    ],
  };

  it("renders verified price breakdown without tour source disclosure", () => {
    const { container } = render(
      <LiveCanvas item={baseEntry} busy={false} send={vi.fn()} />,
    );

    const priceSection = container.querySelector('section[aria-label="Verified quote"]');
    expect(priceSection).toBeInTheDocument();
    expect(priceSection?.textContent).toContain("USD 315");
    expect(priceSection?.textContent).toContain("Rate verified · USD");
    expect(priceSection?.textContent).toContain("Deposit USD 315 · Balance USD 0");
    expect(priceSection?.textContent).toContain("Price verified");

    // Problem 4: Price card must NOT have a tour source disclosure
    expect(priceSection?.querySelector("details.source-disclosure")).toBeNull();
  });

  it("renders selected TourCard as single canonical full-detail presentation", () => {
    const { container } = render(
      <LiveCanvas item={baseEntry} busy={false} send={vi.fn()} />,
    );

    const tourCard = container.querySelector('article[data-tour-id="T01"]');
    expect(tourCard).toBeInTheDocument();
    expect(tourCard?.textContent).toContain("Sigiriya and Minneriya Day Tour from Kandy");

    // Tour card has the single canonical expandable disclosure with "Tour details"
    const disclosure = tourCard?.querySelector("details.source-disclosure");
    expect(disclosure).toBeInTheDocument();
    expect(disclosure?.querySelector("summary")?.textContent).toBe("Tour details");
    expect(disclosure?.querySelector("summary")?.textContent).not.toContain("T01");
  });

  it("renders confirmation panel concisely without source disclosure", () => {
    const { container } = render(
      <LiveCanvas item={baseEntry} busy={false} send={vi.fn()} />,
    );

    const confirmation = container.querySelector('aside[aria-label="Quote saved confirmation"]');
    expect(confirmation).toBeInTheDocument();
    expect(confirmation?.textContent).toContain("Quote saved");
    expect(confirmation?.textContent).toContain("Your private enquiry is available to the travel team.");

    // Problem 5: Confirmation card must NOT expand into a full document
    expect(confirmation?.querySelector("details")).toBeNull();
  });

  it("suppresses redundant 'From the travel library' card when duplicating selected tour", () => {
    const { container } = render(
      <LiveCanvas item={baseEntry} busy={false} send={vi.fn()} />,
    );

    // Problem 6: The redundant SourceReference for T01 must be suppressed
    const libraryCards = Array.from(container.querySelectorAll(".live-card")).filter((el) =>
      el.textContent?.includes("From the travel library"),
    );
    expect(libraryCards.length).toBe(0);
  });

  it("retains legitimate alternative tour recommendations", () => {
    const entryWithAlternative: Entry = {
      ...baseEntry,
      turn: {
        ...baseEntry.turn,
        components: [
          ...baseEntry.turn.components,
          {
            type: "SourceReference",
            source: "T09", // Different tour!
            heading: "Dambulla and Polonnaruwa Day Tour",
            text: "Explore ancient cave temples and royal ruins.",
          },
        ],
      },
    };

    const { container } = render(
      <LiveCanvas item={entryWithAlternative} busy={false} send={vi.fn()} />,
    );

    // Legitimate alternative tour must remain visible
    const alternativeCard = container.querySelector('article[data-source-id="T09"]');
    expect(alternativeCard).toBeInTheDocument();
    expect(alternativeCard?.textContent).toContain("Dambulla and Polonnaruwa Day Tour");
  });

  it("never exposes internal ID 'T01' in any traveller-facing summary labels", () => {
    const { container } = render(
      <LiveCanvas item={baseEntry} busy={false} send={vi.fn()} />,
    );

    const summaries = Array.from(container.querySelectorAll("summary"));
    for (const summary of summaries) {
      expect(summary.textContent).not.toContain("T01");
      expect(summary.textContent).not.toContain("Published source");
    }
  });
});
