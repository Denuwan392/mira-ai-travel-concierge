import { useState } from "react";
import { ResultSurface } from "./AgentSurface";
import { api, type Entry } from "@/lib/live/service";
import type { Component } from "@/lib/live/catalog";
import { RouteMap } from "./RouteMap";
import { photos, type PhotoKey } from "@/lib/photos";
const destinationPhotos: Record<string, PhotoKey> = {
  D01: "sigiriya",
  D02: "elephants",
  D03: "kandy",
  D04: "tea",
  D05: "ella",
  D07: "galle",
  D08: "mirissa",
  D06: "yala",
};
// Representative destination images for published tours with a matching local asset.
const tourPhotos: Partial<Record<string, PhotoKey>> = {
  T01: "sigiriya", T02: "kandy", T04: "galle", T05: "mirissa",
  T06: "train", T07: "kandy", T09: "dambulla", T11: "stilt",
  T13: "yala", T16: "sigiriya",
};
function Source({ id }: { id: string }) {
  const [body, setBody] = useState("");
  return (
    <details
      onToggle={(e) => {
        if (e.currentTarget.open && !body)
          api<{ body: string }>("/sources/" + id)
            .then((r) => setBody(r.body))
            .catch(() => setBody("Source unavailable."));
      }}
    >
      <summary>Published source · {id}</summary>
      <p className="source-copy">{body || "Loading…"}</p>
    </details>
  );
}
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
      <Source id={day.source} />
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
        return <RouteMap value={c} send={send} busy={busy} />;
      case "TourCard": {
        const photo = tourPhotos[c.id];
        return (
          <article className="live-card">
            {photo && <img className="tour-image" loading="lazy" src={photos[photo].src} alt={photos[photo].alt} />}
            <small>
              {c.category} · {c.duration}
            </small>
            <h3>{c.title}</h3>
            <p>{c.summary}</p>
            <Source id={c.source} />
            <button className="pill" disabled={busy} onClick={() => send("@tour " + c.id)}>
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
              <input name="date" type="date" defaultValue={c.date ?? ""} required />
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
          <section className="quote">
            <p className="eyebrow">Rate verified · USD</p>
            <h3>{c.quote.title}</h3>
            <p>
              {c.quote.date} · {c.quote.adults} adults
            </p>
            <strong className="live-total">USD {c.quote.total.toLocaleString()}</strong>
            <p>
              Deposit USD {c.quote.deposit} · Balance USD {c.quote.balance}
            </p>
            <Source id={c.quote.source} />
          </section>
        );
      case "BookingForm":
        return <Booking id={c.quote} />;
      case "EnquiryNotice":
        return (
          <aside className="quote">
            <p className="eyebrow">Specialist enquiry</p>
            <h3>{c.text}</h3>
            {c.reference && <small>Reference {c.reference.slice(0, 8)}</small>}
          </aside>
        );
      default:
        return (
          <article className="live-card">
            <small>{c.type === "ItineraryDay" ? "Itinerary" : "Field notes"}</small>
            <h3>{c.heading}</h3>
            <p>{c.text}</p>
            <Source id={c.source} />
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
        <div>
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
