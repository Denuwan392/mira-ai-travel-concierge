# System Audit: Tour Context, Enquiry Persistence, Dashboard Synchronization, and Missing Metadata

**Date:** 2026-11-25  
**Scope:** End-to-end audit of `apps/api/mira` (LangGraph agent, FastAPI endpoints, SQLite migrations) and `apps/ceylon-compass` (Travel Workspace, Traveller Profile, Quotes, Trips, and Staff Console).  
**Status:** Audit complete. **No application code was modified during this audit.**

---

## Executive Summary

All five reported issues were reproduced and verified against the codebase and SQLite database (`.mira/mira.sqlite3` and isolated `TestClient` runs):

1. **Bug 1 (Wrong Tour Recommendations After Quote Request — Critical / P0):** Multi-turn follow-up pricing requests (e.g., `"Price for 10 January 2027 for two adults and three children aged 7, 7, and 7"` after selecting `T16`) are misclassified as `action = "custom"`, discarding the selected tour (`ctx["tour"] = "T16"`) and returning unrelated fallback tours (`T08, T10, T12`, or `T03/T04` via LLM ranking). Additionally, `parse_date()` does not parse `"Month Day, Year"` (`"January 10, 2027"`), and the child-age regex fails on Oxford commas (`"aged 7, 7, and 7"`).
2. **Bug 2 (Dashboard Metrics Capped at 10 / 10 / 5 — High / P1):** `GET /api/traveller/overview` queries `quotes` and `enquiries` with `LIMIT 10` and computes `total_quotes = len(quotes_rows)` and `total_enquiries = len(enquiries_rows)`, hard-capping both metrics at `10`. `trips` is queried with `LIMIT 5`, hard-capping `Saved Journeys` at `5`. Furthermore, `profile.tsx` never renders `overview.enquiries`, and `evals/runner.py` / manual runs pollute `.mira/mira.sqlite3` (`185` enquiries, `223` visitors).
3. **Bug 3 (Missing / Raw Enquiry Metadata — High / P1):** `enquiries` lacks human-readable references, explicit UTC/timezone-aware timestamps, customer classification (`Guest traveller` vs authenticated user), parsed tour/traveller fields, follow-up dates, and mock booking status. `staff.tsx` renders raw JSON strings (`e.trip`) and raw reason codes (`tour_rate`).
4. **Bug 4 (Staff Enquiry Management Incomplete & Broken on Migrated DB — Critical / P0):** Migration `0003_auth_rbac.py` ran `ALTER TABLE enquiries ADD COLUMN updated_at TEXT DEFAULT CURRENT_TIMESTAMP` inside a `try/except pass`, which SQLite rejects on non-empty tables. As a result, `updated_at` is **missing** from `.mira/mira.sqlite3`, causing `PATCH /api/staff/enquiries/{key}` to fail on the existing dev DB. Follow-up dates, sorting, and `assigned_to` UI filtering are also missing.
5. **Bug 5 (Cross-Dashboard Metric Inconsistency — Medium / P2):** Traveller overview counts all-status enquiries (capped at 10) and `revision > 0` trips (capped at 5), while Staff overview counts global `enquiries` across all visitors/guests and `status IN ('new', 'waiting')` without matching traveller-facing labels.

---

## 1. Reproduction Steps & Observed Behavior

### Bug 1 — Wrong Tour Recommendations After Quote Request
1. Start a fresh Travel Workspace (`POST /api/trips`).
2. Turn 1: Send `"Cultural Triangle Tour"` → Mira selects `T16` (`Cultural Triangle Tour`, `ctx["tour"] = "T16"`).
3. Turn 2: Send `"Price for 10 January 2027 for two adults and three children aged 7, 7, and 7"`.
4. **Observed:**
   - `interpret()` sets `action = "custom"`.
   - `retrieve()` returns `["T08", "T10", "T12"]` (or LLM-ranked unrelated tours such as `T03` Colombo City Tour / `T04` Galle Fort Walking Tour when Gemini is enabled).
   - `compose()` returns `EnquiryNotice` + `TourCard` for `T08`, `T10`, `T12`. `T16` is completely absent.
