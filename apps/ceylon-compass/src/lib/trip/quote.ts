import { STOPS } from "./places";
import type { Itinerary, Trip } from "./types";

export type Rate = {
  key: string;
  unit: "room-night" | "day" | "person";
  price: number; // customer-facing sell price per unit (never cost or margin)
  validUntil: string; // ISO date; rates past this date are treated as missing
};

export type RateTable = {
  kind: "live" | "sample";
  source: string;
  retrievedAt: string | null;
  currency: "USD";
  rates: Record<string, Rate>;
};

export type QuoteLine = {
  key: string;
  label: string;
  detail: string;
  quantity: number;
  unit: Rate["unit"];
  status: "priced" | "missing" | "expired";
  amount: number | null;
};

export type Quote = {
  kind: RateTable["kind"];
  status: "verified" | "confirmation_needed";
  lines: QuoteLine[];
  total: number | null;
  deposit: number | null;
  depositRate: number;
  currency: "USD";
  source: string;
  retrievedAt: string | null;
  signature: string;
  missingCount: number;
};

export const DEPOSIT_RATE = 0.2;

/**
 * Live rates. No deterministic, current rate feed is connected yet, so this table is
 * intentionally empty and every live quote resolves to "Price confirmation needed".
 */
export const LIVE_RATES: RateTable = {
  kind: "live",
  source: "No live rate feed connected",
  retrievedAt: null,
  currency: "USD",
  rates: {},
};

const SAMPLE_VALID = "2027-12-31";
const sampleRates: Record<string, Rate> = {
  "driver:standard": { key: "driver:standard", unit: "day", price: 95, validUntil: SAMPLE_VALID },
  "train:reserved": { key: "train:reserved", unit: "person", price: 18, validUntil: SAMPLE_VALID },
};
let i = 0;
for (const stop of Object.values(STOPS)) {
  for (const h of stop.hotels) {
    sampleRates[`hotel:${h.id}`] = { key: `hotel:${h.id}`, unit: "room-night", price: 180 + ((i * 37) % 160), validUntil: SAMPLE_VALID };
    i += 1;
  }
  for (const a of stop.activities) {
    sampleRates[`activity:${a.id}`] = { key: `activity:${a.id}`, unit: "person", price: 25 + ((i * 13) % 70), validUntil: SAMPLE_VALID };
    i += 1;
  }
}

/** Illustrative numbers that demonstrate the quote design. Never shown as a real price. */
export const SAMPLE_RATES: RateTable = {
  kind: "sample",
  source: "Illustrative sample dataset — not a price",
  retrievedAt: "2026-01-01",
  currency: "USD",
  rates: sampleRates,
};

export function rooms(trip: Trip) {
  return Math.max(1, Math.ceil(trip.party.adults / 2) + (trip.party.children > 2 ? 1 : 0));
}

export function quoteSignature(trip: Trip, itin: Itinerary) {
  const payload = JSON.stringify({
    p: trip.party,
    d: trip.startDate,
    r: itin.route.map((r) => [r.stop.id, r.nights, r.hotel.id]),
    a: itin.days.map((d) => [d.activities.map((a) => a.id), d.transfer?.mode]),
  });
  let h = 2166136261;
  for (let k = 0; k < payload.length; k += 1) {
    h ^= payload.charCodeAt(k);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0).toString(36);
}

export function computeQuote(trip: Trip, itin: Itinerary, table: RateTable, asOf = new Date()): Quote {
  const travellers = trip.party.adults + trip.party.children;
  const roomCount = rooms(trip);
  const asOfIso = asOf.toISOString().slice(0, 10);
  const lines: QuoteLine[] = [];

  const price = (key: string, quantity: number, label: string, detail: string, unit: Rate["unit"]) => {
    const rate = table.rates[key];
    let status: QuoteLine["status"] = "priced";
    if (!rate) status = "missing";
    else if (rate.validUntil < asOfIso) status = "expired";
    lines.push({ key, label, detail, quantity, unit, status, amount: status === "priced" ? rate!.price * quantity : null });
  };

  for (const r of itin.route) {
    if (r.nights === 0) continue;
    price(`hotel:${r.hotel.id}`, r.nights * roomCount, `${r.hotel.name}, ${r.stop.name}`, `${r.nights} night${r.nights > 1 ? "s" : ""} × ${roomCount} room${roomCount > 1 ? "s" : ""}`, "room-night");
  }
  price("driver:standard", itin.totalDays, "Private driver-guide & vehicle", `${itin.totalDays} days`, "day");
  const trainLegs = itin.days.filter((d) => d.transfer?.mode === "train").length;
  if (trainLegs) price("train:reserved", trainLegs * travellers, "Reserved train seats", `${trainLegs} leg${trainLegs > 1 ? "s" : ""} × ${travellers}`, "person");
  const seen = new Set<string>();
  for (const d of itin.days) {
    for (const a of d.activities) {
      if (seen.has(a.id)) continue;
      seen.add(a.id);
      price(`activity:${a.id}`, travellers, a.title, `${travellers} traveller${travellers > 1 ? "s" : ""}`, "person");
    }
  }

  const missingCount = lines.filter((l) => l.status !== "priced").length;
  const verified = missingCount === 0 && lines.length > 0;
  const total = verified ? lines.reduce((s, l) => s + (l.amount ?? 0), 0) : null;
  return {
    kind: table.kind,
    status: verified ? "verified" : "confirmation_needed",
    lines,
    total,
    deposit: total === null ? null : Math.round(total * DEPOSIT_RATE),
    depositRate: DEPOSIT_RATE,
    currency: table.currency,
    source: table.source,
    retrievedAt: table.retrievedAt,
    signature: quoteSignature(trip, itin),
    missingCount,
  };
}

export const formatMoney = (n: number) => `US$${n.toLocaleString("en-US")}`;
