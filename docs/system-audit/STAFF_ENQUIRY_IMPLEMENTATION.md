# Staff Enquiry Management & Customer Follow-Up Implementation Report

**Project:** Ceylon Compass Holidays — Mira AI Travel Booking Assistant  
**Document ID:** `docs/system-audit/STAFF_ENQUIRY_IMPLEMENTATION.md`  
**Date:** November 25, 2026  
**Status:** Implemented and Verified

---

## 1. Verified Root Causes

Inspection of the database (`.mira/mira.sqlite3`), migration history, backend APIs, and frontend components confirmed the following root causes:

1. **Missing Contact Persistence (`Workspace.jsx`, `enquiries` table):**
   - `enquiries` had no columns for `contact_name`, `contact_email`, `contact_phone`, `contact_notes`, `is_contactable`, or `enquiry_type`.
   - `BookingFormPanel` and `CustomEnquiryPanel` in `Workspace.jsx` never called a backend persistence API; they generated fake client-side references (`ENQ-${Date.now()}` / `CUS-${Date.now()}`) and fed PII into chat prompts.
2. **Enquiry Duplication on Quote Recalculations (`agent.py`):**
   - `quote_node()` generated a new `uuid4()` enquiry on every price check without checking if the current `trip_id` already had an active open `verified_quote` enquiry, causing multiple duplicate staff tasks per trip.
3. **Unknown Tour Fallback Leakage (`agent.py`):**
   - Asking for the price of an unknown tour (e.g., `"How much is the rainforest expedition for 2 adults?"`) after a previous verified quote kept `ctx["tour"]` from the prior turn and quoted the old tour instead of treating it as a custom/unknown enquiry.
4. **Capped & Unjoined Staff Listing (`main.py`):**
   - `GET /api/staff/enquiries` lacked `contactable`, `limit`/`offset` pagination, and `X-Total-Count` headers, and `_enrich_enquiry()` did not surface submitted contact request fields or phone numbers.
5. **Non-Functional Workspace Staff UI (`Workspace.jsx`):**
   - `StaffPage` in the new Travel Workspace rendered a static 4-column table with hardcoded fallback counts, `"Visitor"` labels, raw snake_case reason codes, and zero interactive detail, status, note, assignment, search, filter, or pagination controls.

---

## 2. Changed Files

| File | Summary of Changes |
| :--- | :--- |
| `apps/api/mira/migrations/versions/0006_enquiry_contact_fields.py` | Safe additive migration adding `contact_name`, `contact_email`, `contact_phone`, `contact_notes`, `is_contactable`, `enquiry_type`, indexes, and backfills. |
| `apps/api/mira/agent.py` | Reuses active open `verified_quote` enquiry per `trip_id` to prevent duplicate staff tasks while keeping all `quotes` rows; populates `enquiry_type` and `is_contactable`; prevents unknown-tour price queries from reusing prior `ctx["tour"]`. |
| `apps/api/mira/main.py` | Added `POST /api/enquiries/contact`; enhanced `GET /api/enquiries/{reference}` (supports UUID or `ENQ-...` reference + authenticated user access); enriched `_enrich_enquiry()` with contact details; added `open_enquiries`, `contactable_enquiries`, `unassigned_enquiries`, `missing_rate_enquiries` to `GET /api/staff/dashboard/overview`; added pagination (`limit`, `offset`, `X-Total-Count`) and `contactable` filter + customer search to `GET /api/staff/enquiries`; expanded `FollowUp` statuses. |
| `apps/ceylon-compass/workspace/Workspace.jsx` | Connected `BookingFormPanel` and `CustomEnquiryPanel` to `POST /api/enquiries/contact` (preserving no-PII LLM traces and real backend references); updated `EnquiryPage`; replaced static `StaffPage` table with a full Master-Detail Staff Enquiry Workspace preserving Ceylon Compass visual styling. |
| `apps/api/tests/test_staff_enquiry_workflow.py` | Added end-to-end regression test covering Cultural Triangle (`T16`) quote/handoff, deduplication, contact persistence, trace PII isolation, RBAC enforcement, staff notes/status/assignment/follow-up persistence, overview metrics, and public enquiry status retrieval. |
| `apps/web/tests/workspace.spec.ts` | Updated staff dashboard assertion to accept `"Verified quote saved"` alongside `"verified_quote"`. |

