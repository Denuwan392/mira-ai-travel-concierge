# Mira — Start Here (Interview & Live Demo Preparation Index)

**Live Demonstration:** Friday, 27 November 2026 · 11:30 AM – 12:00 PM (Asia/Colombo)  
**Assessment Clock:** `AS_OF_DATE=2026-11-19`  
**Canonical Demo Surface:** `http://127.0.0.1:5175/workspace/index.html` (via `make dev`)

---

## 1. Priority-Based Study Plans

Choose the plan that matches your remaining time before 11:30 AM:

| Time Budget | Focus & Exact Sequence | Outcome |
| :--- | :--- | :--- |
| **30 Minutes** | **1.** Read `Part 0` & `Part 1` of the Handbook (8 min).<br>**2.** Trace `data.calculate` on **T01** (`$315`) and **Q-1043** (`$2,965` / `$742`) in `Part 7` (12 min).<br>**3.** Inspect the archived **P03** trace in `Part 11` (5 min).<br>**4.** Rehearse the 3-minute architecture pitch aloud using `MIRA_DEMO_RUNBOOK.md` (5 min). | You can explain the architecture, defend the pricing engine, explain P03 vs S03, and demo the quick-booker flow. |
| **1 Hour** | Do the 30-minute plan, plus:<br>**5.** Read `Part 5` Workflows A, B, C, D (15 min).<br>**6.** Read `useConversation.js`, `service.ts`, `surface.ts` in `Part 9` (10 min).<br>**7.** Review RBAC & approver-only `publish` in `Part 10` (5 min). | You can trace any turn end-to-end from React to SQLite and defend Generative UI + security boundaries. |
| **2 Hours** | Do the 1-hour plan, plus:<br>**8.** Do one timed 20-minute live demo rehearsal using `MIRA_DEMO_RUNBOOK.md` (25 min).<br>**9.** Practise Exercises 1–5 in `MIRA_LIVE_CODING_PLAYBOOK.md` in an isolated copy (20 min).<br>**10.** Test yourself on 15 Q&As from `Part 13` with the editor closed (15 min). | You are ready for unexpected traveller prompts and live code modifications. |
| **4 Hours** | Do the 2-hour plan, plus:<br>**11.** Read all `Part 4` P0/P1 function dry-runs and failure cases (45 min).<br>**12.** Rehearse edge cases: expired FX (`2027-11-01`), child age 11 vs 12, staff follow-up in a second browser, mock payment failure & retry (45 min).<br>**13.** Practise Exercises 6–15 in `MIRA_LIVE_CODING_PLAYBOOK.md` and replay your weakest explanation (30 min). | Complete mastery of every P0/P1 file, function, edge case, and defense question. |

---

## 2. Recommended Study Order (Documents)

1. **[00_START_HERE.md](00_START_HERE.md)** *(this file)* — Pick your time-boxed plan and open the 20 ranked files in VS Code.
2. **[MIRA_CODEBASE_UNDERSTANDING_HANDBOOK.md](MIRA_CODEBASE_UNDERSTANDING_HANDBOOK.md)** *(or [PDF](MIRA_CODEBASE_UNDERSTANDING_HANDBOOK.pdf))* — Read Parts 0, 1, 5, 7, 11 first, then Parts 4, 6, 8, 9, 10, 13, 16.
3. **[MIRA_LIVE_CODING_PLAYBOOK.md](MIRA_LIVE_CODING_PLAYBOOK.md)** — Practise the top 5 modifications in a temporary copy/worktree (never mutate the submitted branch!).
4. **[MIRA_DEMO_RUNBOOK.md](MIRA_DEMO_RUNBOOK.md)** — Rehearse the 20-minute demo + 10-minute Q&A against a timer.
5. **[MIRA_RAPID_REVISION.pdf](MIRA_RAPID_REVISION.pdf)** — Keep open on a second screen during preparation and Q&A.

---

## 3. Ranked VS Code Tabs to Open Before the Interview (20 Files)

