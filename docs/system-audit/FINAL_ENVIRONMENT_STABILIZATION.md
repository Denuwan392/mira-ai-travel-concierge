# Final Environment Stabilization Report

**Project:** Ceylon Compass Holidays — Mira AI Travel Booking Assistant  
**Document ID:** `docs/system-audit/FINAL_ENVIRONMENT_STABILIZATION.md`  
**Date:** November 25, 2026  
**Active Database:** `.mira/demo.sqlite3` (`database: "demo.sqlite3"`)  
**Backend Revision:** `rc-2026-11-25`

---

## 1. Port & Process Cleanup

1. Inspected listening ports `8000`, `5175`, and `3000`:
   - `lsof -nP -iTCP:8000,5175,3000 -sTCP:LISTEN` identified stale processes `92482` (Python, serving `mira-pricing-acceptance.sqlite3` with revision `live-pricing-repair-r4`), `92484` (Node), and `92487` (Node).
2. Stopped only those stale project processes (`kill 92482 92484 92487`) and verified all three ports were free.
3. Restarted the full stack via `make dev` (`./scripts/dev.sh`):
   - `API` ready on `http://127.0.0.1:8000`
   - `NEXT` ready on `http://127.0.0.1:3000`
   - `WEB` ready on `http://127.0.0.1:5175`

---

## 2. TypeScript Fix in `apps/web/tests/live-pricing.spec.ts`

Fixed the 4 implicit-`any` errors without weakening strict TypeScript checking or test assertions:
- Added `TurnComponent` and `TraceEvent` interfaces.
- Typed component lookups (`as TurnComponent[]`) and trace event lookups (`as TraceEvent[]`).
- Added explicit runtime narrowing guards (`if (!quote) throw new Error(...)`, `if (!notice?.public_reference) throw new Error(...)`).

---

## 3. Build, Lint & Automated Verification Results

| Check | Command | Actual Result |
| :--- | :--- | :--- |
| **Lint & Typecheck** | `make lint` | **Passed** (`compileall`, `apps/web` `tsc --noEmit`, `apps/ceylon-compass` `tsc --noEmit`) |
| **Unit & Integration Tests** | `make test` | **Passed** (`62 / 62` Vitest in 8 files; `216 / 216` pytest) |
| **Production Builds** | `make build` | **Passed** (`apps/ceylon-compass` Nitro build + `apps/web` Next.js 16.4.6 build) |
| **Workspace Browser E2E** | `make workspace-browser` | **Passed** (`8 / 8` Playwright tests in 11.2s) |

---

## 4. Live Stack & Clean Demo Database Verification

Executed against the live `make dev` stack (`:8000`, `:5175`, `:3000`):

1. **Health & Proxy Connectivity:**
   - `GET http://127.0.0.1:8000/api/health` → `database: "demo.sqlite3"`, `revision: "rc-2026-11-25"`, `rates: true`, `published: 30`
   - `GET http://127.0.0.1:5175/api/health` → `database: "demo.sqlite3"`, `revision: "rc-2026-11-25"` (matches backend)
   - `GET http://127.0.0.1:3000/` → `200 OK`
2. **Official Traveller Quotation Workflow (via `:5175`):**
   - `T01` (Sigiriya & Minneriya Day Tour from Kandy), `2026-12-10`, `2` adults → Verified quote `ba421367-6d4e-4651-9452-e9ff85c0c96b` (`USD 315`), enquiry reference `ENQ-2026-46CBE935`.
3. **Traveller & Staff Dashboard Consistency:**
   - `GET /api/enquiries/ENQ-2026-46CBE935` → `reference: "ENQ-2026-46CBE935"`, `tour_id: "T01"`, `travel_date: "2026-12-10"`, `adults: 2`, `status: "new"`.
   - `GET /api/staff/enquiries` (authenticated as `staff.demo@ceyloncompass.example`) → returned `ENQ-2026-46CBE935` with matching `T01`, `2026-12-10`, `2` adults, `status: "new"`.
4. **Staff Rate Preview (Zero DB Writes):**
   - `POST /api/staff/pricing/preview` (`T01`, `2026-12-10`, `2` adults) → `preview_only: true`, `total_usd: 315`; `.mira/demo.sqlite3` row counts remained unchanged (`quotes: 1`, `enquiries: 1`, `traces: 1`).
5. **Original Database & Dataset Preservation:**
   - `.mira/mira.sqlite3` remained untouched (`enquiries: 187`, `quotes: 92`, `traces: 510`, `trips: 80`).
   - `GenAI-Intern-Take-Home-Assignment/ceylon-compass-dataset` was not modified.

---

## 5. Unresolved Limitations

- The live `make dev` stack (`task-1066`) currently holds the single verified quotation/enquiry (`ENQ-2026-46CBE935`) created during live smoke verification in `.mira/demo.sqlite3` (`1` quote, `1` enquiry, `1` trace). Re-running `make demo-db` (after stopping `make dev`) will clear even that verification record if desired.
- `evals/runner.py` (run in the preceding step) reports `53 / 54` passed due to the known `Q-1043` sample email vs. workbook source disagreement.
