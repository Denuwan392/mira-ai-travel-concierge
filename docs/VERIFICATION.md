# Verification

Run from the workspace root. The native launch was exercised on macOS with a newly created Python environment, a clean npm install, pinned dependency caches and a fresh SQLite database. The app reported 30 public documents, 17 starter cases, a valid workbook and no missing required inputs. The staff browser run used temporary role tokens.

| Area | Result | Evidence |
|---|---|---|
| One-command native startup | PASS | `make dev` brought up Next.js and FastAPI and returned source health |
| Build / type check | PASS | `make build` generated the home, planner, trips, staff and CopilotKit routes. `make lint` completed compile and type checks |
| R1 Discovery | PASS | 4/4 discovery cases and 6/6 cases categorized as multi-turn |
| R2 Visitor memory | PASS | Consent, resume, ownership, saved quote and forget tests |
| R3 Generative UI and mobile | PASS | CopilotKit observed 23 AG-UI events in a quote turn. 58/58 eval turns passed catalogue validation. Playwright covered desktop and mobile |
| R4 Source-grounded answers | PASS | 10/10 grounding cases and a separate embedded-price injection test |
| R5 Exact pricing | FAIL for one historical comparator | 20/21 quote cases matched their expected amounts. All 20 workbook-consistent expectations matched. P03 retains the Q-1043 email disagreement |
| R6 Missing and expanded unsupported rates | PASS | 10/10 flagged refusals. Zero unexpected quotes in non-priced cases |
| R7 Enquiries and protected finance | PASS | Ownership, retry, notes, status and trace-linked persistence tests |
| R8 Publication gate | PASS in local draft mode | Direct API denial for Editor and guest. Staff Playwright test observed publication becoming available |
| Mock booking | PASS | Simulated decline, successful retry and idempotent confirmation verified |
| Trace correlation | PASS locally | Smoke quote `d616b944-9c26-40c0-863b-a31eeb0e85c7` linked to trace `eb026b11-540f-4016-83f4-932bfab77647` in the isolated run |
| Before and after | PASS | M02 reproduced USD 365 → USD 365. The fixed run returned USD 365 → USD 410 |
| Source integrity | PASS | All 39 tracked source inputs matched the recorded SHA-256 |
| Optional MCP | PASS | A real stdio client exercised all three tools, verified USD 315, checked staff-only fields were absent, and verified two handoff paths |
| Docker | BLOCKED | Compose configuration included. No Docker executable on this host |
| Live Gemini / Langfuse | BLOCKED | No model credentials or remote trace project configured |
| Human review and judge agreement | BLOCKED | Ten-case review set and judge runner included. Independent human scoring and a configured judge remain outstanding |
| Private remote and demo recording | BLOCKED for submission | Workspace delivery includes code and recording outline. No private remote, reviewer invitation or recording was created |

The final deterministic run completed **55 Python tests**, **3 browser tests**, and **48/49 evaluation cases**. The eval corpus contains 17 employer cases and 32 authored cases, including 7 multi-turn conversations. Exact match was **95.2%** against all supplied and authored price expectations, and flagged no-price handling was **100%** in this suite. See [report.md](../evals/report/report.md) and its paired JSON for observed cases and trace stages.
