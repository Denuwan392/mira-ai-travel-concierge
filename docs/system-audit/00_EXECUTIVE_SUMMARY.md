# Ceylon Compass Holidays — System Audit: Executive Summary

**Date:** 25 November 2026  
**Auditor Roles:** Principal Software Architect, Senior Full-Stack Engineer, LangGraph/A2UI Engineer, Application Security Auditor, Product Manager, UI/UX Researcher, QA Lead  
**Scope:** Complete repository inspection of Ceylon Compass Holidays (Mira AI Travel Assistant) for the Gen AI Full Stack Engineer Intern Take-Home Assignment.

---

## 1. Overall System Condition

The Ceylon Compass Holidays repository demonstrates **exceptional engineering depth in its backend, deterministic pricing engine, LangGraph agent workflows, database governance, and automated evaluation framework**. However, it suffers from a **critical architectural bifurcation in its frontend presentation layer**, resulting in an incomplete Staff Portal within the primary integrated workspace and key generative UI component rendering gaps in the traveller experience.

### System Strengths (Production-Ready or Near Production-Ready)
1. **Deterministic Pricing Engine (`apps/api/mira/data.py`):**
   - Strictly conforms to the employer rate workbook (`rate_sheet_2026-27.xlsx`), applying fixed FX ($300\text{ LKR} = 1\text{ USD}$), vehicle tiering (car, van, mini-coach), group size limits ($\le 20$), room allocations ($2\text{ adults} = 1\text{ double}$, odd adult $=$ single), child extra beds ($2\text{--}11\text{ years}$), margins ($30\%$ day tour, $25\%$ multi-day), and rounding rules.
   - Zero LLM arithmetic: All calculations execute via Python `Decimal` in deterministic code.
   - 43/43 pricing test cases pass.
2. **LangGraph Agent Architecture (`apps/api/mira/agent.py`):**
   - 5-node compiled `StateGraph` (`interpret` $\to$ `retrieve` $\to$ `quote` $\to$ `compose` $\to$ `save`) with strictly typed schemas (`GraphState`, `Turn`, `Component` union).
   - Solid prompt injection guards and refusal routing for unauthorized margin, cost, or discount queries.
   - Semantic content grounding and source disclosure linking to published records only.
3. **Automated Evaluation Suite (`evals/runner.py`):**
   - 54 test cases (17 starter + 37 candidate-authored + 7 multi-turn conversations).
   - $53/54$ passing ($98.1\%$), with the single failing case ($P03$) honestly documenting the historical sales email $Q\text{-}1043$ extra-bed calculation discrepancy against the authoritative rate workbook.
4. **Data Integrity:**
   - All 39 files in `ceylon-compass-dataset` match their original SHA-256 checksums (`docs/source-sha256.txt`). The dataset is completely preserved.

---

## 2. Major Risks and System Architecture Divergence

The primary system risk is **frontend duplication and fragmentation across three separate UI implementations**:

| Implementation | Location | Port / Entry | Status & Completeness |
|---|---|---|---|
| **Primary Integrated Workspace** | `apps/ceylon-compass/workspace/Workspace.jsx` | Port `5175` (`/dump.html`, `/workspace/`) | **Active Preferred UI**. Excellent visual design and chat flow, but **Staff Portal is an unfinished prototype**, and **`ItineraryDay` A2UI rendering is missing**. |
| **TanStack Start Full App** | `apps/ceylon-compass/src/routes/staff.tsx` | Port `5175` (`/staff` direct SSR route) | **Feature-Complete Staff Console** (1,018 LOC) with full overview, enquiries, finance, trace inspector, content studio, and user management. However, it is bypassed when navigating within `Workspace.jsx`. |
| **Legacy Next.js Client** | `apps/web/app/staff/page.tsx` | Port `3000` (`/staff`) | **Token-based legacy console** (181 LOC) developed during early prototyping. |

### The "Two Staff Portals" Problem:
When an evaluator follows the primary demo path starting at `http://127.0.0.1:5175/dump.html` and clicks the **"Staff"** link, `Workspace.jsx` internal router navigates to its own embedded `StaffPage` component (line 4337).
- This embedded `StaffPage` contains **hardcoded dashboard statistics** (`'5'`, `'3'`, `'54'`), a **read-only enquiry list** with no detail modal, no status updates, no notes, and **completely lacks AI content draft creation, approval, and user administration**.
- Meanwhile, an entirely functional 1,018-line staff application exists at `apps/ceylon-compass/src/routes/staff.tsx` with full backend integration, but was never wired into `Workspace.jsx`!

---

## 3. Top 5 Critical Bugs & Vulnerabilities

