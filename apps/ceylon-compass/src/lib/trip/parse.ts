import { STOPS, findStop, findStops } from "./places";
import type { Interest, Pace, StopId, Trip } from "./types";

const NUM: Record<string, number> = {
  a: 1, an: 1, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8,
  nine: 9, ten: 10, eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15,
  sixteen: 16, seventeen: 17, eighteen: 18, nineteen: 19, twenty: 20, another: 1,
};
const NUM_RE = "(\\d{1,2}|a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|another)";
const toNum = (s: string | undefined, fallback = 1) => {
  if (!s) return fallback;
  if (/^\d+$/.test(s)) return parseInt(s, 10);
  return NUM[s] ?? fallback;
};

export const MIN_DAYS = 2;
export const MAX_DAYS = 21;
const clampDays = (n: number) => Math.max(MIN_DAYS, Math.min(MAX_DAYS, n));

const INTEREST_WORDS: Array<[Interest, RegExp]> = [
  ["nature", /\bnature|hik(e|es|ing)|mountain|waterfall|hills?\b|forest|outdoors|scenery|views?\b/],
  ["trains", /\btrains?\b|\brail|railway/],
  ["beaches", /\bbeach(es)?|coast|seaside|\bsea\b|surf|ocean|swim/],
  ["wildlife", /wildlife|safari|leopard|elephant|whales?\b|animals|birds?\b|birding/],
  ["culture", /culture|cultural|temples?|history|historic|heritage|ancient|ruins|unesco/],
  ["food", /\bfood|cook(ing)?|curr(y|ies)|cuisine|eat|culinary|street food/],
  ["tea", /\btea\b|plantation/],
  ["wellness", /wellness|ayurved|spa\b|yoga|retreat|unwind/],
  ["adventure", /adventure|adrenaline|rafting|climb|trek/],
];

export const INTEREST_LABEL: Record<Interest, string> = {
  nature: "Nature", trains: "Trains", beaches: "Beaches", wildlife: "Wildlife", culture: "Culture",
  food: "Food", tea: "Tea", wellness: "Wellness", adventure: "Adventure",
};

const MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"];
const MONTH_SHORT = MONTHS.map((m) => m.slice(0, 3));

export type ParseResult = { trip: Trip; changes: string[]; understood: boolean };

function monthIndex(word: string): number {
  const w = word.toLowerCase();
  const full = MONTHS.indexOf(w);
  if (full >= 0) return full;
  return MONTH_SHORT.indexOf(w.slice(0, 3));
}

function pad(n: number) {
  return String(n).padStart(2, "0");
}

/** Next occurrence of month/day on or after `today`. */
export function nextDate(month: number, day: number, today: Date): string {
  let year = today.getFullYear();
  const candidate = new Date(Date.UTC(year, month, day));
  const todayUtc = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  if (candidate.getTime() < todayUtc) year += 1;
  return `${year}-${pad(month + 1)}-${pad(day)}`;
}

/**
 * Apply a free-form brief or follow-up to the shared trip object.
 * Deterministic: the same text on the same trip always produces the same result.
 */
