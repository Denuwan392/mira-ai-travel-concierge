import type { NextConfig } from "next";

const config: NextConfig = {
  turbopack: { root: __dirname },
  poweredByHeader: false,
  agentRules: false,
  devIndicators: false,
  async rewrites() {
    const api = process.env.MIRA_API_URL ?? "http://127.0.0.1:8000";
    const compass = process.env.MIRA_COMPASS_URL ?? "http://127.0.0.1:5175";
    return { fallback: [
      { source: "/api/:path*", destination: `${api}/api/:path*` },
      { source: "/workspace/:path*", destination: `${compass}/workspace/:path*` },
    ] };
  },
};
export default config;