| Rank | Priority | File & Line Range | Key Symbol | Why It Matters |
| :---: | :---: | :--- | :--- | :--- |
| 1 | **P0** | `apps/api/mira/data.py:226-324` | `calculate` | Deterministic pricing, age/room/season/FX/margin/deposit rules. |
| 2 | **P0** | `apps/api/mira/agent_workflow/routing.py:5-12` (re-exported by `agent.py`) | `quote_route` | Conditional edge deciding when Mira has enough info to quote. |
| 3 | **P0** | `apps/api/mira/main.py:449-525` | `agui` | Trust boundary between browser, LangGraph, tracing, and SQLite. |
| 4 | **P0** | `apps/ceylon-compass/workspace/useConversation.js:49-79` | `send` | Canonical workspace hook: trip state, retry `runId`, 65s timeout. |
| 5 | **P0** | `apps/ceylon-compass/src/lib/live/service.ts:42-68` | `run` | Shared AG-UI `HttpAgent` transport and Zod snapshot validation. |
| 6 | **P0** | `apps/ceylon-compass/workspace/Workspace.jsx:3034` | `PriceBreakdownPanel` | Canonical quote UI; disables checkout if party edits diverge from quote. |
| 7 | **P0** | `apps/api/mira/catalog.py:98-157` | `PublicQuote`, `Turn` | Strict Pydantic v2 contract stripping internal LKR costs/margins. |
| 8 | **P0** | `apps/api/mira/rates_repository.py:16-43` | `current_rates` | SHA-256 workbook snapshot caching in `rate_snapshots`. |
| 9 | **P1** | `apps/api/mira/store.py:82-98` | `published_records` | SQLite WAL + Alembic migrations + immediate published-draft overlay. |
| 10 | **P1** | `apps/api/mira/surface.py:12-43` | `surface_messages` | Converts validated `Turn` into A2UI v0.9 `createSurface`/`updateComponents`. |
| 11 | **P1** | `apps/ceylon-compass/src/lib/live/surface.ts:54-89` | `readSurface` | Client-side structural verification before React renders components. |
| 12 | **P1** | `apps/api/mira/provider.py:81-118` | `rank` | Bounded Gemini structured output (`Suggestions`) with hallucination rejection. |
| 13 | **P1** | `evals/runner.py:168-213` | `execute` | Replays HTTP turns against isolated DB and scores deterministic cases. |
| 14 | **P1** | `apps/api/tests/test_pricing.py:13-63` | `test_exact_quote` | Proves exact totals, group/age/deposit boundaries, and fail-closed refusals. |
| 15 | **P1** | `apps/api/mira/auth.py:286-382` | `get_current_user_optional` | Binds Argon2id user sessions / dev tokens and RBAC (`require_role`). |
| 16 | **P1** | `apps/api/mira/search.py:159-180` | `filter_tours` | Deterministic tour filtering before optional Gemini ranking. |
| 17 | **P1** | `apps/api/mira/observability.py:99-114` | `sanitize_value` | Redacts emails, Bearer tokens, and sensitive keys before logging/tracing. |
| 18 | **P1** | `apps/ceylon-compass/src/components/staff/StaffConsole.tsx:207` | `StaffConsole` | Private staff portal for enquiries, notes, drafts, traces, and evals. |
| 19 | **P1** | `evals/judge.py:223-369` | `judge` | LLM-as-judge qualitative scoring + human agreement calculation. |
| 20 | **P1** | `apps/api/mira/planner.py:12-51` | `get_grounded_day_experience` | Grounds custom multi-day itinerary stops in destination/tour evidence. |

---

## 4. Essential First Commands

```sh
# 1. Start full stack (FastAPI :8000, Next :3000, Vite Workspace :5175)
make dev

# 2. Verify backend health
curl -fsS http://127.0.0.1:8000/api/health

# 3. Run all backend tests (222 tests, ~26s)
PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests

# 4. Run pricing unit tests only (<1s)
PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests/test_pricing.py

# 5. Run frontend Vitest suite (73 tests, ~4s)
npm --prefix apps/ceylon-compass test
```

> [!WARNING]
> **Protect the submitted repo:** `make eval` rewrites `evals/report/report.md` and `evals/report/report.json`. Only run `make eval` or practise live-coding edits inside a **temporary copy or isolated git worktree** — never mutate the live demo database or submitted commit before your presentation.
