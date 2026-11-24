# Travel Workspace integration and verification

## Repository audit

The official DOCX and PDF specify five core requirements, consent-based memory and staff extensions. The submitted dataset includes the costing workbook, four sales examples, 17 starter cases and public and private content. The repository already contained two React clients and one FastAPI service. This table records the starting point.

| Feature | Existing implementation | Missing functionality | Required changes | Priority |
|---|---|---|---|---|
| Prototype navigation and discovery | Mocked cards, itineraries, policies and hash routes in three copies of the HTML | Published-data loading, error states and working handoffs | Port supplied layout to the installed React/Tailwind build and extend the existing guide response | Core |
| Conversation and A2UI | Working notebook AG-UI client, typed graph and A2UI renderer. Mocked keyword handler in prototype | Workspace integration, mobile canvas and safe retry | Reuse the existing session, notebook, stream and catalog validators | Core |
| Grounding | Published Markdown ingestion and source disclosure. Some custom-day and hotel descriptions were hand-authored | Verifiable passages and current policy precedence | Select excerpts from published records and keep their source identifiers | Core |
| Prices | Working SQLite workbook snapshots, Decimal calculator and pricing tests | Prototype showed sample values. Enquiry link and validity semantics were missing in the quote | Use server picker commands, return references and revalidate saved quotes | Core |
| Enquiries and booking | Transactional quote/enquiry writes and mock booking in API. Prototype simulated submission | Some hotel references had no saved row. Guest status lookup was absent | Persist the displayed reference and scope status reads to its visitor | Core |
| Staff and publication | Account authentication, private finance, audit, drafts and two staff consoles | Prototype login was simulated. Production proxy omitted staff cookie. Admin could publish directly | Use real staff dashboard, forward application cookies and require Approver for review and publication | High |
| Observability | Working SQLite stages and optional Langfuse export | No staff trace URL. Interrupted runs missing from local trace lookup | Add protected trace lookup and failed-run diagnostics | High |
| Evaluation | 17 starter and 32 authored cases, judge and review template | Hardcoded headline metrics, limited workflow coverage and ephemeral failed-case references | Compute totals, add booking/authorization cases and embed failed-case trace snapshots | High |
| Returning visitors | Visitor consent and persisted notebooks in API | Prototype forgot the conversation | Restore current journey and expose a 30-day opt-in | Extended |

## Integration and implementation log

1. Kept the original navigation, gradients, card layouts, typography and two-column workspace. The browser now loads a local Vite build. The root HTML opens the development workspace. Both served HTML aliases forward to the compiled page. The earlier editorial notebook and alternate Next.js client remain accessible.
2. Reused FastAPI, SQLite/Alembic, the Markdown loader, itinerary parser, rate repository, deterministic pricing, Gemini adapter, five-node LangGraph, AG-UI service, A2UI SDK, Zod schemas, LiveCanvas and staff dashboard. New frontend code lives under `apps/ceylon-compass/workspace`. New API reads use the same database and role dependencies. Migration 0004 records unsuccessful stream diagnostics separately from committed turns.
3. The agent selects mandatory price, booking and referral components through graph state. Optional panel selection travels in the existing structured intent call. Both the server turn schema and the client surface validator check the payload. The browser renders registered React components.
4. Calendar dates, participant counts and child ages reach the existing server calculator. A successful quote returns its UUID, linked enquiry UUID, travel date, composition, currency, total, deposit, balance and recheck-before-booking validity rule. The staff endpoint exposes a separate persisted internal calculation. No fixed validity period was supplied for an individual quote.
5. Bound account-owned visitor data to authenticated identity, forwarded the staff cookie in the production proxy and restricted publication to Approver. Private drafts remain outside traveller discovery until published.
6. Added a production-browser test harness, source-passage checks, an enquiry persistence regression and measured evaluation reporting. Codex assisted with implementation, tests and this report.

## API contracts

FastAPI serves interactive request and response schemas at `http://127.0.0.1:8000/docs`. The frontend calls the same-origin proxy. The application returns HTTP errors for unauthorized access or invalid input. A stream can also carry a terminal run error.

