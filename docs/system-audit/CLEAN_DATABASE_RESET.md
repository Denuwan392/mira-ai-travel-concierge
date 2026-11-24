# Clean Demo Database Reset Report

**Project:** Ceylon Compass Holidays — Mira AI Travel Booking Assistant  
**Document ID:** `docs/system-audit/CLEAN_DATABASE_RESET.md`  
**Date:** November 25, 2026

---

## 1. Database Locations

| Role | Path | Status |
| :--- | :--- | :--- |
| **Original Development Database** | `.mira/mira.sqlite3` | Preserved untouched (`1,765,376` bytes) |
| **Verified Pre-Reset Backup** | `.mira/mira.sqlite3.backup_20261125_0239` | Created via `sqlite3.Connection.backup()`, `PRAGMA integrity_check = ok`, 100% table count parity |
| **New Clean Demo Database** | `.mira/demo.sqlite3` | Active via `MIRA_DB=.mira/demo.sqlite3` in `.env` |

---

## 2. Schema Inventory & Record Classification

All 16 SQLite tables (Alembic revision `0006_enquiry_contact_fields`):

| Table | Purpose | Record Classification in `.mira/mira.sqlite3` |
| :--- | :--- | :--- |
| `alembic_version` | Schema migration tracking (`0006_enquiry_contact_fields`) | System configuration |
| `users` | Registered staff, approver, admin, and traveller accounts | System configuration + user/test accounts |
| `user_sessions` | Authenticated cookie sessions (`mira_auth`) | User/test-generated |
| `login_attempts` | Rate-limiting & lockout tracking | User/test-generated |
| `visitors` | Anonymous/remembered visitor tokens (`mira_session`) | User/test-generated |
| `trips` | Traveller trip notebooks & context state | User/test-generated |
| `trip_turns` | Turn-to-trip linkage & user prompts | User/test-generated |
| `traces` | AG-UI execution traces & stage events | User/test-generated |
| `failed_traces` | Failed/aborted run diagnostics | Test/runtime-generated |
| `quotes` | Verified server-calculated public & internal quotes | User/test-generated |
| `bookings` | Mock payment/booking records linked to quotes | User/test-generated |
| `enquiries` | Auto-generated & custom specialist enquiries (`ENQ-2026-XXXXXXXX`) | User/test-generated |
| `notes` | Staff internal notes on enquiries | User/test-generated |
| `drafts` | Content studio drafts & published overrides | Test/staff-generated |
| `audit` | Append-only audit log (protected by `BEFORE DELETE/UPDATE` triggers) | System/user/test-generated |
| `rate_snapshots` | Cached SHA-256 snapshot of `rate_sheet_2026-27.xlsx` | Original dataset snapshot |

> **Original Dataset Content:** Tours, destinations, policies (`GenAI-Intern-Take-Home-Assignment/ceylon-compass-dataset/content/*/*.md`), brand pack (`brand/brand_pack.json`), and rate workbook (`rates/rate_sheet_2026-27.xlsx`) are loaded directly from the read-only filesystem by `apps/api/mira/data.py` and `apps/api/mira/rates_repository.py`. They were not modified.

---

## 3. Migrations, Catalogue Loading, and Seeding

1. **Schema Migrations:** Executed automatically by `store.init()` (`apps/api/mira/store.py`) using Alembic (`apps/api/mira/migrations/versions/0001_catalogue.py` through `0006_enquiry_contact_fields.py`) with `PRAGMA journal_mode=WAL`.
2. **Catalogue & Rate Loading:** `apps/api/mira/data.py` loads all published Markdown content from `MIRA_DATA` (`GenAI-Intern-Take-Home-Assignment/ceylon-compass-dataset`), and `apps/api/mira/rates_repository.py` validates and caches `rate_sheet_2026-27.xlsx` in `rate_snapshots` (`digest: a16dd63ffb7ed2324e9d709f4b35e1bb3f0d5c2123b765903bce039f5fefdfe2`).
3. **Synthetic Account Seeding (`scripts/init_demo_db.py`):**
   - `admin.demo@ceyloncompass.example` (`role: admin`)
   - `approver.demo@ceyloncompass.example` (`role: approver`)
   - `editor.demo@ceyloncompass.example` (`role: staff`)
   - `staff.demo@ceyloncompass.example` (`role: staff`)
   - `traveller.demo@ceyloncompass.example` (`role: traveller`)

### Commands Used

```sh
# 1. Initialize clean demo database (Alembic head + 5 synthetic accounts)
PYTHONPATH=apps/api .venv/bin/python scripts/init_demo_db.py --force

# 2. Seed rate_snapshots from official workbook
PYTHONPATH=apps/api MIRA_DB=.mira/demo.sqlite3 .venv/bin/python -c "from mira.rates_repository import current_rates; current_rates()"

# 3. Configure local dev environment (.env)
# MIRA_DB=.mira/demo.sqlite3
```

---

## 4. Before / After Table Counts

| Table | Original (`.mira/mira.sqlite3`) | Backup (`.mira/mira.sqlite3.backup_20261125_0239`) | Clean Demo (`.mira/demo.sqlite3`) |
| :--- | :---: | :---: | :---: |
| `alembic_version` | 1 | 1 | 1 |
| `audit` | 42 | 42 | 0 |
| `bookings` | 32 | 32 | 0 |
| `drafts` | 14 | 14 | 0 |
| `enquiries` | 187 | 187 | 0 |
| `failed_traces` | 3 | 3 | 0 |
| `login_attempts` | 1 | 1 | 0 |
| `notes` | 0 | 0 | 0 |
| `quotes` | 92 | 92 | 0 |
| `rate_snapshots` | 1 | 1 | 1 |
| `traces` | 510 | 510 | 0 |
| `trip_turns` | 210 | 210 | 0 |
| `trips` | 80 | 80 | 0 |
| `user_sessions` | 10 | 10 | 0 |
| `users` | 2 | 2 | 5 |
| `visitors` | 224 | 224 | 0 |

