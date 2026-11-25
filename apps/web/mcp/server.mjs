/** Local MCP transport. FastAPI remains the sole authority for catalogue, quotes and enquiries. */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const api = process.env.MIRA_API_URL ?? "http://127.0.0.1:8000";
const mcp = new McpServer({ name: "mira-travel", version: "1.1.0" });
let session;

function isValidCalendarDate(iso) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) return false;
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  return dt.getUTCFullYear() === y && dt.getUTCMonth() === m - 1 && dt.getUTCDate() === d;
}

async function backend(path, options = {}) {
  const response = await fetch(`${api}/api${path}`, { ...options, signal: AbortSignal.timeout(20000) });
  if (!response.ok) {
    const err = new Error(`Backend error (${response.status})`);
    err.status = response.status;
    throw err;
  }
  return response;
}

function getSession() {
  session ??= backend("/session", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ remember: false }),
  })
    .then((response) => {
      const cookie = response.headers.get("set-cookie")?.split(";")[0];
      if (!cookie?.startsWith("mira_session=")) throw new Error("Mira could not establish a visitor session.");
      return cookie;
    })
    .catch((error) => {
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
      threadId: id,
      runId: id,
      messages: [{ id, role: "user", content: prompt }],
      state: {},
      tools: [],
      context: [],
      forwardedProps: {},
    }),
  });
  const events = (await response.text())
    .split("\n")
    .filter((line) => line.startsWith("data: "))
    .map((line) => JSON.parse(line.slice(6)));
  if (events.at(-1)?.type !== "RUN_FINISHED") throw new Error("The Mira run did not finish.");
  const turn = events.findLast((event) => event.type === "STATE_SNAPSHOT" && event.snapshot.turn)?.snapshot.turn;
  if (turn?.catalog_version !== 1) throw new Error("The Mira catalogue version is unsupported.");
  return turn;
}

async function fetchPublicEnquiry(refOrId) {
  if (!refOrId) return null;
  try {
    const res = await backend(`/enquiries/${encodeURIComponent(refOrId)}`, {
      headers: { cookie: await getSession() },
    });
    return await res.json();
  } catch {
    return null;
  }
}

function result(structuredContent) {
  return { structuredContent, content: [{ type: "text", text: JSON.stringify(structuredContent) }] };
}

function register(name, config, handler) {
  mcp.registerTool(name, config, async (input) => {
    try {
      return result(await handler(input));
    } catch {
      return {
        isError: true,
        content: [{ type: "text", text: "Mira could not complete this request. Check the local service and retry." }],
      };
    }
  });
}

register(
  "search_tours",
  {
    description: "Search Mira’s published tour catalogue by title, category, or destination.",
    inputSchema: z.object({ query: z.string().max(100).default("") }),
    annotations: { readOnlyHint: true },
  },
  async ({ query }) => {
    const rows = await (await backend("/tours")).json();
    const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
    const tours = rows
      .filter((row) =>
        words.every((word) =>
          `${row.title} ${row.category} ${row.start ?? ""} ${(row.destinations ?? []).join(" ")}`.toLowerCase().includes(word),
        ),
      )
      .slice(0, 12)
      .map((row) => ({
        id: row.id,
        title: row.title,
        category: row.category,
        duration: row.duration,
        start: row.start,
        destinations: row.destinations ?? [],
        summary: row.summary,
      }));
    return { tours };
  },
);

register(
  "get_quote",
  {
    description: "Request a USD quote and save a private enquiry using Mira’s deterministic pricing service.",
    inputSchema: z.object({
      tour: z.string().regex(/^[A-Z][A-Z0-9-]{1,60}$/),
      date: z.iso.date(),
      adults: z.number().int().min(1).max(100),
      child_ages: z.array(z.number().int().min(0).max(120)).max(30).default([]),
    }),
  },
  async ({ tour, date, adults, child_ages }) => {
    if (!isValidCalendarDate(date)) {
      return { status: "invalid_input", message: "Please provide a valid calendar date (YYYY-MM-DD)." };
    }
    const catalogue = await (await backend("/tours")).json();
    if (!catalogue.some((row) => row.id === tour)) {
      return { status: "unknown_tour", message: "Choose a published tour or submit a custom enquiry." };
    }
    const turn = await run(`@trip ${tour} ${date} ${adults} ${child_ages.join(",") || "-"}`);
    const quote = turn.components.find((c) => c.type === "PriceBreakdown")?.quote;
    const notice = turn.components.find((c) => c.type === "EnquiryNotice");
    if (quote) {
      const publicRecord = await fetchPublicEnquiry(quote.enquiry);
      return {
        status: "verified",
        quote: {
          id: quote.id,
          source: quote.source,
          title: quote.title,
          date: quote.date,
          adults: quote.adults,
          ages: quote.ages,
          currency: quote.currency,
          total: quote.total,
          deposit: quote.deposit,
          balance: quote.balance,
          validity: quote.validity,
        },
        enquiry: quote.enquiry,
        public_reference: publicRecord?.reference ?? null,
      };
    }
    const enquiryId = notice?.reference ?? null;
    const publicRecord = notice?.public_reference ? null : await fetchPublicEnquiry(enquiryId);
    return {
      status: "specialist_required",
      enquiry: enquiryId,
      public_reference: notice?.public_reference ?? publicRecord?.reference ?? null,
      reason_code: notice?.reason_code ?? null,
      tour_id: notice?.tour_id ?? tour,
      message: turn.text,
    };
  },
);

