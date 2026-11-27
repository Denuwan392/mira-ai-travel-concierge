# Mira — Live Demonstration Runbook (27 November 2026)

**Slot:** Friday, 27 November 2026 · 11:30 AM – 12:00 PM (Asia/Colombo)  
**Format:** 20-minute live demonstration + 10-minute technical Q&A / live modification

---

## 1. Pre-Demo Checklist (Complete by 11:15 AM)

- [ ] **Environment:** Confirm `.env` has `AS_OF_DATE=2026-11-19`, `MIRA_DB=.mira/demo.sqlite3`, and valid `GEMINI_API_KEY` / `GEMINI_MODEL` (do **not** show `.env` on screen).
- [ ] **Start Services:** Run `make dev` from repo root. Wait for `8000` (FastAPI), `3000` (Next), and `5175` (Vite workspace) to report ready.
- [ ] **Health Check:** Run `curl -fsS http://127.0.0.1:8000/api/health` and confirm `"ok": true`.
- [ ] **Browser Profiles:**
  - **Window A (Traveller):** Open `http://127.0.0.1:5175/workspace/index.html` (fresh visitor session).
  - **Window B (Staff — Incognito/Separate Profile):** Open `http://127.0.0.1:3000/staff` and sign in as `staff.demo@ceyloncompass.example` (`Staff#2026!Demo`) or `approver.demo@ceyloncompass.example` (`Approver#2026!Demo`). Keep Window B minimized until minute 12.
- [ ] **VS Code Tabs:** Open `data.py` (`calculate`), `agent_workflow/routing.py` (`quote_route`), `agent_workflow/graph.py` (`builder`), `main.py` (`agui`), `evals/report/report.md`, and `apps/api/tests/test_pricing.py` (`Q-1043`).
- [ ] **Backup Video:** Open the YouTube demo link from `README.md` in a background tab and verify playback in case of total local failure.
- [ ] **Practice Copy:** Keep a separate temporary worktree/copy ready in another terminal if reviewers ask for a live code edit during Q&A.
- [ ] **Screen Share Hygiene:** Close personal tabs, mute notifications, set zoom to 110–125% for readability.

---

## 2. Minute-by-Minute Demonstration Plan (20 Minutes)

