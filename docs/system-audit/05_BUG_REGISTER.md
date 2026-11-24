# Comprehensive Bug Register

**Date:** 25 November 2026  
**Auditor Roles:** Senior Full-Stack Engineer, QA Lead, Application Security Auditor

---

### BUG-001: Staff Dashboard Metrics Check Non-Existent Keys & Display Hardcoded Values

- **Bug ID:** BUG-001
- **Title:** Staff Dashboard metrics fall back to hardcoded demonstration strings ('5', '3', '54') due to key mismatch with backend overview API.
- **Area:** Staff Portal / Frontend UI
- **Severity:** Critical
- **Expected Behavior:** The dashboard overview cards in the Staff Portal should display live, accurate counts computed from database records (`total_enquiries`, `pending_followups`, `quotes_requiring_confirmation`, `pending_content_approvals`).
- **Actual Behavior:** The dashboard cards in `Workspace.jsx` check `overview?.pending_quotes ?? '5'`, `overview?.drafts ?? '3'`, and `overview?.evaluations ?? '54'`. Because the backend returns different key names, the values are always undefined and render the hardcoded strings `'5'`, `'3'`, and `'54'`.
- **Reproduction Steps:**
  1. Open `http://127.0.0.1:5175/dump.html` and click **"Staff"** in the navigation bar.
  2. Sign in with staff credentials (`console@example.test`).
  3. Observe the 4 metric cards at the top of the dashboard.
  4. Note that "Pending quotes" shows 5, "Draft content" shows 3, and "Evaluations" shows 54, regardless of actual database rows.
- **Evidence:**
  - `apps/ceylon-compass/workspace/Workspace.jsx` lines 4443–4446:
    ```javascript
    { label: 'Pending quotes', value: overview?.pending_quotes ?? '5', color: 'brand-sun' },
    { label: 'Draft content', value: overview?.drafts ?? '3', color: 'brand-teal' },
    { label: 'Evaluations', value: overview?.evaluations ?? '54', color: 'brand-leaf' },
    ```
  - `apps/api/mira/main.py` lines 770–776 returns:
    `{"total_enquiries": ..., "pending_followups": ..., "quotes_requiring_confirmation": ..., "pending_content_approvals": ...}`.
- **Root Cause:** Frontend was coded against a mock schema rather than the actual FastAPI response contract.
- **Suggested Fix:** Map `overview.pending_followups`, `overview.quotes_requiring_confirmation`, and `overview.pending_content_approvals` in `Workspace.jsx`.
- **Regression Test:** Vitest/Playwright assertion verifying that inserting new drafts or enquiries dynamically increments dashboard card numbers without hardcoded defaults.
- **Assignment Impact:** Core requirement 7 (Staff Portal) and Grading Criteria "Working system, tested live".

---

### BUG-002: Mandatory A2UI Component `ItineraryDay` Dropped in Travel Workspace

- **Bug ID:** BUG-002
- **Title:** `ItineraryDay` components emitted by the LangGraph agent are ignored by `UIComponentRenderer` and workspace sync in `Workspace.jsx`.
- **Area:** A2UI / Generative UI
- **Severity:** High
- **Expected Behavior:** When Mira returns itinerary day details (e.g., in response to *"What happens on Day 3 of the Cultural Triangle tour?"*), the client must render the `ItineraryDay` component cleanly in the interface as required by Requirement 3.
- **Actual Behavior:** `UIComponentRenderer` in `Workspace.jsx` has no case for `ItineraryDay` and returns `null`. The workspace sync `useEffect` does not handle `ItineraryDay`. The component is completely invisible, leaving only an empty horizontal line artifact in the chat.
- **Reproduction Steps:**
  1. Open `http://127.0.0.1:5175/dump.html#/mira`.
  2. Select the Cultural Triangle tour.
  3. In chat, ask: *"What happens on Day 2?"*.
  4. Observe the assistant reply. While the text appears, no structured itinerary component is rendered.
- **Evidence:**
  - `apps/ceylon-compass/workspace/Workspace.jsx` lines 3153–3250 (`UIComponentRenderer` has branches for `TourCard`, `TravellerPicker`, `PriceBreakdown`, and `EnquiryNotice` only).
  - Lines 2257–2294 (workspace sync effect ignores `ItineraryDay`).
