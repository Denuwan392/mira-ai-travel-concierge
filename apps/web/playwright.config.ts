import fs from "node:fs";
import path from "node:path";
import { defineConfig } from "@playwright/test";

// Load repo root .env so staff tokens and ports are available to tests
const envPath = path.resolve(__dirname, "../../.env");
if (fs.existsSync(envPath)) {
  const envContent = fs.readFileSync(envPath, "utf-8");
  for (const line of envContent.split("\n")) {
    const trimmed = line.trim();
    if (trimmed && !trimmed.startsWith("#") && trimmed.includes("=")) {
      const idx = trimmed.indexOf("=");
      const key = trimmed.slice(0, idx).trim();
      const val = trimmed.slice(idx + 1).trim();
      if (!process.env[key]) {
        process.env[key] = val;
      }
    }
  }
}

const macChromePath = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const defaultChrome = fs.existsSync(macChromePath) ? macChromePath : undefined;
const executablePath = process.env.MIRA_CHROME || defaultChrome;

export default defineConfig({
  testDir: "./tests",
  timeout: 45000,
  workers: 1,
  testIgnore: process.env.MIRA_WORKSPACE_TEST ? [] : ["**/workspace.spec.ts"],
  outputDir: "../../output/playwright-web",
  use: {
    baseURL: process.env.MIRA_WEB_URL ?? "http://127.0.0.1:3000",
    launchOptions: executablePath ? { executablePath } : undefined,
  },
});

