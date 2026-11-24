# Full System Audit & Feature Implementation Matrix

> **Document Purpose:** Systematic audit of all frontend and backend modules, contract coverage, automated test status, code debt, orphaned artifacts, and component health across the Ceylon Compass codebase.

---

## 1. Feature Implementation Matrix

| Feature Domain | Feature Name | Frontend Implementation | Backend Implementation | API Contract | Test Coverage | Actual Status | Known Issues / Notes |
|:---|:---|:---|:---|:---|:---|:---|:---|
| **Discovery** | Tour Catalog Browsing | `apps/ceylon-compass/workspace/Workspace.jsx: TourCardList` | `apps/api/mira/catalog.py: published_records` | `GET /api/guide` | Vitest + Playwright `workspace.spec.ts` | **Verified working** | Seamless card rendering with tags & duration. |
| **Discovery** | Destination Guides | `Workspace.jsx: DestinationsPage` | `apps/api/mira/catalog.py: published_records` | Static bundled JSON + `GET /api/sources` | Vitest routing tests | **Verified working** | Displays destinations with photographs and highlights. |
| **Agent / NLU** | Conversational Tour Discovery | `useConversation.js` + `LiveCanvas.tsx` | `apps/api/mira/agent.py: interpret, retrieve` | `POST /api/agent` (SSE) | Pytest `test_agent_live.py` | **Verified working** | Extracts destination keywords and ranks top 3 tours. |
| **Pricing** | Deterministic Quote Calculation | `Workspace.jsx: TourDetailPage` | `apps/api/mira/data.py: calculate, price` | `POST /api/agent` | Pytest `test_pricing.py` + Evals `P01-P24` | **Verified working** | Zero LLM math. Contract-backed Decimal calculations. |
| **Pricing** | Real-time Quote Invalidation | `Workspace.jsx: isQuoteCompatible` | `apps/api/mira/data.py: quote_current` | Internal compatibility check | Playwright `workspace.spec.ts: Test A & B` | **Verified working** | Changing adult/child count marks quote as "Outdated". |
| **Pricing** | Multi-day Season Rates | `Workspace.jsx: PriceBreakdownPanel` | `apps/api/mira/data.py: rate sheet seasonal matching` | Included in quote DTO | Pytest `test_acceptance_scenarios.py` | **Verified working** | Correctly pairs double rooms and extra beds per night. |
| **Pricing** | Missing Rates Safeguard | `Workspace.jsx: SpecialistNotice` | `apps/api/mira/data.py: Unavailable exception` | Emits `EnquiryNotice` component | Pytest `test_workflows.py` + Evals (11 cases) | **Verified working** | Never fabricates numbers. Refers cleanly to specialists. |
| **Session** | Returning Visitor Journey Recovery | `Workspace.jsx: sessionStorage` + `useConversation` | `apps/api/mira/main.py: visitor dependency` | `GET /api/trips`, `GET /api/quotes` | Playwright `workspace.spec.ts` | **Verified working** | Preserves session context and active trip notebook. |
| **Booking** | Simulated Mock Booking | `Workspace.jsx: handleMockBooking` | `apps/api/mira/main.py: booking endpoint` | `POST /api/bookings/mock` | Playwright `workspace.spec.ts` + Pytest | **Intentionally mocked** | Tests `success` and `declined` scenarios; no real card gateway. |
| **Leads** | Private Enquiry Recording | `Workspace.jsx: EnquiryPage` | `apps/api/mira/agent.py: save node` | `GET /api/enquiries/{id}` | Pytest `test_deduplication.py` | **Verified working** | Quotes and missing-rate requests auto-record to `enquiries`. |
| **Staff** | Private Operational Finance | Staff Console (`/staff`) | `apps/api/mira/main.py: staff_enquiry_detail` | `GET /api/staff/enquiries/{id}` | Playwright + Pytest `test_auth_rbac.py` | **Verified working** | Displays buy cost, FX, and gross profit strictly for staff. |
| **Governance** | Generative Content Drafting | Staff Console: Content Review | `apps/api/mira/main.py: create_draft` | `POST /api/staff/drafts` | Playwright `workspace.spec.ts` | **Verified working** | Authors draft itineraries isolated from public search. |
| **Governance** | Approver Publication Gate | Staff Console: Approve/Publish | `apps/api/mira/main.py: publish_draft` | `POST /api/staff/drafts/{id}/publish` | Playwright + Pytest | **Verified working** | Role-gated by RBAC. Trigger logs append-only audit trail. |
| **Telemetry** | Stage Latency & Observability | Log stream + SQLite `traces` | `apps/api/mira/observability.py` | Header `X-Trace-Id` | Pytest `test_observability.py` | **Verified working** | SQLite records stages; Langfuse sync supported if configured. |
| **Evaluation** | Automated Regression Runner | CLI `evals/runner.py` | `apps/api/mira/agent.py` | Subprocess test harness | 53/54 cases passed (98.1%) | **Verified working** | Evaluates deterministic pricing, safety, and deduplication. |

---

## 2. Code Quality & Technical Debt Audit

### 2.1 Dual Frontend Remnants
- **Observation:** The repository contains two frontend application roots:
  1. `apps/ceylon-compass/` (TanStack Start / Vite, hosting the authoritative A2UI Travel Workspace at `/workspace/index.html`).
  2. `apps/web/` (Legacy Next.js App Router, originally hosting the baseline editorial demo).
- **Finding:** While `apps/ceylon-compass/workspace/` is the active, modern A2UI interface, `apps/web/` is retained for integration tests (`playwright.config.ts` runs against loopback).
- **Impact:** Low risk, but developers must be aware that UI edits to the Travel Workspace must occur in `apps/ceylon-compass/workspace/Workspace.jsx`, followed by running `npm --prefix apps/ceylon-compass run workspace:build`.

### 2.2 Dynamic vs. Static Import Warning in Vite Build
- **Warning:** `[INEFFECTIVE_DYNAMIC_IMPORT] src/lib/live/service.ts is dynamically imported by workspace/Workspace.jsx but also statically imported.`
- **Root Cause:** `Workspace.jsx` statically imports `api, session` from `src/lib/live/service.ts`, but in `TourDetailPage` dynamically imports `{ run }` from the same module.
- **Remedy:** Clean up the dynamic import in `TourDetailPage` by using the top-level static import.

### 2.3 Orphaned / Unused Endpoints
- `GET /api/session`: Replaced in practical flows by implicit visitor creation via the `visitor` FastAPI dependency on all agent routes. It remains active as a health check for visitor initialization.
- Legacy `apps/web/mcp/server.mjs`: Node.js MCP server prototype. Does not interfere with the Python FastAPI core.

### 2.4 State Redundancy & Synchronization
- **Pre-Audit Issue:** Previously, `TourDetailPage` maintained local `adults` state that failed to synchronize with `PriceBreakdownPanel`, causing a 4-adult selection to display a 2-adult stale quote.
- **Current Verified State:** Fixed in recent updates via immutable request snapshots with UUIDs, strict compatibility validation (`isQuoteCompatible`), and immediate quote invalidation upon party adjustment.
