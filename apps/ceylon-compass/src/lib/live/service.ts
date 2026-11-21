import { Turn } from "./catalog";
import { readSurface } from "./surface";

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch("/api" + path, {
    ...options,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!res.ok)
    throw new Error(
      res.status === 404
        ? "This journey is unavailable in this visitor session."
        : "Mira’s service is unavailable. Please retry.",
    );
  return res.json();
}
let pending: Promise<unknown> | undefined;
export async function session() {
  if (!pending)
    pending = (async () => {
      const res = await fetch("/api/session");
      if (res.status === 401) return api("/session", { method: "POST", body: "{}" });
      if (!res.ok) throw Error("Could not open visitor session.");
      return res.json();
    })().finally(() => {
      pending = undefined;
    });
  return pending;
}
export type Entry = { prompt: string; turn: Turn; surface: ReturnType<typeof readSurface> };
export function entry(prompt: string, raw: unknown, surface: unknown): Entry {
  const turn = Turn.parse(raw);
  return { prompt, turn, surface: readSurface(surface, turn) };
}
export async function run(
  id: string,
  prompt: string,
  runId: string,
  signal: AbortController,
  progress: (s: string) => void,
) {
  const { HttpAgent } = await import("@ag-ui/client");
  const agent = new HttpAgent({
    url: "/api/agent?trip_id=" + encodeURIComponent(id),
    threadId: id,
    initialMessages: [{ id: runId, role: "user", content: prompt }],
  });
  let result: Entry | undefined;
  await agent.runAgent(
    { runId, abortController: signal },
    {
      onTextMessageContentEvent: ({ textMessageBuffer }) => progress(textMessageBuffer),
      onStateChanged: ({ state }) => {
        if (state?.["turn"] && state["surface"])
          result = entry(prompt, state["turn"], state["surface"]);
      },
    },
  );
  if (!result) throw Error("Mira couldn’t finish this turn. Retry to recover it.");
  return result;
}
