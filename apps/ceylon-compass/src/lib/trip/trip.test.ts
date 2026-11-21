import { describe, expect, it } from "vitest";
import { applyMessage, newTrip } from "./parse";
import { buildItinerary } from "./itinerary";
import { LIVE_RATES, SAMPLE_RATES, computeQuote, type RateTable } from "./quote";

const today = new Date("2026-11-20T00:00:00Z");
const demo = () => applyMessage(newTrip(today), "We have 6 days and want nature, trains and beaches", today).trip;

describe("trip briefs", () => {
  it("reads duration and interests from the demo brief", () => {
    const t = demo();
    expect(t.days).toBe(6);
    expect(t.interests).toEqual(expect.arrayContaining(["nature", "trains", "beaches"]));
  });

  it("builds a 6-day route that rides the train into Ella and reaches the coast", () => {
    const it = buildItinerary(demo());
    expect(it.totalDays).toBe(6);
    const ids = it.route.map((r) => r.stop.id);
    expect(ids).toContain("kandy");
    expect(ids).toContain("ella");
    expect(ids.some((s) => s === "mirissa" || s === "galle")).toBe(true);
    expect(it.days.some((d) => d.transfer?.mode === "train" && d.stopId === "ella")).toBe(true);
  });

  it("'Add a day in Ella' adds exactly one day to Ella and the trip", () => {
    const before = buildItinerary(demo());
    const after = buildItinerary(applyMessage(demo(), "Add a day in Ella", today).trip);
    const ella = (i: typeof before) => i.route.find((r) => r.stop.id === "ella")!.days;
    expect(after.totalDays).toBe(7);
    expect(ella(after)).toBe(ella(before) + 1);
  });

  it("keeps invalid dates out of the timeline", () => {
    const trip = applyMessage(demo(), "Start on 2027-99-99", today).trip;
    expect(trip.startDate).toBeNull();
    expect(buildItinerary(trip).days).toHaveLength(6);
  });

  it("honours excluded interests in the initial brief", () => {
    expect(applyMessage(newTrip(today), "Nature, no beaches", today).trip.interests).toEqual(["nature"]);
  });

  it("reads party size and a start date", () => {
    const t = applyMessage(newTrip(today), "2 adults and 1 child from 12 March", today).trip;
    expect(t.party).toEqual({ adults: 2, children: 1 });
    expect(t.startDate).toBe("2027-03-12");
  });
});

describe("quotes", () => {
  it("with no live rate data, the trip quote is 'Price confirmation needed' with no total", () => {
    const t = demo();
    const q = computeQuote(t, buildItinerary(t), LIVE_RATES, today);
    expect(q.status).toBe("confirmation_needed");
    expect(q.total).toBeNull();
    expect(q.deposit).toBeNull();
  });

  it("a fully priced sample quote shows a 20% deposit", () => {
    const t = demo();
    const q = computeQuote(t, buildItinerary(t), SAMPLE_RATES, today);
    expect(q.status).toBe("verified");
    expect(q.deposit).toBe(Math.round(q.total! * 0.2));
  });

  it("an expired rate invalidates the quote", () => {
    const t = demo();
    const expired: RateTable = {
      ...SAMPLE_RATES,
      rates: { ...SAMPLE_RATES.rates, "driver:standard": { ...SAMPLE_RATES.rates["driver:standard"]!, validUntil: "2026-01-01" } },
    };
    expect(computeQuote(t, buildItinerary(t), expired, today).status).toBe("confirmation_needed");
  });

  it("editing the trip changes the quote signature so the old quote is invalid", () => {
    const t = demo();
    const q1 = computeQuote(t, buildItinerary(t), SAMPLE_RATES, today);
    const t2 = applyMessage(t, "Add a day in Ella", today).trip;
    const q2 = computeQuote(t2, buildItinerary(t2), SAMPLE_RATES, today);
    expect(q2.signature).not.toBe(q1.signature);
  });
});
