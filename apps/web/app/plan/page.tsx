"use client";

import Image from "next/image";
import { destinationMedia } from "../../lib/media-manifest";
import { HttpAgent } from "@ag-ui/client";
import { ArrowUp, FileText, Map, MessageCircle, Sparkles, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { api, starters } from "../../lib/api";
import { Quote, Turn } from "../../lib/catalog";
import { BrandMark } from "../brand";
import { takePrompt } from "../../lib/handoff";
import { RenderComponent } from "./components";

type Bubble = { text: string; type: "user" | "mira"; time: string; sources?: string[] };
type RequestTurn = { prompt: string; id: string };
type Source = { title: string; body: string };

function timestamp() {
  return new Intl.DateTimeFormat(undefined, { timeStyle: "short" }).format(Date.now());
}

export default function Plan() {
  const [turn, setTurn] = useState<Turn>();
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
      if (!result) throw new Error("Mira couldn’t finish this turn. Please retry.");
      const confirmed = result;
      setTurn(confirmed);
      setBubbles(history => [...history, { text: confirmed.text, type: "mira", time: timestamp(), sources: confirmed.sources }]);
      if (isAction) setTab("journey");
      retry.current = null;
    } catch (error) {
      start.current = null;
      setAlert(error instanceof Error ? error.message : "Mira couldn’t respond. Please retry.");
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
      setAlert("Mira couldn’t update your preference. Try again.");
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    send(message);
  }

  return <main className="frame workspace">
    <div className="workspace-heading"><div className="eyebrow"><Sparkles size={15} /> CEYLON COMPASS HOLIDAYS</div><h1>Plan with Mira</h1></div>
    <div className="mobile-tabs" aria-label="Planning view">
      <button aria-pressed={tab === "chat"} onClick={() => setTab("chat")}><MessageCircle size={17} /> Conversation</button>
      <button aria-pressed={tab === "journey"} onClick={() => setTab("journey")}><Map size={17} /> Journey{turn && <i />}</button>
    </div>
    <div className={`planner ${tab === "chat" ? "chat-selected" : "journey-selected"}`}>
      <section className="conversation panel" aria-label="Conversation">
        <header className="conversation-header"><div className="avatar"><BrandMark size={25} /></div><div><h2>Mira</h2><p>Travel concierge</p></div></header>
        <div className="messages" ref={chat} aria-live="polite" aria-relevant="additions">
          <div className="bubble mira">{latest ? `Welcome back. Your latest saved quote is for ${latest.title}.`
            : "I’m Mira. Tell me where you’d like to go, or start with one of these ideas."}</div>
          {latest && !bubbles.length && <div className="sources">
            <button className="chip" onClick={() => send(`@tour ${latest.source}`, `Resume ${latest.title}`)}>Resume this tour</button>
          </div>}
          {!bubbles.length && <div className="chat-starters">{starters.map(prompt => <button className="chip" onClick={() => send(prompt)} key={prompt}>{prompt}</button>)}</div>}
          {bubbles.map((bubble, i) => <div key={i} className={`message-row ${bubble.type}`}>
            <div className={`bubble ${bubble.type}`}>{bubble.text}</div>
            <small>{bubble.time}</small>
            {bubble.sources?.length ? <div className="sources">{bubble.sources.map(src => <button key={src} className="chip" onClick={() => open(src)}><FileText size={14} /> Source {src}</button>)}</div> : null}
          </div>)}
          {waiting && <div className="bubble mira status" role="status">{streamed || "Mira is working on your request…"}</div>}
        </div>
        {alert && <div className="chat-error" role="alert">{alert} {retry.current && <button className="text-button" onClick={() => retry.current && void run(retry.current, false)}>Retry</button>}</div>}
        <form className="composer" onSubmit={submit}>
          <label className="sr-only" htmlFor="chat-input">Message Mira</label>
          <textarea id="chat-input" placeholder="Ask Mira about your trip…" rows={2} value={message}
            onChange={e => setMessage(e.target.value)} maxLength={1200}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send(message); } }} />
          <button className="button send" aria-label="Send message" disabled={waiting || !message.trim()}><ArrowUp size={21} /></button>
        </form>
        <label className="remember"><input type="checkbox" checked={remember} onChange={e => void changeConsent(e.target.checked)} /> Remember this browser</label>
      </section>
      <section className="canvas" aria-label="Your journey">
        <h2>Your journey</h2>
        {!turn?.components.length && <div className="canvas-empty scenic">
          <Image src={destinationMedia.ella.src} alt={destinationMedia.ella.alt} fill sizes="(max-width:740px) 96vw, 55vw"/>
          <h3>Start with a place or an idea</h3>
          <p>Tour details, travel options, and verified quotes will appear here as you plan.</p>
        </div>}
        <div className="canvas-components">
          {turn?.components.map((component, i) => <div key={`${turn.trace}-${i}`} className={component.type === "TourCard" ? "canvas-tour" : "canvas-wide"}>
            <RenderComponent value={component} send={send} open={open} disabled={waiting} />
          </div>)}
        </div>
      </section>
    </div>
    <dialog ref={dialog} data-source={sourceKey} aria-labelledby="source-title">
      <div className="dialog-head"><h2 id="source-title">{source?.title ?? "Loading source…"}</h2><button className="button icon-button" aria-label="Close source" onClick={() => dialog.current?.close()}><X size={20} /></button></div>
      {source && <div className="source-body">{source.body.replaceAll("**", "").replace(/^#+ /gm, "")}</div>}
    </dialog>
  </main>;
}
