# Architecture and System Integration Audit

**Date:** 25 November 2026  
**Auditor Roles:** Principal Software Architect, Senior Full-Stack Engineer  
**Component:** Full-Stack Architecture, Data Flow, Protocol Mapping

---

## 1. System Topology Overview

The application comprises three distinct process groups supervised by `scripts/dev.py` and `scripts/dev.sh`:

```mermaid
flowchart TD
    subgraph Clients["Frontend Clients Layer"]
        W1["Preferred UI: Workspace.jsx (Port 5175)<br/>Vite + Tailwind /workspace/index.html & dump.html"]
        W2["Alternate UI: TanStack Start App (Port 5175)<br/>SSR Routes /plan, /staff, /trips, /explore"]
        W3["Legacy UI: Next.js App (Port 3000)<br/>CopilotKit Shell & Token Console"]
    end

    subgraph ReverseProxy["Transport & Proxy Layer"]
        ViteProxy["Vite Dev / Nitro Proxy (:5175/api -> :8000/api)"]
        NextProxy["Next.js Route Proxy (:3000/api -> :8000/api)"]
    end

    subgraph BackendCore["FastAPI Backend Service (Port 8000)"]
        FastAPI["mira.serve / main.py"]
        AuthRBAC["mira.auth (Argon2id, Session Cookies, RBAC)"]
        Observability["mira.observability (Trace IDs, Sanitize, Langfuse)"]
        FastAPI --> AuthRBAC
        FastAPI --> Observability
    end

    subgraph Orchestration["Agent Orchestration Layer"]
        LangGraph["LangGraph StateGraph (GraphState)<br/>5 Nodes: interpret -> retrieve -> quote -> compose -> save"]
        GeminiAdapter["mira.gemini (Live Gemini Live / Ranking / Drafts)"]
        LangGraph -.-> GeminiAdapter
    end

    subgraph PricingEngine["Deterministic Financial Engine"]
        PriceCalc["mira.data.price (Decimal Arithmetic)"]
        Workbook[("rate_sheet_2026-27.xlsx Snapshot")]
        PriceCalc --> Workbook
    end

    subgraph Persistence["Storage & Governance"]
        SQLite[("mira.sqlite3 (WAL Mode)<br/>traces, quotes, enquiries, drafts, users, audit")]
        LangfuseExport["Langfuse Exporter (Sanitized spans)"]
    end

    W1 --> ViteProxy
    W2 --> ViteProxy
    W3 --> NextProxy
    ViteProxy --> FastAPI
    NextProxy --> FastAPI

    FastAPI --> LangGraph
    LangGraph --> PriceCalc
    LangGraph --> SQLite
    FastAPI --> SQLite
    Observability -.-> LangfuseExport
```

---

## 2. Real Execution Paths vs Duplicated Implementations

An exhaustive scan reveals that the codebase contains **three concurrent frontend presentations** and multiple overlapping service layers.

### 2.1 The Three Frontend Entry Points

1. **`apps/ceylon-compass/workspace/` (The Preferred Travel Workspace):**
   - **Entry Point:** `apps/ceylon-compass/workspace/index.html` mounting `Workspace.jsx`.
   - **Build Target:** Compiled by `workspace/vite.config.mjs` into `apps/ceylon-compass/public/workspace/` (`index.html`, `assets/index-*.js`, `assets/index-*.css`).
   - **Served Aliases:** Served at `http://127.0.0.1:5175/workspace/index.html`, `http://127.0.0.1:5175/dump.html`, and symlinked or copied at workspace root `dump.html`.
   - **Internal State & Router:** Implements its own hash/path router (`useRouter`) with internal pages (`HomePage`, `ExplorePage`, `ToursPage`, `TourDetailPage`, `DestinationsPage`, `DestinationDetailPage`, `MiraWorkspace`, `AboutPage`, `PoliciesPage`, `EnquiryPage`, `LoginPage`, `RegisterPage`, `ProfilePage`, `StaffPage`).
   - **A2UI Implementation:** Renders a 2-column workspace (`Conversation` on left, `Travel Workspace` on right). Listens to `@ag-ui/client` SSE stream through `useConversation.js`.
   - **Status:** **ACTIVE & AUTHORITATIVE**. This is the UI evaluated in `README.md` and user instructions.

