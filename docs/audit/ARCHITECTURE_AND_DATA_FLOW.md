# Technical Architecture & Data Flow: Ceylon Compass Holidays (Mira)

> **Document Purpose:** In-depth architectural blueprint, component catalog, protocol contracts, and end-to-end data flow specifications for the Mira AI Travel Booking Assistant.

---

## 1. Overall System Architecture

The following diagram illustrates the complete runtime architecture, detailing all client boundaries, network transport protocols, backend services, orchestration graphs, and persistence stores:

```mermaid
flowchart TD
    subgraph ClientLayer["Frontend Presentation Layer"]
        A1["React Travel Workspace\n(/workspace/index.html · Port 5175)"]
        A2["TanStack Start Notebook\n(/plan · Port 5175)"]
        A3["Staff Operations Console\n(/staff · Port 5175 & Port 3000)"]
        A4["A2UI Component Catalog\n(TourCard, PriceBreakdown, TravellerPicker, BookingForm)"]
        A1 --- A4
        A2 --- A4
    end

    subgraph TransportLayer["A2UI & API Gateway Layer"]
        B1["Vite / Nitro Reverse Proxy\n(/api/* -> http://127.0.0.1:8000)"]
        B2["@ag-ui/client Protocol Receiver\n(EventSource / SSE Connection)"]
        B3["FastAPI ASGI Server\n(Port 8000 · Uvicorn)"]
        A1 --> B1 --> B2 --> B3
        A3 --> B1 --> B3
    end

    subgraph SecurityMiddleware["FastAPI Middleware & RBAC"]
        C1["Session & Visitor Cookie Resolver\n(mira_session -> visitors / user_sessions)"]
        C2["RBAC Dependency Gate\n(roles: traveller, staff, approver, admin)"]
        C3["Security Headers & CSRF Protection\n(SameSite=Lax, HttpOnly)"]
        B3 --> C1 --> C2 --> C3
    end

    subgraph LangGraphOrchestrator["LangGraph Agent Workflow (apps/api/mira/agent.py)"]
        D1["Node 1: interpret\n(Intent, Dates, Party Size, Child Ages, Replays)"]
        D2["Node 2: retrieve\n(Published RAG Index · Tours & Destinations)"]
        D3["Node 3: quote\n(Triggered if Tour + Date + Party are Complete)"]
        D4["Node 4: compose\n(A2UI Turn Assembly & Upstream Deduplication)"]
        D5["Node 5: save\n(Atomic SQLite Persistence)"]

        C2 --> D1
        D1 --> D2
        D2 -->|Complete Party & Valid Tour| D3 --> D4
        D2 -->|Incomplete Party / Missing Rates / Custom| D4
        D4 --> D5
    end

    subgraph PricingEngine["Deterministic Pricing Engine (apps/api/mira/data.py)"]
        E1["Excel Contract Sheet Ingestion\n(data/rate_sheet_2026_2027.xlsx)"]
        E2["Vehicle Category Matching\n(Car, Mini Van, Passenger Van, Mini Bus)"]
        E3["Hotel Room & Extra Bed Rules\n(Adult pairs double, single room, child extra-bed)"]
        E4["Fixed LKR/USD FX & Target Margin\n(Decimal arithmetic, round up USD 5 steps)"]
        E5["Deposit & Balance Logic\n(Day tours: 100%; Multi-day: workbook %)"]

        D3 --> E2
        E1 --> E2 --> E3 --> E4 --> E5
    end

    subgraph DataStorage["Persistence & Telemetry Stores (SQLite & Observability)"]
        F1[("SQLite Database\n(mira.sqlite3)")]
        F2["traces & failed_traces Tables\n(Stage latencies, prompt, result)"]
        F3["quotes & enquiries Tables\n(Public quote DTO, internal costs, lead queue)"]
        F4["trips & trip_turns Tables\n(Multi-turn notebook journals)"]
        F5["drafts & audit Tables\n(Content review, append-only trigger)"]
        F6["Optional Langfuse Exporter\n(Sanitized background spans)"]

        D5 --> F1
        F1 --- F2
        F1 --- F3
        F1 --- F4
        F1 --- F5
        D5 -.-> F6
    end
```

