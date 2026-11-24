# Test Coverage and Evaluation Gap Analysis

**Date:** 25 November 2026  
**Auditor Roles:** QA Lead, Principal Software Architect, Test Automation Engineer  
**Component:** Pytest Backend Suite, Vitest React Suite, Playwright Browser Specs, Evals Framework

---

## 1. Inventory of Existing Test Suites

| Suite | Runner & Path | Target Modules | Cases / Files | Observed Result | Status |
|---|---|---|---|---|---|
| **Backend Suite** | `pytest` (`apps/api/tests`) | FastAPI API, Pricing, RBAC, Agent, Store, Observability | 162 cases (17 files) | 162 passed (13.6s) | **Healthy** |
| **Deterministic Evals** | `python` (`evals/runner.py`) | Agent turns, Pricing checks, A2UI validation, Tracing | 54 cases | 53 passed, 1 expected fail (P03) | **Healthy** |
| **Frontend Unit Suite** | `vitest` (`apps/ceylon-compass`) | `LiveCanvas`, `MarkdownContent`, `SourceDisclosure`, `trip.ts`, Routing | 46 cases (6 files) | 46 passed (1.5s) | **Partial / Blind Spots** |
| **Browser Integration** | `playwright` (`apps/web/tests`) | End-to-end user flows, Quote check, Mock booking | 8 specs in `workspace.spec.ts` | 8 passed (in clean environment) | **Selective Coverage** |
| **MCP Smoke** | `node` (`apps/web/mcp/smoke.mjs`) | MCP tools (`search_tours`, `get_quote`, `create_enquiry`) | 1 smoke flow | Passed | **Healthy** |

---

## 2. Analysis of False Confidence & Weak Assertions

While the headline metrics appear strong (162 backend tests + 53 evaluation passes), several critical areas suffer from **false confidence** caused by incomplete assertions or testing the wrong component:

### 2.1 The "4,688-Line Unchecked File" Blind Spot
- **Finding:** The primary integrated frontend file `apps/ceylon-compass/workspace/Workspace.jsx` (4,688 lines of React code) contains **ZERO Vitest unit tests**.
- **Explanation:** All 6 Vitest test files in `apps/ceylon-compass/src/` test components from the earlier TanStack Start experiment (`LiveCanvas.tsx`, `MarkdownContent.tsx`, `SourceDisclosure.tsx`, `lib/trip/trip.test.ts`, `auth-ui.test.tsx`).
- **Consequence:**
  - The missing `ItineraryDay` renderer in `UIComponentRenderer` went completely unnoticed.
  - The hardcoded `'5'`, `'3'`, `'54'` values in `StaffPage` went completely unnoticed.
  - The dropped search query on the Homepage hero went completely unnoticed.
  - The hardcoded child age `7` on `TourDetailPage` went completely unnoticed.

### 2.2 The "Staff Page" Playwright Illusion
- In `apps/web/tests/workspace.spec.ts` lines 51–64:
  ```typescript
  test("staff account reviews the evaluated build through the production proxy", async ({page}) => {
    ...
    await page.goto("/staff");
    await page.getByLabel("Staff Email").fill("console@example.test");
    await page.getByLabel("Password").fill(...);
    await page.getByRole("button", {name:"Sign In to Staff Console"}).click();
    await expect(page.getByRole("link", {name:"View evaluation results"})).toBeVisible();
    await page.getByRole("button", {name:"Enquiries", exact:true}).click();
    await expect(page.getByText("verified_quote").first()).toBeVisible();
  });
  ```
- **Why this gave false confidence:**
  - This test logged in, asserted that the "View evaluation results" link was present, clicked the "Enquiries" tab, and asserted that the string "verified_quote" was visible in the table.
  - Because `Workspace.jsx` lines 4498–4508 render a **hardcoded fallback row with text "verified_quote"** whenever the enquiries list is empty, this test would pass even if the backend returned no data!
  - The test never attempted to click an enquiry, add a note, change a status, review a draft, or inspect financial figures.

### 2.3 Mock Booking Idempotency Gap
- None of the 162 backend tests or 54 evaluation cases tested sending a `scenario: "declined"` or `scenario: "network"` request **after** a `scenario: "success"` request on the same quote.
- Consequently, BUG-003 (where lines 428–430 of `main.py` return `status: "success"` on subsequent failure tests) went undetected until our deep end-to-end audit.

---

## 3. Test Coverage Gap Matrix

| Area | Current Test Coverage | Missing Scenarios | Risk Level |
|---|---|---|---|
| **A2UI Workspace Rendering** | Zero unit tests for `Workspace.jsx` | Rendering of `ItineraryDay`, `PolicySnippet`, `PriceBreakdown`, and `BookingForm` panels. | **High** |
| **Quotation Invalidation** | Tested in Playwright (`workspace.spec.ts` L171) | Invalidation when child ages or dates change in `PriceBreakdownPanel`. | **Medium** |
| **Infant Pricing in UI** | Tested in backend `test_pricing.py` (`infant` case) | Passing infants from `TravellerPickerPanel` to `handleCheckRates` and verifying zero entrance ticket fee. | **High** |
| **Staff Follow-Up Lifecycle** | Tested in API `test_auth_rbac.py` | UI tests for adding staff notes, updating follow-up status, and seeing updated status on traveller side. | **High** |
| **Content Approval Studio** | Tested in API `test_auth_rbac.py` | UI test for draft creation, review notes, and Approver-only publication gate in `Workspace.jsx`. | **High** |
| **Mock Booking Failure Recovery** | Tested single isolated outcomes in API | Re-testing different checkout scenarios on the same quote, retrying after a payment decline. | **Medium** |
| **Prompt Injection Variations** | 4 cases in `evals/runner.py` | Prompt injections without the exact keyword "ignore instructions" (e.g. system prompt extraction, jailbreaks). | **Low** |

---

## 4. Recommended New Regression Test Cases

### 4.1 Backend Regressions (`apps/api/tests/test_audit_regressions.py`)
1. **`test_mock_booking_allows_failure_scenarios_after_success`:**
   - Create quote $\to$ Book with `scenario="success"` $\to$ Call `/api/bookings/mock` with `scenario="declined"` $\to$ Assert response is `{"status": "declined"}`.
2. **`test_admin_publication_permissions`:**
   - Test draft review and publication with both `approver` and `admin` roles, asserting clear permission behavior.
3. **`test_infants_zero_ticket_cost`:**
   - Verify that an infant (age 0 or 1) pays 0 entrance fee, 0 meal cost, and 0 hotel bed fee.

### 4.2 Frontend Regressions (`apps/ceylon-compass/src/test/workspace-components.test.tsx`)
1. **`test_ui_component_renderer_itinerary_day`:**
   - Render `UIComponentRenderer` with `{type: "ItineraryDay", heading: "Day 1: Sigiriya", text: "Climb rock..."}` $\to$ Assert day heading and body are in the DOM.
2. **`test_staff_dashboard_metrics_dynamic_display`:**
   - Mount StaffPage with mock overview payload $\to$ Assert cards display the exact API numbers without falling back to `'5'`, `'3'`, `'54'`.
3. **`test_tour_detail_child_ages_input`:**
   - Change children count to 2 $\to$ Assert child age inputs appear and their values are passed to quote calculation.
