"use client";

import { ArrowUpRight, Compass } from "lucide-react";
import { FormEvent, useState } from "react";
import { useMira } from "./mira-shell";
import { destinationMedia } from "../../lib/media-manifest";

export default function PlannerPage() {
  const open = useMira();
  const [text, setText] = useState("");
  function submit(e: FormEvent) {
    e.preventDefault();
    if (text.trim()) open(text.trim());
  }
  return (
    <main className="planner-entry frame">
      <div className="planner-intro">
        <span className="guide-kicker">
          <Compass size={16} /> Ceylon Compass Holidays
        </span>
        <h1>Plan your trip with Mira</h1>
        <p>
          Explore Sri Lanka’s published journeys, compare routes and check your
          travel dates.
        </p>
        <form onSubmit={submit}>
          <label className="sr-only" htmlFor="planner-search">
            Ask Mira about a city or tour
          </label>
          <input
            id="planner-search"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Where in Sri Lanka would you like to go?"
            maxLength={1200}
            required
          />
          <button className="lux-action" aria-label="Ask Mira">
            Ask Mira <ArrowUpRight size={17} />
          </button>
        </form>
        <button className="guide-back" onClick={() => open(undefined, true)}>
          Browse published journeys
        </button>
      </div>
      <h2>Try asking</h2>
      <div className="planner-ideas">
        {(["ella", "sigiriya", "galle"] as const).map((key, i) => (
          <button
            key={key}
            onClick={() =>
              open(
                ["Ella trip", "A Sigiriya day trip", "Tell me about Galle"][i],
              )
            }
          >
            <img
              src={destinationMedia[key].src}
              alt={destinationMedia[key].alt}
            />
            <span>
              {["Ella trip", "A Sigiriya day trip", "Explore Galle"][i]}{" "}
              <ArrowUpRight size={16} />
            </span>
          </button>
        ))}
      </div>
    </main>
  );
}