- **Root Cause:** The component renderer in `Workspace.jsx` was left incomplete during the initial prototype compilation.
- **Suggested Fix:** Add an `ItineraryDay` case in `UIComponentRenderer` displaying the day number, title, route details, and inclusions.
- **Regression Test:** Add a test verifying that when an agent turn contains `{type: "ItineraryDay", heading: "Day 2", text: "..."}`, the element `[data-component-type="ItineraryDay"]` is rendered in the DOM.
- **Assignment Impact:** Non-negotiable requirement 3: *"The agent chooses UI components from a fixed catalog of at least 5 (traveller picker, tour card, itinerary day, price breakdown, booking form)"*.

---

### BUG-003: Mock Booking Idempotency Lockout Prevents Failure Scenario Testing

- **Bug ID:** BUG-003
- **Title:** `POST /api/bookings/mock` unconditionally returns `status: "success"` for any quote previously booked, ignoring failure scenarios.
- **Area:** Backend API / Mock Booking
- **Severity:** High
- **Expected Behavior:** When a user selects a simulated checkout outcome (`declined`, `network`, `unavailable`) and clicks "Try mock booking", the system should simulate that specific outcome and return appropriate error statuses for recovery.
- **Actual Behavior:** If the quote was previously booked with `success`, any subsequent call with `scenario: "declined"` or `scenario: "network"` immediately returns `{"status": "success", "reference": previous["id"]}`.
- **Reproduction Steps:**
  1. Get a verified quote for Sigiriya Day Tour (`$315`).
  2. Select scenario `success` and click "Try mock booking" $\to$ Status becomes `confirmed`.
  3. Select scenario `declined` and click "Try mock booking".
  4. Notice the API returns `status: "success"` instead of `declined`.
- **Evidence:**
  - `apps/api/mira/main.py` lines 428–430:
    ```python
    previous = conn.execute("SELECT id FROM bookings WHERE quote=?", (str(body.quote),)).fetchone()
    if previous:
        return {"status": "success", "reference": previous["id"]}
    ```
  - Observed in test script `journey_audit.py`:
    `Journey I - Declined booking status: 200, body: {'status': 'success', 'reference': '946659b6...'}`
- **Root Cause:** Premature short-circuit on existing booking row without checking whether the client requested a simulated failure scenario.
- **Suggested Fix:** In `main.py:booking()`, check `if previous and body.scenario == "success": return {"status": "success", ...}`. If `body.scenario != "success"`, return the requested failure simulation.
- **Regression Test:** Backend test submitting `scenario: "success"` followed by `scenario: "declined"` asserting the second response returns `{"status": "declined"}`.
- **Assignment Impact:** Requirement: *"When the mock payment or booking fails, the traveller sees a friendly message and a way forward, never an error page."*

---

### BUG-004: Hardcoded Child Ages & Ignored Infants Counter in Tour Detail

- **Bug ID:** BUG-004
- **Title:** `TourDetailPage` hardcodes all child ages to 7 and `TravellerPickerPanel` drops the infant count from quote requests.
- **Area:** Traveller UX / Pricing Interface
- **Severity:** High
- **Expected Behavior:** Travellers must be able to specify the exact ages of their children and infants to receive accurate pricing per the workbook rules.
- **Actual Behavior:** On `TourDetailPage`, clicking `+` on children creates an array where every child is aged 7 (`Array(children).fill(7)`). In `TravellerPickerPanel`, the `infants` counter is not included in the payload passed to `handleCheckRates`.
- **Reproduction Steps:**
  1. Navigate to `/tours/sigiriya-minneriya-day-tour-from-kandy`.
  2. Increment children from 0 to 2.
  3. Notice there is no field to specify child ages.
  4. In `TravellerPickerPanel`, increment "Infants (under 2)" to 1. Click "Check rates". Inspect outgoing payload: `infants` is omitted.
- **Evidence:**
  - `apps/ceylon-compass/workspace/Workspace.jsx` line 1653:
    `const currentChildAges = children > 0 ? Array(children).fill(7) : [];`
  - Lines 2317–2323 (`handleCheckRates` snapshot omits `infants`).
