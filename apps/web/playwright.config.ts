import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 45000,
  use: {
    baseURL: process.env.MIRA_WEB_URL ?? "http://127.0.0.1:3000",
    launchOptions: process.env.MIRA_CHROME ? { executablePath: process.env.MIRA_CHROME } : undefined,
  },
});
