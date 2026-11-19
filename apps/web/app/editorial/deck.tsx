"use client";

import Image from "next/image";
import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, ArrowUpRight, Compass } from "lucide-react";
import { destinationMedia } from "../../lib/media-manifest";
import type { Tour } from "../../lib/catalog";

import { PremiumActionButton } from "./action";

const Atlas = dynamic(() => import("./atlas"), { ssr: false });

const features = [
  { id: "T01", place: "Sigiriya", photo: "sigiriya", label: "Ancient Wonder" },
  { id: "T08", place: "Hill Country", photo: "tea", label: "Scenic Highlands" },
  { id: "T05", place: "Mirissa", photo: "mirissa", label: "Coastal Escape" },
  { id: "T04", place: "Galle Fort", photo: "galle", label: "Colonial Heritage" },
] as const;

export function DestinationPhotoDeck({ tours, plan }: { tours?: Tour[]; plan: (s: string) => void }) {
  const [selected, setSelected] = useState(0);
  const [atlas, setAtlas] = useState(false);
  const [unavailable, setUnavailable] = useState(false);
  const [capable, setCapable] = useState(false);

  useEffect(() => {
    const query = matchMedia(
      "(min-width: 1000px) and (hover: hover) and (prefers-reduced-motion: no-preference)"
    );
    function sync() { setCapable(query.matches && !document.hidden); }
    sync();
    query.addEventListener("change", sync);
    document.addEventListener("visibilitychange", sync);
    return () => {
      query.removeEventListener("change", sync);
      document.removeEventListener("visibilitychange", sync);
    };
  }, []);

  function toggleCompass() {
    if (atlas) { setAtlas(false); return; }
    const probe = document.createElement("canvas").getContext("webgl2");
    if (!probe) { setUnavailable(true); return; }
    probe.getExtension("WEBGL_lose_context")?.loseContext();
    setAtlas(true);
  }

  const choices = features.flatMap(f => {
    const tour = tours?.find(t => t.id === f.id);
    return tour ? [{ ...f, tour }] : [];
  });
  const active = choices[selected] ?? choices[0];

  return (
    <section className="collection editorial-gallery frame" id="explore">
      {/* Section heading */}
      <div className="collection-heading gallery-heading">
        <div>
          <span className="overline dark-label">The Journey Collection</span>
          <h2>Explore Sri Lanka</h2>
        </div>
        {active && (
          <div className="deck-controls">
            <button aria-label="Previous journey" onClick={() => setSelected((selected + choices.length - 1) % choices.length)}>
              <ArrowLeft/>
            </button>
            <button aria-label="Next journey" onClick={() => setSelected((selected + 1) % choices.length)}>
              <ArrowRight/>
            </button>
          </div>
        )}
      </div>

      {active ? (
        <>
          {/* Asymmetric bento grid */}
          <div className="gallery-bento">
            {/* Dominant panel (large, spans 2 rows) */}
            <div className="gallery-panel gallery-dominant">
              <Image
                src={destinationMedia[active.photo].src}
                alt={destinationMedia[active.photo].alt}
                fill
                sizes="(max-width: 900px) 100vw, 56vw"
              />
              <div className="gallery-panel-overlay"/>
              <div className="gallery-panel-copy">
                <span className="gallery-panel-label">{active.tour.category} · {active.tour.duration}</span>
                <h3 className="gallery-panel-title">{active.place}</h3>
                <p className="gallery-panel-summary">{active.tour.summary}</p>
                <PremiumActionButton variant="light" onClick={() => plan(`@tour ${active.id}`)}>
                  Plan this journey <ArrowUpRight size={16}/>
                </PremiumActionButton>
              </div>
              {capable && !unavailable && (
                <div className="atlas-box">
                  {atlas && (
                    <Atlas
                      selected={selected}
                      count={choices.length}
                      select={setSelected}
                      failed={() => { setAtlas(false); setUnavailable(true); }}
                    />
                  )}
                  <button className="atlas-toggle" aria-pressed={atlas} onClick={toggleCompass}>
                    <Compass size={16}/>
                    {atlas ? "Close compass" : "Explore by compass"}
                  </button>
                </div>
              )}
            </div>

            {/* Secondary panels */}
            {choices.slice(0, 3).map((f, i) => {
              if (i === selected && i === 0) return null; // skip dominant duplicate
              const isActive = selected === i;
              return (
                <button
                  key={f.id}
                  className={`gallery-panel gallery-secondary${isActive ? " gallery-secondary--active" : ""}`}
                  onClick={() => setSelected(i)}
                  aria-pressed={isActive}
                >
                  <Image
                    src={destinationMedia[f.photo].src}
                    alt={destinationMedia[f.photo].alt}
                    fill
                    sizes="(max-width: 900px) 50vw, 22vw"
                  />
                  <div className="gallery-panel-overlay"/>
                  <div className="gallery-secondary-copy">
                    <span className="gallery-panel-label">{f.label}</span>
                    <span className="gallery-secondary-title">{f.place}</span>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Panoramic strip */}
          <div className="gallery-panorama">
            {choices.map((f, i) => (
              <button
                key={f.id}
                className="photo-tile"
                aria-pressed={selected === i}
                onClick={() => setSelected(i)}
              >
                <div className="tile-media">
                  <Image
                    src={destinationMedia[f.photo].src}
                    alt=""
                    fill
                    sizes="(max-width: 640px) 40vw, 20vw"
                  />
                </div>
                <span className="tile-label">{f.place}</span>
                <h3>{f.tour.title}</h3>
              </button>
            ))}
          </div>
        </>
      ) : (
        <p role="status">
          {tours
            ? "No featured journeys are available. Ask Mira about a custom enquiry."
            : "Loading published journeys…"}
        </p>
      )}
    </section>
  );
}
