import { z } from "zod";
import { Tour } from "./catalog";

export const Guide = z.object({
  places: z.record(z.string(), z.object({ id: z.string(), name: z.string() })),
  tours: z.array(Tour.extend({
    places: z.array(z.string()),
    days: z.array(z.object({ number: z.number().int(), title: z.string(), body: z.string() })),
  })),
});
export type Guide = z.infer<typeof Guide>;
export type GuideTour = Guide["tours"][number];
