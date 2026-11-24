# Prioritized Improvement Roadmap: Engineering Action Plan

> **Document Purpose:** Systematic technical roadmap categorized into strict priority tiers (P0, P1, P2, P3). Details problem statements, business justification, architectural solutions, affected modules, difficulty, regression risk, and test verification procedures.

---

## 1. Roadmap Summary Matrix

| ID | Priority | Initiative | Difficulty | Risk | Grading Impact |
|:---:|:---:|:---|:---:|:---:|:---:|
| **REC-01** | **P0** | Enforce Strict Request ID Correlation & Cache Invalidation | Medium | Low | Critical (Financial Correctness) |
| **REC-02** | **P0** | Eliminate Stale `/quotes` Fallback in Tour Detail Pages | Low | Very Low | Critical (Data Integrity) |
| **REC-03** | **P0** | Multi-Tenant Visitor & Auth User Session Linking | Medium | Low | High (Authentication & Stability) |
| **REC-04** | **P1** | Structured JSON Action Dispatch (Eliminate `@trip`) | Medium | Low | High (Protocol Quality & Discretion) |
| **REC-05** | **P1** | Distinct Statuses for Quotes vs Missing Rates vs Enquiries | Low | Very Low | High (User Journey Clarity) |
| **REC-06** | **P1** | Real-Time "Quote Outdated" Banner & Booking Lock | Low | Very Low | High (Financial Guardrail) |
| **REC-07** | **P2** | Dynamic Import Optimization in Workspace Vite Build | Low | Low | Medium (Build Hygiene) |
| **REC-08** | **P2** | Mobile Viewport Tab Switch Animation Refinements | Medium | Low | Medium (UX Polish) |
| **REC-09** | **P3** | Live Stripe / Payment Gateway Integration Sandbox | High | Medium | Bonus (Outside Core Scope) |
| **REC-10** | **P3** | Multi-Language Sinhala & Tamil Localizations | High | Low | Bonus (Localization) |

---

## 2. Detailed Initiative Breakdown

---

### Priority P0: Critical Integrity & Correctness (Pre-Submission Mandates)

#### REC-01: Strict Request Snapshot Correlation & Invalidation
- **Problem:** Fast successive changes in party size or dates could cause slower, earlier network responses to overwrite the newest client-side quote.
- **Why It Matters:** Presenting a 2-adult quote when the user selected 4 adults is an immediate failure of financial state synchronization.
- **Proposed Solution:**
  1. Generate a client-side `currentRequestId = crypto.randomUUID()` before every network dispatch.
  2. Maintain `lastQuoteRequestId.current` in React ref.
  3. Discard any response where `response.requestId !== lastQuoteRequestId.current`.
  4. On form input change, immediately mark active quote status as `outdated`.
- **Affected Modules:** `apps/ceylon-compass/workspace/Workspace.jsx`
- **Difficulty:** Medium (1 day).
- **Regression Risk:** Low (purely client-side guard).
- **Verification:** Fast sequential clicks in Playwright test suite; verify latest parameters always prevail.
- **Grading Relevance:** Core criteria: "Traveller count matches verified quote".

#### REC-02: Eliminate Stale `/quotes` Fallback in Tour Detail Pages
- **Problem:** When an agent response failed to return a price (e.g. for uncontracted tours), the frontend fetched the latest row from `/quotes` and displayed an unrelated tour's price.
- **Why It Matters:** Gross cross-contamination where Tour B displays the price for Tour A.
- **Proposed Solution:**
  1. Remove `const rows = await api('/quotes'); const latest = rows.find(r => r.current)`.
  2. If the turn does not yield a verified breakdown, set `quoteRecord = null` and display `SpecialistNotice`.
- **Affected Modules:** `apps/ceylon-compass/workspace/Workspace.jsx: TourDetailPage`
- **Difficulty:** Low (1 hour).
- **Regression Risk:** Very Low.
- **Verification:** Inspect network and DOM when requesting uncontracted tour `T08`; ensure no price appears.
- **Grading Relevance:** Eliminates Bug 1 & Bug 3 root causes.

#### REC-03: Multi-Tenant Visitor & Auth User Session Linking
- **Problem:** Clearing browser cookies or signing in generated a fresh visitor ID, causing `/api/agent` to throw `404 "Journey unavailable"` when querying existing trips.
- **Why It Matters:** Breaks returning traveller journeys and crashes tour detail page quoting.
- **Proposed Solution:**
  1. Update SQL queries in `main.py` and `agent.py` to match `trips.visitor == key` OR `trips.visitor IN (SELECT id FROM visitors WHERE user_id = auth_user.id)`.
  2. Wrap frontend client runs with an automatic trip-reinitialization retry if 404 is received.
