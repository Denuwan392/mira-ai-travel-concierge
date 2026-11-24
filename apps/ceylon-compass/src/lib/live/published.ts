import { useEffect, useState } from "react";
import { z } from "zod/v4";
import { Tour } from "./catalog";
import type { PhotoKey } from "@/lib/photos";
const Guide = z.object({
  tours: z.array(
    Tour.extend({
      places: z.array(z.string()),
      days: z.array(z.object({ title: z.string(), body: z.string(), number: z.number() })),
    }),
  ),
});
const imagery: Record<string, PhotoKey> = {
  sigiriya: "sigiriya",
  ella: "nineArchesTrain",
  galle: "galleLighthouse",
  mirissa: "mirissa",
  minneriya: "elephants",
  kandy: "kandy",
  yala: "yala",
  "nuwara-eliya": "tea",
  anuradhapura: "dambulla",
  colombo: "landscapeArch",
};

// Tour-specific imagery overrides to ensure every card in the catalog has distinct photography
const tourImagery: Record<string, PhotoKey> = {
  T01: "sigiriyaAerial",       // Sigiriya and Minneriya Day Tour from Kandy
  T02: "kandy",                // Kandy City Tour
  T03: "landscapeArch",        // Colombo City Tour
  T04: "galleLighthouse",      // Galle Fort Walking Tour
  T05: "mirissa",              // Whale and Dolphin Watching Tour in Mirissa
  T06: "nineArchesTrain",      // Train and Day Tour from Kandy to Nuwara Eliya
  T07: "bungalow",             // Kandy Heritage Stay
  T08: "sigiriya",             // Highlights of Sri Lanka
  T09: "dambulla",             // Cultural Triangle Sri Lanka Package
  T10: "nineArchesBridge",     // Instafamous Sri Lanka
  T11: "coastPalms",           // Sri Lanka Beach Stay – Mirissa
  T12: "galleRamparts",        // Treasures of Sri Lanka
  T13: "yala",                 // Wildlife Photography Tour
  T16: "curry",                // Cultural Triangle Tour
};

// Variety pool for custom/concept journeys (C-...) so they never repeat the same image
const conceptPool: PhotoKey[] = [
  "nineArchesTrain",
  "nineArchesBridge",
  "train",
  "hike",
  "tea",
  "ella",
];
export function usePublished() {
  const [items, setItems] = useState<z.infer<typeof Guide>["tours"]>([]),
    [status, setStatus] = useState("Opening the published travel library…");
  useEffect(() => {
    const c = new AbortController();
    fetch("/api/guide", { signal: c.signal })
      .then((r) => {
        if (!r.ok) throw Error();
        return r.json();
      })
      .then((raw) => {
        setItems(Guide.parse(raw).tours);
        setStatus("");
      })
      .catch(() => {
        if (!c.signal.aborted) setStatus("The travel library is unavailable. Reload to retry.");
      });
    return () => c.abort();
  }, []);
  return {
    items: items.map((t, idx) => {
      let photo: PhotoKey = "train";
      const direct = tourImagery[t.id];
      if (direct) {
        photo = direct;
      } else if (t.id.startsWith("C-")) {
        // Concept journeys: distribute unique photos from the concept pool so they don't repeat
        photo = conceptPool[idx % conceptPool.length] ?? "train";
      } else {
        photo = t.places.map((p) => imagery[p]).find(Boolean) ?? "train";
      }
      return {
        ...t,
        photo,
      };
    }),
    status,
  };
}