---

## 2. LangGraph Agent Execution Lifecycle

The conversational agent operates as an explicit, cyclic state machine implemented using `langgraph.graph.StateGraph`:

```mermaid
stateDiagram-v2
    [*] --> Interpret : Human Message Received (SSE Stream)
    
    state Interpret {
        [*] --> CheckReplay
        CheckReplay --> ParseEntities : Not a Replay
        ParseEntities --> ExtractTourAlias : Matches T01-T16
        ParseEntities --> ExtractDate : ISO or Natural Date
        ParseEntities --> ExtractParty : Adults & Child Ages
        CheckReplay --> ReturnReplay : Replay from Trace Cache
    }

    Interpret --> Retrieve : Parsed Working Context

    state Retrieve {
        [*] --> QueryCatalogue
        QueryCatalogue --> FilterPublished : Exclude T14, T15, Drafts
        FilterPublished --> RankResults : Gemini or Local Overlap
    }

    Retrieve --> Quote : Tour + Date + Adults Complete?
    Retrieve --> Compose : Incomplete Info / Custom / Refusal

    state Quote {
        [*] --> ValidateSeason
        ValidateSeason --> CalculateBuyCost : Matched Contract Rows
        CalculateBuyCost --> ApplyFxAndMargin : Decimal Rounding
        ApplyFxAndMargin --> DeriveDeposit : Day vs Multi-Day Rule
        ValidateSeason --> RaiseUnavailable : Missing Hotel / Expired
    }

    Quote --> Compose : Verified Quote / Failure Reason

    state Compose {
        [*] --> DeduplicateComponents
        DeduplicateComponents --> BuildPriceBreakdown : If Quote Verified
        DeduplicateComponents --> BuildEnquiryNotice : If Unavailable / Custom
        DeduplicateComponents --> FormatAssistantText
    }

    Compose --> Save : Validated Turn Schema

    state Save {
        [*] --> BeginTransaction
        BeginTransaction --> InsertTrace
        InsertTrace --> InsertQuote : If Quoted
        InsertQuote --> InsertEnquiry : Private Lead Captured
        InsertEnquiry --> CommitTransaction
    }

    Save --> [*] : Turn Emitted to Client Stream
```

---

## 3. Traveller Conversation & A2UI Protocol Flow

Communication between the client browser and the FastAPI backend uses the Agent-to-User Interface (A2UI) protocol over Server-Sent Events (SSE):

```mermaid
sequenceDiagram
    autonumber
    actor Traveller
    participant UI as Travel Workspace (React)
    participant AG as @ag-ui/client
    participant API as FastAPI /api/agent
    participant Graph as LangGraph Engine
    participant DB as SQLite Database

    Traveller->>UI: Types "Sigiriya day tour for 4 adults on Jan 10, 2027"
    UI->>AG: Dispatch action via run()
    AG->>API: POST /api/agent?trip_id={tripId} (SSE Request)
    Note over API: Ingests X-Request-Id & visitor cookie
    API->>Graph: LangGraphAgent.run(messages, state)
    
    activate Graph
    Graph->>Graph: interpret (T01, 2027-01-10, 4 adults)
    Graph->>Graph: retrieve (T01 Sigiriya Tour)
    Graph->>Graph: quote (price: USD 540)
    Graph->>DB: INSERT into traces, quotes, enquiries
    Graph->>API: Emit Turn (Text, TourCard, PriceBreakdown)
    deactivate Graph

    API-->>AG: SSE Event: STATE_SNAPSHOT { turn, surface }
    API-->>AG: SSE Event: RUN_FINISHED
    AG-->>UI: OnStateChanged callback
    UI->>Traveller: Renders TourCard & PriceBreakdown (USD 540 Verified)
```

---

## 4. Verified Quotation Lifecycle

A quotation moves through strict status transitions to guarantee financial correctness and prevent stale prices from being displayed:

