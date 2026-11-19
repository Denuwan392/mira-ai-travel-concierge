import { MapPin, Minus, Plus } from "lucide-react";
import { useState } from "react";
import type { Guide } from "../../lib/guide";
import { islandOutline, rivers } from "./island-outline";

// Approximate town or park centres. The map represents places in the source, not driving directions.
const centres: Record<string, [number, number]> = {
  sigiriya: [80.76, 7.96],
  minneriya: [80.87, 8.04],
  kandy: [80.64, 7.29],
  ella: [81.05, 6.87],
  "nuwara-eliya": [80.77, 6.97],
  mirissa: [80.46, 5.95],
  galle: [80.22, 6.03],
  colombo: [79.86, 6.93],
  anuradhapura: [80.4, 8.31],
  yala: [81.5, 6.37],
};
function project(lon: number, lat: number) {
  return [(lon - 79.3) * 88 + 36, (9.95 - lat) * 88 + 12];
}

export function IslandMap({
  places,
  visible,
  selected,
  choose,
}: {
  places: Guide["places"];
  visible: string[];
  selected: string;
  choose: (slug: string) => void;
}) {
  const [zoom, setZoom] = useState(false);
  const points = [...new Set(visible)].filter((k) => centres[k] && places[k]);
  const coords = points.map((k) => project(...centres[k]));
  const bounds = coords.length
    ? coords.reduce(
        (a, [x, y]) => [
          Math.min(a[0], x),
          Math.max(a[1], x),
          Math.min(a[2], y),
          Math.max(a[3], y),
        ],
        [Infinity, -Infinity, Infinity, -Infinity],
      )
    : [0, 300, 0, 415];
  const span = Math.max(
    120,
    bounds[1] - bounds[0] + 55,
    (bounds[3] - bounds[2] + 80) * 0.75,
  );
  const box = zoom
    ? [
        (bounds[0] + bounds[1] - span) / 2,
        (bounds[2] + bounds[3] - span / 0.75) / 2,
        span,
        span / 0.75,
      ]
    : [0, 0, 300, 400];
  return (
    <section className="island-map" aria-label="Sri Lanka destination map">
      <header>
        <span>
          <MapPin size={15} />
          Destination map
        </span>
        <button
          type="button"
          aria-label={zoom ? "Show whole island" : "Zoom to destinations"}
          onClick={() => setZoom(!zoom)}
        >
          {zoom ? <Minus size={16} /> : <Plus size={16} />}
        </button>
      </header>
      <svg
        viewBox={box.join(" ")}
        role="group"
        aria-label="Choose a destination pin"
      >
        <defs>
          <pattern
            id="sea-grid"
            width="24"
            height="24"
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M24 0H0V24"
              fill="none"
              stroke="#a0b8b7"
              strokeWidth=".4"
            />
          </pattern>
          <pattern
            id="land-grid"
            width="7"
            height="7"
            patternUnits="userSpaceOnUse"
          >
            <path d="m0 7 7-7" stroke="#d0d7bc" strokeWidth=".7" />
          </pattern>
        </defs>
        <rect x="-600" y="-600" width="1600" height="1600" fill="#dcebec" />
        <rect
          x="-600"
          y="-600"
          width="1600"
          height="1600"
          fill="url(#sea-grid)"
        />
        <path
          d={islandOutline}
          fill="#f6f3dd"
          stroke="#9ba78c"
          strokeWidth="1.6"
        />
        <path d={islandOutline} fill="url(#land-grid)" />
        <path d={rivers} stroke="#99b9bb" strokeWidth=".9" fill="none" />
        <text
          x="57"
          y="217"
          className="ocean-name"
          transform="rotate(-75 57 217)"
        >
          Indian Ocean
        </text>
        {points.map((k, i) => {
          const [x, y] = coords[i];
          const active = k === selected;
          return (
            <g
              key={k}
              role="button"
              tabIndex={0}
              aria-label={places[k].name + " on map"}
              aria-pressed={active}
              onClick={() => choose(k)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  choose(k);
                }
              }}
              className="map-marker"
            >
              <title>{places[k].name}</title>
              <circle
                cx={x}
                cy={y}
                r={active ? 9 : 7}
                fill={active ? "#aa4111" : "#204c3c"}
                stroke="white"
                strokeWidth="2"
              />
              <circle cx={x} cy={y} r="2" fill="white" />
              {!active &&
                !["minneriya", "nuwara-eliya", "mirissa"].includes(k) && (
                  <text
                    className="town-label"
                    x={x + (k === "colombo" ? -9 : 9)}
                    y={y + 3}
                    textAnchor={k === "colombo" ? "end" : "start"}
                  >
                    {places[k].name}
                  </text>
                )}
            </g>
          );
        })}
        {selected &&
          points.includes(selected) &&
          (() => {
            const [x, y] = project(...centres[selected]);
            return (
              <text x={x} y={y - 14} textAnchor="middle" className="pin-label">
                {places[selected].name}
              </text>
            );
          })()}
      </svg>
      <div className="map-places">
        {points.map((k) => (
          <button
            key={k}
            aria-pressed={selected === k}
            onClick={() => choose(k)}
          >
            {places[k].name}
          </button>
        ))}
      </div>
      <small>Approximate locations · Natural Earth</small>
    </section>
  );
}
