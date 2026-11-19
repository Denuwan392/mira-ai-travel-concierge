import { createHash } from "node:crypto";
import { HttpAgent } from "@ag-ui/client";
import { CopilotRuntime, createCopilotHonoHandler } from "@copilotkit/runtime/v2";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const origin = process.env.MIRA_ORIGIN ?? "http://127.0.0.1:3000";
const api = process.env.MIRA_API_URL ?? "http://127.0.0.1:8000";
const visitorCookie = (request: Request) => request.headers.get("cookie")?.match(/(?:^|;\s*)(mira_session=[A-Za-z0-9_-]{43})(?:;|$)/)?.[1];

const copilot = new CopilotRuntime({
  agents: ({ request }) => ({
    mira: new HttpAgent({ url: `${api}/api/agent`, headers: { cookie: visitorCookie(request) ?? "" } }),
  }),
  identifyUser: request => ({ id: createHash("sha256").update(visitorCookie(request) ?? "").digest("hex"), name: "Traveller" }),
  generativeUI: false,
});
const endpoint = createCopilotHonoHandler({ runtime: copilot, basePath: "/api/copilotkit", cors: { origin, credentials: true } });

function handle(request: Request) {
  const requestOrigin = request.headers.get("origin");
  if (requestOrigin && requestOrigin !== origin) return new Response("Origin denied", { status: 403 });
  if (!visitorCookie(request)) return new Response("Visitor session required", { status: 401 });
  return endpoint.fetch(request);
}
export { handle as GET, handle as POST };
