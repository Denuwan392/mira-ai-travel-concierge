import assert from "node:assert/strict";

const base = process.env.MIRA_WEB_URL ?? "http://127.0.0.1:3000";
const session = await fetch(`${base}/api/session`, {
  method: "POST", headers: { "content-type": "application/json" }, body: "{}",
});
assert.equal(session.status, 200);
const cookie = session.headers.get("set-cookie").split(";")[0];
const id = crypto.randomUUID();
const stream = await fetch(`${base}/api/copilotkit/agent/mira/run`, {
  method: "POST", headers: { "content-type": "application/json", accept: "text/event-stream", cookie },
  body: JSON.stringify({
    threadId: id, runId: id, messages: [{ id, role: "user", content: "Sigiriya day trip for two adults on 10 January 2027" }],
    state: {}, tools: [], context: [], forwardedProps: {},
  }),
});
const body = await stream.text();
assert.equal(stream.status, 200, body.slice(-1200));
const events = body.split("\n").filter(line => line.startsWith("data: ")).map(line => JSON.parse(line.slice(6)));
const turn = events.findLast(event => event.type === "STATE_SNAPSHOT" && event.snapshot.turn)?.snapshot.turn;
assert.ok(turn, `CopilotKit did not deliver a turn: ${events.map(event => event.type + (event.message ? " " + event.message : "")).join(", ")}`);
const quote = turn.components.find(component => component.type === "PriceBreakdown")?.quote;
assert.equal(quote?.total, 315);
assert.equal(quote?.deposit, 315);
assert.ok(events.some(event => event.type === "TEXT_MESSAGE_CONTENT"));
assert.ok(events.some(event => event.type === "RUN_FINISHED"));
const saved = await fetch(`${base}/api/quotes`, { headers: { cookie } }).then(response => response.json());
assert.equal(saved[0]?.quote?.id, quote.id);
console.log(`CopilotKit streamed quote ${quote.id} · trace ${turn.trace} · ${events.length} AG-UI events`);