---

## 3. Database Migrations & Data Protection

- **Database Backup:** Created `.mira/mira.sqlite3.backup_20261125` prior to applying migration `0006_enquiry_contact_fields.py`.
- **Migration `0006_enquiry_contact_fields.py`:**
  - Checks `PRAGMA table_info(enquiries)` before each `ALTER TABLE`.
  - Adds `contact_name`, `contact_email`, `contact_phone`, `contact_notes`, `is_contactable`, and `enquiry_type`.
  - Backfills `enquiry_type` (`verified_quote`, `custom_itinerary`, `missing_rate`) and `is_contactable = 1` for enquiries linked to authenticated `users`.
  - Verified cleanly on both the existing `.mira/mira.sqlite3` database (preserving all 185 historical records) and fresh temporary databases.
- **Test/Eval Isolation:** `apps/api/tests/conftest.py`, `evals/runner.py`, and `scripts/test-workspace.sh` all execute against isolated temporary SQLite databases (`tmp_path` / `TemporaryDirectory` / `mktemp -d`), ensuring tests never pollute `.mira/mira.sqlite3`.

---

## 4. API Contracts

### `POST /api/enquiries/contact` (Traveller / Guest)
- **Body (`ContactEnquiryInput`):** `name`, `email`, `phone` (optional), `enquiry_id` (optional), `quote_id` (optional), `trip_id` (optional), `tour_id`, `tour_title`, `date`, `adults`, `child_ages`, `notes`.
- **Behavior:** Validates email format; attaches contact info to an existing matching enquiry owned by the visitor/user or creates a new enquiry with a non-PII trace (`{"stage": "contact_request"}`).
- **Response:** `{"id": "<uuid>", "reference": "ENQ-2026-XXXXXXXX", "status": "new", "is_contactable": true}`.

### `GET /api/enquiries/{reference}` (Traveller / Guest)
- Accepts either internal `UUID` or public `ENQ-YYYY-XXXXXXXX` reference.
- Authorized by matching `mira_session` visitor cookie or authenticated `user_id`.
- Returns safe public fields only (`id`, `reference`, `status`, `quote`, `created`, `tour_name`, `travel_date`). Internal costs, margins, and staff notes are excluded.

### `GET /api/staff/dashboard/overview` (Staff / Approver / Admin)
- Returns authoritative SQL `COUNT(*)` aggregates: `total_enquiries`, `open_enquiries`, `pending_followups`, `contactable_enquiries`, `unassigned_enquiries`, `missing_rate_enquiries`, `quotes_requiring_confirmation`, `pending_content_approvals`, and `recent_activity`.

### `GET /api/staff/enquiries` (Staff / Approver / Admin)
- Query parameters: `status`, `search` (matches ID, reference, trip JSON, reason, `contact_name`, `contact_email`, `users.full_name`, `users.email`), `assigned_to`, `contactable` (`1` or `0`), `sort` (`newest`, `oldest`, `updated`, `status`, `follow_up`), `limit` (1–200, default 50), `offset`.
- Returns enriched enquiry objects and sets `X-Total-Count` header for pagination.

### `PATCH /api/staff/enquiries/{key}` (Staff / Approver / Admin)
- Accepts `status`, `note` (enforcing PII-free regex guard), `assigned_to`, and `follow_up_date` (`YYYY-MM-DD`).
- Updates `updated_at = CURRENT_TIMESTAMP`, appends operational note to `notes`, and logs immutable entry to `audit`.

---