5. **Variants also reproduced:**
   - Single-turn `"Price for Cultural Triangle Tour on January 10, 2027, for two adults and three children aged 7, 7, and 7"` → `parse_date()` returns `None` (because `"January 10, 2027"` is not `DD Month YYYY`), returning `TravellerPicker` with no quote/enquiry.
   - Single-turn `"Cultural Triangle Tour on 2027-01-10 for 2 adults and 3 children aged 7, 7, and 7"` → `ages` regex captures only `[7, 7]` (2 ages instead of 3 due to `", and "`), failing `kids == len(ages)` and asking `"Who’s coming? Please include the ages of any children."`

### Bug 2 — Dashboard Metrics Capped at 10 / 10 / 5
1. Authenticate as a traveller (`POST /api/auth/register` or `/api/auth/login`).
2. Create 13 enquiries across trips (`@trip T16 2027-01-10 2 7,7,7`).
3. Call `GET /api/traveller/overview`.
4. **Observed:**
   - Database `enquiries` table contains `13` rows for this user.
   - `GET /api/traveller/overview` returns `total_enquiries: 10`, `len(enquiries): 10`, `len(trips): 5`.
   - `profile.tsx` displays `10` for Private Enquiries and `5` for Saved Journeys, and does not render any list of enquiries.

### Bug 4 — Missing `updated_at` Column in `.mira/mira.sqlite3`
1. Inspect `PRAGMA table_info(enquiries)` on `.mira/mira.sqlite3`.
2. **Observed columns:** `['id', 'trace', 'quote', 'trip', 'reason', 'status', 'created', 'assigned_to', 'assigned_name']`.
3. `updated_at` is absent because `0003_auth_rbac.py` swallowed the SQLite `OperationalError: Cannot add a column with non-constant default`.

---

## 2. Confirmed Root Causes