- **Affected Modules:** `apps/api/mira/main.py`, `apps/api/mira/agent.py`, `apps/ceylon-compass/workspace/Workspace.jsx`
- **Difficulty:** Medium (2 hours).
- **Regression Risk:** Low.
- **Verification:** Run `pytest apps/api/tests/test_notebooks.py` and Playwright session recovery test.
- **Grading Relevance:** Ensures robust session and notebook resilience.

---

### Priority P1: Journey Clarity & Protocol Hygiene

#### REC-04: Structured JSON Action Dispatch (Eliminate `@trip`)
- **Problem:** UI buttons constructed raw `@trip` machine strings, exposing internal command syntax in chat bubbles.
- **Why It Matters:** Unprofessional traveller experience; leaks internal tour identifiers and protocol details.
- **Proposed Solution:**
  1. Frontend dispatches structured JSON: `{ type: "REQUEST_QUOTE", payload: { tourId, date, adults, childAges } }`.
  2. `agent.py: interpret` deserializes JSON actions directly into `working` context.
  3. `formatUserMessage` converts all stored turns into natural traveller English.
- **Affected Modules:** `apps/ceylon-compass/workspace/Workspace.jsx`, `apps/api/mira/agent.py`
- **Difficulty:** Medium (3 hours).
- **Regression Risk:** Low (backward compatible with regex).
- **Verification:** Playwright Test D: Assert zero `@trip` strings appear in chat bubbles.
- **Grading Relevance:** Directly addresses BUG 2 requirements.

#### REC-05: Distinct Statuses for Quotes vs Missing Rates vs Enquiries
- **Problem:** All outcomes previously emitted identical text: *"A travel specialist will confirm the details. I've saved a private enquiry for our team."*
- **Why It Matters:** Confuses customers when a quote is already calculated and verified.
- **Proposed Solution:**
  - Branch `compose()` in `agent.py`:
    - `Verified Quote`: Provides total, deposit, and inclusions breakdown.
    - `Missing Rates`: Explains that automated rates cannot be verified and provides an enquiry reference.
    - `Custom Itinerary`: Highlights bespoke routing across requested destinations.
- **Affected Modules:** `apps/api/mira/agent.py`
- **Difficulty:** Low (1 hour).
- **Regression Risk:** Very Low.
- **Verification:** Run `evals/runner.py` and assert distinct turn components.
- **Grading Relevance:** Essential for customer trust and clear commercial stages.

#### REC-06: Real-Time "Quote Outdated" Banner & Booking Lock
- **Problem:** Changing party size or travel date left the previously calculated price visible and marked as "Verified".
- **Why It Matters:** Users could click "Book" expecting a 4-adult holiday for the 2-adult price.
- **Proposed Solution:**
  1. Add client-side validator `isQuoteCompatible(quote, tourId, date, adults, children, childAges)`.
  2. If incompatible, render amber warning banner: *"Quote Outdated — Configuration Changed"*.
  3. Disable mock booking button until "Recalculate quote" is pressed.
- **Affected Modules:** `apps/ceylon-compass/workspace/Workspace.jsx: PriceBreakdownPanel`
- **Difficulty:** Low (2 hours).
- **Regression Risk:** Very Low.
- **Verification:** Playwright Test B: Changing adults from 4 to 3 immediately triggers outdated banner.
- **Grading Relevance:** Core requirement in Section 1 (BUG 5).

---

### Priority P2: UX Polish, Accessibility & Maintainability

#### REC-07: Ineffective Dynamic Import Cleanup
- **Problem:** Vite outputs a build warning: `[INEFFECTIVE_DYNAMIC_IMPORT] src/lib/live/service.ts is dynamically imported but also statically imported.`
- **Proposed Solution:** Replace `const { run } = await import('@/lib/live/service')` with top-level `import { run } from "@/lib/live/service"`.
- **Difficulty:** Low (15 mins).
- **Regression Risk:** None.

#### REC-08: Mobile Tab Switch Transitions
- **Problem:** On mobile screens, switching between "Conversation" and "Your journey" tabs snaps instantly.
- **Proposed Solution:** Add CSS transition animations (`transition-opacity duration-150 ease-in-out`).
- **Difficulty:** Low (30 mins).
- **Regression Risk:** None.

---

### Priority P3: Future Production Enhancements (Outside Assessment Scope)

#### REC-09: Real Payment Gateway Sandbox (Stripe / PayHere)
- **Problem:** Current bookings are simulated via `POST /api/bookings/mock`.
- **Proposed Solution:** Integrate Stripe Payment Intents or PayHere Sri Lanka merchant sandbox for real 3D-Secure card tokenization.

#### REC-10: Multi-Language Support (Sinhala & Tamil)
- **Problem:** Current UI and prompts are English-only.
- **Proposed Solution:** Add i18n localization dictionary and multilingual LLM prompt tuning for domestic Sri Lankan tourism.
