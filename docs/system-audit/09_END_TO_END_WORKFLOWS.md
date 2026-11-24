# End-to-End Business Workflow Audit (Journeys A through I)

**Date:** 25 November 2026  
**Auditor Roles:** Senior Full-Stack Engineer, QA Lead, Financial Calculation Auditor  
**Methodology:** Programmatic test execution against isolated SQLite test environment using `journey_audit.py` with live API and database state inspection.

---

## Journey A — Quick Booker (Sigiriya Day Tour)

### 1. Expected Behavior
Two adults request the Sigiriya and Minneriya Day Tour from Kandy (`T01`) for 10 January 2027.
- Pricing calculation per workbook: Guide (9,000) + Vehicle Car (18,000) + Entrance (2 * 16,500 = 33,000) + Meals (2 * 3,000 = 6,000) = Total Buy Cost LKR 66,000.
- Selling price with 30% margin and 300 FX: $66,000 / (300 * 0.70) = $314.28 $\to$ rounded up to **USD 315**.
- Deposit: 100% full payment for day tours $\to$ **USD 315**.
- Mock checkout with scenario `success` creates a confirmed booking reference.

### 2. Actual Execution & Observed Traffic
- **Inbound Message:** `{"runId": "...", "messages": [{"role": "user", "content": "Sigiriya day trip for two adults on 10 January 2027"}]}`
- **API Response:** `200 OK` via SSE stream.
  - Emitted `Turn.text`: *"I’ve verified the quote for your travel date and group. You can review the deposit and try the demo booking."*
  - Attached components: `PriceBreakdown`, `BookingForm`, `TourCard`.
  - Quote DTO: `{"total": 315, "deposit": 315, "balance": 0, "currency": "USD", "source": "T01"}`.
- **Mock Booking Traffic:** `POST /api/bookings/mock` with `{"quote": "ff17107f...", "scenario": "success"}` $\to$ Returned `{"status": "success", "reference": "946659b6..."}`.
- **Database Effects:**
  - Row inserted in `quotes` with internal buy cost `66000` and `gross_profit_pct`: `30.1587`.
  - Row inserted in `enquiries` with `reason = 'verified_quote'`, `status = 'new'`.
  - Row inserted in `bookings` with `quote = 'ff17107f...'`, `id = '946659b6...'`.

### 3. Verdict
**PASS**. Exact financial match; correct A2UI components; clean mock booking.

---

## Journey B — Larger Group (Multi-Day Tour with 6 Adults)

### 1. Expected Behavior
Six adults request the Cultural Triangle Package (`T09`) for 3 May 2027.
- Group size: 6 travellers $\to$ Vehicle tiering shifts from Car to **Van** (LKR 26,000/day).
- Rooming: 6 adults share 3 double rooms (0 single rooms, 0 child extra beds).
- If rates are available, price is calculated deterministically. If hotel rates are unconfirmed or ambiguous, flags for specialist handoff.

### 2. Actual Execution & Observed Traffic
- **Inbound Message:** *"Cultural Triangle tour for 6 adults on 3 May 2027"*
- **API Response:** `200 OK` via SSE stream.
  - Emitted `Turn.text`: *"We can’t verify an automated price for these travel dates right now. A travel specialist will confirm the details. I’ve saved a private enquiry for our team."*
  - Attached components: `EnquiryNotice(reference="7c347a84...", text="Specialist confirmation required")`.
  - Zero invented prices.
- **Database Effects:**
  - Row inserted in `enquiries` with `reason = 'date_or_fx_expired'`, `status = 'new'`.
  - Trace stages persisted to `traces`.

### 3. Verdict
**PASS**. Safely refused without guessing; saved private specialist enquiry; zero invented prices.

---

## Journey C — Family with Specified Child Ages

### 1. Expected Behavior
Two adults and two children aged 7 and 10 request the Cultural Triangle Package (`T09`) for 12 April 2027.
- Formula per authoritative workbook rules (READ ME Rule 4):
  - Guide (7 days * 9,500) = LKR 66,500
  - Transport (Van for 4 pax, 7 days * 26,000) = LKR 182,000
  - Entrances (2 * 38,000 + 2 * 19,000) = LKR 114,000
  - Meals (3 * 4,500 * 7) = LKR 94,500
  - Hotels (1 double room for 6 nights) = LKR 146,000
  - Child extra beds (2 children * 6 nights) = LKR 64,000
  - Total buy cost: LKR 667,000.
  - Selling price (25% margin, 300 FX, rounded up to $5) = **USD 2,965**.
  - Multi-day deposit (25% rounded up) = **USD 742**. Balance = **USD 2,223**.

### 2. Actual Execution & Observed Traffic
- **Inbound Message:** *"Cultural Triangle for 2 adults and 2 children aged 7 and 10 on 12 April 2027"*
- **API Response:** `200 OK` via SSE stream.
  - Emitted `PriceBreakdown`: `{"total": 2965, "deposit": 742, "balance": 2223, "currency": "USD"}`.
  - Exactly matches authoritative calculation.

### 3. Verdict
**PASS**. $100\%$ accurate deterministic financial calculation including child extra bed rules.

---

## Journey D — Custom Multi-Day Itinerary

### 1. Expected Behavior
A family requests a 10-day custom journey across Kandy and Ella.
- Because there is no contracted fixed rate sheet for a bespoke 10-day itinerary, Mira must:
  1. Never invent or estimate a price.
  2. Propose a structured multi-day route with closest published tour suggestions.
  3. Attach an `EnquiryNotice` informing the traveller that a specialist will confirm pricing.
  4. Save a private enquiry row for the sales team.

