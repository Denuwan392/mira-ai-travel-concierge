# Audit Fix Implementation Report

**Date:** 2026-11-25  
**Reference Audit:** `docs/system-audit/ENQUIRY_AND_CONTEXT_AUDIT.md`

---

## 1. Files Modified / Added

- `apps/api/mira/migrations/versions/0005_enquiry_metadata.py` (new): Idempotent migration adding `updated_at`, `reference`, and `follow_up_date` to `enquiries` and backfilling existing rows.
- `apps/api/mira/agent.py`: Preserved selected tour (`ctx["tour"]`) across pricing follow-ups; added `Month DD, YYYY` date parsing, ambiguous numeric date rejection, Oxford-comma child-age parsing (`7, 7, and 7`), safe enquiry reuse (same tour + reason only), and `reference`/`updated_at` persistence.
- `apps/api/mira/main.py`: Added `_utc_iso` and `_enrich_enquiry`; replaced `LIMIT 10`/`LIMIT 5` `len(...)` counts in `GET /api/traveller/overview` with SQL `COUNT(*)` queries (`total_quotes`, `total_enquiries`, `active_enquiries`, `total_trips`); enriched `/api/traveller/enquiries`, `/api/staff/enquiries`, and `/api/staff/enquiries/{key}`; added `sort` and `follow_up_date` support to staff enquiry endpoints.
- `apps/api/mira/store.py`: Added `_guard_dev_db()` safeguard preventing pytest runs from reading/writing `.mira/mira.sqlite3`.
- `apps/api/tests/test_enquiry_and_context_regression.py` (new): Regression tests covering Tests A–H, `>100` dashboard counts, migration repair, date/age parsing, and dev DB isolation.
- `apps/ceylon-compass/src/routes/profile.tsx`: Rendered `overview.enquiries` list with human-readable tour/reason metadata, UTC timestamps, status badges, and `"Resume →"` links; updated `Saved Journeys` to use `overview.total_trips`.
- `apps/ceylon-compass/src/routes/staff.tsx`: Added assignee filter, sort selector, human-readable tour/traveller/reason metadata, UTC timestamps, quotation/booking status, and `follow_up_date` input while preserving the existing Staff Console layout.

---

## 2. Root Cause of Each Correction

1. **Migration failure (`0003_auth_rbac.py`):** `ALTER TABLE enquiries ADD COLUMN updated_at TEXT DEFAULT CURRENT_TIMESTAMP` is rejected by SQLite on non-empty tables and was silently ignored by `except Exception: pass`. Fixed via `0005_enquiry_metadata.py` using `PRAGMA table_info(enquiries)` inspection and constant/NULL `ALTER TABLE` + `UPDATE` backfill without silent error swallowing.
2. **Selected-tour context loss (`agent.py`):** Follow-up pricing messages containing `"price"`/`"quote"` without `"update"`/`"this tour"` fell through to `action = "custom"`, discarding `ctx["tour"]` and returning `T08, T10, T12`. Fixed by preserving `ctx["tour"]` when a valid tour is selected and pricing/party/date details are provided (while still routing unknown tour names like `"the rainforest expedition"` to `custom`).
3. **Date & child-age parsing (`agent.py`):** `parse_date()` missed `"January 10, 2027"`, and the `aged ...` regex missed `", and "` in `"7, 7, and 7"`. Fixed both and ensured ambiguous numeric dates (`01/10/2027`) trigger `invalid_date` clarification.
4. **Capped dashboard counts (`main.py`):** `GET /api/traveller/overview` used `len(rows)` after `LIMIT 10` / `LIMIT 5`. Fixed with dedicated `SELECT COUNT(*)` queries while keeping list responses paginated.
5. **Dev DB isolation (`store.py`):** Added `_guard_dev_db()` so any pytest execution targeting `.mira/mira.sqlite3` raises `RuntimeError`.
6. **Traveller & Staff UI (`profile.tsx`, `staff.tsx`):** Surfaced enriched enquiry metadata, human-readable `ENQ-...` references, UTC timestamps, and `follow_up_date` without altering the A2UI Travel Workspace or page design.

---

## 3. Migration Safety Report

- **Backup created:** `.mira/mira.sqlite3.bak-20261125` (1,679,360 bytes) before migration.
- **Verification on copy & live dev DB:** `store.init()` ran cleanly and idempotently (tested with two consecutive `store.init()` calls); all `185` existing enquiry rows were preserved with backfilled `updated_at` and unique `ENQ-YYYY-XXXXXXXX` references.
- **Test coverage:** `test_migration_0005_repairs_missing_updated_at_idempotently` verifies repairing a legacy `0004_failed_traces` SQLite database missing `updated_at`, `reference`, and `follow_up_date`.

---

## 4. Updated Test Results & Evaluation Pass Rates

- **Backend pytest suite (`PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests`):** **181 passed**, 0 failed (includes pricing, A2UI, auth/RBAC, deduplication, tour relevance, and enquiry/context regression tests).
- **Frontend Vitest suite (`npm --prefix apps/ceylon-compass test`):** **46 passed** across 6 test files, 0 failed.
- **TypeScript typecheck (`cd apps/ceylon-compass && ./node_modules/.bin/tsc --noEmit`):** **0 errors**.
- **Evaluation suite (`PYTHONPATH=apps/api .venv/bin/python evals/runner.py`):** **53/54 passed (98.1%)**, 63/63 turns validated (only pre-existing `P03` pricing diff `2680` vs `2965`, unrelated to these changes).
- **Original dataset (`git status --short GenAI-Intern-Take-Home-Assignment`):** **Unmodified**.

---

## 5. Remaining Defects / Notes

- **Pre-existing `P03` eval case:** `evals/cases/authored.jsonl` expects `2680` while `test_mira_v3.py` and the rate sheet calculate `2965`; intentionally untouched per pricing integrity rules.
- **Playwright browser E2E:** Vitest + `tsc` + FastAPI `TestClient` E2E tests were executed; live Playwright browser tests were not run in this terminal session (require running dev servers).

---

## 6. Exact Commands to Reproduce Verified Workflows

```bash
# 1. Backend full test suite (including pricing, A2UI, migration, and regression tests)
PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests

# 2. Frontend unit/component tests and TypeScript check
npm --prefix apps/ceylon-compass test
cd apps/ceylon-compass && ./node_modules/.bin/tsc --noEmit

# 3. Evaluation suite
PYTHONPATH=apps/api .venv/bin/python evals/runner.py
```