## 5. Staff UI Changes (`Workspace.jsx`)

The `StaffPage` in `apps/ceylon-compass/workspace/Workspace.jsx` was upgraded while preserving the Ceylon Compass visual system:
- **Authoritative Summary Cards:** `Open enquiries`, `Contactable leads`, `Needs pricing`, and `Unassigned`.
- **Search & Filter Toolbar:** Search input, Status dropdown, Contactable/Anonymous filter, and Sort selector (`Newest first`, `Oldest first`, `Follow-up due`, `Last updated`).
- **Master-Detail Workspace:**
  - Clickable enquiry cards showing `ENQ-...` reference, status pill, contactable/guest badge, human-readable tour name, travel date, party size, quote total or `"Needs quote"`, assignee, follow-up due date, and human-readable reason.
  - Server-side pagination (`Previous` / `Next`).
  - Interactive Detail Panel displaying Traveller Information (`mailto:` / `tel:`), Trip Information, Verified Quote & Staff-Only Margin (`cost_lkr`, `gross_profit_pct`, `mock_booking_status`), Follow-Up Management form (status, assignee, follow-up due date, private note), Notes History, and collapsible Trace Inspector.

---

## 6. Enquiry Lifecycle

Supported statuses:
- **Active / Open:** `new` → `in_review` → `contacted` / `quoted` → `waiting` / `waiting_customer`
- **Terminal / Closed:** `booked`, `closed`, `closed_lost`, `unqualified`

Anonymous price checks and missing-rate notices remain clearly labeled as `Guest traveller` (`is_contactable: false`), while registered accounts and submitted contact forms are flagged as `Contactable` (`is_contactable: true`).

---

## 7. Verification & Test Results

| Check | Result | Notes |
| :--- | :--- | :--- |
| **Backend Pytest Suite** (`pytest -q apps/api/tests`) | **182 / 182 passed** | Includes 43 pricing tests and new `test_staff_enquiry_workflow.py` |
| **React Test Suite** (`npm --prefix apps/ceylon-compass test`) | **46 / 46 passed** | All routing, auth UI, and A2UI component tests pass |
| **Workspace Build** (`npm run workspace:build`) | **Passed** | Built cleanly in 527ms |
| **Typecheck & Lint** (`make lint`) | **Passed** | Python `compileall` + TypeScript `tsc --noEmit` |
| **Deterministic Evaluation** (`evals/runner.py`) | **53 / 54 passed (98.1%)** | Isolated temp DB; 1 expected Q-1043 source discrepancy |
| **Playwright Browser Tests** (`./scripts/test-workspace.sh`) | **8 / 8 passed** | Full end-to-end desktop & mobile browser checks |

---

## 8. Remaining Items & Future Enhancements

- **Bulk Archival of Stale Dev Records:** The 185 pre-existing development rows in `.mira/mira.sqlite3` were intentionally preserved. Staff can filter by `"Contactable leads only"` or mark old guest test rows as `unqualified` / `closed`.
- **Optional P3 Enhancements:** Email notification dispatch on specialist quote delivery and unified cross-channel activity timeline.

---

## 9. Live Demo Instructions

1. Ensure services are running (`make dev`, or verify ports `8000` and `5175` are active).
2. Open the Travel Workspace: [`http://127.0.0.1:5175/dump.html#/mira`](http://127.0.0.1:5175/dump.html#/mira).
3. Ask Mira for **"Cultural Triangle Tour"**, choose a travel date and party, and click **"Send enquiry"** to submit name, email, phone, and notes via `BookingFormPanel`. Note the returned `ENQ-2026-...` reference.
4. Navigate to **Staff Portal** ([`http://127.0.0.1:5175/dump.html#/staff`](http://127.0.0.1:5175/dump.html#/staff)), sign in with staff/admin credentials, filter by **Contactable leads only**, open the enquiry, update status/assignee/follow-up due date, add a private note, save, and refresh the page to confirm persistence.
