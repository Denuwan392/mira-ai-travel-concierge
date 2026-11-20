"use client";

import Image from "next/image";

import { ArrowUpRight } from "lucide-react";

import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useMira } from "./plan/mira-shell";
import type { Tour } from "../lib/catalog";
import { destinationMedia } from "../lib/media-manifest";
import { CinematicHero } from "./editorial/hero";
import { DestinationPhotoDeck } from "./editorial/deck";

export default function Home() {
  const plan = useMira();
  const [tours, setTours] = useState<Tour[]>();
  const [story, setStory] = useState<{ title: string; body: string }>();
  useEffect(() => {
    api<Tour[]>("/tours").then(setTours).catch(() => setTours([]));
    api<{ title: string; body: string }>("/sources/D05").then(setStory).catch(() => {});
  }, []);
  const excerpt = story?.body.split("\n").find(line => line.trim() && !line.startsWith("#"));

  return (
    <main className="editorial-home">
      <CinematicHero plan={plan}/>
      <section className="home-trip-strip" aria-label="Destination starters">
        <header><span className="guide-kicker">Explore Sri Lanka</span><h2>Find your next escape</h2></header>
        {(["ella","sigiriya","mirissa"] as const).map((place,index)=>{
          const photo=destinationMedia[place];
          return <button className="trip-pick" key={place} onClick={()=>plan(["Ella trip","A Sigiriya day trip","Tell me about Mirissa"][index])}>
            <Image src={photo.src} alt={photo.alt} fill sizes="(max-width:900px) 30vw, 23vw"/><span>{photo.location}</span><ArrowUpRight size={18}/>
          </button>;
        })}
      </section>
      <DestinationPhotoDeck tours={tours} plan={plan}/>

      {/* Field note — editorial asymmetric two-column */}
      {story && excerpt && (
        <section className="field-note frame editorial-field-note">
          <div className="editorial-fn-image">
            <div className="story-photo editorial-story-crop">
              <Image
                src={destinationMedia.ella.src}
                alt={destinationMedia.ella.alt}
                fill
                sizes="(max-width: 700px) 90vw, 48vw"
              />
            </div>
            <div className="editorial-fn-caption">
              <span>Ella, Sri Lanka</span>
            </div>
          </div>
          <div className="editorial-fn-text">
            <span className="overline dark-label">Destination Notes</span>
            <h2 className="editorial-fn-headline">{story.title}</h2>
            <p className="editorial-fn-excerpt">{excerpt}</p>
            <details className="editorial-fn-details">
              <summary>Read the published source · D05</summary>
              <p>{story.body.replace(/^#+ /gm, "").replaceAll("**", "")}</p>
            </details>
          </div>
        </section>
      )}

      {/* Mira guide — editorial numbered steps */}
      <section id="how" className="mira-guide frame editorial-mira-guide">
        <div className="editorial-guide-header">
          <span className="overline dark-label">Meet Mira</span>
          <h2 className="editorial-guide-headline">
            From conversation<br/>to journey.
          </h2>
          <p className="editorial-guide-intro">
            Mira is your intelligent travel companion. She reads your intent,<br/>
            matches you with curated Sri Lankan experiences, and handles every detail.
          </p>
        </div>
        <ol className="editorial-guide-steps">
          <li className="editorial-guide-step">
            <span className="editorial-step-num" aria-hidden="true">01</span>
            <div>
              <strong>Tell Mira your plans</strong>
              <p>Start with a place, a date or the people coming with you.</p>
            </div>
          </li>
          <li className="editorial-guide-step">
            <span className="editorial-step-num" aria-hidden="true">02</span>
            <div>
              <strong>Explore published tours</strong>
              <p>Read the itinerary and open its source as you go.</p>
            </div>
          </li>
          <li className="editorial-guide-step">
            <span className="editorial-step-num" aria-hidden="true">03</span>
            <div>
              <strong>Check your travel details</strong>
              <p>Get a verified quote or save an enquiry for a specialist.</p>
            </div>
          </li>
        </ol>
      </section>

      {/* Closing — cinematic full-bleed with large serif CTA */}
      <section className="closing editorial-closing">
        <Image
          src={destinationMedia.coast.src}
          alt={destinationMedia.coast.alt}
          fill
          sizes="100vw"
        />
        <div className="editorial-closing-inner">
          <span className="editorial-closing-overline">Begin your journey</span>
          <h2 className="editorial-closing-headline">Where to next?</h2>
          <p className="editorial-closing-sub">
            Every great trip starts with a single conversation.
          </p>
          <button onClick={()=>plan()} className="lux-action editorial-closing-cta">
            Start planning with Mira <ArrowUpRight size={18}/>
          </button>
        </div>
      </section>
    </main>
  );
}
