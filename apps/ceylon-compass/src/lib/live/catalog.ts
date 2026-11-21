import { z } from "zod/v4";

const text = z
  .string()
  .max(6000)
  .regex(/^[^<>]*$/);
const src = z.string().regex(/^[A-Z][A-Z0-9-]{1,60}$/);
const ages = z.array(z.number().int().min(0).max(120)).max(30);
export const Tour = z.strictObject({
  id: src,
  title: text,
  summary: text,
  duration: text,
  category: text,
  start: text,
  source: src,
});
export const Quote = z
  .strictObject({
    id: z.uuid(),
    source: src,
    title: text,
    date: z.iso.date(),
    adults: z.number().int().positive(),
    ages,
    currency: z.literal("USD"),
    total: z.number().int().positive(),
    deposit: z.number().int().positive(),
    balance: z.number().int().nonnegative(),
  })
  .refine((q) => q.total === q.deposit + q.balance);
const component = z.discriminatedUnion("type", [
  z.strictObject({
    type: z.enum(["JourneyPlan", "InteractiveMap"]),
    selected: z.number().int().min(0).max(29),
    days: z
      .array(z.strictObject({ source: src, name: text, passage: text }))
      .min(1)
      .max(30),
  }),
  z.strictObject({ type: z.literal("DateSelector"), value: z.iso.date().nullable() }),
  z.strictObject({
    type: z.enum([
      "SourceReference",
      "StayCard",
      "ActivityCard",
      "ComparisonPanel",
      "ConfirmationPanel",
      "DestinationCard",
    ]),
    source: src,
    heading: text,
    text,
  }),
  Tour.extend({ type: z.literal("TourCard") }),
  z.strictObject({
    type: z.literal("TravellerPicker"),
    tour: src,
    date: z.iso.date().nullable(),
    adults: z.number().int().min(1).max(100),
    ages,
  }),
  z.strictObject({
    type: z.enum(["ItineraryDay", "PolicySnippet", "DestinationHighlight"]),
    source: src,
    heading: text,
    text,
  }),
  z.strictObject({ type: z.literal("PriceBreakdown"), quote: Quote }),
  z.strictObject({ type: z.literal("BookingForm"), quote: z.uuid() }),
  z.strictObject({ type: z.literal("EnquiryNotice"), reference: z.uuid().nullable(), text }),
]);
export const Turn = z.strictObject({
  catalog_version: z.literal(1),
  trace: z.uuid(),
  text,
  sources: z.array(src).max(6),
  components: z.array(component).max(12),
});
export type Tour = z.infer<typeof Tour>;
export type Quote = z.infer<typeof Quote>;
export type Turn = z.infer<typeof Turn>;
export type Component = z.infer<typeof component>;
