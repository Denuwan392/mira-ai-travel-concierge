import { AIRPORT, RAIL_LINE, ROUTE_ORDER, STOPS } from "./places";
import type { Activity, Interest, Itinerary, ItineraryDay, Pace, RouteStop, StopId, Trip } from "./types";

const DAYS_PER_STOP: Record<Pace, number> = { relaxed: 2.6, balanced: 2, active: 1.5 };
const ACTIVITIES_PER_DAY: Record<Pace, number> = { relaxed: 1, balanced: 2, active: 3 };

function score(stop: StopId, interests: Interest[]): number {
  const s = STOPS[stop].scores;
  if (interests.length === 0) return (s.culture ?? 0) + (s.nature ?? 0) + (s.beaches ?? 0);
  return interests.reduce((sum, i) => sum + (s[i] ?? 0), 0);
}

function haversineKm(a: { lat: number; lon: number }, b: { lat: number; lon: number }) {
  const R = 6371;
  const dLat = ((b.lat - a.lat) * Math.PI) / 180;
  const dLon = ((b.lon - a.lon) * Math.PI) / 180;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos((a.lat * Math.PI) / 180) * Math.cos((b.lat * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

/** Approximate road time: straight-line × 1.45 winding factor at ~38 km/h, rounded to 0.5 h. */
export function driveHours(a: { lat: number; lon: number }, b: { lat: number; lon: number }) {
  const km = haversineKm(a, b) * 1.45;
  return Math.max(1, Math.round((km / 38) * 2) / 2);
}

// Approximate door-to-door hours used for planning copy only (always shown as "approx.").
const DRIVE: Record<string, number> = {
  "airport-sigiriya": 4, "airport-kandy": 3, "airport-nuwara": 4.5, "airport-ella": 5.5, "airport-yala": 5,
  "airport-mirissa": 3, "airport-galle": 2.5, "sigiriya-kandy": 2.5, "sigiriya-nuwara": 5, "sigiriya-ella": 5,
  "sigiriya-yala": 6.5, "sigiriya-mirissa": 6.5, "sigiriya-galle": 6, "kandy-nuwara": 2.5, "kandy-ella": 4.5,
  "kandy-yala": 5, "kandy-mirissa": 5, "kandy-galle": 4.5, "nuwara-ella": 2.5, "nuwara-yala": 4,
  "nuwara-mirissa": 5, "nuwara-galle": 5, "ella-yala": 2.5, "ella-mirissa": 3.5, "ella-galle": 4.5,
  "yala-mirissa": 2.5, "yala-galle": 3, "mirissa-galle": 1,
};
const TRAIN: Record<string, number> = { "kandy-nuwara": 4, "nuwara-ella": 3.5, "kandy-ella": 7 };

export function transferHours(from: StopId | "airport", to: StopId | "airport", mode: "drive" | "train") {
  const key = [from, to].sort((a, b) => (a === "airport" ? -1 : b === "airport" ? 1 : ROUTE_ORDER.indexOf(a as StopId) - ROUTE_ORDER.indexOf(b as StopId))).join("-");
  if (mode === "train" && TRAIN[key]) return TRAIN[key];
  if (DRIVE[key]) return DRIVE[key];
  const a = from === "airport" ? AIRPORT : STOPS[from];
  const b = to === "airport" ? AIRPORT : STOPS[to];
  return driveHours(a, b);
}

/** Choose which stops the trip visits, in route order. */
export function chooseStops(trip: Trip): StopId[] {
  const available = ROUTE_ORDER.filter((s) => !trip.excludedStops.includes(s));
  const chosen = new Set<StopId>(trip.requiredStops.filter((s) => available.includes(s)));
  const extras = Object.values(trip.stopExtras).reduce<number>((a, b) => a + Math.max(0, b ?? 0), 0);
  const baseDays = Math.max(1, trip.days - extras);
  const target = Math.max(1, Math.min(available.length, Math.round(baseDays / DAYS_PER_STOP[trip.pace])));

  // Trains: the hill-country line needs both ends to be meaningful.
  if (trip.interests.includes("trains")) {
    for (const s of ["kandy", "ella"] as StopId[]) if (available.includes(s)) chosen.add(s);
  }
  // Cover every interest with at least one stop.
  for (const interest of trip.interests) {
    const covered = [...chosen].some((s) => (STOPS[s].scores[interest] ?? 0) >= 2);
    if (covered) continue;
    const best = available
      .filter((s) => !chosen.has(s))
      .sort((a, b) => (STOPS[b].scores[interest] ?? 0) - (STOPS[a].scores[interest] ?? 0))[0];
    if (best && (STOPS[best].scores[interest] ?? 0) > 0) chosen.add(best);
  }
  // Fill by overall interest score.
  const ranked = available
    .filter((s) => !chosen.has(s))
    .sort((a, b) => score(b, trip.interests) - score(a, trip.interests) || ROUTE_ORDER.indexOf(a) - ROUTE_ORDER.indexOf(b));
  for (const s of ranked) {
    if (chosen.size >= target) break;
    chosen.add(s);
  }
  // Never more stops than days.
  let list = ROUTE_ORDER.filter((s) => chosen.has(s));
  while (list.length > trip.days) {
    const drop = [...list]
      .filter((s) => !trip.requiredStops.includes(s))
      .sort((a, b) => score(a, trip.interests) - score(b, trip.interests))[0] ?? list[list.length - 1];
    list = list.filter((s) => s !== drop);
  }
  return list;
}

/** Split the trip's days across stops; explicit "add a day in X" extras are honoured on top. */
export function allocateDays(trip: Trip, stops: StopId[]): Record<StopId, number> {
  const alloc = {} as Record<StopId, number>;
  const extras = stops.map((s) => Math.max(0, trip.stopExtras[s] ?? 0));
  const extraTotal = extras.reduce((a, b) => a + b, 0);
  const base = Math.max(stops.length, trip.days - extraTotal);
  stops.forEach((s) => (alloc[s] = 1));
  let remaining = base - stops.length;
  const byScore = [...stops].sort(
    (a, b) => score(b, trip.interests) - score(a, trip.interests) || stops.indexOf(a) - stops.indexOf(b),
  );
  let i = 0;
  while (remaining > 0 && byScore.length) {
    alloc[byScore[i % byScore.length]!] += 1;
    remaining -= 1;
    i += 1;
  }
  stops.forEach((s, idx) => (alloc[s] += (extras[idx] ?? 0)));
  // Reconcile with total in case extras exceed the trip length.
  let total = stops.reduce((sum, s) => sum + alloc[s], 0);
  while (total > trip.days) {
    const s = [...stops].sort((a, b) => alloc[b] - alloc[a])[0];
    if (!s || alloc[s] <= 1) break;
    alloc[s] -= 1;
    total -= 1;
  }
  return alloc;
}

function rankActivities(stop: StopId, interests: Interest[]): Activity[] {
  const acts = STOPS[stop].activities;
  if (!interests.length) return acts;
  return [...acts].sort((a, b) => {
    const sa = a.interests.filter((i) => interests.includes(i)).length;
    const sb = b.interests.filter((i) => interests.includes(i)).length;
    return sb - sa;
  });
}

function addDays(iso: string, n: number) {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

export function buildItinerary(trip: Trip): Itinerary {
  const stopIds = chooseStops(trip);
  const alloc = allocateDays(trip, stopIds);
  const totalDays = stopIds.reduce((s, id) => s + alloc[id], 0);

  const route: RouteStop[] = stopIds.map((id, idx) => {
    const stop = STOPS[id];
    const isLast = idx === stopIds.length - 1;
    const hotelId = trip.hotelChoices[id];
    const hotel = stop.hotels.find((h) => h.id === hotelId) ?? stop.hotels[0];
    if (!hotel) throw new Error("Missing stay for " + stop.name);
    return { stop, days: alloc[id], nights: isLast ? Math.max(0, alloc[id] - 1) : alloc[id], hotel };
  });

  const days: ItineraryDay[] = [];
  const perDay = ACTIVITIES_PER_DAY[trip.pace];
  let dayNo = 1;
  route.forEach((r, idx) => {
    const ranked = rankActivities(r.stop.id, trip.interests);
    let cursor = 0;
    for (let d = 0; d < r.days; d += 1) {
      const first = d === 0;
      const isDeparture = idx === route.length - 1 && d === r.days - 1;
      let transfer: ItineraryDay["transfer"] = null;
      if (first) {
        const prev = idx === 0 ? null : route[idx - 1]!.stop;
        const from = prev ?? AIRPORT;
        const onRail = prev && RAIL_LINE.includes(prev.id) && RAIL_LINE.includes(r.stop.id);
        const train = Boolean(onRail && (trip.interests.includes("trains") || trip.interests.length === 0 || trip.interests.includes("nature")));
        const hours = transferHours(prev ? prev.id : "airport", r.stop.id, train ? "train" : "drive");
        transfer = { from: from.name, to: r.stop.name, mode: train ? "train" : "drive", hours };
      }
      const count = Math.max(1, (first ? perDay - 1 : perDay) - (isDeparture ? 1 : 0));
      const acts: Activity[] = [];
      for (let k = 0; k < count && ranked.length; k += 1) {
        acts.push(ranked[cursor % ranked.length]!);
        cursor += 1;
      }
      const unique = acts.filter((a, i) => acts.findIndex((b) => b.id === a.id) === i);
      const lead = unique[0];
      const title = first
        ? transfer?.mode === "train"
          ? `The slow train to ${r.stop.name}`
          : idx === 0
            ? `Arrive, then ${r.stop.name}`
            : `On to ${r.stop.name}`
        : lead?.title ?? r.stop.headline;
      const story = first
        ? transfer?.mode === "train"
          ? `Reserved seats on the hill-country line from ${transfer.from}: tea terraces, tunnels and open doors. ${lead ? `Later, ${lead.title.toLowerCase()}.` : ""}`
          : `${idx === 0 ? "Your driver-guide meets you at arrivals." : `A private transfer from ${transfer?.from}.`} Settle into ${r.hotel.name.toLowerCase()} and ${lead ? lead.title.toLowerCase() : "an easy evening"}.`
        : `${lead?.blurb ?? r.stop.headline}${unique[1] ? ` Afterwards: ${unique[1].title.toLowerCase()}.` : ""}`;
      days.push({
        day: dayNo,
        date: trip.startDate ? addDays(trip.startDate, dayNo - 1) : null,
        stopId: r.stop.id,
        title: isDeparture && r.days > 1 ? `${lead?.title ?? r.stop.name}, then home` : title,
        story: isDeparture ? `${story} Transfer to Colombo airport for your flight (approx. ${transferHours(r.stop.id, "airport", "drive")} hrs).` : story,
        photo: first && transfer?.mode === "train" ? "train" : (lead?.photo ?? r.stop.photo),
        transfer,
        activities: unique,
        isDeparture,
      });
      dayNo += 1;
    }
  });

  return { route, days, totalDays, totalNights: Math.max(0, totalDays - 1) };
}
