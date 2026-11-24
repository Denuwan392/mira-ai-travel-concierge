# UI, UX, Accessibility, and Terminology Audit

**Date:** 25 November 2026  
**Auditor Roles:** UI/UX Researcher, Design System Lead, Accessibility (a11y) Auditor  
**Component:** Visual Hierarchy, Mobile Layout, Responsive Breakpoints, Accessibility, Customer-Facing Terminology

---

## 1. Design System and Visual Hierarchy

### 1.1 Brand Pack Adherence
The user interface follows the official brand guidelines (`brand_pack.json`):
- **Primary Color:** Forest Emerald / Ceylon Teal (`#2d5a3d` / `#1b4332`)
- **Accent Color:** Warm Ochre / Sun Gold (`#d4a373` / `#e07a5f`)
- **Backgrounds:** Warm White (`#fefae0` / `#faf9f6`), Warm Sand (`#f4f1de`)
- **Typography:**
  - Display / Editorial: `Instrument Serif` (italic accents, e.g. *"Your tour."*)
  - Body / Interface: `Inter` / system-ui, high legibility, clean sans-serif.
- **Card Containers:** Rounded cards (`rounded-card`), subtle borders (`border-border`), soft hover elevations.

### 1.2 Desktop vs Mobile Layout
- **Desktop ($\ge 1024\text{px}$):**
  - Split two-column workspace (`Conversation` on left $40\%$, `Travel Workspace` on right $60\%$).
  - Fixed full-height scrollable containers with custom scrollbars (`custom-scroll`).
  - Clear spatial separation between dialogue and structured tools.
- **Mobile ($< 1024\text{px}$):**
  - Tab switcher header: `[ Conversation ]` vs `[ Workspace (panel_name) ]`.
  - Single active column to prevent horizontal overflow.
  - Verified on $390\text{px}$ viewport width: `document.documentElement.scrollWidth <= 390px`. No horizontal scroll blowout.

---

## 2. Terminology and Microcopy Audit

A critical evaluation factor in the assignment brief is customer-facing communication:
> *"Ceylon Compass Holidays is replacing its website with one where the conversation is the product... Friendly labels improve customer UX while retaining IDs internally for provenance."*

The audit identified several areas where **raw internal IDs, machine reason codes, and technical jargon leak into traveller and staff interfaces**:

| Current Label / UI String | Location | Context | Issue | Recommended Traveller-Friendly Replacement |
|---|---|---|---|---|
| `Ref: ff17107f-aa34-430d-8856-36fc16ab0a7b` | `Workspace.jsx` L2040, L2837 | Quote card header | Displays raw 36-char internal database UUID. Highly intimidating and unreadable on mobile. | `Quote Reference: CC-315-0110` or truncated `Quote #ff17107f` |
| `verified_quote` | `Workspace.jsx` L4490, L4493 | Staff table Reason & Status | Exposes internal database enum `verified_quote` as both reason and status. | Reason: *"Standard Quote"*, Status: *"New / Awaiting Review"* |
| `date_or_fx_expired` | `api/staff/enquiries` | Staff table Reason | Displays machine exception code. | *"Travel Dates Outside Contract Season"* |
| `hotel_rate_missing_or_ambiguous` | `api/staff/enquiries` | Staff table Reason | Displays raw Python exception message. | *"Hotel Contract Rate Required"* |
| `custom_or_unsupported` | `api/staff/enquiries` | Staff table Reason | Technical fallback reason. | *"Custom Bespoke Itinerary Request"* |
| `recheck_before_booking` | `Workspace.jsx` L2874 | Quote validity banner | Technical database flag displayed verbatim to customer. | *"Rate re-check recommended before final booking"* |
| `Mock checkout scenario` | `Workspace.jsx` L2072, L2879 | Checkout simulation | Technical developer terminology in user-facing checkout card. | *"Simulation Mode: Select Test Result"* |
| `Check rates` vs `Get verified quote` | `Workspace.jsx` L1964, L2792 | Quoting action buttons | Inconsistent action phrasing across Tour Detail and Traveller Picker. | Standardize to *"Check Verified Rates"* |

