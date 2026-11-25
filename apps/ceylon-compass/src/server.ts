import { reportFailure } from "./lib/error-capture";
import { renderErrorPage } from "./lib/error-page";

type ServerEntry = {
  fetch: (request: Request, env: unknown, ctx: unknown) => Promise<Response> | Response;
};

let serverEntryPromise: Promise<ServerEntry> | undefined;

async function getServerEntry(): Promise<ServerEntry> {
  if (!serverEntryPromise) {
    serverEntryPromise = import("@tanstack/react-start/server-entry").then(
      (m) => (m.default ?? m) as ServerEntry,
    );
  }
  return serverEntryPromise;
}

// h3 swallows in-handler throws into a normal 500 Response with body
// {"unhandled":true,"message":"HTTPError"} — try/catch alone never fires for those.
async function normalizeCatastrophicSsrResponse(response: Response): Promise<Response> {
  if (response.status < 500) return response;
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) return response;

  const body = await response.clone().text();
  if (!isH3SwallowedErrorBody(body)) return response;

  reportFailure("ssr.invalid_response");
  return new Response(renderErrorPage(), {
    status: 500,
    headers: { "content-type": "text/html; charset=utf-8" },
  });
}

function isH3SwallowedErrorBody(body: string): boolean {
  try {
    const payload = JSON.parse(body) as { unhandled?: unknown; message?: unknown };
    return payload.unhandled === true && payload.message === "HTTPError";
  } catch {
    return false;
  }
}

// Hosting compresses every response at the edge. Never compress a body (gzip, brotli,
// CompressionStream) or set content-encoding here or in a server route: the body gets encoded
// twice and renders garbled.
export default {
  async fetch(request: Request, env: unknown, ctx: unknown) {
    const incoming = new URL(request.url);
    const canonicalRedirects = new Set([
      "/",
      "/dump.html",
      "/workspace",
      "/workspace/",
      "/workspace/index.htm",
      "/plan",
      "/destinations",
      "/experiences",
      "/journeys",
      "/explore",
      "/about",
      "/trips",
    ]);
    if (canonicalRedirects.has(incoming.pathname)) {
      const target = new URL("/workspace/index.html", incoming);
      target.search = incoming.search;
      return Response.redirect(target, 302);
    }
    const proxy = incoming.pathname.startsWith("/api/");
    try {
      if (proxy) {
        const target = new URL(process.env["MIRA_API_URL"] || "http://127.0.0.1:8000");
        target.pathname = incoming.pathname;
        target.search = incoming.search;
        const headers = new Headers();
        for (const name of ["accept", "content-type", "authorization", "origin", "x-request-id"]) {
          const value = request.headers.get(name);
          if (value) headers.set(name, value);
        }
        const cookies = request.headers.get("cookie")?.split(";")
          .map(value => value.trim()).filter(value => /^(mira_session|mira_auth)=/.test(value));
        if (cookies?.length) headers.set("cookie", cookies.join("; "));
        const body = ["GET","HEAD"].includes(request.method) ? undefined : await request.arrayBuffer();
        return await fetch(target,{method:request.method,headers,...(body ? {body}:{}),redirect:"manual",signal:request.signal});
      }
      const handler = await getServerEntry();
      const response = await handler.fetch(request, env, ctx);
      return await normalizeCatastrophicSsrResponse(response);
    } catch {
      reportFailure(proxy ? "proxy.failed" : "ssr.failed", request.headers.get("x-request-id") ?? undefined, 500);
      return new Response(renderErrorPage(), {
        status: 500,
        headers: { "content-type": "text/html; charset=utf-8" },
      });
    }
  },
};
