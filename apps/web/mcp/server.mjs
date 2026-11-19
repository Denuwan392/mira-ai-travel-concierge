/** Local MCP transport. FastAPI remains the sole authority for catalogue, quotes and enquiries. */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const api = process.env.MIRA_API_URL ?? "http://127.0.0.1:8000";
const mcp = new McpServer({ name: "mira-travel", version: "1.0.0" });
let session;

async function backend(path, options = {}) {
  const response = await fetch(`${api}/api${path}`, { ...options, signal: AbortSignal.timeout(20000) });
  if (!response.ok) throw new Error("Mira could not complete this request. Check the local service.");
  return response;
}

function getSession() {
  session ??= backend("/session", {
    method: "POST", headers: { "content-type": "application/json" }, body: "{}",
  }).then(response => {
    const cookie = response.headers.get("set-cookie")?.split(";")[0];
    if (!cookie?.startsWith("mira_session=")) throw new Error("Mira could not establish a visitor session.");
    return cookie;
  }).catch(error => {
    session = undefined;
    throw error;
  });
  return session;
}

async function run(prompt) {
  const id = crypto.randomUUID();
  const response = await backend("/agent", {
    method: "POST",
    headers: { "content-type": "application/json", accept: "text/event-stream", cookie: await getSession() },
    body: JSON.stringify({
      threadId: id, runId: id, messages: [{ id, role: "user", content: prompt }],
      state: {}, tools: [], context: [], forwardedProps: {},
    }),
  });
  const events = (await response.text()).split("\n").filter(line => line.startsWith("data: "))
    .map(line => JSON.parse(line.slice(6)));
  if (events.at(-1)?.type !== "RUN_FINISHED") throw new Error("The Mira run did not finish.");
  const turn = events.findLast(event => event.type === "STATE_SNAPSHOT" && event.snapshot.turn)?.snapshot.turn;
  if (turn?.catalog_version !== 1) throw new Error("The Mira catalogue version is unsupported.");
  return turn;
}

function result(structuredContent) {
  return { structuredContent, content: [{ type: "text", text: JSON.stringify(structuredContent) }] };
}

function register(name, config, handler) {
  mcp.registerTool(name, config, async input => {
    try { return result(await handler(input)); }
    catch { return { isError: true, content: [{ type: "text", text: "Mira could not complete this request. Check the local service and retry." }] }; }
  });
}

register("search_tours", {
  description: "Search Mira’s published fictional tour catalogue by title or category.",
  inputSchema: z.object({ query: z.string().max(100).default("") }),
  annotations: { readOnlyHint: true },
}, async ({query}) => {
  const rows = await (await backend("/tours")).json();
  const words = query.trim().toLowerCase().split(/\s+/);
  const tours = rows.filter(row => words.every(word => `${row.title} ${row.category}`.toLowerCase().includes(word)));
  return { tours: tours.slice(0, 12) };
});

register("get_quote", {
  description: "Request a USD quote and save a private enquiry using Mira’s deterministic pricing service.",
  inputSchema: z.object({
    tour: z.string().regex(/^[A-Z][A-Z0-9-]{1,60}$/),
    date: z.iso.date(),
    adults: z.number().int().min(1).max(100),
    child_ages: z.array(z.number().int().min(0).max(120)).max(30).default([]),
  }),
}, async ({tour, date, adults, child_ages}) => {
  const catalogue = await (await backend("/tours")).json();
  if (!catalogue.some(row => row.id === tour)) {
    return { status: "unknown_tour", message: "Choose a published tour or submit a custom enquiry." };
  }
  const turn = await run(`@trip ${tour} ${date} ${adults} ${child_ages.join(",") || "-"}`);
  const quote = turn.components.find(c => c.type === "PriceBreakdown")?.quote;
  const enquiry = turn.components.find(c => c.type === "EnquiryNotice")?.reference;
  return quote ? { status: "verified", quote } : { status: "specialist_required", enquiry, message: turn.text };
});

register("create_enquiry", {
  description: "Save a private, non-priced custom journey enquiry without contact information.",
  inputSchema: z.object({
    destinations: z.array(z.enum(["Colombo", "Kandy", "Sigiriya", "Ella", "Galle", "Yala", "Minneriya", "Mirissa", "Anuradhapura"])).min(1).max(6),
    days: z.number().int().min(1).max(90),
    adults: z.number().int().min(1).max(100),
    date: z.iso.date().optional(),
  }),
}, async ({destinations, days, adults, date}) => {
  const turn = await run(`Design a ${days}-day custom journey across ${destinations.join(" and ")} for ${adults} adults ${date ?? ""}`);
  const enquiry = turn.components.find(c => c.type === "EnquiryNotice")?.reference;
  if (!enquiry) throw new Error("Mira did not save an enquiry.");
  return { status: "saved", enquiry };
});

await mcp.connect(new StdioServerTransport());
