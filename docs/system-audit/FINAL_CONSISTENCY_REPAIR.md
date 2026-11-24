# Final Consistency Repair Report: Mira Pricing, Enquiry, Dashboard & State Consistency

**Project:** Ceylon Compass Holidays — Mira AI Travel Booking Assistant  
**Document ID:** `docs/system-audit/FINAL_CONSISTENCY_REPAIR.md`  
**Date:** November 25, 2026  
**Status:** Implemented & Verified

---

## 1. Confirmed Root Causes (Bugs A–G)

Investigation of the live database (`.mira/mira.sqlite3`), trace logs, backend services, and frontend state revealed the exact causes of all seven reported inconsistencies:

1. **Stale Running Backend Process (`PID 18762` on Port 8000):**
   - Inspection of trace `4fa58796` (`2026-11-24 19:46:37 UTC`) in `.mira/mira.sqlite3` showed `{"type":"REQUEST_QUOTE","payload":{"tourId":"T03","date":"2027-01-10","adults":2,"childAges":[7,7,7,7]}}` being routed through the legacy `gemini_intent` → `custom_or_unsupported` path with `updated_at: None`, `reference: None`, and `enquiry_type: 'auto'`.
   - The running `mira.serve` process (`PID 18762`) on port `8000` had been running from an earlier session without reloading updated Python modules, causing live browser requests to hit old `agent.py` and `main.py` logic.
   - **Important:** When tested against the updated backend (`TestClient`), `T03` (Colombo City Tour) on `2027-01-10` for `2` adults and `4` children aged `[7, 7, 7, 7]` **does** have valid workbook rates and deterministically calculates **`total: USD 245`, `deposit: USD 245`, `balance: USD 0`**.

2. **Slug vs. ID Resolution in Structured Quote Actions (`agent.py` — Bugs A & B):**
   - `structured_action` (`REQUEST_QUOTE` / `PRICE_TOUR` / `SELECT_TOUR`) assumed `tourId` was always an uppercase tour ID (`T03`), without resolving tour slugs (`colombo-city-tour`).

3. **Contactability Flag Trusting Stale Column (`main.py` — Bug D):**
   - `_enrich_enquiry()` previously computed `"is_contactable": bool(data.get("is_contactable") or data.get("contact_email"))` before evaluating `include_traveller`, allowing legacy rows with `is_contactable=1` and empty email/phone to appear contactable if `include_traveller=False`.

4. **Missing Traveller Overview Lists & `sessionStorage` Mismatch (`main.py`, `Workspace.jsx` — Bug F):**
   - `GET /api/traveller/overview` did not return `tour`, `tour_name`, `date`, or `adults` on `trips`, and `active_enquiries` only excluded `'closed'` rather than all terminal statuses (`booked`, `closed`, `closed_lost`, `unqualified`).
   - `ProfilePage` in `Workspace.jsx` wrote `localStorage.setItem('mira-workspace-trip', ...)` while `useConversation.js` read `sessionStorage.getItem('mira-workspace-trip')`, preventing `"Resume"` / `"Open"` from restoring the selected trip.

5. **Rate Status Wording (`Workspace.jsx` — Section 10):**
   - `ProfilePage` displayed `"Current Rate"` / `"Current rate"` and `RegisterPage` used `"guaranteed transparent rates"` instead of `"Price verified"` / `"verified transparent rates"`.

---

## 2. Files Modified / Added

| File | Summary of Changes |
| :--- | :--- |
| `apps/api/mira/agent.py` | Resolved `tourId` by ID or slug in `structured_action` (`REQUEST_QUOTE`, `PRICE_TOUR`, `SELECT_TOUR`, `VIEW_TOUR`); normalized `childAges` integers; preserved `ctx["tour"]` across follow-ups while routing unknown tour names to `custom`; reused active open `verified_quote` enquiry per `trip_id`. |
| `apps/api/mira/main.py` | Computed `is_contactable` strictly from actual usable email/phone channels (`contact_email` or `users.email`); updated `active_enquiries` filter to exclude terminal statuses (`booked`, `closed`, `closed_lost`, `unqualified`); enriched `trips` in `GET /api/traveller/overview` with `tour`, `tour_name`, `date`, `adults`, `updated`; included `trip_id` and `children` on `quotes` and `last_quote`. |
| `apps/ceylon-compass/workspace/Workspace.jsx` | Updated `"Current Rate"` → `"Price verified"` and `"guaranteed transparent rates"` → `"verified transparent rates"`; synchronized both `sessionStorage` and `localStorage` on `"Resume"` / `"Open"` in `ProfilePage`; preserved `StaffConsole` integration and `isQuoteCompatible` stale-quote checks. |
| `apps/api/tests/test_final_consistency_repair.py` | Added targeted regression tests covering Tests 1–10 (Colombo City Tour `T03` exact price `USD 245`, tour preservation, A2UI relevance, staff metrics vs pagination, contactability on fresh & legacy incomplete rows, enquiry metadata, traveller dashboard ownership isolation, and quote deduplication). |