- **Root Cause:** Incomplete form state mapping in `Workspace.jsx`.
- **Suggested Fix:** Add a child ages input field to `TourDetailPage` matching `TravellerPickerPanel`, and include infants (as age 0) in `handleCheckRates`.
- **Regression Test:** Component test asserting that setting child ages to `2, 10` passes `[2, 10]` to `api/agent`.
- **Assignment Impact:** Non-negotiable pricing accuracy and family traveller discovery.

---

### BUG-005: Administrator Forbidden from Publishing Drafts

- **Bug ID:** BUG-005
- **Title:** System Administrator cannot approve or publish content drafts (`403 Forbidden`) due to strict `actor != "approver"` check.
- **Area:** Application Security / RBAC
- **Severity:** Medium
- **Expected Behavior:** An administrator should be able to perform or delegate content approval, or the system should provide explicit documentation and seamless role assignment.
- **Actual Behavior:** Endpoints `POST /api/staff/drafts/{id}/review` and `POST /api/staff/drafts/{id}/publish` strictly check `if actor != "approver": raise HTTPException(403)`. When the root administrator (role `admin`) attempts to publish, the API returns `403 Forbidden`.
- **Reproduction Steps:**
  1. Log in with `MIRA_ADMIN_EMAIL` and `MIRA_ADMIN_PASSWORD` (role `admin`).
  2. Post a draft generation command.
  3. Attempt to publish the draft via `POST /api/staff/drafts/{id}/publish`.
  4. Response is `403 Forbidden: Approver access required`.
- **Evidence:**
  - `apps/api/mira/main.py` lines 923 and 946:
    ```python
    if actor != "approver":
        raise HTTPException(403, "Approver access required")
    ```
- **Root Cause:** Overly restrictive string equality check (`actor != "approver"`) instead of checking if actor has approver privileges or allowing admin override.
- **Suggested Fix:** In `main.py`, allow `actor in {"approver", "admin"}` or require admin to explicitly set role to approver in test/dev fixtures.
- **Regression Test:** Test case verifying an admin account can publish a draft or successfully promote a staff user to approver to complete the flow.
- **Assignment Impact:** Requirement 8: *"only a user with the Approver role can publish it"*.

---

### BUG-006: Fake Client-Generated Enquiry Reference in Booking Form

- **Bug ID:** BUG-006
- **Title:** `BookingFormPanel` generates a fake client-side string `ENQ-...` rather than retrieving the persisted database enquiry UUID.
- **Area:** Frontend UI / Enquiry Management
- **Severity:** Medium
- **Expected Behavior:** Submitting a private enquiry from the booking form should persist the enquiry in SQLite and return the real database reference.
- **Actual Behavior:** `handleSubmitEnquiry` sends a message to chat and immediately returns `ENQ-${Date.now().toString(36).toUpperCase()}`. Navigating to that reference results in `404 Not Found`.
- **Evidence:**
  - `apps/ceylon-compass/workspace/Workspace.jsx` lines 2350–2354:
    ```javascript
    const handleSubmitEnquiry = async (formData) => {
      const prompt = `...`;
      send(prompt);
      return `ENQ-${Date.now().toString(36).toUpperCase()}`;
    };
    ```
- **Suggested Fix:** Await the agent turn response, extract `EnquiryNotice.reference` or query `/api/quotes`, and return the verified database UUID.
- **Assignment Impact:** Requirement 7: *"Every quote is saved as a private enquiry"*.

---

### BUG-007: Homepage Search Input Discards Query on Submit

- **Bug ID:** BUG-007
- **Title:** Typing a prompt into the homepage hero input and pressing Enter navigates to `/mira` with an empty chat prompt.
- **Area:** Traveller UX / Navigation
- **Severity:** Low
- **Expected Behavior:** Submitting a travel query from the homepage should carry that query into the Mira workspace and automatically submit it.
- **Actual Behavior:** `onKeyDown` and the Send button simply call `navigate('/mira')` without capturing the input value.
- **Evidence:**
  - `apps/ceylon-compass/workspace/Workspace.jsx` lines 1333–1341.
- **Suggested Fix:** Store the query in `sessionStorage.setItem('mira-pending-prompt', inputVal)` before calling `navigate('/mira')`, and read it in `useConversation`.
- **Assignment Impact:** First-impression usability and smooth trip discovery.