| Time | Stage | What to Open / Type | What to Show & Explain | Code File Ready | Fallback if Feature Stalls |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **00–01** | **Intro** | `http://127.0.0.1:5175/workspace/index.html` | "Mira helps Ceylon Compass travellers discover published tours and get deterministic, rate-sheet-backed quotes. Today I'll trace one request from the traveller UI through LangGraph, pricing, staff handoff, and evals." | — | — |
| **01–04** | **Architecture** | Part 1 & Part 6 diagrams | Explain the 5-node LangGraph (`agent_workflow/graph.py`: `interpret → retrieve → quote_route → quote/compose → save`), `state.working` ContextVar, `agent.py` backward-compatible facade, and the strict split: **LLM** ranks/classifies IDs only; **Python** owns pricing, RBAC, and UI schemas. | `agent_workflow/routing.py:5-12`, `quote.py:15-43` | Walk through `main.py:agui` directly. |
| **04–07** | **Workflow A: Quick Booker** | Fresh trip: `"Sigiriya day trip for two adults on 10 January 2027"` | Point out `T01`, **USD 315 total / USD 315 deposit** (day tour = 100% due), `ENQ-2026-...` reference, `PriceBreakdownPanel`, and run **Mock Booking** (try success or decline+retry). | `data.py:226-324` | Show `test_exact_quote` (`Q1041`) passing in pytest. |
| **07–10** | **Workflow B: Multi-Day Family** | New trip: `"Plan a family holiday"` → `"6-day family trip from Colombo for 2 adults and 2 children aged 7 and 10 starting 12 April 2027"` | Show multi-turn context retention, `JourneyPlan` / `InteractiveMap` grounded days, `TravellerPicker`, and `ENQ-...` creation. Note how child ages (2–11 vs 12+) drive bed & meal rules. | `planner.py:12-51` | Explain `filter_tours` + `get_grounded_day_experience`. |
| **10–12** | **Workflow D: Missing / Expired Rates** | New trip: `"Sigiriya day trip for 2 adults on 1 November 2027"` (or custom itinerary) | Show **zero invented prices** (`EnquiryNotice` with `PRICE_UNAVAILABLE` / `date_or_fx_expired`), explain FX expiry (`30 Sep 2027`), and automatic specialist handoff. | `data.py:258-272` | Show `test_refuses` in `test_pricing.py`. |
| **12–14** | **Workflow F: Staff Portal** | Switch to Window B (`/staff`) | Search the `ENQ-2026-...` reference from minute 04/07. Show internal `cost_lkr` & `gross_profit_pct` (never exposed to traveller), add a note, update status to `contacted`. Mention `approver`-only `publish` gate. | `main.py:1463-1522` | Show `test_staff_enquiry_workflow.py`. |
| **14–16** | **Tracing & Eval Evidence** | `evals/report/report.md` + Staff Trace tab | Show `53/54 (98.1%)`, `63/63` valid UI turns, `11/11` handoffs. Open trace `f108d88e-...` (`interpret → retrieval → pricing → validated_ui → persistence`). Explain **P03 vs S03** (`$2,680` email vs `$2,965` workbook due to `$64,000` LKR extra beds). | `evals/runner.py:168-213` | Show `evals/report/report.md` offline. |
| **16–18** | **Real Bug & Fix** | `apps/api/tests/test_pricing.py` & `M02` | Explain the **M02** child-age regex fix (`"age is 12"` -> `$365` to `$410` across the age-12 boundary) and the `LKR 28,000` string parser fix (`test_lkr_string_regression`). | `data.py:106-123` | Walk through `number()` in `data.py`. |
| **18–20** | **Live Prompt / Wrap-up** | Invite a reviewer prompt | Ask reviewers for a tour, date, and party. **Predict** before hitting Send whether it will quote or hand off, and why. | `agent_workflow/routing.py:5-12` | — |
| **20–30** | **Q&A & Live Edit** | Isolated practice copy | Restate any requested rule change, identify exact file/function, edit in practice copy, run targeted `pytest`/`vitest`, and explain the delta. | `MIRA_LIVE_CODING_PLAYBOOK.md` | — |

---

## 3. Podium Emergency Recovery (Quick Lookup)

1. **Services won't start / Port conflict:**
   Run `PYTHONPATH=apps/api .venv/bin/python scripts/dev.py --check-ports` or `lsof -nP -iTCP:5175 -sTCP:LISTEN` (check `8000`, `3000`, `5175`).
2. **API unreachable on 5175, works on 8000:**
   Compare `curl -fsS http://127.0.0.1:8000/api/health` vs `5175`. Check `MIRA_API_URL` / Vite proxy and restart `make dev`.
3. **Database locked or init fails:**
   Never delete `.mira/demo.sqlite3` mid-demo. Start a clean isolated DB in a separate terminal: `MIRA_DB=/tmp/mira_emergency.sqlite3 make dev`.
4. **Gemini quota / timeout / key error:**
   Mira automatically falls back to deterministic rules (`gemini.fallback` in logs). Quick-booker (`T01`), policy Q&A (`G01`), pricing, and staff portal all work 100% offline without Gemini.
5. **Blank UI / `RUN_ERROR`:**
   Check DevTools Network `/api/agent` response. If `readSurface` rejected a component index/type, retry once (same `runId` replays safely). If you edited `Workspace.jsx`, rebuild with `npm --prefix apps/ceylon-compass run workspace:build`.
6. **401 / 403 in Staff Console:**
   Ensure Staff is in a separate browser profile from Traveller. Remember: `staff` role gets `403` on `/api/staff/drafts/{id}/publish` — only `approver` or `admin` can publish.
