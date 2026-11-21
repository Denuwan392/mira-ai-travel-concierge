import { z } from "zod/v4";
import type { Turn } from "./catalog";
export const catalogId = "urn:ceylon-compass:mira:1";
export const kinds = [
  "JourneyPlan",
  "InteractiveMap",
  "DateSelector",
  "SourceReference",
  "StayCard",
  "ActivityCard",
  "ComparisonPanel",
  "ConfirmationPanel",
  "DestinationCard",
  "TourCard",
  "TravellerPicker",
  "ItineraryDay",
  "PolicySnippet",
  "DestinationHighlight",
  "PriceBreakdown",
  "BookingForm",
  "EnquiryNotice",
] as const;
export const slot = z.object({ index: z.number().int().min(0).max(11) });
const node = z.union([
  z.strictObject({
    id: z.literal("root"),
    component: z.literal("JourneyColumn"),
    children: z.array(z.string()).max(13),
  }),
  z.strictObject({
    id: z.literal("results"),
    component: z.literal("JourneyResults"),
  }),
  z.strictObject({ id: z.string(), component: z.enum(kinds), ...slot.shape }),
]);
const target = z.literal("journey");
export const SurfaceMessages = z.tuple([
  z.strictObject({
    version: z.literal("v0.9"),
    createSurface: z.strictObject({
      surfaceId: target,
      catalogId: z.literal(catalogId),
    }),
  }),
  z.strictObject({
    version: z.literal("v0.9"),
    updateComponents: z.strictObject({
      surfaceId: target,
      components: z.array(node).min(1).max(14),
    }),
  }),
]);
export type SurfaceMessages = z.infer<typeof SurfaceMessages>;
export function readSurface(raw: unknown, turn: Turn) {
  const ops = SurfaceMessages.parse(raw);
  const [root, ...items] = ops[1].updateComponents.components;
  if (
    !root ||
    root.component !== "JourneyColumn" ||
    root.children.length !== items.length ||
    new Set(items.map((item) => item.id)).size !== items.length ||
    items.some(
      (item, i) =>
        root.children[i] !== item.id ||
        item.id === "root" ||
        item.component === "JourneyColumn" ||
        ("index" in item &&
          (item.id !== "item-" + item.index ||
            turn.components[item.index]?.type !== item.component)),
    )
  )
    throw Error("Invalid journey surface.");
  const discovery =
    turn.components.some((c) => c.type === "TourCard") &&
    !turn.components.some((c) =>
      ["TravellerPicker", "PriceBreakdown", "BookingForm"].includes(c.type),
    );
  if (items.some((n) => n.component === "JourneyResults") !== discovery)
    throw Error("Unexpected discovery surface.");
  const expected = turn.components.flatMap((c, i) =>
    c.type === "TourCard" && items.some((n) => n.component === "JourneyResults")
      ? []
      : ["item-" + i],
  );
  const actual = items.filter((n) => n.component !== "JourneyResults").map((n) => n.id);
  if (expected.length !== actual.length || expected.some((id, i) => id !== actual[i]))
    throw Error("Incomplete journey surface.");
  return ops;
}
