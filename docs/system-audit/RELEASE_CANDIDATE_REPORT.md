# Final Release Candidate Report — Ceylon Compass Holidays (Mira AI Travel Assistant)

**Date:** 2026-11-25  
**Final Verdict:** **READY WITH DOCUMENTED LIMITATIONS**

---

## 1. Verified Repository State

- **Active Canonical Entrypoint:** `http://127.0.0.1:5175/dump.html` (and `/workspace/index.html`) backed by `apps/ceylon-compass/workspace/Workspace.jsx` and unified `apps/ceylon-compass/src/components/staff/StaffConsole.tsx`.
- **Backend Service:** FastAPI (`apps/api/mira/main.py`) + 5-node LangGraph workflow (`apps/api/mira/agent.py`) + deterministic `Decimal` workbook pricing (`apps/api/mira/data.py`).
- **Dataset Checksums (`shasum -a 256 -c docs/source-sha256.txt`):** **39/39 OK** — zero modifications to original dataset, brand pack, rate workbook, or evaluation seed.
- **Database Schema Revision:** `0006_enquiry_contact_fields` (verified via Alembic + `PRAGMA table_info`).

---

## 2. Commands Executed

| Command | Outcome | Notes |
|---|---|---|
| `make lint` | **PASS** | `python -m compileall -q apps/api/mira evals`, `tsc --noEmit` (`apps/web` & `apps/ceylon-compass`) |
| `make build` | **PASS** | Vite `workspace:build`, Vite Nitro SSR (`.output/`), Next.js `apps/web` |
| `make test` | **PASS** | `apps/ceylon-compass` Vitest + `apps/api/tests` Pytest |
| `make workspace-browser` | **PASS (8/8)** | Real Playwright Chromium against live FastAPI (`18008`) + Nitro (`15175`) on isolated temp DB |
| `PYTHONPATH=apps/api .venv/bin/python evals/runner.py` | **53/54 (98.1%)** | Isolated `TemporaryDirectory`; sole failure is documented `P03` / `Q-1043` extra-bed discrepancy |
| `PYTHONPATH=apps/api .venv/bin/python scripts/init_demo_db.py --force` | **PASS** | Clean demo DB created at `.mira/demo.sqlite3` (`make demo-db`) |
| `shasum -a 256 -c docs/source-sha256.txt` | **PASS (39/39)** | Original dataset untouched |
| `make mcp-smoke` | **FAIL (standalone)** | Expects an already-running local API server on port `8000` |

---

## 3. Backend Test Results

- **Command:** `.venv/bin/python -m pytest -q apps/api/tests`
- **Result:** **206 passed, 0 failed** (18.46s)
- **Coverage Added in Release Candidate (`apps/api/tests/test_release_candidate.py`, 8/8 passed):**
  - Complete customer-to-staff lifecycle with deterministic pricing verification, child-age recalculation, contact submission, staff status/note/follow-up persistence, and public privacy checks.
  - Enquiry deduplication, tour switching within a trip, separate-trip isolation, closed enquiry reopening (`closed -> contacted` blocked `422`, `closed -> in_review` allowed `200`), guest-to-authenticated upgrade, and concurrent requests across independent sessions.
  - Isolated Alembic migration tests (fresh DB, pre-0006 DB upgrade preserving rows & backfilling `reference`, repeated startup idempotency).
  - LLM failure/timeout/malformed JSON recovery, prompt-injection resistance, cross-user/RBAC/CSRF/PII security checks, and full mock booking state matrix (`success`, `declined`, `network`, `unavailable`, `expired`, retry, post-confirmation failure preservation).

---

## 4. Frontend Test Results

- **Command:** `npm --prefix apps/ceylon-compass test` (`vitest run --pool=threads`)
- **Result:** **61 passed across 8 test files, 0 failed**
- Includes `src/test/workspace-preferred.test.tsx` (11 tests covering `StaffConsole`, `MarkdownContent`, `UIComponentRenderer` `ItineraryDay`/`PolicySnippet`, `EnquiryPage` 404 state, and `HomePage` prompt forwarding) and `src/test/staff-layout.test.tsx` (4 tests).

---

## 5. Real Browser Test Results

- **Command:** `make workspace-browser` (`./scripts/test-workspace.sh` → `playwright test workspace.spec.ts`, executed outside sandbox restrictions)
- **Result:** **8/8 passed in 13.1s**
  1. Published guide, verified quote, booking, and private staff trace (`1.8s`)
  2. Mobile discovery, retry, and missing rates (`1.7s`)
  3. Staff account reviews the evaluated build through the production proxy (`503ms`)
  4. Consented returning traveller resumes verified quote and recovers expired session (`1.2s`)
  5. Conversation selects published tour, renders itinerary, and prices picker (`2.8s`)
  6. Staff draft stays private through review and appears after Approver publication (`1.4s`)
  7. Four-adult quotation, quote invalidation, and tour switching (`1.2s`)
  8. Internal command leakage prevention in traveller chat (`538ms`)
