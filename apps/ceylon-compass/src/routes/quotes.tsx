import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { api, session } from "@/lib/live/service";

export const Route = createFileRoute("/quotes")({
  component: QuotesPage,
});

type PublicQuote = {
  id: string;
  source: string;
  title: string;
  date: string;
  adults: number;
  ages: number[];
  total: number;
  deposit: number;
};

type QuoteItem =
  | { current: true; quote: PublicQuote }
  | { current: false; title: string; date: string; total?: number; deposit?: number };

export default function QuotesPage() {
  const [quotes, setQuotes] = useState<QuoteItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadQuotes() {
      setLoading(true);
      setError("");
      try {
        await session();
        try {
          // Attempt traveller-specific quotes endpoint
          const res = await api<QuoteItem[]>("/traveller/quotes");
          setQuotes(res);
        } catch {
          // Fallback to visitor quotes endpoint
          const res = await api<QuoteItem[]>("/quotes");
          setQuotes(res);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load quotes.");
      } finally {
        setLoading(false);
      }
    }
    loadQuotes();
  }, []);

  return (
    <main className="folio">
      <p className="eyebrow">Ceylon Compass Holidays</p>
      <h1>My verified quotes</h1>
      <p>
        Review deterministic quotes verified against our official rates. Quotes stay bookable until departure dates pass.
      </p>

      {error && (
        <div role="status" className="my-4 p-3 rounded-lg bg-coral/10 text-ink border border-coral/50 text-sm">
          {error}
        </div>
      )}

      {loading && <p role="status">Loading verified quotes…</p>}

      {!loading && quotes.length === 0 && (
        <div className="bg-paper-deep rounded-2xl p-8 text-center my-6 border border-border">
          <h2 className="text-xl font-semibold mb-2">No quotes found yet</h2>
          <p className="text-muted-foreground mb-6">
            Ask Mira to plan your journey and verify an exact quote with official seasonal rates.
          </p>
          <Link to="/plan" className="gold">
            Ask Mira for a Quote ✦
          </Link>
        </div>
      )}

      <div className="grid gap-4 my-6">
        {quotes.map((q, idx) => {
          if (q.current) {
            return (
              <div key={q.quote.id} className="bg-white rounded-xl p-6 border border-saffron/40 shadow-xs">
                <div className="flex justify-between items-start flex-wrap gap-2 mb-2">
                  <h3 className="font-semibold text-lg">{q.quote.title}</h3>
                  <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-leaf/10 text-ink border border-leaf/50">
                    Verified rate
                  </span>
                </div>
                <p className="text-sm text-muted-foreground mb-4">
                  Departure: {q.quote.date} • Party: {q.quote.adults} Adults
                  {q.quote.ages?.length ? `, Children: ages ${q.quote.ages.join(", ")}` : ""}
                </p>
                <div className="flex items-baseline justify-between flex-wrap gap-4 pt-3 border-t border-border">
                  <div>
                    <span className="text-2xl font-bold text-ink">USD {q.quote.total.toLocaleString()}</span>
                    <span className="text-xs text-muted-foreground ml-3">Deposit: USD {q.quote.deposit.toLocaleString()}</span>
                  </div>
                  <Link to="/plan" search={{ id: q.quote.id }} className="pill text-xs font-semibold">
                    Open in Planner →
                  </Link>
                </div>
              </div>
            );
          } else {
            return (
              <div key={idx} className="bg-paper-deep rounded-xl p-5 border border-border opacity-80">
                <div className="flex justify-between items-start flex-wrap gap-2 mb-1">
                  <h3 className="font-semibold text-base">{q.title}</h3>
                  <span className="text-xs px-2 py-0.5 rounded-full font-semibold bg-sun/10 text-ink border border-sun/50">
                    Rates need rechecking
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">Departure date: {q.date}</p>
                <div className="mt-3 text-xs text-muted-foreground">
                  This rate was verified for an earlier departure or prior season. Ask Mira for a refreshed quote.
                </div>
              </div>
            );
          }
        })}
      </div>

      <div className="mt-8 flex gap-4">
        <Link to="/plan" className="gold">
          Plan a New Journey ✦
        </Link>
        <Link to="/profile" className="pill">
          Back to Profile
        </Link>
      </div>
    </main>
  );
}
