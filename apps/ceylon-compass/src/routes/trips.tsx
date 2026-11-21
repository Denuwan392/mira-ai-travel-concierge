import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { api, session } from "@/lib/live/service";
import { listTrips } from "@/lib/trip/storage";
import type { Trip as LegacyTrip } from "@/lib/trip/types";
type Trip = { id: string; title: string };
export const Route = createFileRoute("/trips")({ component: Trips });
function Trips() {
  const [legacy, setLegacy] = useState<LegacyTrip[]>([]);
  useEffect(() => setLegacy(listTrips()), []);
  const [items, setItems] = useState<Trip[]>([]);
  const [status, setStatus] = useState("Loading journeys…");
  useEffect(() => {
    session()
      .then(() => api<Trip[]>("/trips"))
      .then((next) => {
        setItems(next);
        setStatus(
          next.length ? "" : "Your journeys will appear here after your first conversation.",
        );
      })
      .catch(() => setStatus("Could not load your trips. Reload to retry."));
  }, []);
  return (
    <main className="folio">
      <p className="eyebrow">Your travel notebook</p>
      <h1>My trips</h1>
      <p role="status">{status}</p>
      {items.map((t) => (
        <Link className="trip-link" key={t.id} to="/plan" search={{ id: t.id }}>
          {t.title} <span>Open journey →</span>
        </Link>
      ))}
      {legacy.length > 0 && (
        <section>
          <h2>Earlier browser drafts</h2>
          {legacy.map((t) => (
            <details key={t.id}>
              <summary>{t.title}</summary>
              <p>
                {t.days} days · {t.party.adults} adults · {t.party.children} children
              </p>
              <Link
                className="pill"
                to="/plan"
                search={{ q: t.messages.find((m) => m.role === "user")?.text ?? t.title }}
              >
                Start a private notebook from this brief
              </Link>
            </details>
          ))}
        </section>
      )}
      <Link className="gold" to="/plan" search={{ fresh: "1" }}>
        Plan a new journey ✦
      </Link>
    </main>
  );
}
