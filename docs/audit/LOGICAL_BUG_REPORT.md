# Logical & Business Rule Bug Report: Deep Audit

> **Document Purpose:** Rigorous audit of all logical, financial, state-synchronization, concurrency, and security failure modes. Each bug is documented with exact reproduction steps, root cause analysis, severity classification, affected source files, and verified resolution status.

---

## 1. Summary of Bug Classifications

| Bug ID | Title | Severity | Area | Status |
|:---|:---|:---:|:---:|:---:|
| **BUG-01** | Stale 2-Adult Quote Displayed After 4-Adult Selection | **CRITICAL** | State Sync / Pricing | **Verified Fixed** |
| **BUG-02** | Internal Machine Instructions (`@trip`) Exposed in Chat | **HIGH** | UX / Chat Formatting | **Verified Fixed** |
| **BUG-03** | Tour Switching Retained Incompatible Active Quote | **HIGH** | Workspace Context | **Verified Fixed** |
| **BUG-04** | Conflation of Verified Quotes, Missing Rates, and Custom Enquiries | **MEDIUM** | Agent Node (`compose`) | **Verified Fixed** |
| **BUG-05** | Stale Quote Remains Valid After Travel Date or Party Changes | **HIGH** | Financial Guardrails | **Verified Fixed** |
| **BUG-06** | 404 "Journey Unavailable" on Session Cookie Refresh | **HIGH** | Auth / Multi-Tenant Session | **Verified Fixed** |
| **BUG-07** | Child Ages Count Inconsistent with Child Number Selector | **MEDIUM** | Form State Validation | **Verified Fixed** |
| **BUG-08** | Asynchronous Network Race Overwrites Active Configuration | **HIGH** | Concurrency / Network | **Verified Fixed** |
| **BUG-09** | Q-1043 Child Extra Bed Financial Evaluation Discrepancy | **INFO** | Rate Sheet Derivation | **Documented & Expected** |

---

## 2. In-Depth Bug Analyses & Evidence

---

### BUG-01: Stale 2-Adult Quote Displayed After 4-Adult Selection
- **Severity:** **CRITICAL (Financial Integrity Failure)**
- **Reproduction Steps:**
  1. Open `/workspace/index.html#/tours`.
  2. Select Sigiriya and Minneriya Day Tour (`T01`).
  3. Set Date: `2027-01-10`, Adults: `2`, Children: `0`. Click "Get verified quote". Observe USD 315.
  4. Now change Adults to `4`. Click "Get verified quote".
  5. Prior to fix: The UI displayed `2 adults` and `USD 315` instead of recalculating for 4 adults.
- **Root Cause:**
  - In `Workspace.jsx: TourDetailPage`, if the agent response did not return a component breakdown directly, the frontend fell back to `const rows = await api('/quotes'); const latest = rows.find(r => r.current)`.
  - If a previous quote existed in the database for 2 adults, the UI unconditionally adopted that quote, completely ignoring the active user selection.
  - Furthermore, asynchronous response handling lacked request correlation IDs, allowing stale responses to overwrite active state.
- **Affected Files:**
  - `apps/ceylon-compass/workspace/Workspace.jsx`
  - `apps/api/mira/agent.py`
- **Resolution & Verification:**
  - Removed the arbitrary `/quotes` fallback.
  - Bound every quote request to an immutable `currentRequestId = crypto.randomUUID()`.
  - Added `isQuoteCompatible(quote, tourId, date, adults, children, childAges)` check.
  - Verified in Playwright Test A: Selecting 4 adults on 2027-01-10 calculates **USD 540**, stores 4 adults in `quotes`, and renders USD 540 in the UI.

---

### BUG-02: Internal Machine Instructions (`@trip`) Exposed in Chat
- **Severity:** **HIGH (UX & Security Discretion)**
- **Reproduction Steps:**
  1. In Travel Workspace, click "Check rates" on a TourCard.
  2. Prior to fix: Visible chat bubbles contained raw strings like `@trip T08 2027-01-10 2 -` or `@trip T01 2027-01-10 4 -`.
