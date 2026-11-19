"use client";

import { Guide } from "../../lib/guide";
import { GuideBoard } from "./guide-board";
import "./advisor.css";
import { HttpAgent } from "@ag-ui/client";
import { ArrowUp, FileText, Map, MessageCircle, Sparkles, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { api, starters } from "../../lib/api";
import { Quote, Turn } from "../../lib/catalog";
import { BrandMark } from "../brand";
import { takePrompt } from "../../lib/handoff";
import { RenderComponent } from "./components";

type Bubble = { text: string; type: "user" | "mira"; time: string; sources?: string[]; result?: Turn; comparison?: boolean };
type RequestTurn = { prompt: string; id: string };
type Source = { title: string; body: string };

function timestamp() {
  return new Intl.DateTimeFormat(undefined, { timeStyle: "short" }).format(Date.now());
}

export default function Plan() {
  const [turn, setTurn] = useState<Turn>();
  const [guide, setGuide] = useState<Guide>();
  const [guideError, setGuideError] = useState(false);
  const [saved, setSaved] = useState<string[]>([]);
  const [preview, setPreview] = useState<Turn>();
  useEffect(() => {
    api<unknown>("/guide").then(raw => setGuide(Guide.parse(raw))).catch(() => setGuideError(true));
  }, []);
  const [tab, setTab] = useState("chat");
  const [message, setMessage] = useState("");
  const [waiting, setWaiting] = useState(false);
  const [streamed, setStreamed] = useState("");
  const [alert, setAlert] = useState("");
  const [bubbles, setBubbles] = useState<Bubble[]>([]);
  const [source, setSource] = useState<Source>();
  const [sourceKey, setSourceKey] = useState("");
  const [remember, setRemember] = useState(false);
  const [latest, setLatest] = useState<Quote>();
  const retry = useRef<RequestTurn>(null);
  const busy = useRef(false);
  const start = useRef<Promise<{ remember: boolean }>>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const activeSource = useRef("");
  const thread = useRef("");
  const chat = useRef<HTMLDivElement>(null);

  function ensureSession() {
    start.current ??= api<{ remember: boolean }>("/session").catch(() => api("/session", {
      method: "POST", body: JSON.stringify({ remember: false }),
    }));
    return start.current;
  }

  const run = useCallback(async (request: RequestTurn, isAction: boolean) => {
    if (busy.current) return;
    busy.current = true;
    setWaiting(true);
    setStreamed("");
    setAlert("");
    retry.current = request;
    const abortController = new AbortController();
    const timer = setTimeout(() => abortController.abort(), 18000);
    try {
      const session = await ensureSession();
      setRemember(session.remember);
      thread.current ||= crypto.randomUUID();
      let result: Turn | undefined;
      const agent = new HttpAgent({
        url: "/api/copilotkit/agent/mira/run",
        threadId: thread.current,
        initialMessages: [{ id: request.id, role: "user", content: request.prompt }],
      });
      await agent.runAgent({ runId: request.id, abortController }, {
        onTextMessageContentEvent: ({ textMessageBuffer }) => {
          setStreamed(textMessageBuffer);
        },
        onStateChanged: ({ state }) => {
          if (state?.turn) {
            const parsed = Turn.safeParse(state.turn);
            if (parsed.success) result = parsed.data;
          }
        },
      });
      if (!result) throw new Error("Mira couldn't finish this turn. Please retry.");
      const confirmed = result;
      setTurn(confirmed);
      setPreview(undefined);
      setBubbles(history => [...history, { text: confirmed.text, type: "mira", time: timestamp(), sources: confirmed.sources, result: confirmed, comparison: /^(please )?compare /i.test(request.prompt) }]);
      if (isAction) setTab("journey");
      retry.current = null;
    } catch (error) {
      start.current = null;
      setAlert(error instanceof Error ? error.message : "Mira couldn't respond. Please retry.");
    } finally {
      clearTimeout(timer);
      busy.current = false;
      setWaiting(false);
    }
  }, []);

  const send = useCallback((prompt: string, display?: string) => {
    if (!prompt.trim() || busy.current) return;
    setMessage("");
    setBubbles(history => [...history, { text: display || prompt, type: "user", time: timestamp() }]);
    void run({ prompt: prompt.trim(), id: crypto.randomUUID() }, Boolean(display));
  }, [run]);

  useEffect(() => {
    if (window.location.hash === "#destinations") setTab("journey");
    const first = takePrompt();
    if (first) queueMicrotask(() => send(first, first.startsWith("@tour ") ? "Explore a published tour" : undefined));
    else ensureSession().then(async s => {
      setRemember(s.remember);
      if (!s.remember) return;
      const [row] = await api<{current: boolean; quote?: Quote}[]>("/quotes");
      const quote = Quote.safeParse(row?.quote);
      if (row?.current && quote.success) setLatest(quote.data);
    }).catch(() => {});
  }, [send]);

  useEffect(() => {
    if (chat.current) chat.current.scrollTop = chat.current.scrollHeight;
  }, [bubbles, waiting]);

  function open(id: string) {
    activeSource.current = id;
    setSource(undefined);
    setSourceKey(id);
    dialog.current?.showModal();
    api<Source>(`/sources/${id}`).then(data => {
      if (dialog.current?.open && activeSource.current === id) setSource(data);
    }).catch(() => setSource({ title: "Source unavailable", body: "Try again in a moment." }));
  }

  async function changeConsent(next: boolean) {
    try {
      await ensureSession();
      const result = await api<{ remember: boolean }>("/session", { method: "POST", body: JSON.stringify({ remember: next }) });
      start.current = Promise.resolve(result);
      setRemember(result.remember);
      if (!result.remember) setLatest(undefined);
      setAlert("");
    } catch {
      setAlert("Mira couldn't update your preference. Try again.");
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    send(message);
  }

  const displayed = preview ?? turn;
  const resultIds = displayed?.components.flatMap(c => c.type === "TourCard" ? [c.id] : []);
  const destination = Object.entries(guide?.places ?? {}).find(([,p]) => displayed?.sources.includes(p.id));
  const exploration = !displayed || Boolean(destination) || displayed.components.every(c => c.type === "TourCard");
  const showBoard = Boolean(guide && (exploration || resultIds?.length));
  const showResults = (result: Turn) => {setPreview(result === turn ? undefined : result); setTab("journey");};
  return (
    <main className="frame workspace advisor-workspace">
      {/* Workspace Header */}
      <div className="workspace-heading planner-workspace-heading">
        <div className="eyebrow"><Sparkles size={15} /> CEYLON COMPASS HOLIDAYS · SRI LANKA</div>
        <h1 className="planner-title serif">Trip planner</h1>
      </div>

      {/* Mobile tab switcher */}
      <div className="mobile-tabs" aria-label="Planning view">
        <button aria-pressed={tab === "chat"} onClick={() => setTab("chat")}>
          <MessageCircle size={17} /> Conversation
        </button>
        <button aria-pressed={tab === "journey"} onClick={() => setTab("journey")}>
          <Map size={17} /> Journey{turn && <i />}
        </button>
      </div>

      {/* Three-column bento grid */}
      <div className={`planner bento-workspace ${tab === "chat" ? "chat-selected" : "journey-selected"}`}>

        {/* LEFT: Chat Panel */}
        <section className="conversation panel workspace-chat" aria-label="Conversation">
          <header className="conversation-header chat-header">
            <div className="chat-avatar">
              <BrandMark size={24} />
              <span className="mira-status" aria-hidden="true" />
            </div>
            <div className="chat-header-info">
              <h2>Mira</h2>
              <p>{waiting ? <span role="status" className="mira-thinking">Working on your trip…</span> : "Your travel concierge"}</p>
            </div>
          </header>

          <div className="messages" ref={chat} aria-live="polite" aria-relevant="additions">
            {/* Welcome / latest quote bubble */}
            <div className="bubble mira">
              {latest
                ? `Welcome back. Your latest saved quote is for ${latest.title}.`
                : "I'm Mira. Tell me where you'd like to go, or start with one of these ideas."}
            </div>

            {/* Resume chip for latest quote */}
            {latest && !bubbles.length && (
              <div className="sources">
                <button className="chip" onClick={() => send(`@tour ${latest.source}`, `Resume ${latest.title}`)}>
                  Resume this tour
                </button>
              </div>
            )}

            {/* Starter suggestions */}
            {!bubbles.length && (
              <div className="chat-starters">
                {["Ella trip", ...starters].map(prompt => (
                  <button className="chip suggestion-chip" onClick={() => send(prompt)} key={prompt}>
                    {prompt}
                  </button>
                ))}
              </div>
            )}

            {/* Conversation bubbles */}
            {bubbles.map((bubble, i) => (
              <div key={i} className={`message-row ${bubble.type}`}>
                <div className={`bubble ${bubble.type}`}>{bubble.text}</div>
                <small>{bubble.time}</small>
                {bubble.result===turn && bubble.result && bubble.result.components.filter(c=>c.type==="TourCard").length>1 && !bubble.comparison && <button className="chat-result" disabled={waiting} onClick={()=>send("Compare these tours")}><Map size={15}/>Compare these tours</button>}
                {bubble.result?.components.some(c=>c.type==="TourCard" || c.type==="DestinationHighlight") && (
                  <button className="chat-result" onClick={()=>showResults(bubble.result!)}><Map size={15}/>Explore these results</button>
                )}
                {bubble.sources?.length ? (
                  <div className="sources">
                    {bubble.sources.map(src => (
                      <button key={src} className="chip" onClick={() => open(src)}>
                        <FileText size={14} /> Source {src}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}

            {/* Streaming / waiting indicator */}
            {waiting && (
              <div className="bubble mira status" role="status">
                {streamed || "Mira is working on your request…"}
              </div>
            )}
          </div>

          {/* Error / alert bar */}
          {alert && (
            <div className="chat-error" role="alert">
              {alert}{" "}
              {retry.current && (
                <button className="text-button" onClick={() => retry.current && void run(retry.current, false)}>
                  Retry
                </button>
              )}
            </div>
          )}

          {/* Message composer */}
          <form className="composer" onSubmit={submit}>
            <label className="sr-only" htmlFor="chat-input">Message Mira</label>
            <textarea
              id="chat-input"
              placeholder="Ask Mira about your trip…"
              rows={2}
              value={message}
              onChange={e => setMessage(e.target.value)}
              maxLength={1200}
              onKeyDown={e => {
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault();
                  send(message);
                }
              }}
            />
            <button className="button send composer-send" aria-label="Send message" disabled={waiting || !message.trim()}>
              <ArrowUp size={21} />
            </button>
          </form>

          {/* Remember / consent checkbox */}
          <label className="remember">
            <input type="checkbox" checked={remember} onChange={e => void changeConsent(e.target.checked)} />
            Remember this browser
          </label>
        </section>

        <section id="destinations" className="canvas journey-canvas advisor-canvas" aria-label="Your journey">
          {preview && <button className="history-return" onClick={()=>setPreview(undefined)}>Viewing earlier results · Return to latest trip</button>}
          {displayed && !preview && !exploration && <div className="guide-result-heading"><span className="guide-kicker">Your journey</span><h2>{displayed.components.some(c=>c.type==="PriceBreakdown")?"Your trip quote":displayed.components.some(c=>c.type==="EnquiryNotice")?"Specialist handoff":"Trip details"}</h2></div>}
          <div className="advisor-components">
            {displayed?.components.filter(c=>{
              if(preview && ["PriceBreakdown","BookingForm","TravellerPicker"].includes(c.type)) return false;
              return !(showBoard && exploration && c.type==="TourCard");
            }).map((c,i)=><RenderComponent key={displayed.trace+"-"+i} value={c} send={send} open={open} disabled={waiting}/>)}
          </div>
          {showBoard && guide && <GuideBoard key={displayed?.trace??"welcome"} guide={guide} results={resultIds} initialPlace={destination?.[0]} comparison={Boolean(displayed && bubbles.find(b=>b.result?.trace===displayed.trace)?.comparison)} contextual={Boolean(displayed)} send={send} open={open} busy={waiting} saved={saved}
            toggleSaved={id=>setSaved(old=>old.includes(id)?old.filter(k=>k!==id):[...old,id])}/>}
          {!guide && !displayed && <p role="status">{guideError?"The destination guide is unavailable. You can still ask Mira about a trip.":"Loading published journeys…"}</p>}
        </section>
      </div>

      {/* Source dialog */}
      <dialog ref={dialog} data-source={sourceKey} aria-labelledby="source-title">
        <div className="dialog-head">
          <h2 id="source-title">{source?.title ?? "Loading source…"}</h2>
          <button className="button icon-button" aria-label="Close source" onClick={() => dialog.current?.close()}>
            <X size={20} />
          </button>
        </div>
        {source && <div className="source-body">{source.body.replaceAll("**", "").replace(/^#+ /gm, "")}</div>}
      </dialog>
    </main>
  );
}
