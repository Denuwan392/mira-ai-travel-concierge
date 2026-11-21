import { buildItinerary } from "@/lib/trip/itinerary";
import { computeQuote, formatMoney, LIVE_RATES, SAMPLE_RATES } from "@/lib/trip/quote";
import { photos } from "@/lib/photos";
import type { RouteStop, Trip } from "@/lib/trip/types";
import { saveTrip } from "@/lib/trip/storage";

function MapPreview({ route }: { route: RouteStop[] }) {
  const point = (lat: number, lon: number) => [(lon - 79.6) * 110 + 24, (8.2 - lat) * 65 + 14];
  const dots = route.map(({ stop }) => point(stop.lat, stop.lon));
  return (
    <figure className="route-map">
      <svg
        viewBox="0 0 290 175"
        role="img"
        aria-label={"Route map: " + route.map((r) => r.stop.name).join(" to ")}
      >
        <polyline
          points={dots.map((d) => d.join(",")).join(" ")}
          fill="none"
          stroke="#986629"
          strokeWidth="2"
          strokeDasharray="4 3"
        />
        {route.map(({ stop }, i) => {
          const [x, y] = dots[i]!;
          return (
            <g key={stop.id}>
              <circle cx={x} cy={y} r="4" fill="#7a1832" />
              <text x={x! + 6} y={y! - 5} fontSize="8">
                {stop.name}
              </text>
            </g>
          );
        })}
      </svg>
      <figcaption>Route sketch · Sri Lanka</figcaption>
    </figure>
  );
}
export function TripCanvas({ trip, update }: { trip: Trip; update: (t: Trip) => void }) {
  const itinerary = buildItinerary(trip);
  const cover = itinerary.route.find((r) => r.stop.id === "ella") ?? itinerary.route[0];
  const quote = computeQuote(trip, itinerary, LIVE_RATES);
  const sample = computeQuote(trip, itinerary, SAMPLE_RATES);
  const change = (partial: Partial<Trip>) => update({ ...trip, ...partial, enquiry: null });
  return (
    <>
      {cover && (
        <figure className="canvas-cover" key={cover.stop.id}>
          <img src={photos[cover.stop.photo].src} alt={photos[cover.stop.photo].alt} />
          <figcaption>
            <small>FIELD NOTES / SRI LANKA</small>
            <strong>{cover.stop.name}</strong>
          </figcaption>
        </figure>
      )}
      <div className="route-summary">
        <div>
          <p className="eyebrow">Your route</p>
          <h3>{itinerary.route.map((r) => r.stop.name).join(" → ")}</h3>
          <p>
            {trip.days} days · {trip.party.adults + trip.party.children} travellers · {trip.pace}{" "}
            pace
          </p>
        </div>
        <MapPreview route={itinerary.route} />
      </div>
      <div className="fields travel-fields">
        <label>
          Departure
          <input
            type="date"
            value={trip.startDate ?? ""}
            onChange={(e) => change({ startDate: e.target.value || null })}
          />
        </label>
        {(["adults", "children"] as const).map((key) => (
          <label key={key}>
            {key === "adults" ? "Adults" : "Children"}
            <select
              value={trip.party[key]}
              onChange={(e) => change({ party: { ...trip.party, [key]: Number(e.target.value) } })}
            >
              {Array.from({ length: Math.max(12, trip.party[key] + 1) }, (_, i) => i)
                .filter((n) => n || key === "children")
                .map((n) => (
                  <option key={n}>{n}</option>
                ))}
            </select>
          </label>
        ))}
      </div>
      <h3 className="chapter">The itinerary</h3>
      <div className="timeline">
        {itinerary.days.map((d) => (
          <article key={d.day}>
            <img loading="lazy" src={photos[d.photo].src} alt={photos[d.photo].alt} />
            <div>
              <p className="eyebrow">
                Day {String(d.day).padStart(2, "0")} · {d.stopId} {d.date && " · " + d.date}
              </p>
              <h4>{d.title}</h4>
              <p>{d.story}</p>
              <details>
                <summary>Activities</summary>
                {d.activities.map((a) => (
                  <p key={a.id}>
                    <b>{a.title}</b> · {a.duration}
                    <br />
                    {a.blurb}
                  </p>
                ))}
              </details>
            </div>
          </article>
        ))}
      </div>
      <h3 className="chapter">Where you’ll stay</h3>
      <div className="stays">
        {itinerary.route
          .filter((r) => r.nights > 0)
          .map((r) => (
            <label key={r.stop.id}>
              <img loading="lazy" src={photos[r.hotel.photo].src} alt={photos[r.hotel.photo].alt} />
              <small>
                {r.stop.name} · {r.nights} nights
              </small>
              <select
                aria-label={"Stay in " + r.stop.name}
                value={r.hotel.id}
                onChange={(e) =>
                  change({ hotelChoices: { ...trip.hotelChoices, [r.stop.id]: e.target.value } })
                }
              >
                {r.stop.hotels.map((h) => (
                  <option key={h.id} value={h.id}>
                    {h.name}
                  </option>
                ))}
              </select>
              <p>{r.hotel.blurb}</p>
            </label>
          ))}
      </div>
      <section className="quote">
        <p className="eyebrow">Your trip quote</p>
        <h3>{quote.total === null ? "Price confirmation needed" : formatMoney(quote.total)}</h3>
        <p>
          {quote.total === null
            ? "A specialist needs to confirm availability and rates for these dates and stays."
            : "Rate verified · Deposit " + formatMoney(quote.deposit!)}
        </p>
        {sample.total !== null && (
          <details>
            <summary>View illustrative pricing</summary>
            <p>Sample rates · for demonstration only</p>
            {sample.lines.map((l) => (
              <div className="price-line" key={l.key}>
                <span>{l.label}</span>
                <b>{formatMoney(l.amount!)}</b>
              </div>
            ))}
            <p>
              Total {formatMoney(sample.total)} · Deposit {formatMoney(sample.deposit!)}
            </p>
          </details>
        )}
        {trip.enquiry ? (
          <p role="status">Enquiry saved on this device · {trip.enquiry.reference}</p>
        ) : (
          <details>
            <summary>Prepare an enquiry →</summary>
            <form
              className="fields"
              onSubmit={(e) => {
                e.preventDefault();
                const values = new FormData(e.currentTarget);
                update(
                  saveTrip({
                    ...trip,
                    enquiry: {
                      name: String(values.get("name")),
                      email: String(values.get("email")),
                      notes: String(values.get("notes")),
                      phone: "",
                      submittedAt: new Date().toISOString(),
                      reference: crypto.randomUUID().slice(0, 8),
                      demo: true,
                    },
                  }),
                );
              }}
            >
              <label>
                Name
                <input name="name" required />
              </label>
              <label>
                Email
                <input name="email" type="email" required />
              </label>
              <label>
                Notes
                <textarea name="notes" />
              </label>
              <p>Demo enquiries stay in this browser.</p>
              <button className="gold">Save enquiry locally</button>
            </form>
          </details>
        )}
      </section>
    </>
  );
}