2. **`apps/ceylon-compass/src/routes/` (The TanStack Start SSR App):**
   - **Entry Point:** `apps/ceylon-compass/src/router.tsx` and `routeTree.gen.ts`.
   - **Served Routes:** Root path `/`, `/plan`, `/staff`, `/trips`, `/explore`, `/login`, etc.
   - **Key Components:** `LiveCanvas.tsx`, `AgentSurface.tsx` (using `@a2ui/react/v0_9`), `RouteMap.tsx`, `MarkdownContent.tsx`, and `routes/staff.tsx`.
   - **Disconnection:** While `routes/staff.tsx` is an extremely comprehensive 1,018-line implementation with full dashboard, enquiry editing, financial disclosures, trace inspector, draft review, and user management, it is **only accessible if the browser navigates directly to `/staff` in the TanStack Start shell**. When a user is inside the Preferred Workspace (`dump.html`), clicking "Staff" routes to `Workspace.jsx`'s internal `StaffPage` instead!

3. **`apps/web/` (The Next.js App on Port 3000):**
   - **Entry Point:** Next.js 15 app router on `http://127.0.0.1:3000`.
   - **Routes:** `/` (editorial journal), `/plan` (CopilotKit chat shell), `/staff` (legacy 181-line token console), `/api/copilotkit/[[...rest]]`.
   - **Status:** **LEGACY PROTOTYPE**. Retained for backward compatibility with CopilotKit and starter smoke tests.

---

## 3. Backend API Service Layer Map (`apps/api/mira/`)

The FastAPI application (`mira.main:app`) exposes 31 documented endpoints organized into 6 functional domains:

| Domain | Method & Endpoint | Auth Required | Downstream Modules | Functionality |
|---|---|---|---|---|
| **System** | `GET /api/health` | Public | `rates_repository` | Reports rates readiness, published records count, provider status |
| **Catalog** | `GET /api/tours`<br/>`GET /api/guide`<br/>`GET /api/sources/{key}` | Public | `data.published()`, `store.published_records()` | Returns published tours, destinations, itinerary days, policies. Strictly filters out drafts (`status != 'published'`) and historic (`T14`). |
| **Visitor Session** | `POST /api/session`<br/>`GET /api/session`<br/>`DELETE /api/session` | Public / Cookie | `store.db()`, `auth.COOKIE` | Manages 30-day consent, session UUIDs, binds authenticated user IDs, clears cookies. |
| **Trips & Journeys** | `POST /api/trips`<br/>`GET /api/trips`<br/>`GET /api/trips/{trip_id}` | Visitor Cookie | `store.db()`, `surface_messages` | Journey state persistence, multi-turn history retrieval, revalidates saved quotes against current rates. |
| **Agent / Turn** | `POST /api/agent?trip_id={id}` | Visitor Cookie | `agent.graph` (`ag_ui_langgraph`) | **AG-UI Streaming Protocol**. Executes LangGraph 5-node workflow via SSE. Delivers state snapshots, validated A2UI turns, and trace IDs. |
| **Public Quotes** | `GET /api/quotes` | Visitor Cookie | `data.price()`, `rates_repository` | Retrieves session's quotes with `current: true/false` validity flag. Emits `PublicQuote` only (never costs or margins). |
| **Mock Booking** | `POST /api/bookings/mock` | Visitor Cookie | `store.db()` | Simulates checkout outcomes (`success`, `declined`, `unavailable`, `network`, `expired`). |
| **Auth & Profile** | `POST /api/auth/register`<br/>`POST /api/auth/login`<br/>`POST /api/auth/logout`<br/>`GET /api/auth/me`<br/>`PATCH /api/auth/profile`<br/>`POST /api/auth/password` | Mixed | `auth.py`, Argon2id, `user_sessions` | Account registration, secure password hashing, HttpOnly session cookie creation, lockout checks, profile updates. |
| **Staff Enquiries** | `GET /api/staff/dashboard/overview`<br/>`GET /api/staff/enquiries`<br/>`GET /api/staff/enquiries/{key}`<br/>`PATCH /api/staff/enquiries/{key}` | Role: Staff/Admin | `store.db()`, `auth.role` | Staff dashboard counts, enquiry listing/filtering, enquiry details with internal costs & gross profit %, follow-up status, staff notes, staff assignment. |
| **Content Studio** | `POST /api/staff/drafts`<br/>`GET /api/staff/drafts`<br/>`POST /api/staff/drafts/{key}/review`<br/>`POST /api/staff/drafts/{key}/publish` | Role: Staff/Approver | `gemini.py`, `data.public_text` | Draft generation from destination material, draft listing, review notes, Approver-only publication gate. |
| **Audit & Traces** | `GET /api/staff/traces/{trace}`<br/>`GET /api/staff/evaluation`<br/>`GET /api/staff/audit`<br/>`GET /api/admin/audit` | Role: Staff/Admin | `observability.py`, SQLite `traces` | Full stage execution inspection, deterministic evaluation JSON report, append-only immutable audit trail. |
| **Admin Users** | `GET /api/admin/users`<br/>`PATCH /api/admin/users/{user_id}` | Role: Admin | `auth.py`, `store.db()` | User listing with role/status filters, role promotion (`staff`, `approver`, `admin`), account deactivation. |

