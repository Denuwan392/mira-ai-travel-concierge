import { INTEREST_LABEL } from "./parse";
import type { Citation, Itinerary, Trip } from "./types";

const monthIdx = (m: string) =>
  ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"].indexOf(m.toLowerCase());

function travelMonthIndex(trip: Trip): number | null {
  if (trip.startDate) return parseInt(trip.startDate.slice(5, 7), 10) - 1;
  if (trip.travelMonth) return monthIdx(trip.travelMonth);
  return null;
}

/** Season notes Mira can cite. Kept general and marked for specialist confirmation. */
function seasonNotes(trip: Trip, itin: Itinerary): Citation[] {
  const m = travelMonthIndex(trip);
  const ids = itin.route.map((r) => r.stop.id);
  const notes: Citation[] = [];
  if (m === null) return notes;
  if (ids.includes("yala") && (m === 8 || m === 9)) {
    notes.push({ label: "Yala often closes for part of Sept–Oct", source: "Dept. of Wildlife Conservation notices", note: "Closure dates change yearly — your specialist confirms." });
  }
  if (ids.includes("mirissa") && (m >= 4 && m <= 9)) {
    notes.push({ label: "South-west monsoon brings rougher seas May–Sept", source: "Ceylon Compass season notes", note: "Whale trips run mainly Nov–Apr." });
  }
  if (ids.includes("mirissa") && (m >= 10 || m <= 3)) {
    notes.push({ label: "Whale-watching season off Mirissa", source: "Ceylon Compass season notes", note: "Typically November to April; sightings are never guaranteed." });
  }
  return notes;
}

export function composeReply(prev: Trip, trip: Trip, itin: Itinerary, changes: string[], understood: boolean, isFirst: boolean) {
  if (!understood) {
    return {
      text: "I'd love to help shape that. Tell me roughly how many days you have, who's travelling, and what you want to feel — wild, slow, curious, salty?",
      citations: [] as Citation[],
      suggestions: ["We have 6 days and want nature, trains and beaches", "Two weeks, family of four, wildlife", "Romantic escape in March"],
    };
  }
  const routeNames = itin.route.map((r) => r.stop.name).join(" → ");
  const interests = trip.interests.map((i) => INTEREST_LABEL[i].toLowerCase());
  const hasTrain = itin.days.some((d) => d.transfer?.mode === "train");
  const citations: Citation[] = [];
  let text: string;

  const addedDay = changes.find((c) => c.startsWith("+"));
  if (!isFirst && addedDay) {
    const stopName = addedDay.match(/in ([A-Za-z ]+) ·/)?.[1];
    const r = itin.route.find((x) => x.stop.name === stopName);
    text = stopName && r
      ? `Done — ${stopName} now has ${r.days} days, so there's room to breathe up there. Your trip is ${itin.totalDays} days: ${routeNames}. I've shifted the timeline and flagged the quote for recalculation.`
      : `Added. You're now at ${itin.totalDays} days: ${routeNames}.`;
  } else if (isFirst) {
    const lead = interests.length ? `${trip.days} days of ${interests.slice(0, -1).join(", ")}${interests.length > 1 ? " and " : ""}${interests.at(-1)}` : `${trip.days} days`;
    text = `Lovely — ${lead}. I've drawn a first route: ${routeNames}.${hasTrain ? " The hill-country train is the spine of it, so we ride the most scenic stretch in daylight." : ""} Nothing here is booked; tell me what to change and I'll redraw.`;
    if (hasTrain) {
      citations.push({ label: "Kandy–Ella is one of the island's most scenic rail lines", source: "Ceylon Compass route notes", note: "Reserved seats sell out early in peak months; times confirmed by your specialist." });
    }
  } else {
    text = `Updated: ${changes.join("; ")}. Your route is now ${routeNames} over ${itin.totalDays} days.`;
  }
  if (prev.days !== trip.days && !addedDay && !isFirst) text += " I've rebalanced the nights across each stop.";
  citations.push(...seasonNotes(trip, itin));

  const suggestions: string[] = [];
  const ids = itin.route.map((r) => r.stop.id);
  if (ids.includes("ella") && !(trip.stopExtras.ella ?? 0)) suggestions.push("Add a day in Ella");
  if (!trip.startDate && !trip.travelMonth) suggestions.push("We're travelling from 12 March");
  if (trip.pace !== "relaxed") suggestions.push("Make it more relaxed");
  if (!trip.interests.includes("wildlife")) suggestions.push("Add wildlife");
  if (!ids.includes("galle")) suggestions.push("Include Galle");
  if (trip.party.children === 0) suggestions.push("We're a family of 4");
  return { text, citations, suggestions: suggestions.slice(0, 3) };
}