- **Root Cause:**
  - UI handlers directly formatted internal DSL commands into user message prompts (`@trip {tourId} {date} {adults} {childAges}`) and passed them directly to the chat renderer `{item.prompt}`.
- **Affected Files:**
  - `apps/ceylon-compass/workspace/Workspace.jsx`
  - `apps/ceylon-compass/workspace/useConversation.js`
  - `apps/api/mira/agent.py`
- **Resolution & Verification:**
  - Upgraded `apps/api/mira/agent.py: interpret` to natively support typed JSON action payloads:
    ```json
    { "type": "REQUEST_QUOTE", "payload": { "tourId": "T01", "date": "2027-01-10", "adults": 4, "childAges": [] } }
    ```
  - Added `formatUserMessage(item, tours)` in `Workspace.jsx`. Any legacy string or JSON action is mapped to natural English:
    *"Check rates for Sigiriya and Minneriya Day Tour from Kandy on 2027-01-10 for 4 adults."*
  - Verified in Playwright Test D: Zero `@trip` regex strings appear in visible chat bubbles.

---

### BUG-03: Tour Switching Retained Incompatible Active Quote
- **Severity:** **HIGH (State Contamination)**
- **Reproduction Steps:**
  1. Select Tour A (`T01`), generate quote (USD 315).
  2. Navigate back to `/tours` and click Tour B (`T02: Kandy City Tour`).
  3. Prior to fix: The price panel on Tour B continued to display the USD 315 quote from Tour A.
- **Root Cause:**
  - `activeQuote` and `quoteRecord` state lived in parent component state without an invalidation listener triggered by tour navigation.
- **Affected Files:**
  - `apps/ceylon-compass/workspace/Workspace.jsx`
- **Resolution & Verification:**
  - Added `handleSelectTour(tour)` which immediately sets `setActiveQuote(null)`, clears `mockBookingStatus`, and updates `travellerConfig.tourId`.
  - Added `TourDetailPage` mount check that compares `quoteRecord.source` with active `tour.id`, invalidating incompatible records immediately.
  - Verified in Playwright Test C: Switching from T01 to T02 completely clears the T01 price breakdown.

---

### BUG-04: Conflation of Verified Quotes, Missing Rates, and Custom Enquiries
- **Severity:** **MEDIUM (Customer Journey Clarity)**
- **Reproduction Steps:**
  1. Request a tour with uncontracted hotel rates or future dates (`T08` on 2027-01-10).
  2. Prior to fix: Mira responded with a generic message *"A travel specialist will confirm the details. I've saved a private enquiry for our team"* even when quotes were successful.
- **Root Cause:**
  - `apps/api/mira/agent.py: compose` lacked branching logic to distinguish successfully verified quotes from missing-rate notices and custom proposals.
- **Affected Files:**
  - `apps/api/mira/agent.py`
  - `apps/ceylon-compass/workspace/Workspace.jsx`
- **Resolution & Verification:**
  - Separated `compose()` into three distinct message states:
    1. Verified Quote: Itemized totals and deposit rules.
    2. Missing Rates: Explains why rates cannot be verified and provides an enquiry tracking reference.
    3. Custom Itinerary: Tailored proposal across multi-day destinations.

---

### BUG-05: Stale Quote Remains Valid After Travel Date or Party Changes
- **Severity:** **HIGH (Financial Accuracy)**
- **Reproduction Steps:**
  1. Generate a verified quote for 2 adults on 2027-01-10.
  2. Change adults counter to 3, or change date to 2027-01-15.
  3. Prior to fix: The quote remained green and marked "Verified", allowing the user to initiate a mock booking for an outdated configuration.
- **Root Cause:**
  - The UI treated quotes as permanently valid until an entirely new API response arrived, with no client-side dirty checking.
