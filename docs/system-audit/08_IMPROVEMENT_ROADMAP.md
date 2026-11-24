# Prioritized Improvement Roadmap

**Date:** 25 November 2026  
**Auditor Roles:** Principal Software Architect, Senior Full-Stack Engineer, Product Manager

---

## 1. Summary of Priority Tiers

Because the submission deadline is close, improvements are structured into strict tiers. **P0 and P1 represent the minimum critical set of fixes required for an unassailable live demo and submission.**

```
┌────────────────────────────────────────────────────────────────────────┐
│ P0: Critical Correctness & Security (Must Fix Immediately)             │
│ • Unify Staff Portal in Workspace (replace mock with real controls)    │
│ • Implement missing ItineraryDay A2UI component renderer               │
│ • Fix mock booking idempotency lockout bug in backend                  │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
┌────────────────────────────────────▼───────────────────────────────────┐
│ P1: Incomplete Core Workflows & Data Consistency                       │
│ • Add child ages & infant inputs to Tour Detail & Traveller Picker     │
│ • Resolve Admin publication gate (actor != 'approver')                 │
│ • Fix Homepage search input & quick chip query forwarding              │
│ • Replace fake client-side enquiry reference in BookingFormPanel       │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
┌────────────────────────────────────▼───────────────────────────────────┐
│ P2: UI/UX, Accessibility, and Microcopy                                │
│ • Replace raw UUIDs and backend reason codes with friendly labels      │
│ • Automatic tab switching / unread badge on mobile for new quotes      │
│ • Form label & ARIA accessibility fixes (WCAG 2.1 AA)                  │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
┌────────────────────────────────────▼───────────────────────────────────┐
│ P3: Polish, Maintenance, and Optional Bonus Enhancements               │
│ • Consolidate/deprecate legacy Next.js app (apps/web)                  │
│ • Visual evaluation dashboard in Staff Portal                          │
│ • Dynamic multi-model routing evals report                             │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Detailed Improvement Specifications

### P0 — Critical Correctness and Security

#### P0-1: Unify Staff Portal in Workspace (`Workspace.jsx`)
- **Reason:** The primary workspace at `/dump.html` has an incomplete mock `StaffPage` with hardcoded stats and read-only tables, while a full 1,018-line staff application exists unlinked at `src/routes/staff.tsx`.
- **Expected Benefit:** Evaluators clicking "Staff" immediately access the real dashboard overview, interactive enquiry management, financial calculations (cost, GP%), trace inspector, and AI content approval.
- **Complexity:** Medium (Port or import the rich components from `src/routes/staff.tsx` into `Workspace.jsx` `StaffPage`).
- **Risk:** Low (Backend endpoints `/api/staff/*` and `/api/admin/*` are already fully implemented and tested).
- **Files Affected:** `apps/ceylon-compass/workspace/Workspace.jsx`.
- **Verification Strategy:** Run `make dev`, log in to `http://127.0.0.1:5175/dump.html#/staff`, verify overview stats update dynamically, click enquiry detail, add a note, change status, and test content approval.

#### P0-2: Add Missing `ItineraryDay` Renderer to A2UI Catalog (`Workspace.jsx`)
- **Reason:** Requirement 3 mandates 5 specific catalog components including `ItineraryDay`. Currently, `UIComponentRenderer` drops `ItineraryDay`, creating empty separator lines.
- **Expected Benefit:** Completes Requirement 3 compliance and allows Mira to display day-by-day itinerary cards cleanly in the conversation.
- **Complexity:** Low.
- **Risk:** Very Low.
- **Files Affected:** `apps/ceylon-compass/workspace/Workspace.jsx`.
- **Verification Strategy:** Ask Mira *"What happens on Day 2 of Sigiriya day tour?"* and verify the day card renders with title, description, and accommodation details.

#### P0-3: Fix Mock Booking Idempotency Lockout (`main.py`)
- **Reason:** In `main.py:booking()`, `if previous: return {"status": "success", ...}` returns success on subsequent failure simulation requests (`declined`, `network`), preventing error recovery testing.
- **Expected Benefit:** Allows evaluators to test payment decline and network failure recovery on any quote as required by the assignment.
- **Complexity:** Very Low (3 lines of Python).
- **Risk:** Very Low.
- **Files Affected:** `apps/api/mira/main.py`.
- **Verification Strategy:** Backend test calling mock booking with `success` followed by `declined`, asserting the second call returns `{"status": "declined"}`.

---

### P1 — Incomplete Core Functionality and Broken Workflows

#### P1-1: Add Child Ages and Infant Inputs to Tour Detail & Traveller Picker
- **Reason:** `TourDetailPage` currently hardcodes all child ages to 7 (`Array(children).fill(7)`), and `TravellerPickerPanel` ignores the `infants` counter in `handleCheckRates`.
- **Expected Benefit:** Eliminates hardcoded ages; enables true family quoting with accurate child and infant policies.
- **Complexity:** Low.
- **Risk:** Low.
- **Files Affected:** `apps/ceylon-compass/workspace/Workspace.jsx`.
- **Verification Strategy:** Select 2 adults and 1 infant (age 0); verify the calculated price charges 0 entrance fee for the infant.

#### P1-2: Allow Admin Role to Review and Publish Drafts
- **Reason:** Endpoints `/api/staff/drafts/{id}/review` and `/publish` check `if actor != "approver": raise HTTPException(403)`. When logged in with root `MIRA_ADMIN_EMAIL`, the admin cannot publish.
- **Expected Benefit:** Seamless administrator workflow during the demo without needing to switch to a separate approver account.
- **Complexity:** Very Low (Change check to `if actor not in ("approver", "admin"): raise HTTPException(403)`).
- **Risk:** Low.
- **Files Affected:** `apps/api/mira/main.py`.
- **Verification Strategy:** Log in as admin, create a draft, approve and publish it, verify 200 response and immediate appearance in search.

#### P1-3: Forward Homepage Search Query and Quick Chips to Mira Chat
- **Reason:** Typing a query in the homepage hero or clicking suggestion chips calls `navigate('/mira')` without passing the text.
- **Expected Benefit:** Smooth traveller UX: what the user types on the landing page immediately seeds their first conversation with Mira.
- **Complexity:** Low.
- **Risk:** Very Low.
- **Files Affected:** `apps/ceylon-compass/workspace/Workspace.jsx`.
- **Verification Strategy:** Type *"Kandy day tour"* on the homepage and hit Enter; verify Mira receives and answers the prompt immediately.

#### P1-4: Retrieve Persisted Enquiry UUID in `BookingFormPanel`
- **Reason:** `handleSubmitEnquiry` generates a fake client-side string `ENQ-...` instead of using the backend-generated enquiry reference.
- **Expected Benefit:** The enquiry reference shown to the customer matches the real database row and can be looked up at `/enquiry/{ref}`.
- **Complexity:** Low.
- **Risk:** Low.
- **Files Affected:** `apps/ceylon-compass/workspace/Workspace.jsx`.
- **Verification Strategy:** Submit enquiry from `BookingFormPanel`, copy the returned reference, navigate to `/enquiry/{reference}`, verify status is loaded from backend.

---

### P2 — UX, Accessibility, Performance, and Microcopy

#### P2-1: Friendly Customer-Facing Microcopy & Raw UUID Masking
- **Reason:** Raw 36-character UUIDs and machine reason strings (`verified_quote`, `date_or_fx_expired`) leak into customer and staff screens.
- **Expected Benefit:** Elevated professional aesthetic; clear, understandable status badges for both customers and staff.
- **Complexity:** Low (Add formatting helper function).
- **Files Affected:** `apps/ceylon-compass/workspace/Workspace.jsx`.

#### P2-2: Mobile Workspace Synchronization Feedback
- **Reason:** On screens $< 1024\text{px}$, when a quote or card is generated, the user remains on the chat tab with no obvious indicator that the workspace updated.
- **Expected Benefit:** Travellers on mobile instantly know a quote is ready on the Workspace tab.
- **Complexity:** Low (Add unread indicator badge to mobile tab button).
- **Files Affected:** `apps/ceylon-compass/workspace/Workspace.jsx`.

#### P2-3: Form Accessibility & Contrast Conformance
- **Reason:** Missing `htmlFor` / `aria-label` on search and send buttons; low-contrast gray badge text.
- **Expected Benefit:** WCAG 2.1 AA compliance.
- **Complexity:** Low.
- **Files Affected:** `apps/ceylon-compass/workspace/Workspace.jsx`.

---

### P3 — Optional Enhancements and Bonus Features

#### P3-1: Visual Evaluation Dashboard in Staff Portal
- Render `evals/report/report.json` as an interactive visual component inside the Staff Portal instead of linking to raw JSON.
#### P3-2: Deprecation of Legacy Next.js App (`apps/web`)
- After the assignment submission, remove the legacy `apps/web` folder to avoid developer confusion. (Preserved during audit and demo).
