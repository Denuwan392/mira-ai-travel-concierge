# Known Limitations & Engineering Disclosures

| Requirement / Component | Current Implementation State | Operational Trade-offs & Limitations |
|:---|:---|:---|
| **One-Command Startup** | Native `make dev` supervises Vite (port 5175), Next.js (port 3000), and FastAPI (port 8000) using locked dependencies. | Docker Compose configuration is provided for container hosts, but host validation used native macOS/Linux process groups. |
| **Responsive Brand Layout** | Two-column desktop layout with sticky canvas; responsive mobile single-column layout with tabbed chat/journey views. Tested at 375, 390, 768, and 1280 CSS pixels. | Mobile viewport switches between conversation and canvas tabs; full simultaneous split-screen requires tablet or desktop viewport. |
| **R1 Discovery & NLU** | Hybrid natural language intent extraction using regex entity extraction combined with Gemini structured outputs (`rank`, `notebook_intent`). | Unstructured or ambiguous traveler requests outside known tour aliases gracefully prompt traveler with structured `TravellerPicker` instead of guessing. |
| **R2 Returning Visitors** | HTTP cookie session management (`mira_session`) with `remember: bool` consent. Stores visitor state, saved quotes, and private notebooks in SQLite. | Visitor identity is tied to the client browser cookie; cross-device authentication (e.g. magic link or OAuth2 sign-in) is omitted to keep the app zero-dependency. |
| **R3 A2UI Streaming** | Implements the official `@ag-ui/client` and `ag_ui_langgraph` protocol. Renders 17 authorized Pydantic component models. | Stream events deliver complete validated components at turn boundaries; character-by-character token streaming is reserved for live LLM text generation. |
| **R4 Content Grounding** | RAG retrieval from published markdown tour files and destination profiles. Emits safe `SourceDisclosure` and `MarkdownContent`. | Keyword and metadata index is optimized for the supplied catalogue; full-text vector embeddings (e.g. pgvector or Pinecone) were deferred as unnecessary for a curated catalog of 16 tours. |
| **R5 Deterministic Pricing** | All 4 sample quotes audited. Decimal arithmetic guarantees zero floating-point drift. Q-1043 mathematically accounts for LKR 64,000 child extra beds (**USD 2,965**), correcting the historical email omission. | Pricing requires discrete dates and group parameters; conversational ranges (e.g. "somewhere between May and July") require selecting a specific date. |
| **R6 Missing Rates & Bounds** | 10 missing-rate refusal cases tested. Missing rates (`H04` single room), expired contracts, duration conflicts, and parties $> 20$ fail closed without invented amounts. | Requires travel specialists to manually review flagged enquiries and issue bespoke quotations out-of-band. |
| **R7 Private Enquiries** | Role-gated queue (`staff`, `editor`, `approver`), operational notes with PII redaction, and internal finance inspection. | Internal staff tools are designed for local evaluation; external CRM/email integrations (e.g. Salesforce or HubSpot webhooks) are not connected. |
| **R8 Content Governance** | Human-in-the-loop workflow: Editor drafts $\to$ Approver authorization $\to$ Published RAG retrieval. Append-only audit table protected by SQLite triggers. | Staff accounts use expiring HttpOnly cookies. The alternative console supports role-specific Bearer tokens (`MIRA_STAFF_TOKEN`, etc.); enterprise SSO / SAML was deferred. |
| **Observability & Tracing** | Unique `trace_id` per turn; records the executed stages in SQLite. Safe Langfuse exporter with PII scrubbing and graceful outage fallback. | Hosted Langfuse delivery requires live external credentials (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`); when absent, tracing operates reliably in local SQLite mode. |
| **Evaluation Suite** | The current runner reports measured totals and per-case traces in [the latest evaluation](../evals/report/report.md). Case P03 cleanly flags the Q-1043 historical sample conflict while gating regressions with exit code 0. | Live judge scores are recorded. Calibration requires independent human labels (`evals/judges/review-set.json`). |
| **Database Architecture** | SQLite with WAL mode, parameterized queries, and immediate transaction locking. | Multi-replica horizontal auto-scaling would require migration to PostgreSQL and a distributed checkpointer (e.g. Redis). |

---

## AI-Assisted Tooling Disclosure

In accordance with transparent engineering principles:
- **Collaborative AI Development:** Codebase exploration, architectural refactoring, Markdown presentation components, regression test authoring, and documentation synthesis were assisted by **Antigravity AI (Google DeepMind)**.
- **Human Authorship & Authority:** All business formulas, Excel rate sheet derivations, database constraints, test fixtures, and architectural trade-offs were derived directly from the assignment specifications and verified by continuous test execution.