---

## 5. Health & Environment Isolation

- **Backend Health Endpoint (`GET /api/health`):** Updated `apps/api/mira/main.py` to return `"database": store.DB.name` (filename only, e.g. `"demo.sqlite3"`), reporting the active database without exposing host filesystem paths or secrets.
- **Frontend & Backend Wiring:** `.env` sets `MIRA_DB=.mira/demo.sqlite3`. `scripts/dev.sh` sources `.env` for the FastAPI backend (`:8000`), and both frontends (`apps/ceylon-compass` on `:5175` and `apps/web` on `:3000`) proxy `/api/*` to the backend.
- **Browser Session Isolation:**
  - Unknown `mira_session` cookies from `.mira/mira.sqlite3` are rejected on `GET /api/session` (`401`) and automatically replaced with fresh visitor tokens on `POST /api/session`.
  - Unknown `mira-workspace-trip` IDs in `sessionStorage` return `404` from `GET /api/trips/{id}` and trigger creation of a new trip in `.mira/demo.sqlite3`.
- **Automated Test & Eval Isolation:**
  - `apps/api/tests/conftest.py` overrides `store.DB` to `tmp_path / "demo.sqlite3"` and enforces `_guard_dev_db()`.
  - `evals/runner.py` overrides `store.DB` to a `TemporaryDirectory` (`eval.sqlite3`).
  - `scripts/test-workspace.sh` exports `MIRA_DB="$state/mira.sqlite3"` in a temporary directory.

---

## 6. Verification & Post-Reset Acceptance Results

### Post-Reset Acceptance Tests (Executed Directly Against `.mira/demo.sqlite3`, Followed by Clean Re-Seed)
1. **Health & DB Reporting:** `GET /api/health` returned `database="demo.sqlite3"`, `rates=True`, `published=38` (no path separators exposed).
2. **Staff & Approver Auth + Content Publishing RBAC:** Staff login (`staff.demo@ceyloncompass.example`) and Approver login (`approver.demo@ceyloncompass.example`) succeeded; staff publish attempt returned `403`, Approver publish returned `200`.
3. **Published Tour Discovery:** `GET /api/tours` returned published tours including `T01`; `"Show me day trips"` returned validated `Card` components.
4. **Sigiriya Two-Adult Verified Quote (`T01`, `2026-12-10`, 2A):** Returned `Breakdown` with `$315` total, persisted to `quotes` and `enquiries`.
5. **Sigiriya Four-Adult Verified Quote (`T01`, `2026-12-10`, 4A):** Returned `Breakdown` with `$540` total, persisted with `adults=4`.
6. **Cultural Triangle Missing-Rate Handoff (`T09`, `2027-01-10`, 4A + 3C):** Returned `Notice` (`ENQ-2026-6BAEFF42`) with zero `Breakdown` components and no invented prices.
7. **Private Enquiry Persistence & Dashboard Visibility:** `GET /api/enquiries/{id}` and `GET /api/staff/enquiries` both returned `ENQ-2026-6BAEFF42` linked to `T09` and `status="new"`.
8. **Staff Enquiry Status Update:** `PATCH /api/staff/enquiries/ENQ-2026-6BAEFF42` updated status to `in_review` and persisted staff note.
9. **Returning Visitor Session:** Reusing the `mira_session` cookie across a fresh client restored `remember=True` and both persisted trips.
10. **A2UI Validation & Staff Rate Preview (Zero DB Writes):** All turns passed `Turn.model_validate()`, and `POST /api/staff/pricing/preview` returned `preview_only=True` while `quotes`, `enquiries`, and `traces` row counts remained unchanged (`20`, `27`, `36`).

### Automated Suites (Isolated Temporary Databases)
- **Backend Pytest (`PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests`):** `216 passed` (18.26s)
- **Deterministic Evaluation (`PYTHONPATH=apps/api .venv/bin/python evals/runner.py`):** `53 / 54 passed` (`63` validated turns; 1 known `Q-1043` source disagreement)
- **Frontend Vitest (`npm --prefix apps/ceylon-compass test`):** `62 passed` (8 files)
- **Playwright Workspace E2E (`./scripts/test-workspace.sh`):** `8 passed` (12.1s)

---

## 7. Rollback Procedure

To revert to the original development database without data loss:

1. Stop running dev servers (`make dev`).
2. Update `.env` to remove `MIRA_DB=.mira/demo.sqlite3` or set `MIRA_DB=.mira/mira.sqlite3`.
3. If needed, restore from the verified backup:
   ```sh
   cp .mira/mira.sqlite3.backup_20261125_0239 .mira/mira.sqlite3
   ```
4. Restart `make dev`.

---

## 8. Known Limitations

- Running `scripts/init_demo_db.py --force` generates fresh random passwords for the 5 synthetic demo accounts on stdout unless `MIRA_ADMIN_PASSWORD` / `MIRA_DEMO_*_PASSWORD` environment variables are explicitly supplied.
- `make lint` currently fails on 4 pre-existing implicit-`any` TypeScript errors in `apps/web/tests/live-pricing.spec.ts` (unrelated to this database reset; `apps/ceylon-compass` `tsc --noEmit` and Python `compileall` pass).
- An existing background API process (`PID 88967`) was observed listening on port `8000` prior to updating `.env`; `make dev` must be restarted after stopping that process so the live server picks up `MIRA_DB=.mira/demo.sqlite3`.
