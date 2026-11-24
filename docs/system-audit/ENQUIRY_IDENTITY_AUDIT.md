# Enquiry Identity, Reuse & Confirmation Consistency Audit

**Project:** Ceylon Compass Holidays — Mira AI Travel Booking Assistant  
**Document ID:** `docs/system-audit/ENQUIRY_IDENTITY_AUDIT.md`  
**Date:** November 25, 2026  
**Audited Record:** `4fa58796-73e7-40c0-a547-46d75755f3a0`

---

## 1. Exact Database Findings for `4fa58796-73e7-40c0-a547-46d75755f3a0`

Querying `.mira/mira.sqlite3` directly revealed the complete history of `4fa58796-73e7-40c0-a547-46d75755f3a0`:

| Field / Relationship | Observed Value in `.mira/mira.sqlite3` |
| :--- | :--- |
| **Enquiry ID** | `4fa58796-73e7-40c0-a547-46d75755f3a0` |
| **Enquiry `created` Timestamp** | `2026-11-24 19:46:37` (UTC) |
| **Enquiry `updated_at` Timestamp** | `None` (created by pre-reload server process `PID 18762`) |
| **Enquiry `reference`** | `None` (in DB row; derived as `ENQ-2026-4FA58796` in enriched API) |
| **Enquiry `reason` / `status`** | `custom_or_unsupported` / `new` |
| **Enquiry `quote`** | `None` (0 linked quotes in `quotes` table) |
| **Enquiry `trip` JSON** | `'{}'` |
| **Linked Trip ID** | `f5c76e48-1c6c-4267-8b82-419221e99426` (`title: "Find a day trip"`, `revision: 10`) |
| **Linked Visitor / User** | Visitor `b0RNGU2U1RgZXtw3phh1O48vSHKCTPkKFYRbsd9dSrQ` → Admin user (`bea6b5a1-74f1-4b15-b79b-843ed63e7778`, PII redacted) |
| **Currently Linked Trace ID** | `9db6f61e-81e8-4620-b66d-0de6c06755ea` (`traces.created: 2026-11-24 20:37:32` UTC) |
| **Latest Linked Prompt** | `{"type":"REQUEST_QUOTE","payload":{"tourId":"T11","date":"2027-01-10","adults":2,"childAges":[]}}` |

### Turn-by-Turn History on Trip `f5c76e48-1c6c-4267-8b82-419221e99426`

| Turn | Trace Created (UTC) | Prompt Summary | Linked Enquiry After Overwrite |
| :---: | :--- | :--- | :--- |
| 1 | `2026-11-24 19:46:02` | `Find a day trip` | — |
| 2 | `2026-11-24 19:46:14` | `Tell me more about Colombo City Tour` | — |
| 3 | `2026-11-24 19:46:37` | `REQUEST_QUOTE` (`T03`, 3A + 2C) | Created `4fa58796...` (`created = 19:46:37`) |
| 4 | `2026-11-24 19:51:10` | `REQUEST_QUOTE` (`T03`, 2A + 4C) | Overwrote `4fa58796.trace` |
| 5 | `2026-11-24 20:18:55` | `what are the tours in kandy` | — |
| 6 | `2026-11-24 20:20:10` | `REQUEST_QUOTE` (`T09`, 4A + 3C) | Overwrote `4fa58796.trace` |
| 7 | `2026-11-24 20:21:07` | `REQUEST_QUOTE` (`T09`, 2A + 3C) | Overwrote `4fa58796.trace` |
| 8 | `2026-11-24 20:34:24` | `REQUEST_QUOTE` (`T09`, 2A + 3C) | Overwrote `4fa58796.trace` |
| 9 | `2026-11-24 20:37:20` | `REQUEST_QUOTE` (`T08`, 2A) | Overwrote `4fa58796.trace` |
| 10 | `2026-11-24 20:37:32` | `REQUEST_QUOTE` (`T11`, 2A) | Overwrote `4fa58796.trace` (`9db6f61e...`) |

---

## 2. Confirmed Root Cause

