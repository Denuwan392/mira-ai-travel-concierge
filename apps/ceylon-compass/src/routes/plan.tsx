import { createFileRoute, Link } from "@tanstack/react-router";
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { photos } from "@/lib/photos";
import { DEMO_BRIEF, JOURNEYS } from "@/lib/content";
const LiveCanvas = import.meta.env.SSR ? () => null : lazy(() =>
  import("@/components/plan/LiveCanvas").then((m) => ({ default: m.LiveCanvas })),
);
import { api, entry, run, session, type Entry } from "@/lib/live/service";
type Search = { q?: string; journey?: string; id?: string; fresh?: string };
export const Route = createFileRoute("/plan")({
  validateSearch: (raw: Record<string, unknown>): Search =>
    Object.fromEntries(
      ["q", "journey", "id", "fresh"]
        .filter((k) => typeof raw[k] === "string")
        .map((k) => [k, raw[k]]),
    ),
  component: Planner,
});

function Planner() {
  const params = Route.useSearch();
  const navigate = Route.useNavigate();
  const seed = params.q || JOURNEYS.find((j) => j.id === params.journey)?.brief || "";
  const [history, setHistory] = useState<Entry[]>([]),
    [input, setInput] = useState(""),
    [error, setError] = useState(""),
    [stream, setStream] = useState(""),
    [busy, setBusy] = useState(false),
    [loaded, setLoaded] = useState(false),
    [retryInit, setRetryInit] = useState(0),
    [tab, setTab] = useState("chat"),
    [pending, setPending] = useState("");
  const lock = useRef(false),
    request = useRef<{ text: string; runId: string } | null>(null),
    controller = useRef<AbortController | null>(null);
  const create = useRef<Promise<{ id: string }> | null>(null);
  const launched = useRef("");
  const log = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let active = true;
    setLoaded(false);
    setError("");
    setHistory([]);
    request.current = null;
    launched.current = "";
    (async () => {
      await session();
      if (!params.id) {
        create.current ??= api<{ id: string }>("/trips", { method: "POST" });
        const { id } = await create.current;
        if (active) {
          create.current = null;
          await navigate({ replace: true, search: { id, ...(seed ? { q: seed } : {}) } });
        }
        return;
      }
      const r = await api<{ history: Entry[] }>("/trips/" + encodeURIComponent(params.id));
      if (active) {
        setHistory(r.history.map((h) => entry(h.prompt, h.turn, h.surface)));
        if (r.history.length) setTab("journey");
        setLoaded(true);
      }
    })().catch((cause: unknown) => {
      if (active) {
        create.current = null;
        setError(cause instanceof Error && cause.message.includes("visitor session")
          ? "This trip is unavailable in this browser session."
          : "Mira couldn’t load your notebook. Check the connection and retry.");
      }
    });
    return () => {
      active = false;
      controller.current?.abort();
    };
  }, [params.id, retryInit]);
  async function send(text: string, runId = crypto.randomUUID() as string) {
    if (lock.current || !params.id || !text.trim()) return;
    lock.current = true;
    setBusy(true);
    setError("");
    setPending(text);
    setStream("");
    setInput("");
    request.current = { text, runId };
    const abort = new AbortController();
    controller.current = abort;
    const timeout = setTimeout(() => abort.abort(), 65000);
    try {
      const item = await run(params.id, text, runId, abort, setStream);
      setHistory((h) => [...h, item]);
      setPending("");
      request.current = null;
      if (seed) void navigate({ replace: true, search: { id: params.id } });
    } catch {
      setError("Mira could not finish this turn. Retry to recover the same request.");
    } finally {
      clearTimeout(timeout);
      lock.current = false;
      setBusy(false);
      setStream("");
    }
  }
  useEffect(() => {
    if (loaded && params.id && seed && !history.length && launched.current !== params.id) {
      launched.current = params.id;
      void send(seed, params.id);
    }
  }, [loaded, params.id, seed, history.length]);
  useEffect(() => {
    if (log.current) log.current.scrollTop = log.current.scrollHeight;
  }, [history, stream, busy]);
  const last = history.at(-1);
  const message = (s: string) =>
    s.startsWith("@day ")
      ? "View day " + s.slice(5)
      : s.startsWith("@depart ")
        ? "Set departure to " + s.slice(8)
        : s.startsWith("@tour ")
          ? "Explore published tour " + s.slice(6)
          : s.startsWith("@trip ")
            ? "Check rates for " + s.split(" ").slice(1, 3).join(" · ")
            : s;
  return (
    <main className={"workspace live-workspace tab-" + tab}>
      <nav className="workspace-tabs" aria-label="Planner views">
        {["chat", "journey"].map((t) => (
          <button disabled={!loaded} aria-pressed={tab === t} key={t} onClick={() => setTab(t)}>
            {t === "chat" ? "Conversation" : "Your journey"}
          </button>
        ))}
      </nav>
      <section className="conversation">
        <header>
          <p className="eyebrow">Ceylon Compass Holidays</p>
          <h1>
            <span>✦</span> Mira
          </h1>
          <p>Your Sri Lanka travel concierge</p>
        </header>
        <div className="messages" ref={log} role="log">
          <p className="bubble">
            Where shall we begin? Tell me where you’d like to go and who’s coming.
          </p>
          {history.map((h) => (
            <div className="exchange" key={h.turn.trace}>
              <p className="bubble user">{message(h.prompt)}</p>
              <p className="bubble">
                <small>✦ Mira</small>
                {h.turn.text}
              </p>
            </div>
          ))}
          {pending && <p className="bubble user">{message(pending)}</p>}
          {busy && <p role="status">{stream || "Mira is checking the catalogue…"}</p>}
        </div>
        {error && (
          <p role="alert">
            {error}{" "}
            <button
              className="pill"
              onClick={() =>
                request.current
                  ? void send(request.current.text, request.current.runId)
                  : setRetryInit((v) => v + 1)
              }
            >
              Retry
            </button>
            {!loaded && params.id && <Link className="pill" to="/plan" search={{ fresh: "1" }}>Start a new trip</Link>}
          </p>
        )}
        <div className="compose">
          <div className="suggestions">
            {(last
              ? ["Add another day in Ella", "Compare these tours"]
              : ["Sigiriya day trip for two adults on 10 January 2027", DEMO_BRIEF]
            ).map((s) => (
              <button disabled={busy || !loaded} key={s} onClick={() => send(s)}>
                {s}
              </button>
            ))}
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void send(input.trim());
            }}
          >
            <input
              maxLength={1200}
              aria-label="Message Mira"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Describe or change your journey…"
            />
            <button
              className="gold"
              aria-label="Send message"
              disabled={busy || !loaded || !input.trim()}
            >
              ↑
            </button>
          </form>
        </div>
      </section>
      <section className="canvas">
        <header className="canvas-head">
          <div>
            <p className="eyebrow">Your travel notebook</p>
            <h2>Your journey</h2>
          </div>
          <Link className="pill" to="/trips">
            My trips →
          </Link>
        </header>
        {last ? (
          <Suspense fallback={<p>Opening journey…</p>}>
            <LiveCanvas
              key={last.turn.trace}
              item={last}
              busy={busy}
              send={(s) => {
                void send(s);
                setTab("journey");
              }}
            />
          </Suspense>
        ) : (
          <div className="empty-canvas">
            <img src={photos.ella.src} alt={photos.ella.alt} />
            <div>
              <p className="eyebrow">Sri Lanka</p>
              <h2>
                The island, <em>your way.</em>
              </h2>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