---

## 3. Accessibility (a11y) & Keyboard Navigation Audit

### 3.1 Strengths
1. **ARIA Roles & Live Regions:**
   - Quoting cards properly use `role="region"` with dynamic `aria-label="Verified quote"` and `aria-label="Outdated quote"`.
   - Mock booking outcomes use `role="status"` to announce confirmation or decline to assistive technology.
   - Form error containers use `role="alert"`.
2. **Keyboard Trapping & Form Submissions:**
   - Native `<form>` tags with explicit `onSubmit` prevent keyboard entrapment and support standard Enter-key submission.
   - Explicit `type="button"` on plus/minus counters prevents accidental form submissions.

### 3.2 Accessibility Defects & Gaps
1. **Missing `htmlFor` / `id` Association on Search Inputs:**
   - **Location:** `Workspace.jsx` lines 1333–1338 and lines 2518–2525.
   - **Issue:** The primary homepage search bar and the chat input field lack an associated `<label>` or explicit `aria-label`, failing WCAG 2.1 Success Criterion 4.1.2 (Name, Role, Value).
   - **Fix:** Add `aria-label="Tell Mira what you want to experience"` to the input.
2. **Interactive Elements Without Accessible Names:**
   - **Location:** `Workspace.jsx` line 1340:
     ```javascript
     <Button variant="primary" onClick={() => navigate('/mira')}>
       <Send className="w-4 h-4" />
     </Button>
     ```
   - **Issue:** The Send button contains only an SVG icon (`<Send />`) with no textual name or `aria-label`, leaving screen readers unable to announce its function.
   - **Fix:** Add `aria-label="Send message to Mira"`.
3. **Contrast on Sub-Muted Badges:**
   - Light gray background pills (`bg-gray-100 text-text-muted`) on white cards have a measured contrast ratio of $\sim 3.8:1$, failing WCAG AA minimum threshold of $4.5:1$ for normal body text.

---

## 4. Mobile Responsiveness & Layout Defects

### 4.1 Silent Tab Synchronization on Mobile
- **Location:** `Workspace.jsx` lines 2247–2294.
- **Scenario:** A mobile traveller ($< 1024\text{px}$) asks Mira for a quote while on the `Conversation` tab.
- **Problem:** When the quote arrives, the backend sends a `PriceBreakdown`. The state updates `setWorkspacePanel('quote')`, but **does NOT switch `mobileTab` to `'workspace'`**.
- **User Experience:** The chat simply displays a small text link: *"Quote calculated — see workspace $\to$"*. Because there is no automatic tab transition or unread indicator on the "Workspace" tab, mobile users frequently assume the assistant failed to generate a price.
- **Recommendation:** When a `PriceBreakdown` or `BookingForm` arrives, either:
  1. Automatically toggle `setMobileTab('workspace')`, or
  2. Display an active pulsing notification badge on the `Workspace` mobile tab button.

### 4.2 Chat Bubble Layout & Empty Component Spacing
- **Location:** `Workspace.jsx` lines 2435–2445.
- **Problem:** Because `UIComponentRenderer` returns `null` for unhandled component types (`ItineraryDay`, `PolicySnippet`), each unhandled item renders an empty `<div>` with a top border line (`border-t border-border/50`).
- **Visual Artifact:** When a turn attaches multiple factual snippets, the assistant's response bubble displays stacked horizontal lines with empty space between them.
- **Recommendation:** Filter the components list prior to rendering:
  ```javascript
  const renderable = item.turn.components?.filter(c => ['TourCard', 'TravellerPicker', 'PriceBreakdown', 'EnquiryNotice', 'ItineraryDay'].includes(c.type));
  ```