| Area | File & Lines | Root Cause |
|---|---|---|
| **Follow-up pricing misclassification** | [agent.py](file:///Users/denuwanwijesinghe/Documents/BSc.%20Artficial%20Intellligence/Competition/intern_assignment/apps/api/mira/agent.py#L299-L303) | `if action == "discover" and not named and re.search(r"price\|how much\|quote", text):` overwrites `action = "custom"` unless `explicit_followup` or `party_reply` matches, **even when `ctx.get("tour")` is already set** (`T16`). |
| **Date parsing gap** | [agent.py](file:///Users/denuwanwijesinghe/Documents/BSc.%20Artficial%20Intellligence/Competition/intern_assignment/apps/api/mira/agent.py#L45-L52) | `parse_date()` only supports `YYYY-MM-DD` and `DD Month YYYY`, not `Month DD, YYYY` (`January 10, 2027`). |
| **Oxford-comma age parsing** | [agent.py](file:///Users/denuwanwijesinghe/Documents/BSc.%20Artficial%20Intellligence/Competition/intern_assignment/apps/api/mira/agent.py#L257) | `(\d{1,3}(?:\s*(?:,\|and)\s*\d{1,3})*)` fails on `", and "` in `"aged 7, 7, and 7"`, extracting 2 ages for 3 kids. |
| **Custom fallback tours** | [agent.py](file:///Users/denuwanwijesinghe/Documents/BSc.%20Artficial%20Intellligence/Competition/intern_assignment/apps/api/mira/agent.py#L448-L460) | `action == "custom"` defaults to `["T08", "T10", "T12"]` and calls `rank(w["tours"], ...)` without preserving `ctx.get("tour")`. |
| **Enquiry deduplication / overwrite** | [agent.py](file:///Users/denuwanwijesinghe/Documents/BSc.%20Artficial%20Intellligence/Competition/intern_assignment/apps/api/mira/agent.py#L564-L579) & [L789-L793](file:///Users/denuwanwijesinghe/Documents/BSc.%20Artficial%20Intellligence/Competition/intern_assignment/apps/api/mira/agent.py#L789-L793) | Reuses `prior["id"]` for any non-closed enquiry on `trip_id`, and `ON CONFLICT(id) DO UPDATE` only updates `trace` and `trip` (leaving `reason`, `quote`, `status` stale). |
| **Traveller overview count cap** | [main.py](file:///Users/denuwanwijesinghe/Documents/BSc.%20Artficial%20Intellligence/Competition/intern_assignment/apps/api/mira/main.py#L624-L675) | `LIMIT 10` on `quotes_rows`/`enquiries_rows` and `LIMIT 5` on `trips_rows`, then `len(...)` used as total counts. |
| **Silent migration failure** | [0003_auth_rbac.py](file:///Users/denuwanwijesinghe/Documents/BSc.%20Artficial%20Intellligence/Competition/intern_assignment/apps/api/mira/migrations/versions/0003_auth_rbac.py#L53-L56) | `ALTER TABLE enquiries ADD COLUMN updated_at TEXT DEFAULT CURRENT_TIMESTAMP` fails on non-empty SQLite tables and is silenced by `except Exception: pass`. |
| **Missing UI enquiry list & raw staff rendering** | [profile.tsx](file:///Users/denuwanwijesinghe/Documents/BSc.%20Artficial%20Intellligence/Competition/intern_assignment/apps/ceylon-compass/src/routes/profile.tsx#L231-L274), [staff.tsx](file:///Users/denuwanwijesinghe/Documents/BSc.%20Artficial%20Intellligence/Competition/intern_assignment/apps/ceylon-compass/src/routes/staff.tsx#L558-L600) | `profile.tsx` never renders `overview.enquiries`; `staff.tsx` renders raw `e.trip` JSON and raw `e.reason` codes. |

---

## 3. Relevant Source Files & Functions

- **Agent & State:** `apps/api/mira/agent.py` (`parse_date`, `interpret`, `retrieve`, `quote_node`, `compose`, `persist`)
- **API Endpoints:** `apps/api/mira/main.py` (`traveller_overview`, `traveller_quotes`, `traveller_enquiries`, `visitor_enquiry`, `dashboard_overview`, `enquiries`, `enquiry`, `follow_up`)
- **Auth & Sessions:** `apps/api/mira/auth.py` (`create_user_session`, `get_current_user_optional`)
- **Migrations:** `apps/api/mira/migrations/versions/0001_catalogue.py`, `0002_notebooks.py`, `0003_auth_rbac.py`
- **Frontend:**
  - `apps/ceylon-compass/src/routes/plan.tsx` & `apps/ceylon-compass/src/components/plan/LiveCanvas.tsx`
  - `apps/ceylon-compass/src/routes/profile.tsx`
  - `apps/ceylon-compass/src/routes/quotes.tsx`
  - `apps/ceylon-compass/src/routes/trips.tsx`
  - `apps/ceylon-compass/src/routes/staff.tsx`

---

## 4. Actual API Requests & Responses (Redacted)

### Reproduction 1: Follow-up Pricing on `T16` (Bug 1)
- **Request:** `POST /api/agent?trip_id=<trip_uuid>` with `{"messages": [{"content": "Price for 10 January 2027 for two adults and three children aged 7, 7, and 7"}]}` (after Turn 1 `"Cultural Triangle Tour"`).
- **Response (`STATE_SNAPSHOT.turn`):**
  ```json
  {
    "text": "A travel specialist will confirm the details. I’ve saved a private enquiry for our team. Limited service: I’m using the published catalogue.",
    "sources": ["T08", "T10", "T12"],
    "components": [
      {"type": "EnquiryNotice", "reference": "<uuid>", "text": "Specialist confirmation required"},
      {"type": "TourCard", "id": "T08", "title": "Highlights of Sri Lanka"},
      {"type": "TourCard", "id": "T10", "title": "Instafamous Sri Lanka"},
      {"type": "TourCard", "id": "T12", "title": "Treasures of Sri Lanka"}
    ]
  }
  ```

### Reproduction 2: Traveller Overview Cap (Bug 2)
- **Request:** `GET /api/traveller/overview` (after creating 13 enquiries).
- **Response (abbreviated):**
  ```json
  {
    "total_quotes": 0,
    "total_enquiries": 10,
    "enquiries": ["... 10 items ..."],
    "trips": ["... 5 items ..."]
  }
  ```

### Reproduction 3: Staff Enquiry Detail (Bug 3)
- **Request:** `GET /api/staff/enquiries/<enquiry_uuid>`
- **Response keys:** `["assigned_name", "assigned_to", "created", "events", "finance", "id", "notes", "quote", "reason", "status", "trace", "trip", "updated_at"]` (note: `updated_at` is absent on `.mira/mira.sqlite3`).
- **`trip` field:** `"{\"tour\":\"T16\",\"date\":\"2027-01-10\",\"adults\":2,\"kids\":3,\"ages\":[7,7,7],\"traveller_type\":\"family\",\"trip_type\":\"multi-day\"}"`

---

## 5. Database Findings (`.mira/mira.sqlite3`)

- **Row counts:** `visitors: 223`, `users: 2` (`1` admin, `1` traveller), `trips: 78`, `traces: 489`, `quotes: 92`, `enquiries: 185` (all `status='new'`), `notes: 0`, `audit: 39`, `bookings: 32`, `drafts: 14`.
- **Test contamination:** Automated test/eval runs executed without an isolated `MIRA_DB` wrote `185` enquiries and `223` visitors into `.mira/mira.sqlite3`.
- **Schema defect:** `enquiries` table in `.mira/mira.sqlite3` is missing `updated_at` due to the silent `ALTER TABLE` failure in `0003_auth_rbac.py`.

---

## 6. UI State-Flow Analysis

- **Travel Workspace (`plan.tsx` → `LiveCanvas.tsx`):** `LiveCanvas` is stateless with respect to tour selection; it renders `last.turn.components` from the latest `STATE_SNAPSHOT`. Therefore, when the backend drops `ctx["tour"]` and emits `TourCard`s for `T08, T10, T12` (or `T03, T04`), the right-side Travel Workspace immediately switches to displaying those unrelated tours.
- **Traveller Profile (`profile.tsx`):** Fetches `/api/traveller/overview` once on mount (`useEffect(..., [])`). There is no refetch trigger when returning from `/plan` (though client-side navigation remounts `ProfilePage`), and `overview.enquiries` is stored in state but never rendered in JSX.
- **Staff Console (`staff.tsx`):** `Enquiries` tab loads up to 100 rows via `GET /api/staff/enquiries`. `status` and `search` filters require clicking `Apply Filter`. `assigned_to` filter and sort controls are not rendered.

---

## 7. Missing Enquiry Metadata

| Metadata Field | Current State | Gap |
|---|---|---|
| Human-readable reference (e.g. `ENQ-YYYY-NNNN`) | Missing | Only raw UUID `id` exists |
| Internal ID | Present (`id`) | Exposed directly in UI |
| Created / Updated timestamps | `created` (UTC string without `Z`); `updated_at` missing on migrated DB | Need ISO-8601 UTC (`Z`) + explicit timezone rendering |
| Traveller name / email / classification | Missing from enquiry API | Must join `traces → visitors → users`; use `"Guest traveller"` / `"Contact details not provided"` when absent |
| Tour name & Tour ID | Buried in `trip` JSON (`"tour": "T16"`) | Expose `tour_id` and resolved `tour_name` |
| Travel date, adults, children, ages | Buried in `trip` JSON | Expose structured `travel_date`, `adults`, `children_count`, `child_ages` |
| Category & Human-readable reason | Only raw `reason` (`tour_rate`, `custom_or_unsupported`) | Map to `enquiry_category` and `human_reason` |
| Quotation status, total, deposit | Only `quote` UUID in list; `finance` in detail | Expose `quotation_status`, `quoted_total_usd`, `quoted_deposit_usd` |
| Follow-up status, assignee, notes | Present (`status`, `assigned_to`, `assigned_name`, `notes`) | `follow_up` crashes on migrated DB without `updated_at` |
| Follow-up date | Missing | Not in DB, API, or UI |
| Last activity & Mock booking status | Missing | Derive from latest note/audit/update and `bookings` table |

---

## 8. Staff Enquiry Management Audit (Bug 4)

| # | Action | Classification | Notes |
|---|---|---|---|
| 1 | Open an enquiry | **Partially working** | Opens detail panel; displays raw `trip` JSON and UUIDs. |
| 2 | Inspect full information | **Partially working** | Missing traveller classification, tour title, booking status, timezone. |
| 3 | View associated quote | **Partially working** | Shows `finance` (`cost_lkr`, `gross_profit_pct`, `total`), missing `deposit`, `balance`, `date`, `ages`, booking status. |
| 4 | View traveller configuration | **Partially working** | Shown only as unparsed JSON string in `trip`. |
| 5 | Identify why confirmation is required | **Partially working** | Shows raw `reason` code (`tour_rate`) instead of human explanation. |
| 6 | Add private notes | **Broken on migrated DB** | Crashes on `.mira/mira.sqlite3` due to missing `updated_at`; works on fresh DB. |
| 7 | Change follow-up status | **Broken on migrated DB** | Crashes on `.mira/mira.sqlite3` due to missing `updated_at`; works on fresh DB. |
| 8 | Assign responsibility | **Broken on migrated DB** | Backend supports `assigned_to`, crashes on `.mira/mira.sqlite3` due to missing `updated_at`. |
| 9 | Set follow-up dates | **Missing** | No column, API field, or UI control. |
| 10 | View activity history | **Partially working** | Trace `events` shown; no unified per-enquiry timeline (creation + notes + status + booking). |
| 11 | Access originating trace | **Partially working** | Raw `<a href="/api/staff/traces/{trace}">` link; fails if using Bearer token instead of cookie. |
| 12 | Search, filter, and sort enquiries | **Partially working** | `status` and `search` work; `assigned_to` filter not in UI; no sort options (`ORDER BY rowid DESC` hardcoded). |

---

## 9. Dashboard Metric Definitions (Bug 5)

| Metric | Endpoint | Current Definition | Discrepancy / Issue |
|---|---|---|---|
| **Verified Quotes** (`profile.tsx`) | `GET /api/traveller/overview` | `len(quotes LIMIT 10)` for visitor + linked `user_id` | Capped at 10; includes expired/superseded quotes. |
| **Private Enquiries** (`profile.tsx`) | `GET /api/traveller/overview` | `len(enquiries LIMIT 10)` for visitor + linked `user_id` | Capped at 10; includes `closed` enquiries (not just active). |
| **Saved Journeys** (`profile.tsx`) | `GET /api/traveller/overview` | `len(trips WHERE revision > 0 LIMIT 5)` | Capped at 5; does not match `/trips` (which has no `revision > 0` or `LIMIT 5`). |
| **Total Enquiries** (`staff.tsx`) | `GET /api/staff/dashboard/overview` | `COUNT(*) FROM enquiries` (global) | Global across all guests + users; contaminated by test runs in `.mira/mira.sqlite3`. |
| **Pending Follow-ups** (`staff.tsx`) | `GET /api/staff/dashboard/overview` | `COUNT(*) FROM enquiries WHERE status IN ('new', 'waiting')` | Excludes `contacted` (open but awaiting resolution). |
| **Quotes Requiring Confirmation** (`staff.tsx`) | `GET /api/staff/dashboard/overview` | `COUNT(*) FROM enquiries WHERE reason='verified_quote' AND status='new'` | Accurate for new verified quotes. |

---

## 10. Security Implications

- **Account isolation:** Verified working (`Test E`: Traveller 2 receives `404` on Traveller 1's enquiry ID and `0` in `/api/traveller/overview`).
- **Role enforcement:** Verified working (`traveller` receives `403` on `/api/staff/enquiries/{id}`).
- **PII protection:** `PATCH /api/staff/enquiries/{key}` rejects notes containing `@` or 7+ consecutive digits (`422`). When exposing traveller name/email to staff from `users`, ensure guest sessions never fabricate PII (`"Guest traveller"` / `"Contact details not provided"`).
- **Cookie vs Bearer precedence:** `get_current_user_optional` checks `mira_auth` cookie before `Authorization: Bearer`, which can cause a logged-in traveller cookie in the same browser to override a staff Bearer token.

---

## 11. End-to-End Test Results (Observed)

| Test | Description | Result | Observed Evidence |
|---|---|---|---|
| **A** | Preserve `T16` on follow-up pricing (`2 adults, 3 kids aged 7, 7, 7`) | **FAIL** | Returned `T08, T10, T12` (`action="custom"`); `parse_date` failed `"January 10, 2027"`; `ages` failed `"7, 7, and 7"`. |
| **B** | Enquiry persistence (`@trip T16 2027-01-10 2 7,7,7`) | **PASS** | `EnquiryNotice` returned UUID; `GET /api/enquiries/{ref}` returned `200` with `status: "new"`. |
| **C** | Dashboard freshness after 13 enquiries | **FAIL** | DB had `13` enquiries; `/api/traveller/overview` returned `total_enquiries: 10`, `trips: 5`. |
| **D** | Retry deduplication (same `run_id`) | **PASS** | Replayed identical `trace` UUID without creating duplicate enquiry. |
| **E** | Account isolation | **PASS** | Traveller 2 received `404` on Traveller 1's enquiry and `0` in overview. |
| **F** | Metadata consistency | **PARTIAL** | Fresh DB had `updated_at` & `trip` JSON; `.mira/mira.sqlite3` lacked `updated_at`; human metadata missing. |
| **G** | Staff status update (`PATCH`) | **PASS (fresh DB) / FAIL (migrated DB)** | `200 {"status":"contacted"}` on fresh DB; fails on `.mira/mira.sqlite3` due to missing `updated_at`. |
| **H** | Session restoration | **PASS** | Re-logging in as `t1@example.com` restored `total_enquiries: 1`, `trips: 1`. |

---

## 12. Corrective Implementation Plan (Prioritized)

### Priority 0 (Critical — Fix Immediately)
1. **Preserve selected tour & fix date/age parsing (`apps/api/mira/agent.py`):**
   - When `ctx.get("tour")` is set and the user asks for a price/quote follow-up (e.g., `"Price for 10 January 2027 for two adults and three children aged 7, 7, and 7"`), keep `action = "discover"` and preserve `ctx["tour"]` instead of falling back to `action = "custom"`.
   - Support `"Month Day, Year"` in `parse_date()` and Oxford commas (`", and "`) in child-age extraction.
   - Ensure missing-rate `quote_node` errors preserve the selected tour (`T16`) and never replace it with unrelated tours.
2. **Repair `enquiries.updated_at` migration (`apps/api/mira/migrations/versions/` + `store.py`):**
   - Add a new migration `0005_enquiry_metadata.py` that safely adds `updated_at TEXT` (without `DEFAULT CURRENT_TIMESTAMP` in `ALTER TABLE`), `reference TEXT`, and `follow_up_date TEXT`, backfilling `updated_at = created` and generating human-readable `ENQ-...` references.

### Priority 1 (High — Dashboard Accuracy & Enquiry Metadata)
3. **Fix `/api/traveller/overview` counts (`apps/api/mira/main.py`):**
   - Run dedicated `SELECT COUNT(*) ...` queries for `total_quotes`, `total_enquiries` (plus `active_enquiries` where `status != 'closed'`), and `total_trips` instead of `len(rows)` after `LIMIT 10` / `LIMIT 5`.
4. **Enrich Enquiry API & UI (`main.py`, `profile.tsx`, `staff.tsx`):**
   - Add structured `EnquirySummary` fields (human-readable reference, ISO-8601 UTC timestamps, traveller classification/contact, `tour_id`, `tour_name`, `travel_date`, `adults`, `children_count`, `child_ages`, `enquiry_category`, `human_reason`, `quotation_status`, `quoted_total_usd`, `quoted_deposit_usd`, `mock_booking_status`, `follow_up_date`, `last_activity_at`).
   - Render the traveller's Private Enquiries list in `profile.tsx` and format timestamps with an explicit timezone label.
   - Upgrade `staff.tsx` enquiry list & detail panel to show human-readable tour/traveller/reason metadata, follow-up date input, assignee filter, and sort selector, while preserving the existing layout.

### Priority 2 (Medium — Regression Tests & DB Hygiene)
5. **Regression Tests (`apps/api/tests/test_enquiry_and_context_regression.py`):**
   - Automate Tests A–H in pytest, including migrated-DB `updated_at` verification, `>10` enquiry overview counts, and Oxford-comma / US-date parsing.
   - Ensure `evals/runner.py` / scripts default to a separate `MIRA_DB` or clean up test rows so `.mira/mira.sqlite3` is not contaminated.
