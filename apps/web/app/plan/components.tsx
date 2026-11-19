"use client";

import { ArrowRight, CalendarDays, Check, CircleHelp, MapPin } from "lucide-react";
import { FormEvent, useState } from "react";
import { api, money } from "../../lib/api";
import type { Component, Quote, Tour } from "../../lib/catalog";

export function MoneyPanel({ quote }: { quote: Quote }) {
  return <section className="panel quote-panel" aria-label="Verified quote">
    <span className="verified"><Check size={16} /> Verified from workbook rates</span>
    <h3>{quote.title}</h3>
    <span className="muted">{quote.date} · {quote.adults} adult{quote.adults === 1 ? "" : "s"}{quote.ages.length ? ` · Ages ${quote.ages.join(", ")}` : ""}</span>
    <span className="quote-reference">Quote {quote.id.slice(0, 8)}</span>
    <div className="total">{money(quote.total)}</div>
    <dl><div><dt>Deposit</dt><dd>{money(quote.deposit)}</dd></div>{quote.balance > 0 && <div><dt>Balance</dt><dd>{money(quote.balance)}</dd></div>}</dl>
  </section>;
}

function Picker({ value, send, disabled }: { value: Extract<Component, {type:"TravellerPicker"}>; send: (prompt: string, display?: string) => void; disabled: boolean }) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const ages = String(data.get("ages")).trim().replace(/\s/g, "");
    if (ages && !/^\d{1,3}(?:,\d{1,3})*$/.test(ages)) return;
    send(`@trip ${value.tour} ${data.get("date")} ${data.get("adults")} ${ages || "-"}`,
      `Check rates for ${data.get("adults")} adult(s) on ${data.get("date")}${ages ? `, with child ages ${ages}` : ""}.`);
  }
  return <form className="panel picker" onSubmit={submit}>
    <h3><CalendarDays size={19} /> Your travel details</h3>
    <div className="input-grid">
      <label>Travel date<input type="date" name="date" defaultValue={value.date ?? ""} required /></label>
      <label>Adults<input type="number" name="adults" defaultValue={value.adults} min={1} max={100} required /></label>
    </div>
    <label>Child ages, separated by commas<input name="ages" placeholder="e.g. 7, 10" defaultValue={value.ages.join(", ")} pattern="[0-9]{1,3}( *, *[0-9]{1,3})*" maxLength={100} /></label>
    <button className="button primary" disabled={disabled}>Check rates <ArrowRight size={17} /></button>
  </form>;
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
      setStatus(result.status === "success" ? `Demo booking confirmed · ${result.reference?.slice(0, 8)}`
        : errors[result.status] ?? "The demo booking did not complete. Please retry.");
    } catch {
      setStatus("The booking service couldn’t be reached. Please retry.");
    } finally {
      setBusy(false);
    }
  }
  return <form className="panel booking" onSubmit={submit}>
    <h3>Try a demo booking</h3><p className="muted">No payment details or personal information are needed.</p>
    <label>Simulation<select name="scenario"><option value="success">Successful booking</option><option value="declined">Payment declined</option><option value="unavailable">Booking unavailable</option><option value="network">Connection failure</option></select></label>
    <button className="button dark" disabled={busy}>{busy ? "Submitting…" : "Try demo booking"}</button>
    {status && <p role="status">{status}</p>}
  </form>;
}

export function JourneyCard({ tour, open, send, disabled }: { tour: Tour; open: (id: string) => void; send: (prompt: string, display?: string) => void; disabled: boolean }) {
  return <article className="panel journey-card">
    <div className="eyebrow">{[tour.category, tour.duration].filter(Boolean).join(" · ")}</div>
    <h3>{tour.title}</h3>
    <p>{tour.summary}</p>
    {tour.start && <p className="start"><MapPin size={16} /> {tour.start}</p>}
    <div className="card-actions">
      <button className="text-button" onClick={() => open(tour.source)}>Tour details</button>
      <button className="button outline" disabled={disabled} onClick={() => send(`@tour ${tour.id}`, `Plan ${tour.title}`)}>Select tour</button>
    </div>
  </article>;
}

export function RenderComponent({ value, ...actions }: {
  value: Component;
  open: (id: string) => void;
  send: (prompt: string, display?: string) => void;
  disabled: boolean;
}) {
  switch (value.type) {
    case "TourCard": return <JourneyCard tour={value} {...actions} />;
    case "TravellerPicker": return <Picker value={value} {...actions} />;
    case "PriceBreakdown": return <MoneyPanel quote={value.quote} />;
    case "BookingForm": return <Booking id={value.quote} />;
    case "EnquiryNotice": return <section className="panel notice"><CircleHelp size={22} /><div><h3>{value.text}</h3>{value.reference && <p>Enquiry {value.reference.slice(0, 8)}</p>}</div></section>;
    case "ItineraryDay":
    case "PolicySnippet":
    case "DestinationHighlight":
      return <section className="panel excerpt"><h3>{value.heading}</h3><p>{value.text.replaceAll("**", "")}</p>
        <button className="text-button" onClick={() => actions.open(value.source)}>View source <ArrowRight size={16} /></button></section>;
  }
}