| Workflow | Endpoint | Contract |
|---|---|---|
| Catalogue | GET /api/guide, /api/tours, /api/sources/{id} | Published cards, destination links, days, policies and filtered source text |
| Visitor | POST, GET, DELETE /api/session | Create, read, set remember consent or forget current visitor using an HttpOnly cookie |
| Journey | POST, GET /api/trips and GET /api/trips/{id} | Create or list journeys and restore validated history |
| Turn | POST /api/agent?trip_id={id} | AG-UI RunAgentInput with UUID runId and user message. SSE delivers validated turn, A2UI surface and completion. Retrying the same run ID recovers the saved turn |
| Quote and enquiry creation | POST /api/agent | The graph saves a verified quote and linked enquiry, or saves a specialist flag. Both writes share the trace transaction |
| Visitor reads | GET /api/quotes and /api/enquiries/{reference} | Rechecked public quotes and visitor-scoped enquiry status |
| Mock checkout | POST /api/bookings/mock | Supply quote UUID and scenario. Success returns a stored booking reference. Other outcomes include declined, unavailable, network or expired |
| Authentication | POST /api/auth/register, /api/auth/login, /api/auth/logout | Account sessions and server-enforced roles |
| Private queue | GET /api/staff/enquiries, GET or PATCH /api/staff/enquiries/{id} | Staff search, follow-up, notes, internal calculation and generating trace |
| Evidence | GET /api/staff/traces/{id}, /api/staff/evaluation | Authenticated trace events or most recent deterministic report |
| Content | GET or POST /api/staff/drafts, POST /api/staff/drafts/{id}/review or /publish | Staff draft generation and separate Approver-controlled publication |
| Administration | GET /api/admin/users, PATCH /api/admin/users/{id} | Administrator-managed accounts and roles |

## Reproduce

From the repository root, run `make dev` and open `http://127.0.0.1:5175/dump.html`. Keep the assessment clock at 2026-11-19. The bootstrap account requires an email and password in the local environment. The existing token console is available at port 3000. Use fictional travellers and separate role credentials.

| Command | Evidence |
|---|---|
| make eval | Frontend and backend tests, isolated deterministic suite, Markdown and JSON reports in evals/report |
| make workspace-browser | Production React build, isolated API/database, six Playwright workflows, desktop and 390px mobile |
| make lint and make build | Type checks and production builds for both existing applications |
| PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests/test_pricing.py | Direct workbook pricing checks |
| shasum -a 256 -c docs/source-sha256.txt | Supplied input integrity |
| PYTHONPATH=apps/api .venv/bin/python evals/judge.py --score | Independent model scores with GEMINI_API_KEY and GEMINI_MODEL exported |
| PYTHONPATH=apps/api .venv/bin/python evals/judge.py --labels evals/judges/human_labels.json --resume evals/report/judge.json | Compare independent human labels against the saved judge and worksheet |

## Executed checks

| Check | Observed result |
|---|---|
| Backend unit and integration suite | 162 passed, including all 43 pricing cases |
| React unit suite | 46 passed |
| Production-browser integration | 6 passed, including mobile, session expiry, custom handoff and Approver publication |
| Deterministic evaluation | 53/54 cases, 63 validated turns, seven multi-turn cases |
| Live Gemini judge | 10/10 cases scored. All ten received positive grounded, relevant, helpful and non-invented judgements. Human agreement is pending |
| Type checks and production builds | Passed for both React clients |
| Supplied input checksums | 39/39 matched |

## Findings and limitations

The hotel-rate regression initially failed because the response generated a UUID while the save node saw neither an enquiry reason nor that UUID. After connecting the two, the test retrieved the row and verified its trace. The production browser checks also exercise the staff cookie through the deployed HTTP proxy, which the Vite development proxy previously masked.

The observed deterministic result is 53 of 54 cases. All 17 starter cases passed. P03 preserves sales email Q-1043, which omits the six nights of child extra beds. The workbook and starter S03 give USD 2,965 with USD 742 due. The email gives USD 2,680 with USD 670 due. See the [failed-case trace](../evals/report/report.md) and [calculation](PRICING_RULES.md). The report counts three booking-failure checks that repeat the same exact quote. Eleven cases exercise a no-price handoff, including eight specifically classified as rate cases.

A live Gemini traveller intent call succeeded. The deterministic report exercises the local provider-independent path. The live judge report records model scores and availability separately. Ten independent human labels are still required to compute agreement. Hosted Langfuse receipt needs a configured project. Local staff traces and the exporter contract are tested. Browser checks cover the compiled assignment interface and its staff portal. Production supplier inventory, payment capture, and a submitted demo recording are outside these checks.

## Five-minute demonstration

| Time | Action and evidence |
|---|---|
| 0:00–0:45 | Browse published tours, open an itinerary, then open Mira from its card. Show the matching source. |
| 0:45–1:40 | Ask for the Sigiriya day trip for two adults on 10 January 2027. Show USD 315 total and deposit, the quote reference and the enquiry status. |
| 1:40–2:20 | Try a declined mock payment and then retry with success. Open the staff enquiry and its pricing trace. |
| 2:20–3:10 | Request a custom family journey across Kandy and Ella. Open a day source and the specialist enquiry. |
| 3:10–4:10 | Create a draft from Ella material. Show that the source is private, then use an Approver account to review and publish it. Refresh discovery. |
| 4:10–5:00 | Open the evaluation report and P03 trace. Explain the workbook extra-bed rule, show the regression test for saved references and distinguish automated scores from pending human calibration. |