| Bug ID | Title | Severity | Impact Area | Summary |
|---|---|---|---|---|
| **BUG-001** | Staff Dashboard Incomplete & Hardcoded in Workspace | **Critical** | Staff Portal / UI | `Workspace.jsx` displays hardcoded stat values (`'5'`, `'3'`, `'54'`) and lacks enquiry editing, notes, content draft review, and user management. |
| **BUG-002** | `ItineraryDay` & Excerpt Components Dropped in A2UI Workspace | **High** | A2UI / Chat | `UIComponentRenderer` in `Workspace.jsx` lacks handlers for `ItineraryDay`, `PolicySnippet`, and `DestinationHighlight`, rendering empty lines in chat and failing Requirement 3. |
| **BUG-003** | Mock Booking State Lockout on Prior Success | **High** | Backend / Booking | `POST /api/bookings/mock` returns `status: "success"` for *any* subsequent request on an already-booked quote, ignoring `declined` or `network` scenarios and preventing failure testing. |
| **BUG-004** | Hardcoded Child Ages & Ignored Infant Count in Tour Detail | **High** | Traveller UX / Pricing | `TourDetailPage` hardcodes all child ages to `7` (`Array(children).fill(7)`) without age inputs, and `handleCheckRates` completely omits the `infants` counter. |
| **BUG-005** | Admin Role Publication Denial (`actor != 'approver'`) | **Medium** | Security / RBAC | Endpoints `/api/staff/drafts/{id}/review` and `/publish` strictly enforce `actor == 'approver'`, returning `403 Forbidden` to users logged in as `admin` despite admin documentation. |

---

## 4. Assignment Requirements Readiness

| Requirement | Category | Spec Target | Actual Repo Status | Confidence |
|---|---|---|---|---|
| **1. Trip Discovery** | Core | $\le 3$ questions before showing useful UI | **Complete** (Chat asks 1 question & attaches `TravellerPicker`/`TourCard`) | High |
| **2. Returning Visitors** | Extended | Greet with quote, remember known info | **Complete** (30-day session cookie, `/api/trips`, `/api/quotes`) | High |
| **3. Generative UI (A2UI)** | Core | $\ge 5$ components (picker, card, itinerary, price, booking) | **Incomplete** (`ItineraryDay` dropped in `Workspace.jsx`) | Needs Fix |
| **4. Grounded Content Only** | Core | Tour content with source; say when missing | **Complete** (Markdown ingestion, `public_text`, source tags) | High |
| **5. Verified Pricing** | Core | Rate workbook, deterministic code, GP% hidden from guest | **Complete** ($100\%$ accuracy on workbook formulas, costs private) | High |
| **6. Missing/Expired Rates** | Core | No guessing, specialist handoff, staff flag | **Complete** (`Unavailable` exceptions route to `EnquiryNotice`) | High |
| **7. Private Enquiries** | Extended | Save all quotes, staff notes, follow-up status | **Complete in Backend / Broken in Workspace UI** | Needs Fix |
| **8. Content Approval** | Extended | AI drafts, Approver publish, Mira retrieves | **Complete in Backend / Broken in Workspace UI** | Needs Fix |
| **Observability & Tracing** | Standard | Trace ID correlation, local stages, Langfuse | **Complete** (Local SQLite stages, sanitized telemetry) | High |
| **Automated Evaluation** | Standard | $\ge 40$ cases, multi-turn, report with traces | **Complete** (54 cases, 7 multi-turn, markdown/JSON reports) | High |

---

## 5. Recommended Next Actions

1. **Keep Audit Pure:** Do not alter application code, database schema, or packages during this turn.
2. **Review Audit Documentation:** Walk through the 10 detailed reports in `docs/system-audit/`.
3. **Execute High-Impact Fixes in Phase 2:**
   - **Fix 1 (Staff Portal Unification):** Integrate the comprehensive staff controls from `src/routes/staff.tsx` into `Workspace.jsx` `StaffPage` so evaluators clicking "Staff" access the real dashboard, enquiries, finance, drafts, and users.
   - **Fix 2 (A2UI Renderer Completion):** Add `ItineraryDay`, `PolicySnippet`, and `DestinationHighlight` renderers to `UIComponentRenderer` in `Workspace.jsx`.
   - **Fix 3 (Pricing Input Correction):** Allow travellers on `TourDetailPage` to enter specific child ages and include infants in `handleCheckRates`.
   - **Fix 4 (Mock Booking Idempotency):** Fix `main.py` mock booking endpoint to honor the requested `scenario` parameter rather than short-circuiting on an existing booking record.
   - **Fix 5 (Admin Role Publication):** Allow `admin` role in `main.py` `/publish` and `/review` or document clear role separation.
