"use client";

import { ArrowRight, CalendarDays, Check, CircleHelp, MapPin } from "lucide-react";
import { TourPhoto } from "../editorial/tour-photo";
import { FormEvent, useState } from "react";
import { api, money } from "../../lib/api";
import type { Component, Quote, Tour } from "../../lib/catalog";

export function MoneyPanel({ quote, open }: { quote: Quote; open?: (id: string) => void }) {
  return (
    <section className="panel quote-panel premium-quote" aria-label="Verified quote">
      <div className="premium-quote-header">
        <span className="verified quote-verified-badge">
          <Check size={14} /> Verified from workbook rates
        </span>
        <span className="quote-reference">Ref {quote.id.slice(0, 8).toUpperCase()}</span>
      </div>

      <h3 className="serif premium-quote-title">{quote.title}</h3>

      <p className="premium-quote-meta">
        {quote.date} · {quote.adults} adult{quote.adults === 1 ? "" : "s"}
        {quote.ages.length ? ` · Ages ${quote.ages.join(", ")}` : ""}
      </p>

      <div className="premium-quote-total">
        <span className="quote-total-label">Total</span>
        <div className="quote-total serif">{money(quote.total)}</div>
      </div>

      <dl className="quote-breakdown">
        <div>
          <dt>Deposit</dt>
          <dd>{money(quote.deposit)}</dd>
        </div>
        {quote.balance > 0 && (
          <div>
            <dt>Balance due</dt>
            <dd>{money(quote.balance)}</dd>
          </div>
        )}
      </dl>

      {open && (
        <button className="text-button quote-source-link" onClick={() => open(quote.source)}>
          View tour source <ArrowRight size={15} />
        </button>
      )}
    </section>
  );
}

function Picker({ value, send, disabled }: {
  value: Extract<Component, { type: "TravellerPicker" }>;
  send: (prompt: string, display?: string) => void;
  disabled: boolean;
}) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const ages = String(data.get("ages")).trim().replace(/\s/g, "");
    if (ages && !/^\d{1,3}(?:,\d{1,3})*$/.test(ages)) return;
    send(
      `@trip ${value.tour} ${data.get("date")} ${data.get("adults")} ${ages || "-"}`,
      `Check rates for ${data.get("adults")} adult(s) on ${data.get("date")}${ages ? `, with child ages ${ages}` : ""}.`
    );
  }

  return (
    <form className="panel picker refined-picker" onSubmit={submit} aria-label="Travel details">
      <div className="picker-header">
        <CalendarDays size={19} aria-hidden="true" />
        <h3>Your travel details</h3>
      </div>

      <div className="input-grid refined-input-grid">
        <label className="refined-label">
          <span>Travel date</span>
          <input type="date" name="date" defaultValue={value.date ?? ""} required />
        </label>
        <label className="refined-label">
          <span>Adults</span>
          <input type="number" name="adults" defaultValue={value.adults} min={1} max={100} required />
        </label>
      </div>

      <label className="refined-label refined-label-full">
        <span>Child ages, separated by commas</span>
        <input
          name="ages"
          placeholder="e.g. 7, 10"
          defaultValue={value.ages.join(", ")}
          pattern="[0-9]{1,3}( *, *[0-9]{1,3})*"
          maxLength={100}
        />
      </label>

      <button className="button primary refined-submit" disabled={disabled}>
        Check rates <ArrowRight size={17} />
      </button>
    </form>
  );
}

