# Read-Only Pricing Preview & Verification Report

**Date:** 2026-11-25  
**Scope:** Staff-only read-only pricing preview endpoint (`POST /api/staff/pricing/preview`), Staff Console `Rate Preview` calculator UI, zero-DB-write verification, and regression suite.

---

## 1. Endpoint & API Contract

- **Endpoint:** `POST /api/staff/pricing/preview`
- **Authorization & Security:** Requires authenticated staff/editor/approver/admin (`Depends(role)`) and trusted-origin CSRF check (`Depends(website)`). Unauthenticated requests receive `401`; untrusted `Origin` receives `403`.
- **Request Body (`PricingPreviewInput`, `Strict`):**
  ```json
  {
    "tour_id": "T01",
    "date": "2027-01-10",
    "adults": 2,
    "child_ages": [7, 10],
    "infants": 0
  }
  ```
- **Response (`preview_only: true`, zero DB writes):**
  - `preview_only`: `true`
  - `outcome`: `"PRICE_VERIFIED"` | `"PRICE_UNAVAILABLE"` | `"PRICING_SERVICE_ERROR"`
  - `rate_digest`: SHA-256 workbook digest from `current_rates().digest`
  - `evaluated_config`: `{ "tour_id", "tour_title", "date", "adults", "child_ages", "infants", "as_of" }`
  - `currency`: `"USD"`
  - `total_usd`, `deposit_usd`, `balance_usd`, `snapshot`: populated when `PRICE_VERIFIED`; `null` otherwise
  - `reason_code`, `reason`: populated when `PRICE_UNAVAILABLE` / `PRICING_SERVICE_ERROR`; `null` otherwise
  - `finance`: `{ "cost_lkr", "gross_profit_pct", "breakdown" }` (strictly behind `Depends(role)`, `null` when unavailable)

---

## 2. UI Location & Design Preservation

- **UI Location:** `Rate Preview` tab inside the unified `StaffConsole` (`apps/ceylon-compass/src/components/staff/StaffConsole.tsx`), accessible at `/staff` and `/dump.html#/staff`.
- **Controls:** Tour selector (`/api/tours`), travel date, adult count, comma-separated child ages, infant count (`<2`), and **"Run Rate Preview"** button.
- **Explicit Disclaimer:** Result pane always displays **"Pricing preview — not a saved quotation or booking."**

---

## 3. Files Modified & Added

- `apps/api/mira/main.py` — Added `PricingPreviewInput`, `_PREVIEW_REASON_MESSAGES`, and `POST /api/staff/pricing/preview` invoking the exact same `current_rates()` + `price()` function as official quotes.
- `apps/ceylon-compass/src/components/staff/StaffConsole.tsx` — Added `"preview"` (`Rate Preview`) tab, form, and preview-only result display.
- `apps/api/tests/test_pricing_preview.py` — Added 4 regression test functions covering all 10 required scenarios and zero-write DB assertions.
- `apps/ceylon-compass/src/test/workspace-preferred.test.tsx` — Added `StaffConsole Read-Only Rate Preview` UI test.

---

## 4. No-Write & Calculation Parity Verification

- **Before/After Database Table Counts:** `test_pricing_preview_valid_cases_and_no_db_writes`, `test_pricing_preview_unavailable_expired_unsupported_and_invalid`, and `test_pricing_preview_matches_official_quote_exactly` assert `before == after` across all 6 operational tables (`quotes`, `enquiries`, `trips`, `traces`, `bookings`, `audit`).
- **Parity Proof:** `test_pricing_preview_matches_official_quote_exactly` verifies that `T09` (`2027-04-12`, `4 adults`, `child_ages=[7, 7, 7]`) produces identical `total_usd` (`4530`), `deposit_usd` (`1133`), `balance_usd` (`3397`), `cost_lkr`, and `gross_profit_pct` between the official LangGraph quote workflow and `POST /api/staff/pricing/preview`.

---

## 5. Pricing Test Matrix

| Scenario | Input | Outcome | Result / Reason Code |
|---|---|---|---|
| Valid 2-adult day tour | `T01`, `2027-01-10`, `2 adults` | `PRICE_VERIFIED` | `USD 315` (deposit `USD 315`) |
| Valid 4-adult day tour | `T01`, `2027-01-10`, `4 adults` | `PRICE_VERIFIED` | `USD 540` (deposit `USD 540`) |
| Family + child ages + infant | `T09`, `2027-04-12`, `2 adults`, `[7, 10]`, `1 infant` | `PRICE_VERIFIED` | `USD 2,965` (deposit `USD 742`) |
| Cultural Triangle family parity | `T09`, `2027-04-12`, `4 adults`, `[7, 7, 7]` | `PRICE_VERIFIED` | `USD 4,530` (deposit `USD 1,133`) |
| Missing hotel rate | `T12`, `2027-04-10`, `1 adult` | `PRICE_UNAVAILABLE` | `missing_amount` (H04 single-room rate missing) |
| Overlapping hotel rates | `T09`, `2027-01-10`, `4 adults`, `[7, 7, 7]` | `PRICE_UNAVAILABLE` | `hotel_rate_missing_or_ambiguous` (H03 Row 13 vs Row 56) |
| Unsupported / unpublished tour | `T16` / `T99`, `2027-01-10`, `2 adults` | `PRICE_UNAVAILABLE` | `tour_rate` / `not_published` |
| Expired rate (`AS_OF_DATE=2027-01-11`) | `T01`, `2027-01-10`, `2 adults` | `PRICE_UNAVAILABLE` | `date_or_fx_expired` |
| Invalid input | `2027-02-31`, `adults=0`, `age=150` | HTTP `422` | Pydantic validation rejection |

---

## 6. Remaining Rate Limitations

- Automated quotes and previews remain strictly bounded by `rate_sheet_2026-27.xlsx` contract dates, single-room hotel availability (e.g., `H04` in `T12`), and unambiguous hotel rate rows (e.g., `H03` Peak season in `T09`).
- All official traveller-facing quotes continue to be routed through the LangGraph workflow and persisted with a private enquiry and trace.
