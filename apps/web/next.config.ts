import type { NextConfig } from "next";

const config: NextConfig = {
  poweredByHeader: false,
  agentRules: false,
  devIndicators: false,
  async rewrites() {
    const api = process.env.MIRA_API_URL ?? "http://127.0.0.1:8000";
    return { fallback: [{ source: "/api/:path*", destination: `${api}/api/:path*` }] };
  },
};
export default config;
