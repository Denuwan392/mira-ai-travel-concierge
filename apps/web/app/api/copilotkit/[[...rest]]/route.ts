import { createHash, randomUUID } from "node:crypto";
import { HttpAgent } from "@ag-ui/client";
import { CopilotRuntime, createCopilotHonoHandler } from "@copilotkit/runtime/v2";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const origin = process.env.MIRA_ORIGIN ?? "http://127.0.0.1:3000";
const api = process.env.MIRA_API_URL ?? "http://127.0.0.1:8000";
const visitorCookie = (request: Request) => request.headers.get("cookie")?.match(/(?:^|;\s*)(mira_session=[A-Za-z0-9_-]{43})(?:;|$)/)?.[1];

const correlationHeader = "x-request-id";
const requestId = (request: Request) => {
  const value = request.headers.get(correlationHeader);
  return value && /^[a-f\d]{8}(-[a-f\d]{4}){3}-[a-f\d]{12}$/i.test(value) ? value.toLowerCase() : randomUUID();
};

const copilot = new CopilotRuntime({
  agents: ({ request }) => ({
    mira: new HttpAgent({ url: `${api}/api/agent`, headers: { cookie: visitorCookie(request) ?? "", [correlationHeader]: requestId(request) } }),
  }),
  identifyUser: request => ({ id: createHash("sha256").update(visitorCookie(request) ?? "").digest("hex"), name: "Traveller" }),
  generativeUI: false,
});
const endpoint = createCopilotHonoHandler({ runtime: copilot, basePath: "/api/copilotkit", cors: { origin, credentials: true } });

async function handle(request: Request) {
  const requestOrigin = request.headers.get("origin");
  if (requestOrigin && requestOrigin !== origin) return new Response("Origin denied", { status: 403 });
  if (!visitorCookie(request)) return new Response("Visitor session required", { status: 401 });
  const id = requestId(request);
  const headers = new Headers(request.headers);
  headers.set(correlationHeader, id);
  try {
    const response = await endpoint.fetch(new Request(request, { headers }));
    const responseHeaders = new Headers(response.headers);
    responseHeaders.set(correlationHeader, id);
    return new Response(response.body, { status: response.status, headers: responseHeaders });
  } catch {
    console.error(JSON.stringify({ component: "NEXT", level: "ERROR", event: "copilot.proxy_failed", request_id: id, status: 500 }));
    return new Response("Mira is temporarily unavailable", { status: 500, headers: { [correlationHeader]: id } });
  }
}
export { handle as GET, handle as POST };