- **Note:** `make browser` and `make smoke` target the secondary `apps/web` Next.js port (`3000`); the canonical workspace Playwright suite (`make workspace-browser`) verified the production proxy, cookies, session recovery, AG-UI/A2UI rendering, mobile layout, and StaffConsole end-to-end.

---

## 6. Evaluation Results

- **Command:** `PYTHONPATH=apps/api .venv/bin/python evals/runner.py`
- **Result:** **53/54 cases passed (98.1%)**, **63/63 validated UI turns**, **23/24 exact pricing matches**, **11/11 no-price/specialist-handoff passes**, **0 unexpected quote components**.
- **P03 / Q-1043 Discrepancy:** Preserved intentionally. Authoritative workbook rules (`rate_sheet_2026-27.xlsx`) include child extra beds across 6 nights, producing **USD 2,965** (deposit **USD 742**) rather than the historical sample email's **USD 2,680** (deposit **USD 670**). Workbook accuracy is 100% deterministic; historical sample agreement is 23/24.

---

## 7. LLM Judge Calibration Results

- **Artifact Inspected:** `evals/report/judge.json` (`judge_model: gemini-3.5-flash-lite`, `sample_count: 10`, `scored_count: 10`, `unavailable: []`).
- **Observed Scores:** LLM judge scored 10/10 review cases (`S01`–`S10` in `evals/judges/review-set.json`).
- **Calibration Status:** `human_scores: null`, `agreement: null` — human-reviewed calibration labels have not yet been supplied via `evals/judges/calibration_template.json` + `--labels`. Manual labels were intentionally **not** fabricated.

---

## 8. Database Migration Verification

- Verified `0006_enquiry_contact_fields` on:
  1. Fresh empty SQLite DB (`store.init()`)
  2. Populated `0005_enquiry_metadata` DB upgraded to `0006_enquiry_contact_fields` with existing rows preserved and missing `reference` values backfilled (`UPDATE enquiries SET reference = 'ENQ-' || upper(substr(replace(id, '-', ''), 1, 8)) WHERE reference IS NULL OR reference = ''`)
  3. Repeated `store.init()` startup (idempotent, zero errors)
- Primary development DB (`.mira/mira.sqlite3`) remains intact at `0006_enquiry_contact_fields` (`enquiries: 186`, `quotes: 92`, `traces: 496`, `users: 2`) with backup at `.mira/mira.sqlite3.bak.20261125`.

---

## 9. Database Isolation Verification

- **Clean Demo DB Initializer:** Added `scripts/init_demo_db.py` and `make demo-db` to create an isolated demonstration database (`.mira/demo.sqlite3`: `enquiries: 0`, `quotes: 0`, `traces: 0`, `users: 5` synthetic demo accounts: Admin, Approver, Editor, Staff, and Traveller).
- **Eval Isolation Proof:** Verified row counts of both `.mira/mira.sqlite3` and `.mira/demo.sqlite3` before and after running `evals/runner.py`: **identical** (`before_dev == after_dev: True`, `before_demo == after_demo: True`).
- **Git Hygiene:** `git check-ignore -v .mira/demo.sqlite3 .mira/mira.sqlite3` confirms `.mira/` is excluded from git tracking.

---

## 10. Security Verification

- Cross-user enquiry, quote, and trip access blocked (`404` / `[]` / `401`).
- Staff/Editor/Admin cannot publish drafts (`403`); Approver-only publish enforced server-side.
- CSRF `Origin` validation enforced on mutating endpoints (`403`).
- Traces omit raw traveller email/phone PII.
- Secret scan across tracked files (`git grep` for Google/API token patterns): **0 secrets found**.

---

## 11. Confirmed Defects Fixed in Release Candidate

1. **`0006_enquiry_contact_fields.py`:** Added non-null `ENQ-...` reference backfill for pre-0006 rows that lacked a `reference` value during Alembic upgrade.
2. **Demo DB Isolation (`scripts/init_demo_db.py`, `Makefile` `demo-db`):** Added reproducible clean demonstration database initialization separated from `.mira/mira.sqlite3` and evaluation temp DBs.

---

## 12. Remaining Limitations

1. **Human Judge Calibration Pending:** `evals/report/judge.json` has 10/10 LLM judge scores, but human-reviewed labels (`--labels`) have not yet been supplied to compute an empirical human-vs-judge agreement rate.
2. **`make mcp-smoke` Standalone Assumption:** Expects an active API server on port `8000` rather than launching one itself.
3. **Local Demonstration Architecture:** Uses local SQLite persistence and simulated mock booking/payment states; not hardened for multi-instance production deployment.

---

## 13. Submission Readiness Verdict

**READY WITH DOCUMENTED LIMITATIONS** — All automated backend (`206/206`), frontend (`61/61`), real Playwright Chromium E2E (`8/8`), lint/typecheck, build, dataset checksum (`39/39`), migration, security, and DB isolation checks pass cleanly.