1. **This was an INCORRECT cross-tour reuse of an older enquiry record (NOT a duplicate-enquiry bug):**
   - `4fa58796-73e7-40c0-a547-46d75755f3a0` was originally created at `19:46:37 UTC` for `T03` (Colombo City Tour).
   - Because the earlier running backend (`PID 18762`) queried `WHERE t.trip=? AND e.reason='custom_or_unsupported' AND e.status!='closed'` without checking whether the selected tour or custom request matched, **6 subsequent requests across 4 distinct tours (`T03`, `T09`, `T08`, `T11`) reused and overwrote the same `4fa58796` record**.
2. **Why the Displayed Creation Time Appeared Wrong:**
   - The confirmation page and traveller dashboard both retrieved the exact same `4fa58796` record, whose `created` timestamp remained `19:46:37 UTC` (the `T03` turn 51 minutes earlier), even though the user's latest `T11` submission occurred at `20:37:32 UTC` — and `updated_at` was `None`.
3. **Presentation & Policy Gaps:**
   - `GET /api/enquiries/{reference}` omitted `human_reason`, `adults`, `children_count`, and `updated_at`.
   - `EnquiryPage` in `Workspace.jsx` included an unsupported `"get back to you within 24 hours"` promise not backed by the company's policy documents.

---

## 3. Corrections Applied

1. **Scoped Custom Enquiry Deduplication (`apps/api/mira/agent.py`):**
   - Verified quotes (`quote_node`) and missing-rate notices (`compose`) already verify `json.loads(candidate["trip"]).get("tour") == ctx.get("tour")` before reusing a `prior` enquiry.
   - Updated `action == "custom"` in `compose()` so a prior `custom_or_unsupported` enquiry is reused **only** when `panel_action == "date"`, or when `destinations` & `days` (or exact `request`) match — preventing distinct custom journeys from overwriting unrelated enquiries.
2. **Enriched Public Enquiry Endpoint (`apps/api/mira/main.py`):**
   - Updated `GET /api/enquiries/{reference}` to return safe public metadata (`id`, `reference`, `status`, `quote`, `created`, `updated_at`, `tour_id`, `tour_name`, `travel_date`, `adults`, `children_count`, `human_reason`, `quoted_total_usd`, `quoted_deposit_usd`) while strictly excluding internal financials, staff notes, and PII.
3. **Customer-Facing Presentation (`apps/ceylon-compass/workspace/Workspace.jsx`):**
   - Updated `EnquiryPage` to remove the unsupported `"within 24 hours"` response-time promise.
   - Rendered `reference` (`ENQ-2026-XXXXXXXX`), `tour_name`, `travel_date`, `adults`/`children_count` (only when known), `human_reason` (never raw `custom_or_unsupported`), and UTC-normalized local `Submitted` timestamp.
4. **Regression Tests (`apps/api/tests/test_enquiry_identity_lifecycle.py`):**
   - Added 10-point lifecycle coverage verifying new enquiry creation, confirmation & dashboard consistency, `runId` idempotency, cross-tour separation (`T03` → `T01`, `T09` → `T10`, distinct custom trips), quote history preservation, UTC timestamps, public reference search by staff, read-only status lookup, and safe rendering of legacy incomplete records.

---

## 4. Before / After Behavior

| Aspect | Before | After |
| :--- | :--- | :--- |
| **Switching tours on same trip (`T03` → `T09` → `T11`)** | Overwrote `4fa58796` across all tours; `created` stayed `19:46:37` | Each distinct tour/custom request creates its own enquiry with accurate `created` & `updated_at` |
| **Recalculating quote on same tour** | Preserved quote history (when `tour` matched) | Reuses same enquiry for the tour while preserving every historical `quotes` row |
| **Enquiry confirmation page (`/enquiry/{ref}`)** | Promised `"within 24 hours"`; omitted party size, reason, and timestamp | Removes unsupported 24h claim; shows `ENQ-...` reference, tour, date, travellers, human reason, and local time |

---

## 5. Verification Results

- **Backend Pytest Suite (`PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests`):** **212 / 212 passed**
- **Frontend Vitest Suite (`npm --prefix apps/ceylon-compass test`):** **61 / 61 passed**
- **Workspace Bundle Build (`npm --prefix apps/ceylon-compass run workspace:build`):** **Passed**
- **Typecheck & Lint (`make lint`):** **Passed**
- **Playwright Browser Tests (`./scripts/test-workspace.sh`):** **8 / 8 passed** (14.9s) across desktop and mobile E2E workflows