export function applyMessage(input: Trip, raw: string, today = new Date()): ParseResult {
  const text = ` ${raw.toLowerCase().replace(/[’]/g, "'")} `;
  const trip: Trip = structuredClone(input);
  const changes: string[] = [];
  let understood = false;
  let consumed = text;

  // 1. Day adjustments at a specific stop: "add a day in Ella", "two more nights in Galle"
  const addRe = new RegExp(`(?:add|plus|extra|give us)\\s+(?:${NUM_RE}\\s+)?(?:more\\s+|extra\\s+)?(?:day|days|night|nights)\\s+(?:in|at|to|for)\\s+([a-z']+(?:\\s+[a-z']+)?)`, "g");
  const moreRe = new RegExp(`${NUM_RE}\\s+(?:more|extra)\\s+(?:day|days|night|nights)\\s+(?:in|at)\\s+([a-z']+(?:\\s+[a-z']+)?)`, "g");
  const extraRe = /\b(another|one more|an extra|extra)\s+(?:day|night)\s+(?:in|at)\s+([a-z']+(?:\s+[a-z']+)?)/g;
  for (const re of [addRe, moreRe, extraRe]) {
    for (const m of consumed.matchAll(re)) {
      const stop = findStop(m[2] ?? "");
      if (!stop) continue;
      const n = toNum(m[1], 1);
      trip.stopExtras[stop] = (trip.stopExtras[stop] ?? 0) + n;
      trip.days = clampDays(trip.days + n);
      if (!trip.requiredStops.includes(stop)) trip.requiredStops.push(stop);
      trip.excludedStops = trip.excludedStops.filter((s) => s !== stop);
      changes.push(`+${n} day${n > 1 ? "s" : ""} in ${STOPS[stop].name} · now ${trip.days} days`);
      consumed = consumed.replace(m[0], " ");
      understood = true;
    }
  }

  const lessRe = new RegExp(`(?:remove|drop|cut|lose|one less)\\s+(?:${NUM_RE}\\s+)?(?:day|days|night|nights)\\s+(?:from|in|at)\\s+([a-z']+(?:\\s+[a-z']+)?)`, "g");
  for (const m of consumed.matchAll(lessRe)) {
    const stop = findStop(m[2] ?? "");
    if (!stop) continue;
    const n = toNum(m[1], 1);
    trip.stopExtras[stop] = (trip.stopExtras[stop] ?? 0) - n;
    trip.days = clampDays(trip.days - n);
    changes.push(`−${n} day${n > 1 ? "s" : ""} in ${STOPS[stop].name} · now ${trip.days} days`);
    consumed = consumed.replace(m[0], " ");
    understood = true;
  }

  // Generic "add a day" without a place
  const addGeneric = consumed.match(new RegExp(`\\b(?:add|plus)\\s+(?:${NUM_RE}\\s+)?(?:more\\s+|extra\\s+)?(?:day|days)\\b`));
  if (addGeneric) {
    const n = toNum(addGeneric[1], 1);
    trip.days = clampDays(trip.days + n);
    changes.push(`+${n} day${n > 1 ? "s" : ""} · now ${trip.days} days`);
    consumed = consumed.replace(addGeneric[0], " ");
    understood = true;
  }

  // 2. Skip / remove a place entirely
  for (const m of consumed.matchAll(/\b(?:skip|remove|drop|without|no|not)\s+(?:going to\s+|visiting\s+)?([a-z']+(?:\s+[a-z']+)?)/g)) {
    const stop = findStop(m[1] ?? "");
    if (!stop) continue;
    trip.excludedStops = Array.from(new Set([...trip.excludedStops, stop]));
    trip.requiredStops = trip.requiredStops.filter((s) => s !== stop);
    delete trip.stopExtras[stop];
    changes.push(`Removed ${STOPS[stop].name}`);
    consumed = consumed.replace(m[0], " ");
    understood = true;
  }

  // 3. Overall duration
  const durRe = new RegExp(`${NUM_RE}[\\s-]*(day|days|night|nights|week|weeks)\\b`);
  const fortnight = /\bfortnight\b/.test(consumed);
  const dm = consumed.match(durRe);
  if (fortnight || dm) {
    let n = fortnight ? 14 : toNum(dm![1], 1);
    const unit = dm?.[2] ?? "days";
    if (unit.startsWith("week")) n *= 7;
    if (unit.startsWith("night")) n += 1;
    const days = clampDays(n);
    if (days !== trip.days) {
      trip.days = days;
      trip.stopExtras = {};
      changes.push(`Duration · ${days} days`);
    }
    understood = true;
  }

  // 4. Party
  const adults = consumed.match(new RegExp(`${NUM_RE}\\s+adults?`));
  const kids = consumed.match(new RegExp(`${NUM_RE}\\s+(?:kids|children|child|teens?|teenagers)`));
  const familyOf = consumed.match(new RegExp(`family of\\s+${NUM_RE}`));
  const groupOf = consumed.match(new RegExp(`(?:group of|party of|${NUM_RE}\\s+of us)\\s*${NUM_RE}?`));
  let partyChanged = false;
  if (familyOf) {
    const total = toNum(familyOf[1], 4);
    trip.party = { adults: Math.min(2, total), children: Math.max(0, total - 2) };
    partyChanged = true;
  }
  if (adults) {
    trip.party.adults = Math.max(1, toNum(adults[1], 2));
    partyChanged = true;
  }
  if (kids) {
    trip.party.children = toNum(kids[1], 1);
    partyChanged = true;
  }
  if (!partyChanged && groupOf) {
    const n = toNum(groupOf[1] ?? groupOf[2], 2);
    trip.party = { adults: Math.max(1, n), children: 0 };
    partyChanged = true;
  }
  if (!partyChanged && /\b(couple|honeymoon|romantic|my (wife|husband|partner)|two of us|partner and i)\b/.test(consumed)) {
    trip.party = { adults: 2, children: 0 };
    partyChanged = true;
  }
  if (!partyChanged && /\b(solo|by myself|alone|just me)\b/.test(consumed)) {
    trip.party = { adults: 1, children: 0 };
    partyChanged = true;
  }
  if (!partyChanged && /\b(family|kids|children)\b/.test(consumed) && trip.party.children === 0) {
    trip.party = { adults: 2, children: 2 };
    partyChanged = true;
  }
  if (partyChanged) {
    const { adults: a, children: c } = trip.party;
    changes.push(`Travellers · ${a} adult${a > 1 ? "s" : ""}${c ? `, ${c} child${c > 1 ? "ren" : ""}` : ""}`);
    understood = true;
  }

  // 5. Interests (with removal phrases)
  const removed: Interest[] = [];
  for (const [interest, re] of INTEREST_WORDS) {
    const neg = new RegExp(`(?:no|without|skip|not into|less|fewer|drop)\\s+(?:the\\s+)?(?:${re.source})`);
    if (neg.test(consumed)) {
      removed.push(interest);
      trip.interests = trip.interests.filter((i) => i !== interest);
      understood = true;
    }
  }
  const added: Interest[] = [];
  for (const [interest, re] of INTEREST_WORDS) {
    if (removed.includes(interest)) continue;
    if (re.test(consumed) && !trip.interests.includes(interest)) {
      trip.interests.push(interest);
      added.push(interest);
    }
  }
  if (/surprise/.test(consumed)) {
    for (const i of ["culture", "wildlife", "trains", "beaches"] as Interest[]) {
      if (!trip.interests.includes(i)) {
        trip.interests.push(i);
        added.push(i);
      }
    }
    trip.style = trip.style ?? "Surprise me";
  }
  if (added.length) {
    changes.push(`Interests · ${added.map((i) => INTEREST_LABEL[i]).join(", ")}`);
    understood = true;
  }
  if (removed.length) changes.push(`Less · ${removed.map((i) => INTEREST_LABEL[i]).join(", ")}`);

  // 6. Pace
  let pace: Pace | null = null;
  if (/relax|slow|easy|unhurried|laid.?back|gentle|leisur/.test(consumed)) pace = "relaxed";
  else if (/packed|fast|active|see (it all|everything)|busy|action/.test(consumed)) pace = "active";
  else if (/balanced|moderate|middle/.test(consumed)) pace = "balanced";
  if (pace && pace !== trip.pace) {
    trip.pace = pace;
    changes.push(`Pace · ${pace}`);
  }
  if (pace) understood = true;

  // 7. Style
  if (/honeymoon|romantic|romance|anniversary/.test(consumed)) trip.style = "Romantic escape";
  else if (/family/.test(consumed)) trip.style = trip.style ?? "Family adventure";

  // 8. Dates
  const iso = consumed.match(/(\d{4})-(\d{2})-(\d{2})/);
  const dayMonth = consumed.match(/\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\b/);
  const monthDay = consumed.match(/\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?\b/);
  const monthOnly = consumed.match(/\b(?:in|during|around|from|early|late|mid|this|next|over)\s+(january|february|march|april|may|june|july|august|september|october|november|december)\b/)
    ?? consumed.match(/\b(january|february|march|april|june|july|august|september|october|november|december)\b/);
  let candidate: string | null = null;
  if (iso) candidate = iso[0];
  if (dayMonth) candidate = nextDate(monthIndex(dayMonth[2]!), Number(dayMonth[1]), today);
  if (monthDay) candidate = nextDate(monthIndex(monthDay[1]!), Number(monthDay[2]), today);
  if (candidate) {
    const date = new Date(candidate + "T00:00:00Z");
    if (Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === candidate) {
      trip.startDate = candidate;
      trip.travelMonth = null;
      changes.push(`Dates · from ${candidate}`);
      understood = true;
    }
  } else if (monthOnly?.[1]) {
    const month = monthOnly[1];
    trip.travelMonth = month.charAt(0).toUpperCase() + month.slice(1);
    trip.startDate = null;
    changes.push(`Travel month · ${trip.travelMonth}`);
    understood = true;
  }

  // 9. Specific stops mentioned positively
  const mentioned = findStops(consumed).filter((s) => !trip.excludedStops.includes(s));
  const newStops = mentioned.filter((s) => !trip.requiredStops.includes(s));
  if (newStops.length) {
    trip.requiredStops.push(...newStops);
    changes.push(`Stops · ${newStops.map((s) => STOPS[s].name).join(", ")}`);
    understood = true;
  }

  if (understood) {
    trip.briefCount += 1;
    trip.updatedAt = new Date().toISOString();
  }
  trip.title = makeTitle(trip);
  return { trip, changes, understood };
}

export function makeTitle(trip: Trip): string {
  if (trip.style && trip.style !== "Surprise me") return `${trip.days}-day ${trip.style.toLowerCase()}`;
  const tops = trip.interests.slice(0, 2).map((i) => INTEREST_LABEL[i].toLowerCase());
  if (tops.length === 0) return `${trip.days} days in Sri Lanka`;
  return `${trip.days} days of ${tops.join(" & ")}`;
}

export function newTrip(now = new Date()): Trip {
  const iso = now.toISOString();
  return {
    id: `trip_${now.getTime().toString(36)}${Math.random().toString(36).slice(2, 6)}`,
    title: "A new Sri Lanka journey",
    createdAt: iso,
    updatedAt: iso,
    days: 7,
    startDate: null,
    travelMonth: null,
    party: { adults: 2, children: 0 },
    interests: [],
    pace: "balanced",
    style: null,
    requiredStops: [],
    excludedStops: [],
    stopExtras: {},
    hotelChoices: {},
    messages: [],
    briefCount: 0,
    enquiry: null,
    savedAt: null,
  };
}
