"use client";

import { ArrowRight, Briefcase, Trash2 } from "lucide-react";
import { useMira } from "../plan/mira-shell";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { Quote } from "../../lib/catalog";
import { MoneyPanel } from "../plan/components";

type Saved = { current: true; quote: Quote } | { current: false; title: string; date: string };

export default function MyTrips() {
  const launch=useMira();
  const [quotes, setQuotes] = useState<Saved[]>();
  const [hasSession, setHasSession] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => {
    api("/session").then(() => {
      setHasSession(true);
      return api<Saved[]>("/quotes").then(setQuotes).catch(() => setMessage("Couldn’t load saved trips. Refresh to retry."));
    }).catch(() => setQuotes([]));
  }, []);

  async function forget() {
    try {
      await api("/session", { method: "DELETE" });
      setQuotes([]);
      setHasSession(false);
      setMessage("This browser’s access and remembered trip details have been cleared.");
    } catch {
      setMessage("Couldn’t clear your trip details. Try again.");
    }
  }

  return <main className="frame workspace saved-page">
    <div className="workspace-heading"><span className="eyebrow"><Briefcase size={17} /> YOUR TRAVEL PLANS</span><h1>My trips</h1></div>
    {message && <p role="status">{message}</p>}
    {!quotes && !message && <p role="status">Loading saved trips…</p>}
    {quotes?.length === 0 && <div className="canvas-empty"><h2>No saved quotes</h2><p>When Mira verifies a quote, it will appear here.</p></div>}
    <div className="saved-grid">{quotes?.map((row, i) => row.current
      ? (() => { const parsed = Quote.safeParse(row.quote); return parsed.success ? <MoneyPanel key={parsed.data.id} quote={parsed.data} /> : null; })()
      : <section key={i} className="panel"><h3>{row.title}</h3><p>{row.date} · Rates need rechecking</p></section>)}</div>
    <div className="card-actions">
      <button onClick={()=>launch()} className="button primary">Resume planning <ArrowRight size={17} /></button>
      {hasSession && <button className="button outline" onClick={() => void forget()}><Trash2 size={16} /> Forget this browser</button>}
    </div>
  </main>;
}