register(
  "create_enquiry",
  {
    description: "Save a private, non-priced custom journey enquiry without contact information.",
    inputSchema: z.object({
      destinations: z
        .array(
          z.enum(["Colombo", "Kandy", "Sigiriya", "Ella", "Galle", "Yala", "Minneriya", "Mirissa", "Anuradhapura"]),
        )
        .min(1)
        .max(6),
      days: z.number().int().min(1).max(90),
      adults: z.number().int().min(1).max(100),
      date: z.iso.date().optional(),
    }),
  },
  async ({ destinations, days, adults, date }) => {
    if (date && !isValidCalendarDate(date)) {
      return { status: "invalid_input", message: "Please provide a valid calendar date (YYYY-MM-DD)." };
    }
    const turn = await run(
      `Design a ${days}-day custom journey across ${destinations.join(" and ")} for ${adults} adults ${date ?? ""}`.trim(),
    );
    const notice = turn.components.find((c) => c.type === "EnquiryNotice");
    const enquiry = notice?.reference;
    if (!enquiry) throw new Error("Mira did not save an enquiry.");
    const publicRecord = notice?.public_reference ? null : await fetchPublicEnquiry(enquiry);
    return {
      status: "saved",
      enquiry,
      public_reference: notice?.public_reference ?? publicRecord?.reference ?? null,
      reason_code: notice?.reason_code ?? "custom_or_unsupported",
      message: turn.text,
    };
  },
);

register(
  "list_destinations",
  {
    description: "List published Sri Lanka destinations from Mira’s travel guide.",
    inputSchema: z.object({}),
    annotations: { readOnlyHint: true },
  },
  async () => {
    const guideData = await (await backend("/guide")).json();
    const places = Object.entries(guideData.places ?? {}).map(([slug, place]) => ({
      slug,
      id: place.id,
      name: place.name,
      description: place.description ?? "",
    }));
    return { destinations: places };
  },
);

register(
  "get_tour_details",
  {
    description: "Retrieve published itinerary and source details for a published tour ID.",
    inputSchema: z.object({ tour: z.string().regex(/^[A-Z][A-Z0-9-]{1,60}$/) }),
    annotations: { readOnlyHint: true },
  },
  async ({ tour }) => {
    const catalogue = await (await backend("/tours")).json();
    if (!catalogue.some((row) => row.id === tour)) {
      return { status: "unknown_tour", message: "Choose a published tour ID from search_tours." };
    }
    const src = await (await backend(`/sources/${encodeURIComponent(tour)}`)).json();
    return {
      status: "published",
      id: src.id,
      title: src.title,
      source: src.source,
      last_updated: src.last_updated ?? null,
      body: src.body,
    };
  },
);

register(
  "get_enquiry_status",
  {
    description: "Check the status of a private enquiry belonging to the active MCP visitor session.",
    inputSchema: z.object({ reference: z.string().min(3).max(80) }),
    annotations: { readOnlyHint: true },
  },
  async ({ reference }) => {
    const data = await fetchPublicEnquiry(reference.trim());
    if (!data) {
      return { status: "unavailable", message: "Enquiry unavailable in this session." };
    }
    return {
      status: "found",
      enquiry: {
        id: data.id,
        reference: data.reference,
        status: data.status,
        tour_name: data.tour_name ?? null,
        travel_date: data.travel_date ?? null,
        created: data.created,
      },
    };
  },
);

await mcp.connect(new StdioServerTransport());