---

## 3. Before / After Behavior

| Area | Before | After |
| :--- | :--- | :--- |
| **Colombo City Tour (`T03`, `2027-01-10`, 2A + 4C aged 7)** | Routed to `custom_or_unsupported`, returned `EnquiryNotice` + `T03` + `T09` cards (stale server) | Returns verified `PriceBreakdown` (`USD 245` total, `USD 245` deposit, `USD 0` balance) and preserves `T03` only |
| **Staff Dashboard Counts** | Showed `0 / 0 / 0 / 0` with `186 total recorded` due to old backend serializer | Authoritative SQL aggregates: `open_enquiries`, `contactable_enquiries`, `missing_rate_enquiries`, `unassigned_enquiries` |
| **Contactability Badge** | Legacy/stale `is_contactable=1` rows without email/phone could appear contactable | Strictly requires usable `contact_email` or registered `users.email`; anonymous sessions show `Guest traveller` / `Guest only` |
| **Traveller Profile Overview** | `trips` lacked `tour_name`/`date`/`adults`; `"Resume"` wrote `localStorage` only; `"Current Rate"` wording | Enriched `trips` and `quotes` with `trip_id`; `"Resume"`/`"Open"` syncs `sessionStorage`; displays `"Price verified"` |

---

## 4. Verification & Test Results

| Check | Command | Result |
| :--- | :--- | :--- |
| **Backend Pytest Suite** | `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests` | **198 / 198 passed** (includes pricing, RBAC, deduplication, `test_staff_enquiry_workflow.py`, and `test_final_consistency_repair.py`) |
| **Frontend Vitest Suite** | `npm --prefix apps/ceylon-compass test` | **61 / 61 passed** across 8 test files (including `staff-layout.test.tsx` & `workspace-preferred.test.tsx`) |
| **Workspace Bundle Build** | `npm --prefix apps/ceylon-compass run workspace:build` | **Passed** |
| **TypeScript & Python Lint** | `make lint` | **Passed** (`compileall` + `tsc --noEmit` on both apps) |
| **Playwright Browser Tests** | `./scripts/test-workspace.sh` | **8 / 8 passed** (13.1s) |
| **Deterministic Evaluation** | `PYTHONPATH=apps/api .venv/bin/python evals/runner.py` | **53 / 54 passed (98.1%)** (63 validated turns; 1 expected `P03`/`Q-1043` workbook vs. sample email discrepancy preserved untouched) |
| **Full Production Build** | `make build` | **Passed** (`apps/ceylon-compass` + `apps/web`) |

---

## 5. Remaining Limitations & Live Restart Note

1. **Pre-existing `P03` / `Q-1043` Evaluation Discrepancy:** `evals/cases/authored.jsonl` expects `USD 2,680`, whereas the official rate workbook requires six nights of extra beds for two children (`USD 2,965`). Intentionally preserved untouched per pricing rules.
2. **Live Dev Stack Restart Required:** The background `mira.serve` process (`PID 18762`) on port `8000` was started before these code edits and does not hot-reload. **Stop the existing dev stack (`Ctrl+C` in its terminal or kill `PID 18762`) and run `make dev`** so the live browser on `http://127.0.0.1:5175/dump.html` serves the updated FastAPI backend and built workspace bundle.

---

## 6. Live Demo Verification Commands

```bash
# 1. Stop any stale server on port 8000, then start the full stack:
make dev

# 2. Run all automated verification suites:
PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests
npm --prefix apps/ceylon-compass test
./scripts/test-workspace.sh
PYTHONPATH=apps/api .venv/bin/python evals/runner.py
```