function Booking({ id }: { id: string }) {
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    const scenario = new FormData(event.currentTarget).get("scenario");
    try {
      const result = await api<{ status: string; reference?: string }>("/bookings/mock", {
        method: "POST", body: JSON.stringify({ quote: id, scenario }),
      });
      const errors: Record<string, string> = {
        declined: "The mock payment was declined. You can retry or keep the saved quote.",
        expired: "This quote needs to be refreshed. Ask Mira to check current rates.",
        unavailable: "The mock booking is unavailable. Your enquiry is still saved.",
        network: "The mock connection failed. You can retry.",
      };
      setStatus(
        result.status === "success"
          ? `Demo booking confirmed · ${result.reference?.slice(0, 8)}`
          : errors[result.status] ?? "The demo booking did not complete. Please retry."
      );
    } catch {
      setStatus("The booking service couldn't be reached. Please retry.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel booking refined-booking" onSubmit={submit} aria-label="Demo booking">
      <h3>Try a demo booking</h3>
      <p className="muted">No payment details or personal information are needed.</p>

      <label className="refined-label">
        <span>Simulation</span>
        <select name="scenario">
          <option value="success">Successful booking</option>
          <option value="declined">Payment declined</option>
          <option value="unavailable">Booking unavailable</option>
          <option value="network">Connection failure</option>
        </select>
      </label>

      <button className="button dark refined-submit" disabled={busy}>
        {busy ? "Submitting…" : "Try demo booking"}
      </button>

      {status && <p role="status" className="booking-status">{status}</p>}
    </form>
  );
}

export function JourneyCard({ tour, open, send, disabled }: {
  tour: Tour;
  open: (id: string) => void;
  send: (prompt: string, display?: string) => void;
  disabled: boolean;
}) {
  return (
    <article className="panel journey-card editorial-journey-card">
      {/* Large hero image */}
      <TourPhoto id={tour.id} />

      <div className="journey-card-body">
        {/* Category + duration overline */}
        <div className="eyebrow journey-card-eyebrow">
          {[tour.category, tour.duration].filter(Boolean).join(" · ")}
        </div>

        {/* Title in editorial serif */}
        <h3 className="serif journey-card-title">{tour.title}</h3>

        {/* Summary */}
        <p className="journey-card-summary">{tour.summary}</p>

        {/* Start location */}
        {tour.start && (
          <p className="journey-card-start">
            <MapPin size={15} aria-hidden="true" /> {tour.start}
          </p>
        )}

        {/* Actions */}
        <div className="card-actions journey-card-actions">
          <button className="text-button" onClick={() => open(tour.source)}>
            Tour details
          </button>
          <button
            className="button outline"
            disabled={disabled}
            onClick={() => send(`@tour ${tour.id}`, `Plan ${tour.title}`)}
          >
            Select tour
          </button>
        </div>
      </div>
    </article>
  );
}

export function RenderComponent({ value, ...actions }: {
  value: Component;
  open: (id: string) => void;
  send: (prompt: string, display?: string) => void;
  disabled: boolean;
}) {
  switch (value.type) {
    case "TourCard":
      return <JourneyCard tour={value} {...actions} />;
    case "TravellerPicker":
      return <Picker value={value} {...actions} />;
    case "PriceBreakdown":
      return <MoneyPanel quote={value.quote} open={actions.open} />;
    case "BookingForm":
      return <Booking id={value.quote} />;
    case "EnquiryNotice":
      return (
        <section className="panel notice editorial-notice">
          <CircleHelp size={22} aria-hidden="true" />
          <div>
            <h3>{value.text}</h3>
            {value.reference && <p>Enquiry {value.reference.slice(0, 8)}</p>}
          </div>
        </section>
      );
    case "ItineraryDay":
    case "PolicySnippet":
    case "DestinationHighlight":
      return (
        <section className="panel excerpt editorial-excerpt">
          {value.type === "ItineraryDay" && (
            <div className="timeline-marker" aria-hidden="true" />
          )}
          {value.type === "ItineraryDay" && <TourPhoto id={value.source} timeline />}
          <h3 className="excerpt-heading">{value.heading}</h3>
          <p className="excerpt-text">{value.text.replaceAll("**", "")}</p>
          <button className="text-button" onClick={() => actions.open(value.source)}>
            View source <ArrowRight size={16} />
          </button>
        </section>
      );
  }
}