- **Affected Files:**
  - `apps/ceylon-compass/workspace/Workspace.jsx`
- **Resolution & Verification:**
  - Implemented `isCompatible = isQuoteCompatible(quoteRecord, tour.id, travelDate, adults, children, currentChildAges)`.
  - If `!isCompatible`, the UI displays an amber **"Quote Outdated — Configuration Changed"** badge, disables the mock booking button, and renders a primary **"Recalculate quote"** button.
  - Verified in Playwright Test B: Decreasing adults immediately triggers the "Quote Outdated" warning banner.

---

### BUG-06: 404 "Journey Unavailable" on Session Cookie Refresh
- **Severity:** **HIGH (Authentication & Reliability)**
- **Reproduction Steps:**
  1. In incognito or after clearing cookies, open `/workspace/index.html`.
  2. Click "Get verified quote".
  3. Prior to fix: Alert dialog popped up: `Could not calculate quote: HTTP 404: {"detail":"Journey unavailable"}`.
- **Root Cause:**
  - In `apps/api/mira/main.py: agui` and `apps/api/mira/agent.py: interpret`, the SQL query required `WHERE id=trip_id AND visitor=key`. If the visitor cookie rotated or user logged in, the visitor ID changed, causing the query to fail and throw 404.
- **Affected Files:**
  - `apps/api/mira/main.py`
  - `apps/api/mira/agent.py`
  - `apps/ceylon-compass/workspace/Workspace.jsx`
- **Resolution & Verification:**
  - Updated SQL queries to join across `visitors` where `user_id` matches, allowing trips owned by an authenticated user to be accessed even if session visitor rotated.
  - Added client-side retry in `TourDetailPage`: if a 404 is encountered, `sessionStorage` clears the stale trip ID and creates a fresh trip automatically.

---

### BUG-07: Child Ages Count Inconsistent with Child Number Selector
- **Severity:** **MEDIUM (Data Integrity)**
- **Reproduction Steps:**
  1. Set Children count to 2.
  2. Only specify 1 child age. Click "Check rates".
- **Root Cause & Fix:**
  - `Workspace.jsx` maintains an explicit array `currentChildAges`. If the array length differs from `children`, the pricing engine pads missing ages or validates before dispatch.
  - Displayed child count strictly matches `childAges.length`.

---

### BUG-08: Asynchronous Network Race Overwrites Active Configuration
- **Severity:** **HIGH (Concurrency)**
- **Reproduction Steps:**
  1. User clicks "Get quote" for 2 adults (Network request 1).
  2. Immediately changes to 4 adults and clicks "Get quote" (Network request 2).
  3. If Request 1 finishes after Request 2, the old 2-adult quote overwrites the 4-adult quote.
- **Root Cause & Fix:**
  - Solved using `lastQuoteRequestId.current = crypto.randomUUID()`. Any response arriving whose request ID does not match `lastQuoteRequestId.current` is silently dropped.

---

### BUG-09: Q-1043 Child Extra Bed Financial Evaluation Discrepancy
- **Severity:** **INFORMATIONAL (Historical Sample Conflict)**
- **Explanation:**
  - Sample quote email Q-1043 lists a price of USD 2,680.
  - However, Q-1043 includes 2 children staying 6 nights across hotels `H12`, `H02`, and `H03`.
  - According to the authoritative workbook contract rules, children staying in parent rooms require an extra bed at rates LKR 4,500, LKR 6,000, and LKR 5,500 per night.
  - Total extra bed buy cost: $2 \times 2 \times (4,500 + 6,000 + 5,500) = \text{LKR } 64,000$.
  - Adding LKR 64,000 to the email's buy cost yields LKR 667,000, which calculates to **USD 2,965 (Deposit: USD 742)**.
  - **Resolution:** The deterministic pricing engine correctly calculates USD 2,965. The discrepancy is documented in `docs/PRICING_RULES.md` and explicitly preserved in evaluation case `P03`.
