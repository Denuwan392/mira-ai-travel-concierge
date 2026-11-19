import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const client = new Client({ name: "mira-mcp-smoke", version: "1.0.0" });
const transport = new StdioClientTransport({
  command: process.execPath,
  args: [fileURLToPath(new URL("./server.mjs", import.meta.url))],
  env: { MIRA_API_URL: process.env.MIRA_API_URL ?? "http://127.0.0.1:8000" },
});

async function tool(name, args) {
  const response = await client.callTool({ name, arguments: args });
  assert.ok(!response.isError, JSON.stringify(response.content));
  return response.structuredContent;
}

await client.connect(transport);
try {
  assert.deepEqual((await client.listTools()).tools.map(t => t.name).sort(), ["create_enquiry", "get_quote", "search_tours"]);
  const catalogue = await tool("search_tours", { query: "sigiriya" });
  assert.ok(catalogue.tours.some(tour => tour.id === "T01"));
  const verified = await tool("get_quote", { tour: "T01", date: "2027-01-10", adults: 2 });
  assert.equal(verified.quote.total, 315);
  assert.equal(verified.quote.deposit, 315);
  assert.ok(!("cost_lkr" in verified.quote));
  const blocked = await tool("get_quote", { tour: "T11", date: "2027-01-20", adults: 2 });
  assert.equal(blocked.status, "specialist_required");
  assert.ok(blocked.enquiry && !blocked.quote);
  const handoff = await tool("create_enquiry", { destinations: ["Kandy", "Ella"], days: 10, adults: 4 });
  assert.equal(handoff.status, "saved");
  assert.ok(handoff.enquiry);
  console.log("MCP catalogue, verified quote, expired-rate flag and custom enquiry passed.");
} finally {
  await client.close();
}
