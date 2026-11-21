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
  ella: "ella",
  galle: "galle",
  mirissa: "mirissa",
  minneriya: "elephants",
  kandy: "kandy",
  yala: "yala",
  "nuwara-eliya": "tea",
};
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
    items: items.map((t) => ({
      ...t,
      photo: t.places.map((p) => imagery[p]).find(Boolean) ?? ("train" as PhotoKey),
    })),
    status,
  };
}