```mermaid
stateDiagram-v2
    [*] --> NONE : Traveller opens tour page
    NONE --> LOADING : Traveller clicks "Get verified quote"
    
    state LOADING {
        [*] --> CreateImmutableSnapshot
        CreateImmutableSnapshot --> DispatchBackendRequest
    }

    LOADING --> VERIFIED : Backend returns valid quote
    LOADING --> UNAVAILABLE : Rates expired / missing contracted row
    LOADING --> ERROR : Network or server failure

    state VERIFIED {
        [*] --> DisplayPriceBreakdown
        DisplayPriceBreakdown --> AllowMockBooking : Config matches quote
    }

    VERIFIED --> OUTDATED : Traveller modifies party count or travel date
    
    state OUTDATED {
        [*] --> ShowAmberWarningBanner
        ShowAmberWarningBanner --> DisableMockBooking
        ShowAmberWarningBanner --> ShowRecalculateButton
    }

    OUTDATED --> LOADING : Traveller clicks "Recalculate quote"
    VERIFIED --> NONE : Traveller switches to another tour
    OUTDATED --> NONE : Traveller switches to another tour
```

---

## 5. Enquiry and Mock Booking Lifecycle

Every commercial interaction is captured for operations staff while preserving simulated test checkout:

```mermaid
flowchart LR
    subgraph QuoteGeneration["Phase 1: Quotation"]
        Q1["Traveller Configures Trip"] --> Q2["FastAPI / Deterministic Engine"]
        Q2 --> Q3["Verified Quote Record\n(quotes table)"]
    end

    subgraph EnquiryRecording["Phase 2: Private Lead Capture"]
        Q3 --> E1["Automatic Private Enquiry\n(enquiries table: status 'new')"]
        Q2 -->|Rates Missing / Custom| E2["Specialist Enquiry\n(enquiries table: status 'new')"]
        E1 --> E3["Staff Console Queue\n(/staff Enquiries view)"]
        E2 --> E3
    end

    subgraph MockCheckout["Phase 3: Simulated Booking"]
        Q3 --> B1["Traveller selects scenario\n('success' or 'declined')"]
        B1 --> B2["POST /api/bookings/mock"]
        B2 -->|Scenario: success| B3["Create Booking Record\n(bookings table)"]
        B2 -->|Scenario: declined| B4["Reject & Alert Client\n(Zero DB write)"]
        B3 --> B5["Booking Confirmed Badge\n(Confirmation ID displayed)"]
    end

    subgraph StaffOperations["Phase 4: Operations Follow-Up"]
        E3 --> S1["Assign Specialist (Staff RBAC)"]
        S1 --> S2["Add Operational Note (notes table)"]
        S2 --> S3["Mark Complete / Contacted"]
    end
```

---

## 6. Staff Content Approval & Governance Lifecycle

To protect brand integrity, generative AI tour drafting is strictly isolated behind human approval:

```mermaid
sequenceDiagram
    autonumber
    actor Editor as Staff Editor
    actor Approver as Content Approver
    participant Console as Staff Console (/staff)
    participant API as Content API (/api/staff/drafts)
    participant DB as SQLite (drafts, audit)
    participant RAG as Published Catalogue

    Editor->>Console: Enter prompt: "Prepare private Ella itinerary"
    Console->>API: POST /api/staff/drafts
    API->>DB: INSERT into drafts (status: 'draft')
    API-->>Console: Draft created (ID: D-xxx)
    Note over RAG: Draft is HIDDEN from traveller search

    Editor->>Console: Tries to publish draft
    Console->>API: POST /api/staff/drafts/D-xxx/publish
    API-->>Console: 403 Forbidden (Editors cannot publish)

    Approver->>Console: Logs in with Approver credentials
    Approver->>Console: Inspects draft content & reviews safety
    Approver->>Console: Clicks "Approve Content"
    Console->>API: PATCH /api/staff/drafts/D-xxx (status: 'approved')
    API->>DB: UPDATE drafts SET status = 'approved'

    Approver->>Console: Clicks "Publish"
    Console->>API: POST /api/staff/drafts/D-xxx/publish
    API->>DB: UPDATE drafts SET status = 'published'
    API->>DB: INSERT into audit (actor, action, target)
    Note over DB: SQLite trigger enforces append-only audit
    API->>RAG: Append new tour to published_records()
    API-->>Console: Published! Now active in discovery
```
