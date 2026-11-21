import { islandOutline } from "./island-outline";
import type { Component } from "@/lib/live/catalog";
const centres: Record<string, [number, number]> = {
  D01: [80.76, 7.96],
  D02: [80.87, 8.04],
  D03: [80.64, 7.29],
  D04: [80.77, 6.97],
  D05: [81.05, 6.87],
  D06: [81.5, 6.37],
  D07: [80.22, 6.03],
  D08: [80.46, 5.95],
  D09: [80.4, 8.31],
  D10: [79.86, 6.93],
};
export function RouteMap({
  value,
  send,
  busy,
}: {
  value: Extract<Component, { days: unknown }>;
  send: (text: string) => void;
  busy: boolean;
}) {
  const pins = value.days.flatMap((day, index) => {
    const loc = centres[day.source];
    return loc && value.days.findIndex((d) => d.source === day.source) === index
      ? [{ ...day, index, x: (loc[0] - 79.3) * 88 + 36, y: (9.95 - loc[1]) * 88 + 12 }]
      : [];
  });
  return (
    <aside className="notebook-map">
      <div>
        <p className="eyebrow">Route map</p>
        {pins.map((p) => (
          <button
            key={p.source}
            disabled={busy}
            className="pill"
            onClick={() => send("@day " + (p.index + 1))}
          >
            {p.name}
          </button>
        ))}
      </div>
      <svg viewBox="30 12 245 365" aria-label="Approximate stop locations">
        <path d={islandOutline} fill="#e2dcc8" />
        <polyline
          points={pins.map((p) => [p.x, p.y].join(",")).join(" ")}
          stroke="#7a1832"
          fill="none"
          strokeDasharray="5 3"
        />
        {pins.map((p) => (
          <circle
            key={p.source}
            cx={p.x}
            cy={p.y}
            r={value.days[value.selected]?.source === p.source ? 8 : 5}
            fill="#7a1832"
          >
            <title>{p.name}</title>
          </circle>
        ))}
      </svg>
    </aside>
  );
}
