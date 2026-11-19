"use client";

import Image from "next/image";
import { ArrowUpRight, ChevronLeft, ChevronRight, MapPin } from "lucide-react";
import { useState } from "react";
import { destinationMedia } from "../../lib/media-manifest";

import { PremiumActionButton } from "./action";

const scenes = ["sigiriya", "ella", "mirissa"] as const;

export function CinematicHero({ plan }: { plan: (prompt: string) => void }) {
  const [scene, setScene] = useState(0);
  const [entry, setEntry] = useState("");
  const key = scenes[scene];
  const photo = destinationMedia[key];

  return (
    <section className="cinematic-hero" aria-label="Plan your Sri Lankan journey">
      {/* Decorative SVG background curves */}
      <svg className="hero-curve-bg" aria-hidden="true" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice">
        <path d="M-80 600 Q400 200 900 500 Q1200 700 1540 300" stroke="#F26B1D" strokeWidth="1" fill="none" strokeOpacity="0.12"/>
        <path d="M200 900 Q600 400 1100 750 Q1300 850 1540 600" stroke="#C5A778" strokeWidth="1" fill="none" strokeOpacity="0.10"/>
        <path d="M0 300 Q350 100 700 350 Q950 540 1200 200" stroke="#17392F" strokeWidth="0.8" fill="none" strokeOpacity="0.07"/>
      </svg>

      {/* LEFT: editorial text + form */}
      <div className="hero-editorial-left">
        <div className="hero-overline-row">
          <span className="hero-overline-line" aria-hidden="true"/>
          <span className="hero-overline-text">Ceylon Compass Holidays</span>
        </div>

        <h1 className="hero-headline">
          Your island.<br/>
          <em className="hero-headline-em">Your story.</em>
        </h1>

        <p className="hero-subtext">
          The island is yours. Make it unforgettable with Mira,<br/>
          your personal travel companion. Tell her what moves you.
        </p>

        <form
          className="travel-entry hero-entry"
          onSubmit={e => { e.preventDefault(); plan(entry); }}
        >
          <label htmlFor="hero-starter">
            <span className="mira-dot"/>
            Plan with Mira
          </label>
          <div>
            <textarea
              id="hero-starter"
              rows={1}
              required
              maxLength={1200}
              value={entry}
              placeholder="Where would you like to go?"
              onChange={e => setEntry(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  plan(entry);
                }
              }}
            />
            <PremiumActionButton variant="primary" className="ask" aria-label="Start planning">
              <ArrowUpRight size={22}/>
            </PremiumActionButton>
          </div>
        </form>

        <div className="hero-chips">
          {["Ella trip", "A Sigiriya day trip", "Design a custom journey"].map(s => (
            <button key={s} className="hero-chip" onClick={() => plan(s)}>
              {s}<ArrowUpRight size={12}/>
            </button>
          ))}
        </div>
      </div>

      {/* RIGHT: cinematic image */}
      <div className="hero-editorial-right">
        <div className="hero-image-frame">
          {key === "sigiriya" ? (
            <picture>
              <source media="(max-width: 640px)" srcSet="/media/licensed/sigiriya-mobile.webp"/>
              <source media="(max-width: 1280px)" srcSet="/media/licensed/sigiriya-medium.webp"/>
              <img
                className="hero-scene-photo"
                src="/media/licensed/sigiriya-wide.webp"
                alt={photo.alt}
                width={2200}
                height={1300}
                fetchPriority="high"
              />
            </picture>
          ) : (
            <Image
              className="hero-scene-photo"
              src={photo.src}
              alt={photo.alt}
              placeholder="blur"
              blurDataURL={photo.blurDataURL}
              fill
              sizes="(max-width: 900px) 100vw, 52vw"
              priority
            />
          )}

          {/* Floating location label */}
          <div className="hero-location-label">
            <MapPin size={13}/>
            <span>{photo.location}</span>
          </div>

          {/* Scene switcher */}
          <div className="hero-scene-controls scene-index">
            <span className="hero-scene-count scene-count">0{scene + 1} / 03</span>
            <button
              className="hero-scene-btn"
              aria-label="Previous landscape"
              onClick={() => setScene((scene + 2) % 3)}
            >
              <ChevronLeft size={18}/>
            </button>
            <button
              className="hero-scene-btn"
              aria-label="Next landscape"
              onClick={() => setScene((scene + 1) % 3)}
            >
              <ChevronRight size={18}/>
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
