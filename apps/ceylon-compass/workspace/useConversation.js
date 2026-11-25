import { useEffect, useRef, useState } from "react";
import { api, entry, run, session } from "@/lib/live/service";

export function useConversation(seed, autoSubmitSeed = false) {
  const [items, setItems] = useState([]);
  const [input, setInput] = useState(autoSubmitSeed ? "" : (seed || ""));
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [remember, setRemember] = useState(false);
  const [privacyBusy, setPrivacyBusy] = useState(false);
  const trip = useRef("");
  const active = useRef(null);
  const pending = useRef(null);
  const autoSubmitted = useRef(false);
  useEffect(() => {
    let mounted = true;
    (async () => {
      const visitor = await session();
      let id = sessionStorage.getItem("mira-workspace-trip");
      if (!id && visitor.remember) id = (await api("/trips"))[0]?.id;
      let history = [];
      if (id) {
        const response = await fetch("/api/trips/" + encodeURIComponent(id));
        if (response.status === 404) id = null;
        else {
          if (!response.ok) throw Error();
          history = (await response.json()).history.map((h) => entry(h.prompt, h.turn, h.surface));
        }
      }
      if (!id) {
        id = (await api("/trips", { method: "POST" })).id;
      }
      if (!mounted) return;
      sessionStorage.setItem("mira-workspace-trip", id);
      trip.current = id;
      setItems(history);
      setRemember(Boolean(visitor.remember));
      setReady(true);
      setError("");
    })().catch(() => mounted && setError("Mira couldn’t open this conversation. Please retry."));
    return () => {
      mounted = false;
      active.current?.abort();
    };
  }, [attempt]);

  async function send(value = input, displayText) {
    const prompt = value.trim();
    if (!ready || !prompt || active.current) return;
    const controller = new AbortController();
    active.current = controller;
    if (pending.current?.prompt !== prompt) pending.current = { prompt, id: crypto.randomUUID() };
    setBusy(true);
    setError("");
    const timeout = setTimeout(() => controller.abort(), 65000);
    try {
      const item = await run(trip.current, prompt, pending.current.id, controller, () => {});
      if (displayText) item.displayPrompt = displayText;
      setItems((prior) => [...prior, item]);
      pending.current = null;
      setInput("");
    } catch {
      setInput(prompt);
      setError("Mira couldn’t finish this request. Retry to recover your turn.");
      const state = await fetch("/api/session", { cache: "no-store" }).catch(() => null);
      if (state?.status === 401) {
        setReady(false);
        setItems([]);
        pending.current = null;
        setError("Your visitor session expired. Reopen the conversation to start again.");
      }
    } finally {
      clearTimeout(timeout);
      active.current = null;
      setBusy(false);
    }
  }
  useEffect(() => {
    if (ready && autoSubmitSeed && seed && seed.trim() && !autoSubmitted.current && !active.current) {
      autoSubmitted.current = true;
      send(seed.trim());
    }
  }, [ready, autoSubmitSeed, seed]);

  async function newTrip() {
    if (!ready || active.current || busy) return;
    setReady(false);
    try {
      const { id } = await api("/trips", { method: "POST" });
      sessionStorage.setItem("mira-workspace-trip", id);
      trip.current = id;
      pending.current = null;
      setItems([]);
      setInput("");
      setError("");
    } catch {
      setError("Mira couldn’t start a new trip. Your current journey is still open.");
    } finally {
      setReady(true);
    }
  }

  async function consent(enabled) {
    setPrivacyBusy(true);
    try {
      const state = await api("/session", {
        method: "POST",
        body: JSON.stringify({ remember: enabled }),
      });
      setRemember(state.remember);
    } catch {
      setError("Couldn’t save your privacy preference. Please try again.");
    } finally {
      setPrivacyBusy(false);
    }
  }
  return {
    items,
    input,
    setInput,
    ready,
    busy,
    error,
    send,
    remember,
    consent,
    newTrip,
    privacyBusy,
    retry: () => (ready ? send() : setAttempt((n) => n + 1)),
  };
}
