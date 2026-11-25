import { useState, useMemo } from "react";
import { ResultSurface } from "./AgentSurface";
import { api, type Entry } from "@/lib/live/service";
import type { Component } from "@/lib/live/catalog";
import { RouteMap } from "./RouteMap";
import { destinationPhotos, photos, type PhotoKey } from "@/lib/photos";
import { SourceDisclosure } from "./SourceDisclosure";

// Representative destination images for published tours with a matching local asset.
const tourPhotos: Partial<Record<string, PhotoKey>> = {
  T01: "sigiriya",
  T02: "kandy",
  T04: "galle",
  T05: "mirissa",
  T06: "train",
  T07: "kandy",
  T09: "dambulla",
  T11: "stilt",
  T13: "yala",
  T16: "sigiriya",
};

function Days({
  value,
  send,
  busy,
}: {
  value: Extract<Component, { days: unknown }>;
  send: (s: string) => void;
  busy: boolean;
}) {
  const day = value.days[value.selected] ?? value.days[0]!;
  const photo = destinationPhotos[day.source];
  return (
    <section>
      <p className="eyebrow">Proposed itinerary · {value.days.length} days</p>
      <div className="day-tabs">
        {value.days.map((d, i) => (
          <button
            className="pill"
            aria-pressed={day === d}
            key={i}
            disabled={busy}
            onClick={() => send("@day " + (i + 1))}
          >
            Day {i + 1}
          </button>
        ))}
      </div>
      {photo && (
        <figure className="canvas-cover">
          <img src={photos[photo].src} alt={photos[photo].alt} />
          <figcaption>
            <small>YOUR JOURNEY</small>
            <strong>{day.name}</strong>
          </figcaption>
        </figure>
      )}
      <h3>{day.name}</h3>
      <p>{day.passage}</p>
      <SourceDisclosure
        id={day.evidence ?? day.source}
        title={day.name}
        label={`Source: ${day.name}`}
      />
      <button
        disabled={busy}
        className="pill"
        onClick={() => send("Add another day in " + day.name)}
      >
        Add a day in {day.name}
      </button>
    </section>
  );
}

function Booking({ id }: { id: string }) {
  const [status, set] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <form
      className="fields"
      onSubmit={async (e) => {
        e.preventDefault();
        const scenario = new FormData(e.currentTarget).get("scenario");
        setBusy(true);
        try {
          const r = await api<{ status: string }>("/bookings/mock", {
            method: "POST",
            body: JSON.stringify({ quote: id, scenario }),
          });
          set(
            r.status === "success"
              ? "Simulated booking confirmed."
              : "Simulation: " +
                  r.status +
                  ". Your enquiry is saved. You may retry or request a fresh quote.",
          );
        } catch {
          set("Connection failed. Please retry.");
        } finally {
          setBusy(false);
        }
      }}
    >
      <label>
        Booking simulation
        <select name="scenario">
          <option value="success">Successful booking</option>
          <option value="declined">Payment declined</option>
          <option value="unavailable">Unavailable</option>
        </select>
      </label>
      <button disabled={busy} className="gold">
        Try mock booking
      </button>
      <p role="status">{status}</p>
    </form>
  );
}

