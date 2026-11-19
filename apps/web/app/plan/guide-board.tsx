"use client";

import Image from "next/image";
import {
  ArrowLeft,
  ArrowRight,
  Bookmark,
  Check,
  MapPin,
  SlidersHorizontal,
} from "lucide-react";
import { useState } from "react";
import type { Guide, GuideTour } from "../../lib/guide";
import { destinationMedia } from "../../lib/media-manifest";
import { IslandMap } from "./island-map";

const photos: Partial<Record<string, keyof typeof destinationMedia>> = {
  sigiriya: "sigiriya",
  ella: "ella",
  mirissa: "mirissa",
  galle: "galle",
  "nuwara-eliya": "tea",
};
const tourPlaces: Record<string, string> = {
  T10: "ella",
  T12: "sigiriya",
  T08: "nuwara-eliya",
  T01: "sigiriya",
  T04: "galle",
  T05: "mirissa",
};
const featured = ["T10", "T01", "T08", "T04", "T05"];

export function GuideBoard({
  guide,
  results,
  initialPlace,
  comparison,
  send,
  open,
  busy,
  saved,
  toggleSaved,
  contextual,
}: {
  guide: Guide;
  results?: string[];
  initialPlace?: string;
  comparison: boolean;
  busy: boolean;
  contextual: boolean;
  send: (text: string, display?: string) => void;
  open: (source: string) => void;
  saved: string[];
  toggleSaved: (id: string) => void;
}) {
  const [place, setPlace] = useState(initialPlace ?? "");
  const [detail, setDetail] = useState("");
  const [day, setDay] = useState(0);
  const [mode, setMode] = useState<"explore" | "saved" | "compare">(
    comparison ? "compare" : "explore",
  );
  const [showMap, setShowMap] = useState(false);
  const [all, setAll] = useState(false);
  const [compare, setCompare] = useState<string[]>(
    comparison ? (results ?? []).slice(0, 2) : [],
  );
  const ordered = results?.length
    ? results
    : [...featured, ...guide.tours.map((t) => t.id)];
  const pool = [...new Set(ordered)].flatMap(
    (id) => guide.tours.find((t) => t.id === id) ?? [],
  );
  const tour = guide.tours.find((t) => t.id === detail);
  const choices =
    mode === "saved" ? guide.tours.filter((t) => saved.includes(t.id)) : pool;
  const filtered = choices.filter((t) => !place || t.places.includes(place));
  const visible =
    all || results?.length || mode !== "explore" || place
      ? filtered
      : filtered.slice(0, 4);
  const places = tour
    ? tour.places
    : [...new Set(choices.flatMap((t) => t.places))];
  function inspect(t: GuideTour) {
    setDetail(t.id);
    setDay(0);
    setPlace("");
  }
  function changeMode(next: typeof mode) {
    setMode(next);
    setPlace("");
    setDetail("");
  }
  function pair(id: string) {
    setCompare((old) =>
      old.includes(id) ? old.filter((x) => x !== id) : [...old, id].slice(-2),
    );
  }
  const selected = guide.tours.filter((t) => compare.includes(t.id));
  const currentDay = tour?.days.find((d) => d.number === day);
  const dayPlaces =
    currentDay && tour
      ? tour.places.filter((k) =>
          (currentDay.title + " " + currentDay.body)
            .toLowerCase()
            .includes(guide.places[k].name.toLowerCase()),
        )
      : [];
  const mapPlaces = dayPlaces.length ? dayPlaces : places;
  const caption = place && guide.places[place]?.name;
  return (
    <section className="advisor-board" aria-label="Interactive journey guide">
      <div className="guide-toolbar">
        <div className="guide-modes">
          <button
            aria-pressed={mode === "explore"}
            onClick={() => changeMode("explore")}
          >
            Explore
          </button>
          <button
            aria-pressed={mode === "saved"}
            onClick={() => changeMode("saved")}
          >
            <Bookmark size={14} />
            Shortlist{saved.length > 0 && " (" + saved.length + ")"}
          </button>
          <button
            aria-pressed={mode === "compare"}
            onClick={() => changeMode("compare")}
          >
            <SlidersHorizontal size={14} />
            Compare
          </button>
        </div>
        <button
          className="guide-map-switch"
          aria-pressed={showMap}
          onClick={() => setShowMap(!showMap)}
        >
          <MapPin size={15} />
          {showMap ? "Hide map" : "Map"}
        </button>
      </div>
      <div className={"guide-layout" + (showMap ? " show-map" : "")}>
        <div className="guide-results">
          {tour ? (
            <>
              <button
                className="guide-back"
                onClick={() => {
                  setDetail("");
                  setPlace(initialPlace ?? "");
                }}
              >
                <ArrowLeft size={15} />
                Back to journeys
              </button>
              <span className="guide-kicker">
                {tour.category} · {tour.duration}
              </span>
              <h2>{tour.title}</h2>
              <p>{tour.summary}</p>
              {tour.days.length > 0 ? (
                <>
                  <nav aria-label="Itinerary days" className="day-switch">
                    <button
                      aria-pressed={day === 0}
                      onClick={() => {
                        setDay(0);
                        setPlace("");
                      }}
                    >
                      All days
                    </button>
                    {tour.days.map((d) => (
                      <button
                        key={d.number}
                        aria-pressed={day === d.number}
                        onClick={() => {
                          setDay(d.number);
                          setPlace("");
                        }}
                      >
                        Day {d.number}
                      </button>
                    ))}
                  </nav>
                  {tour.days
                    .filter((d) => !day || d.number === day)
                    .map((d) => (
                      <article className="trip-day" key={d.number}>
                        <span>DAY {d.number}</span>
                        <h3>{d.title}</h3>
                        <p>{d.body}</p>
                      </article>
                    ))}
                </>
              ) : (
                <div className="trip-day">
                  <h3>Places in this journey</h3>
                  <p>
                    {tour.places.map((k) => guide.places[k].name).join(" · ") ||
                      tour.start}
                  </p>
                </div>
              )}
              <div className="guide-actions">
                <button onClick={() => open(tour.source)}>Tour details</button>
                <button
                  disabled={busy}
                  onClick={() => send("@tour " + tour.id, "Plan " + tour.title)}
                >
                  Plan with Mira <ArrowRight size={14} />
                </button>
              </div>
            </>
          ) : (
            <>
              <span className="guide-kicker">
                {mode === "saved"
                  ? "Saved in this planner"
                  : contextual
                    ? "Mira’s results"
                    : "Ceylon Compass field guide"}
              </span>
              <h2>
                {mode === "compare"
                  ? "Compare journeys"
                  : mode === "saved"
                    ? "Your shortlist"
                    : caption
                      ? caption + " journeys"
                      : contextual
                        ? "Journeys for your trip"
                        : "Explore Sri Lanka"}
              </h2>
              {mode === "compare" && (
                <p className="guide-instruction">
                  Choose two published tours to compare their duration, starting
                  point and destinations.
                </p>
              )}
              {mode === "compare" && selected.length === 2 && (
                <div className="compare-pair">
                  {selected.map((t) => (
                    <article key={t.id}>
                      <strong>{t.title}</strong>
                      <dl>
                        <dt>Duration</dt>
                        <dd>{t.duration || "See tour source"}</dd>
                        <dt>Starts in</dt>
                        <dd>{t.start || "See tour source"}</dd>
                        <dt>Destinations</dt>
                        <dd>
                          {t.places.map((k) => guide.places[k].name).join(", ")}
                        </dd>
                      </dl>
                      <button onClick={() => inspect(t)}>View itinerary</button>
                    </article>
                  ))}
                </div>
              )}
              {place && (
                <button className="guide-back" onClick={() => setPlace("")}>
                  Clear destination filter ×
                </button>
              )}
              {visible.map((t) => {
                const key =
                  photos[tourPlaces[t.id]] ||
                  (place && photos[place]) ||
                  photos[t.places.find((k) => photos[k]) ?? ""];
                const photo = key ? destinationMedia[key] : undefined;
                return (
                  <article key={t.id} className="guide-card">
                    {photo && (
                      <div className="guide-photo">
                        <Image
                          src={photo.src}
                          alt={photo.alt}
                          fill
                          sizes="(max-width: 680px) 30vw, 155px"
                        />
                      </div>
                    )}
                    <div className="guide-card-copy">
                      <span className="guide-kicker">
                        {[t.category, t.duration].filter(Boolean).join(" · ")}
                      </span>
                      <h3>{t.title}</h3>
                      <p>{t.summary}</p>
                      <div className="guide-actions">
                        <button onClick={() => inspect(t)}>
                          View itinerary
                        </button>
                        {mode === "compare" ? (
                          <button
                            disabled={
                              !compare.includes(t.id) && compare.length === 2
                            }
                            aria-pressed={compare.includes(t.id)}
                            onClick={() => pair(t.id)}
                          >
                            {compare.includes(t.id) ? (
                              <Check size={14} />
                            ) : null}
                            Compare tour
                          </button>
                        ) : (
                          <button
                            disabled={busy}
                            onClick={() =>
                              send("@tour " + t.id, "Plan " + t.title)
                            }
                          >
                            Select tour <ArrowRight size={14} />
                          </button>
                        )}
                      </div>
                    </div>
                    <button
                      className="save-tour"
                      onClick={() => toggleSaved(t.id)}
                      aria-pressed={saved.includes(t.id)}
                      aria-label={
                        (saved.includes(t.id) ? "Remove " : "Shortlist ") +
                        t.title
                      }
                    >
                      <Bookmark
                        size={16}
                        fill={saved.includes(t.id) ? "currentColor" : "none"}
                      />
                    </button>
                  </article>
                );
              })}
              {!visible.length && (
                <p>
                  {mode === "saved"
                    ? "Use the bookmark on a journey to keep it here during this visit."
                    : "No published tours match this destination."}
                </p>
              )}
              {!all && visible.length < filtered.length && (
                <button className="guide-back" onClick={() => setAll(true)}>
                  Show all {filtered.length} journeys <ArrowRight size={14} />
                </button>
              )}
            </>
          )}
        </div>
        <aside className="guide-locator">
          <IslandMap
            places={guide.places}
            visible={mapPlaces}
            selected={place}
            choose={(k) => setPlace(place === k ? "" : k)}
          />
          {caption && (
            <button
              className="ask-place"
              disabled={busy}
              onClick={() => send("Tell me about " + caption)}
            >
              <MapPin size={15} />
              Ask Mira about {caption} <ArrowRight size={14} />
            </button>
          )}
        </aside>
      </div>
    </section>
  );
}