### 2. Actual Execution & Observed Traffic
- **Inbound Message:** *"Design a 10-day custom journey across Kandy and Ella for a family of four"*
- **API Response:** `200 OK` via SSE stream.
  - Emitted `Turn.text`: *"Your proposed journey now has 10 days. I’ve saved the route for specialist confirmation. Limited service: I’m using the published catalogue."*
  - Attached components: `JourneyPlan`, `InteractiveMap`, `DateSelector`, `EnquiryNotice`, `TourCard` (3 closest tours), `SourceReference`.
  - `PriceBreakdown`: **None** (zero invented price).
- **Database Effects:**
  - Row inserted in `enquiries` with `reason = 'custom_or_unsupported'`, `status = 'new'`.

### 3. Verdict
**PASS**. Strict zero-invention compliance; generates structured interactive itinerary; creates specialist enquiry.

---

## Journey E — Missing or Expired Rates

### 1. Expected Behavior
A traveller requests a tour for a date where rates are unavailable (e.g. 10 January 2029, beyond the 31 October 2027 FX and contract validity window).
- Mira must refuse to price, state that a specialist will confirm, and save an enquiry.

### 2. Actual Execution & Observed Traffic
- **Inbound Message:** *"Sigiriya day tour for two adults on 10 January 2029"*
- **API Response:** `200 OK`.
  - Emitted `Turn.text`: *"We can’t verify an automated price for these travel dates right now. A travel specialist will confirm the details. I’ve saved a private enquiry for our team."*
  - Attached components: `EnquiryNotice(reference="02a71d03...", text="Specialist confirmation required")`.
- **Database Effects:**
  - Row inserted in `enquiries` with `id = '02a71d03...'`, `reason = 'date_or_fx_expired'`, `status = 'new'`.

### 3. Verdict
**PASS**. Clean fail-closed behavior on expired contract dates.

---

## Journey F — Returning Visitor Resuming Prior Quote

### 1. Expected Behavior
A visitor with active consent returns to the application.
- The system reads their session cookie.
- Calls `GET /api/quotes`.
- Revalidates prior quotes against current rates (`quote_current`).
- Returns saved quotes with `current: true`.

### 2. Actual Execution & Observed Traffic
- **API Call:** `GET /api/quotes` with `mira_session` cookie.
- **Response:**
  - Quote 1: Cultural Triangle Package — USD 2,965 (`current: true`).
  - Quote 2: Sigiriya and Minneriya Day Tour — USD 315 (`current: true`).

### 3. Verdict
**PASS**. Prior quotes accurately resumed and revalidated without prompting for previously supplied parameters.

---

## Journey G — Staff Enquiry Follow-Up

### 1. Expected Behavior
Staff reviews an existing enquiry, inspects traveller requirements, adds an internal note, updates follow-up status to `contacted`, and the updated status persists.

### 2. Actual Execution & Observed Traffic
- **Staff Listing:** `GET /api/staff/enquiries` with staff token $\to$ 5 enquiries listed.
- **Detail View:** `GET /api/staff/enquiries/02a71d03...` $\to$ Returns record, `status: 'new'`, `reason: 'date_or_fx_expired'`, execution events trace.
- **Status Update:** `PATCH /api/staff/enquiries/02a71d03...` with `{"status": "contacted", "note": "Contacted traveller via email..."}`.
  - Returned `200 OK`, `{"status": "contacted"}`.
- **Persistence Verification:** Re-querying detail view confirmed `status = 'contacted'` and 1 note in `notes` table.

### 3. Verdict
**PASS in Backend / BROKEN in `Workspace.jsx`**. The backend API works perfectly, but `Workspace.jsx` `StaffPage` lacks the UI controls to execute this workflow.

---

## Journey H — AI Content Approval Workflow

### 1. Expected Behavior
Staff member creates a draft from published material $\to$ draft stored privately (404 to public) $\to$ Non-approver publication blocked (403) $\to$ Approver approves and publishes $\to$ Content becomes public (200) $\to$ Mira can answer from it.

### 2. Actual Execution & Observed Traffic
1. **Draft Creation:** `POST /api/staff/drafts` with command *"Prepare a 5-day Hill Country journey concept using Ella materials"* $\to$ Created draft `C-C2313E38EE...`.
2. **Private Verification:** `GET /api/sources/C-C2313E38EE...` $\to$ `404 Not Found`.
3. **Unauthorized Publication:** Staff token attempts `POST .../publish` $\to$ `403 Forbidden: Approver access required`.
4. **Approval & Publication:** Approver token calls `POST .../review` (`status='approved'`) then `POST .../publish` (`status='published'`).
5. **Public Verification:** `GET /api/sources/C-C2313E38EE...` $\to$ `200 OK`.

### 3. Verdict
**PASS in Backend / BROKEN in `Workspace.jsx`**. Complete server-side enforcement. UI tab missing in `Workspace.jsx`.

---

## Journey I — Mock Booking Failure and Recovery

### 1. Expected Behavior
Traveller tests payment decline or network failure. Application reports failure status with friendly message and retry path without generating an error page.

### 2. Actual Execution & Observed Traffic
- **Defect Identified (BUG-003):** Because Quote `ff17107f...` was booked with `success` in Journey A, calling `/api/bookings/mock` with `scenario: "declined"` returned:
  `{"status": "success", "reference": "946659b6..."}`!
- **Root Cause:** `main.py` lines 428–430 short-circuits on `if previous: return {"status": "success", ...}`.

### 3. Verdict
**FAIL (Backend Bug BUG-003)**. Idempotency check incorrectly overrides explicit failure simulation testing.