---

## 4. LangGraph Agent Internal Architecture

The conversation flow is strictly governed by `apps/api/mira/agent.py`:

```mermaid
sequenceDiagram
    autonumber
    actor Traveller
    participant Client as Web Client (@ag-ui/client)
    participant API as FastAPI (/api/agent)
    participant Interpret as Node 1: interpret
    participant Retrieve as Node 2: retrieve
    participant QuoteNode as Node 3: quote
    participant Compose as Node 4: compose
    participant Save as Node 5: save
    participant DB as SQLite (mira.sqlite3)

    Traveller->>Client: "Sigiriya day tour for 2 adults on 10 Jan 2027"
    Client->>API: POST /api/agent?trip_id=... (RunAgentInput)
    API->>Interpret: GraphState(messages, surface)
    Note over Interpret: Deterministic regex parsing: T01, 2027-01-10, adults=2. Check injection guards.
    Interpret->>Retrieve: Query published records (T01)
    Retrieve->>QuoteNode: quote_route condition met (tour, date, party complete)
    Note over QuoteNode: Execute mira.data.price(). Zero LLM arithmetic.
    QuoteNode->>Compose: Price result: total=315, deposit=315, margin=30%
    Note over Compose: Assemble Turn payload: PriceBreakdown, BookingForm, TourCard
    Compose->>Save: BEGIN IMMEDIATE Transaction
    Save->>DB: INSERT quotes, INSERT enquiries, INSERT traces, UPDATE trips
    Save->>API: Validated Turn + Surface Messages
    API-->>Client: SSE stream (TEXT_MESSAGE_CONTENT, STATE_SNAPSHOT, RUN_FINISHED)
    Client-->>Traveller: Render A2UI PriceBreakdown & BookingForm
```

### Typed Shared State & Catalog Schema
- **State Schema:** `GraphState(TypedDict)` containing `surface: list[dict]`, `messages: list`, `turn: dict`.
- **Catalogue Schemas (`apps/api/mira/catalog.py`):**
  - Inherits from `pydantic.BaseModel` with `extra="forbid"`.
  - Component models: `TourCard`, `TravellerPicker`, `ItineraryDay`, `PolicySnippet`, `DestinationHighlight`, `PriceBreakdown`, `BookingForm`, `EnquiryNotice`, `JourneyPlan`, `InteractiveMap`, `DateSelector`, `SourcePanel`.
- **Validation:** Every turn emitted from LangGraph passes through `Turn.model_validate()`. Malformed or unapproved payloads are stopped before reaching the client.

---

## 5. Security & Isolation Architecture

1. **Deterministic Isolation:**
   - LLMs are completely excluded from pricing calculations, database modifications, and publication decisions.
   - Even when live Gemini is configured, it is restricted to natural language intent assistance (`notebook_intent`), recommendation ranking (`rank`), and content drafting (`DraftText`).
2. **Database Integrity:**
   - Single-file SQLite database with Write-Ahead Logging (`PRAGMA journal_mode=WAL`).
   - Append-only audit logging: Database triggers `audit_no_update` and `audit_no_delete` abort any SQL `UPDATE` or `DELETE` statements on the `audit` table.
3. **Data Protection & PII Redaction:**
   - Outbound telemetry via Langfuse (`export_trace`) strips emails (`[REDACTED_EMAIL]`), auth tokens, staff costs (`cost_lkr`), and commercial margins.
   - Guest APIs (`/api/quotes`, `/api/enquiries/{ref}`) omit internal costs and gross margins.
