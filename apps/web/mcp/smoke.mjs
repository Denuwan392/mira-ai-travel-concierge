import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const apiUrl = process.env.MIRA_API_URL ?? "http://127.0.0.1:8000";

function makeClient(name = "mira-mcp-smoke") {
  const client = new Client({ name, version: "1.1.0" });
  const transport = new StdioClientTransport({
    command: process.execPath,
    args: [fileURLToPath(new URL("./server.mjs", import.meta.url))],
    env: { MIRA_API_URL: apiUrl },
  });
  return { client, transport };
}

async function callTool(client, name, args) {
  const response = await client.callTool({ name, arguments: args });
  assert.ok(!response.isError, `Unexpected tool error for ${name}: ${JSON.stringify(response.content)}`);
  return response.structuredContent;
}

const report = {
  generated_at: new Date().toISOString(),
  api_url: apiUrl,
  scenarios: [],
};

const { client, transport } = makeClient("mira-mcp-smoke-primary");
await client.connect(transport);

try {
  // MCP-01: Tool discovery
  const listed = (await client.listTools()).tools.map((t) => t.name).sort();
  for (const required of ["search_tours", "get_quote", "create_enquiry"]) {
    assert.ok(listed.includes(required), `Missing required tool: ${required}`);
  }
  report.scenarios.push({ id: "MCP-01", name: "Tool discovery", pass: true, tools: listed });

  // MCP-02: Published catalogue search (Sigiriya)
  const catalogue = await callTool(client, "search_tours", { query: "sigiriya" });
  assert.ok(catalogue.tours.some((tour) => tour.id === "T01"));
  assert.ok(!catalogue.tours.some((tour) => tour.id === "T15" || tour.id.startsWith("C-")));
  report.scenarios.push({ id: "MCP-02", name: "Published catalogue search", pass: true, count: catalogue.tours.length });

  // MCP-03: Verified day-tour quote (T01, 2 adults, 2027-01-10)
  const dayQuote = await callTool(client, "get_quote", { tour: "T01", date: "2027-01-10", adults: 2 });
  assert.equal(dayQuote.status, "verified");
  assert.equal(dayQuote.quote.total, 315);
  assert.equal(dayQuote.quote.deposit, 315);
  assert.equal(dayQuote.quote.balance, 0);
  assert.ok(dayQuote.public_reference?.startsWith("ENQ-"));
  report.scenarios.push({
    id: "MCP-03",
    name: "Verified day-tour quote",
    pass: true,
    total: dayQuote.quote.total,
    deposit: dayQuote.quote.deposit,
    balance: dayQuote.quote.balance,
    public_reference: dayQuote.public_reference,
  });

  // MCP-04: Verified multi-day quote (T09 Cultural Triangle, 2 adults, 2027-05-03)
  const multiQuote = await callTool(client, "get_quote", { tour: "T09", date: "2027-05-03", adults: 2 });
  assert.equal(multiQuote.status, "verified");
  assert.equal(multiQuote.quote.total, 2125);
  assert.equal(multiQuote.quote.deposit, 532);
  assert.equal(multiQuote.quote.balance, 1593);
  report.scenarios.push({
    id: "MCP-04",
    name: "Verified multi-day quote",
    pass: true,
    total: multiQuote.quote.total,
    deposit: multiQuote.quote.deposit,
    balance: multiQuote.quote.balance,
    public_reference: multiQuote.public_reference,
  });

  // MCP-05: Cultural Triangle family pricing reconciliation (T09, 2 adults, [7, 10], 2027-04-12)
  const familyQuote = await callTool(client, "get_quote", {
    tour: "T09",
    date: "2027-04-12",
    adults: 2,
    child_ages: [7, 10],
  });
  assert.equal(familyQuote.status, "verified");
  assert.equal(familyQuote.quote.total, 2965);
  assert.equal(familyQuote.quote.deposit, 742);
  assert.equal(familyQuote.quote.balance, 2223);
  report.scenarios.push({
    id: "MCP-05",
    name: "Family pricing reconciliation (T09 / S03)",
    pass: true,
    total: familyQuote.quote.total,
    deposit: familyQuote.quote.deposit,
    balance: familyQuote.quote.balance,
  });

  // MCP-06: Expired rates (T01 on 2027-11-01)
  const expired = await callTool(client, "get_quote", { tour: "T01", date: "2027-11-01", adults: 2 });
  assert.equal(expired.status, "specialist_required");
  assert.ok(!expired.quote);
  assert.ok(expired.public_reference?.startsWith("ENQ-"));
  assert.ok(expired.reason_code);
  report.scenarios.push({
    id: "MCP-06",
    name: "Expired rates fail closed",
    pass: true,
    reason_code: expired.reason_code,
    public_reference: expired.public_reference,
  });

  // MCP-07: Custom 10-day family enquiry across Kandy and Ella
  const handoff = await callTool(client, "create_enquiry", { destinations: ["Kandy", "Ella"], days: 10, adults: 4 });
  assert.equal(handoff.status, "saved");
  assert.ok(!handoff.quote);
  assert.ok(handoff.public_reference?.startsWith("ENQ-"));
  const ownStatus = await callTool(client, "get_enquiry_status", { reference: handoff.public_reference });
  assert.equal(ownStatus.status, "found");
  assert.equal(ownStatus.enquiry.reference, handoff.public_reference);
  report.scenarios.push({
    id: "MCP-07",
    name: "Custom enquiry persisted & retrievable in own session",
    pass: true,
    public_reference: handoff.public_reference,
  });

  // MCP-08: Financial privacy (no internal cost, margin, or staff notes)
  const serialized = JSON.stringify({ dayQuote, multiQuote, familyQuote, expired, handoff, ownStatus });
  for (const forbidden of ["cost_lkr", "gross_profit_pct", "margin", "hotel_rows"]) {
    assert.ok(!serialized.includes(forbidden), `Sensitive field leaked: ${forbidden}`);
  }
  report.scenarios.push({ id: "MCP-08", name: "Financial privacy", pass: true });

  // MCP-09: Invalid inputs (invalid calendar date, unknown tour, invalid adults/ages)
  const badDate = await client.callTool({ name: "get_quote", arguments: { tour: "T01", date: "2027-02-31", adults: 2 } });
  assert.equal(badDate.isError, true);
  const unknownTour = await callTool(client, "get_quote", { tour: "T99", date: "2027-01-10", adults: 2 });
  assert.equal(unknownTour.status, "unknown_tour");
  const badAdults = await client.callTool({ name: "get_quote", arguments: { tour: "T01", date: "2027-01-10", adults: 0 } });
  assert.equal(badAdults.isError, true);
  const badAges = await client.callTool({
    name: "get_quote",
    arguments: { tour: "T01", date: "2027-01-10", adults: 2, child_ages: [150] },
  });
  assert.equal(badAges.isError, true);
  report.scenarios.push({ id: "MCP-09", name: "Invalid input handling", pass: true });

  // Bonus read-only tools: list_destinations & get_tour_details
  const dests = await callTool(client, "list_destinations", {});
  assert.ok(dests.destinations.length >= 5);
  const details = await callTool(client, "get_tour_details", { tour: "T01" });
  assert.equal(details.status, "published");
  assert.equal(details.id, "T01");

  // MCP-10: Session isolation (independent MCP client cannot read primary session's enquiry)
  const { client: otherClient, transport: otherTransport } = makeClient("mira-mcp-smoke-other");
  await otherClient.connect(otherTransport);
  try {
    const crossSession = await callTool(otherClient, "get_enquiry_status", { reference: handoff.public_reference });
    assert.equal(crossSession.status, "unavailable");
  } finally {
    await otherClient.close();
  }
  report.scenarios.push({ id: "MCP-10", name: "Session isolation", pass: true });

  const outPath = path.resolve("evals/report/mcp_smoke.json");
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify(report, null, 2));
  console.log(`MCP verification passed (${report.scenarios.length}/10 scenarios). Report: ${outPath}`);
} finally {
  await client.close();
}
