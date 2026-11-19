"use client";

import { ArrowRight, ArrowUp, Compass, MapPin, MessageCircle, ShieldCheck, Sparkles, Users } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Image from "next/image";
import { api, starters } from "../lib/api";
import { queuePrompt } from "../lib/handoff";
import { Tour } from "../lib/catalog";

const featured = ["T01", "T08", "T05"];

export default function Home() {
  const [entry, setEntry] = useState("");
  const [items, setItems] = useState<Tour[]>();
  const router = useRouter();
  useEffect(() => { api<Tour[]>("/tours").then(setItems).catch(() => setItems([])); }, []);

  function plan(prompt: string) {
    if (!prompt.trim()) return;
    queuePrompt(prompt.trim());
    router.push("/plan");
  }

  return (
    <main>
      <section className="hero frame">
        <div className="hero-copy">
          <div className="eyebrow"><Sparkles size={15} /> YOUR PERSONAL TRAVEL COMPANION</div>
          <h1>Your island.<br /><em>Your story.</em></h1>
          <p className="hero-subtitle">Explore Sri Lanka, your way. Meet Mira, your travel companion for finding and planning a journey that fits.</p>
          <form className="hero-form" onSubmit={e => { e.preventDefault(); plan(entry); }}>
            <label className="sr-only" htmlFor="starter">Tell Mira what you have in mind</label>
            <MessageCircle size={20} aria-hidden="true" />
            <input id="starter" value={entry} onChange={e => setEntry(e.target.value)} placeholder="Tell Mira what you have in mind…" maxLength={1200} required />
            <button aria-label="Start planning" className="button send"><ArrowUp size={20} /></button>
          </form>
          <div className="starter-list">
            {starters.map(prompt => <button className="chip" key={prompt} onClick={() => plan(prompt)}>{prompt}</button>)}
          </div>
        </div>
        <figure className="hero-art">
          <Image src="/island.svg" alt="Illustrated Sri Lankan landscape with Sigiriya rising above forest at sunset" priority width={650} height={630} />
          <figcaption><MapPin size={14} /> SIGIRIYA, SRI LANKA</figcaption>
        </figure>
      </section>
      <div className="frame benefits" aria-label="What Mira can help with">
        <span><Compass size={19} /> Source-backed journeys</span>
        <span><ShieldCheck size={19} /> Workbook-verified quotes</span>
        <span><Users size={19} /> Specialist follow-up</span>
      </div>
      <section id="explore" className="frame section">
        <div className="eyebrow">FIND YOUR STARTING POINT</div>
        <h2>Explore journeys</h2>
        {!items && <p role="status">Loading journeys…</p>}
        {items?.length === 0 && <p>Journeys are temporarily unavailable. Try chatting with Mira.</p>}
        <div className="tour-grid">
          {featured.flatMap((id, index) => items?.filter(item => item.id === id).map(item => (
            <article className="tour-preview" key={id}>
              <div className={`landscape scene-${index}`} aria-hidden="true"><span /><i /><b /></div>
              <div className="tour-preview-content">
                <span className="eyebrow">{item.duration} · {item.category}</span>
                <h3>{item.title}</h3>
                <button className="text-button" onClick={() => plan(`@tour ${id}`)}>Explore this tour <ArrowRight size={16} /></button>
              </div>
            </article>
          )) ?? [])}
        </div>
      </section>
      <section id="how" className="frame section how">
        <h2>How Mira works</h2>
        <div className="steps">
          <div><MessageCircle size={24} /><h3>Tell Mira your plans</h3><p>Start with a place, a date, or the kind of trip you’re after.</p></div>
          <div><Compass size={24} /><h3>Explore your options</h3><p>See published journeys and a verified quote when rates are available.</p></div>
          <div><Users size={24} /><h3>Take the next step</h3><p>Try a demo booking or save an enquiry for a specialist.</p></div>
        </div>
      </section>
    </main>
  );
}