export function LiveCanvas({
  item,
  send,
  busy,
}: {
  item: Entry;
  send: (s: string) => void;
  busy: boolean;
}) {
  // Problem 3 & 6: Track selected tours in this turn to avoid duplicate full documents and library cards
  const selectedTourIds = useMemo(() => {
    return new Set(
      item.turn.components
        .filter((c) => c.type === "TourCard")
        .map((c) => (c as Extract<Component, { type: "TourCard" }>).id),
    );
  }, [item.turn.components]);

  const render = (c: Component) => {
    switch (c.type) {
      case "JourneyPlan":
        return <Days value={c} send={send} busy={busy} />;
      case "DateSelector":
        return (
          <label className="fields">
            Proposed departure
            <input
              aria-label="Proposed departure"
              type="date"
              disabled={busy}
              value={c.value ?? ""}
              onChange={(e) => {
                if (e.target.value) send("@depart " + e.target.value);
              }}
            />
          </label>
        );
      case "InteractiveMap":
        return <RouteMap value={c} onSelectDay={(index) => send("@day " + (index + 1))} busy={busy} />;
      case "TourCard": {
        const photo = tourPhotos[c.id];
        return (
          <article className="live-card" data-tour-id={c.id}>
            {photo && (
              <img
                className="tour-image"
                loading="lazy"
                src={photos[photo].src}
                alt={photos[photo].alt}
              />
            )}
            <small>
              {c.category} · {c.duration}
            </small>
            <h3>{c.title}</h3>
            <p>{c.summary}</p>
            {/* Problem 1, 2, 3 & 7: Canonical full-detail presentation with safe markdown and friendly label */}
            <SourceDisclosure
              id={c.source}
              title={c.title}
              label="Tour details"
              stripLeadingH1={true}
            />
            <button
              className="pill"
              disabled={busy}
              onClick={() => send("@tour " + c.id)}
            >
              Explore itinerary →
            </button>
          </article>
        );
      }
      case "TravellerPicker":
        return (
          <form
            className="fields"
            onSubmit={(e) => {
              e.preventDefault();
              const d = new FormData(e.currentTarget);
              send(
                [
                  "@trip",
                  c.tour,
                  d.get("date"),
                  d.get("adults"),
                  String(d.get("ages")).replace(/\s/g, "") || "-",
                ].join(" "),
              );
            }}
          >
            <h3>Your travel details</h3>
            <label>
              Travel date
              <input
                name="date"
                type="date"
                defaultValue={c.date ?? ""}
                required
              />
            </label>
            <label>
              Adults
              <input
                name="adults"
                type="number"
                min="1"
                max="100"
                defaultValue={c.adults}
                required
              />
            </label>
            <label>
              Child ages, separated by commas
              <input
                name="ages"
                defaultValue={c.ages.join(",")}
                pattern="[0-9]{1,2}(, *[0-9]{1,2})*"
              />
            </label>
            <button className="gold" disabled={busy}>
              Check rates
            </button>
          </form>
        );
      case "PriceBreakdown":
        return (
          <section className="quote" aria-label="Verified quote">
            <p className="eyebrow">Rate verified · USD</p>
            <small>Quote {c.quote.id} · Rechecked before booking</small>
            <h3>{c.quote.title}</h3>
            <p>
              {c.quote.date} · {c.quote.adults} adult{c.quote.adults === 1 ? "" : "s"}
              {c.quote.ages.length ? ` · Ages ${c.quote.ages.join(", ")}` : ""}
            </p>
            <strong className="live-total">
              USD {c.quote.total.toLocaleString()}
            </strong>
            <p>
              Deposit USD {c.quote.deposit.toLocaleString()} · Balance USD{" "}
              {c.quote.balance.toLocaleString()}
            </p>
            {/* Problem 4: Pricing provenance only; no tour markdown document */}
            <div className="price-verified-note">
              <span className="verified-badge">✓</span> Price verified
            </div>
            <details className="price-provenance">
              <summary>How this price was calculated</summary>
              <div className="price-provenance-body">
                <p>
                  Rate verified from our official 2026–2027 tariff for {c.quote.adults} adult
                  {c.quote.adults > 1 ? "s" : ""}
                  {c.quote.ages.length
                    ? ` with child ages ${c.quote.ages.join(", ")}`
                    : ""}{" "}
                  on {c.quote.date}. Deposit of USD {c.quote.deposit.toLocaleString()} confirms your
                  booking; balance is due before departure.
                </p>
              </div>
            </details>
          </section>
        );
      case "BookingForm":
        return <Booking id={c.quote} />;
      case "ConfirmationPanel":
        {/* Problem 5: Concise saved confirmation state without repeated tour document */}
        return (
          <aside className="quote-confirmation live-card" aria-label="Quote saved confirmation">
            <p className="eyebrow">Private enquiry</p>
            <h3>{c.heading}</h3>
            <p>{c.text}</p>
          </aside>
        );
      case "EnquiryNotice":
        return (
          <aside className="quote live-card" aria-label="Specialist enquiry notice">
            <p className="eyebrow">Specialist enquiry</p>
            <h3>{c.text}</h3>
            {c.reference && <small>Reference {c.reference.slice(0, 8)}</small>}
          </aside>
        );
      case "SourceReference": {
        {/* Problem 6: Suppress redundant travel library card if it duplicates the selected tour */}
        if (selectedTourIds.has(c.source)) {
          return null;
        }
        return (
          <article className="live-card" data-source-id={c.source}>
            <small>From the travel library</small>
            <h3>{c.heading}</h3>
            <p>{c.text}</p>
            <SourceDisclosure
              id={c.source}
              title={c.heading || c.text}
              label={c.heading ? `Source: ${c.heading}` : "Tour details"}
            />
          </article>
        );
      }
      default:
        return (
          <article className="live-card" data-source-id={c.source}>
            <small>
              {c.type === "ItineraryDay"
                ? "Itinerary"
                : c.type === "StayCard"
                  ? "Accommodation"
                  : c.type === "ActivityCard"
                    ? "Activities"
                    : "Field notes"}
            </small>
            <h3>{c.heading}</h3>
            <p>{c.text}</p>
            <SourceDisclosure
              id={c.source}
              title={c.heading}
              label={c.heading ? `Source: ${c.heading}` : "Tour details"}
            />
          </article>
        );
    }
  };

  return (
    <ResultSurface
      turn={item.turn}
      messages={item.surface}
      render={render}
      guide={
        <div className="tour-results">
          {item.turn.components
            .filter((c) => c.type === "TourCard")
            .map((c) => (
              <div key={c.id}>{render(c)}</div>
            ))}
        </div>
      }
    />
  );
}
