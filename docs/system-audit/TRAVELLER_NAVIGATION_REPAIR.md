# Traveller Enquiry Navigation & Dashboard Clarity Repair

**Project:** Ceylon Compass Holidays — Mira AI Travel Booking Assistant  
**Document ID:** `docs/system-audit/TRAVELLER_NAVIGATION_REPAIR.md`  
**Date:** November 25, 2026

---

## 1. Root Cause Analysis

1. **Interrupting Dead-End on Enquiry Status Page (`Workspace.jsx` `EnquiryPage`):**
   - `EnquiryPage` offered only a single `Back to home` button (`navigate('/')`), forcing travellers away from their active quotation and trip workspace.
   - `EnquiryPage` did not display the linked **Verified Quotation** (`quoted_total_usd`, `quoted_deposit_usd`) or **Demo booking** simulation status separately from **Enquiry Status** (`status`).
2. **Missing Origin Tracking & Safe Return Validation (`useRouter`):**
   - Hash-based routing (`window.location.hash`) did not record the originating internal route when navigating to `/enquiry/{reference}` or strip query strings before extracting the reference.
3. **UUID Exposure & Ambiguous Booking Labels (`ProfilePage`, `PriceBreakdownPanel`, `TourDetailPage`):**
   - `ProfilePage` (`Recent Quotations`) rendered raw 36-character quote UUIDs (`q.id`) instead of `ENQ-2026-XXXXXXXX` public references or short readable identifiers (`Quote #XXXXXXXX`), and omitted a direct `View Enquiry` action.
   - Mock checkout badges used `"Existing booking confirmed"`, `"Booking outcome: CONFIRMED"`, and `"Booking: confirmed"` rather than explicitly labeling simulated checkouts as `"Demo booking: Confirmed"`.

---

## 2. Changes Implemented

### Backend (`apps/api/mira/main.py`)
- **`GET /api/enquiries/{reference}` (`visitor_enquiry`):** Added safe session-owned fields `"mock_booking_status"`, `"mock_booking_reference"`, and `"trip_id"` so `EnquiryPage` can restore the originating trip on direct URLs/refreshes and display simulation status separately from enquiry status.
- **`GET /api/auth/overview` (`traveller_overview`):** Added `"enquiry_reference": pq.enquiry_reference` to `recent_quotes` entries.

### Frontend (`apps/ceylon-compass/workspace/Workspace.jsx`)
- **Safe Origin Tracking (`isSafeInternalRoute` + `useRouter`):** Validates originating routes against `^\/(mira|plan|profile|tours\/[a-z0-9-]+)$` (never accepting arbitrary external redirect URLs) and stores valid origins in `sessionStorage['mira-enquiry-origin']`.
- **Context-Aware `EnquiryPage` Actions:**
  - Replaced `Back to home` with **Back to quote** / **Continue planning** (restoring `mira-workspace-trip` to `enquiry.trip_id` and returning to `/mira` or `/tours/{slug}`) and **My journeys** (`/profile`).
  - Separated **Verified Quotation** (`USD ...` + deposit), **Enquiry Status** (`Status: new` / `in_review`), and **Simulation Status** (`Demo booking: Confirmed`).
  - Kept **Home** accessible in the standard header and footer.
- **Readable References & Clear Simulation Labels (`ProfilePage`, `PriceBreakdownPanel`, `TourDetailPage`):**
  - Updated `Recent Quotations` to display `q.enquiry_reference` (or `Quote #XXXXXXXX`) plus a `View Enquiry` button.
  - Updated all simulated checkout labels to **`Demo booking: Confirmed`** (and `Demo booking: #XXXXXXXX` in dashboard lists).

### Automated Tests (`apps/web/tests/workspace.spec.ts`)
- Added **`Test E: Traveller enquiry navigation, Back to quote, refresh, Back/Forward, and Demo booking label`** verifying:
  - Direct NL quote → `Verified tour price` (`USD 315`), `Add contact details` (no `Send enquiry`).
  - Simulated checkout → `Demo booking: Confirmed`.
  - `View enquiry` → `Verified Quotation` + `Demo booking: Confirmed` + `Back to quote` + `My journeys`.
  - Full page reload (`page.reload()`) preserves access to the saved enquiry.
  - `Back to quote` restores the exact `USD 315` quote in `/mira` without creating duplicates.
  - Browser `Back` / `Forward` navigates cleanly between `/enquiry/{ref}` and `/mira`.

---

## 3. Verification Results

| Check | Command | Result |
| :--- | :--- | :--- |
| **Lint & Typecheck** | `make lint` | **Passed** (`compileall`, `apps/web` `tsc --noEmit`, `apps/ceylon-compass` `tsc --noEmit`) |
| **Unit & Integration Tests** | `make test` | **Passed** (`63 / 63` Vitest in 8 files; `218 / 218` pytest) |
| **Playwright Workspace E2E** | `make workspace-browser` | **Passed** (`9 / 9` tests in `15.5s`, including `Test E`) |

> Note: No new screenshots were captured in `docs/screenshots/` for this pass; visual and DOM assertions were verified directly via Playwright Chromium in `make workspace-browser`.
