# 10 — Comprehensive Technical Gap & Risk Register

**Audit Date:** 22 November 2026  
**Auditor:** Principal AI Systems Architect & Technical Auditor  
**Scope:** Architecture, Financial Engine, Frontend Clients, Security, and Evaluations

---

## 1. Prioritized Gap Summary Table

| Gap ID | Severity | Affected Requirement | Summary Description | Complexity | Priority |
|:---:|:---:|:---:|:---|:---:|:---:|
| **GAP-01** | **MEDIUM** | Architecture / R7 | Dual Frontend Architecture: Staff console only on Next.js, notebook on TanStack Start | Medium | P0 |
| **GAP-02** | **LOW** | Evaluation / Judge | LLM Judge Human Calibration Worksheet is unpopulated (unexecuted human scoring) | Low | P0 |
| **GAP-03** | **LOW** | Evaluation / R5 | Evaluation case `P03` fails due to asserting historical email amount (USD 2,680) | Low | P1 |
| **GAP-04** | **LOW** | R3 (A2UI) | Binderless Component Index pattern used instead of canonical full-schema A2UI properties | Medium | P2 |
| **GAP-05** | **LOW** | Bonus: Routing | Model Routing (small vs. large model) is not implemented | Medium | P2 |
| **GAP-06** | **LOW** | Bonus: Personalization | Browsing history consent-based personalization is not implemented | Medium | P2 |
| **GAP-07** | **LOW** | Security / Production | Pre-shared tokens in `.env` without OAuth2/OIDC integration | Medium | P3 |
| **GAP-08** | **LOW** | Security / Production | Absence of application-level rate limiting on `/api/agent` | Low | P3 |
| **GAP-09** | **INFORMATIONAL** | R4 (Grounding) | Keyword RAG index used rather than vector embeddings (sufficient for 36 docs) | Medium | P3 |
| **GAP-10** | **INFORMATIONAL** | R5 (Pricing) | Conversational pricing requires discrete dates rather than continuous date ranges | High | P3 |

---

## 2. Granular Gap Profiles

---

### GAP-01: Dual Frontend Architecture (Split Traveller & Staff Surfaces)
- **Severity:** **MEDIUM**
- **Affected Area:** System Architecture, Operational Maintenance, Requirement R7 (Staff Console).
- **Evidence:**
  - `apps/web`: Next.js 16 on port 3000 houses `/staff` (staff console) and 11 Playwright tests.
  - `apps/ceylon-compass`: TanStack Start / Vite on port 5175 houses `/plan`, interactive map, and 33 Vitest tests.
  - `scripts/dev.py`: Launches API (8000), NEXT (3000), and WEB (5175) concurrently.
- **Reproduction Steps:**
  1. Navigate to `http://127.0.0.1:5175/staff` -> HTTP 404 Not Found (TanStack router has no `/staff` route).
  2. Navigate to `http://127.0.0.1:3000/staff` -> Staff console loads correctly.
- **Root Cause:** A migration from Next.js (`apps/web`) to TanStack Start (`apps/ceylon-compass`) was partially completed, leaving the staff console and Playwright suite on Next.js.
- **Business Impact:** High developer cognitive load, double build steps (`make build`), high memory consumption in dev (spawning 3 node/python servers).
- **Proposed Fix:** Re-implement the staff console route `/staff` inside `apps/ceylon-compass/src/routes/staff.tsx`, migrate the Playwright tests to port 5175, and deprecate `apps/web`.
- **Acceptance Criteria:** A single command `npm run build` builds the entire frontend; `/staff` is accessible directly on port 5175.
- **Estimated Complexity:** Medium (4–6 hours).

---

### GAP-02: LLM Judge Human Calibration Worksheet is Unpopulated
- **Severity:** **LOW**
- **Affected Area:** Evaluation Requirements (Take-Home Brief Section "Evaluation").
- **Evidence:**
  - `evals/judge.py` exists with scoring prompts for Relevance, Grounding, and Helpfulness.
  - `evals/judges/calibration_worksheet.md` contains the 10 representative cases (`S01`, `S07`, `S08`, `S09`, `S10`, `S12`, `S14`, `S17`, `D03`, `G02`).
  - `evals/judges/calibration_template.json` contains empty score fields (`"human_score": null`).
- **Reproduction Steps:**
  1. Inspect `evals/judges/calibration_template.json` -> all entries have null human scores.
  2. Run `python evals/judge.py --labels evals/judges/calibration_template.json` -> fails or reports 0 agreement due to null labels.
- **Root Cause:** Automated test suite was prioritized; manual labeling of the 10 worksheet cases was deferred.
- **Business Impact:** Take-home brief specifically requests: *"Report how often it agrees with you."*
- **Proposed Fix:** Review the 10 worksheet cases, enter human scores (1–5) in `calibration_template.json`, execute `evals/judge.py`, and record the agreement percentage in `report.md`.
- **Acceptance Criteria:** `calibration_template.json` contains 10 populated human scores; `report.md` records the human-judge agreement rate.
- **Estimated Complexity:** Low (1 hour).

---

### GAP-03: Evaluation Case P03 Fails Due to Asserting Historical Email Omission
- **Severity:** **LOW**
- **Affected Area:** Evaluation Suite (`evals/cases/authored.jsonl`), Requirement R5.
- **Evidence:**
  - In `evals/runner.py`, test case `P03` fails with:  
    `Expected [{'tour': 'T09', 'price_usd': 2680, 'deposit_usd': 670}], observed [{'tour': 'T09', 'price_usd': 2965, 'deposit_usd': 742}]`.
- **Reproduction Steps:**
  1. Run `PYTHONPATH=apps/api:apps/api/.deps python evals/runner.py`.
  2. Examine `evals/report/report.md` under "Failed Cases Summary".
- **Root Cause:** Historical email `Q-1043` omitted LKR 64,000 for child extra beds. Case `P03` was authored with the email numbers rather than the workbook numbers.
- **Business Impact:** Creates a single failing test (48/49 passed), which requires verbal explanation during the demo.
- **Proposed Fix:** Either:
  - Option A: Update `P03` in `authored.jsonl` to expect USD 2,965 / USD 742 (matching `S03`), achieving a 100% pass rate (49/49).
  - Option B (Recommended): Retain `P03` as a labeled discrepancy test and add explicit documentation explaining the audited sales email omission.
- **Acceptance Criteria:** Test suite behavior is clearly documented and defended during the live demo.
- **Estimated Complexity:** Low (15 minutes).

---

### GAP-04: Binderless A2UI Component Index Pattern (Protocol Variant)
- **Severity:** **LOW**
- **Affected Area:** Requirement R3 (Generative UI / A2UI Protocol).
- **Evidence:**
  - `apps/api/mira/surface.py`: Emits component nodes with `{"id": "item-0", "component": "TravellerPicker", "index": 0}`.
  - `apps/ceylon-compass/src/components/plan/AgentSurface.tsx`: Components register with schema `{ index: sdkSchema.number().int() }` and look up props from `turn.components[index]`.
- **Reproduction Steps:**
  1. Inspect network payload of `/api/agent`.
  2. Notice `updateComponents` has minimal properties (`{"index": 0}`), while full properties reside in companion `Turn` payload.
- **Root Cause:** Simplifies Zod validation and leverages Pydantic types directly in React components.
- **Business Impact:** Technically deviates from canonical A2UI where all component properties reside in `updateComponents.properties`.
- **Proposed Fix:** Serialize complete component props into `updateComponents.properties` and register full Zod schemas in `AgentSurface.tsx`.
- **Acceptance Criteria:** Components render purely from `context.componentModel.properties` without referencing external `Turn` state.
- **Estimated Complexity:** Medium (4 hours).

---

### GAP-05: Missing Bonus Feature — Model Routing
- **Severity:** **LOW**
- **Affected Area:** Optional Bonus Features (Take-Home Brief).
- **Evidence:**
  - `apps/api/mira/provider.py`: Uses a single static environment variable `os.environ["GEMINI_MODEL"]` (set to `gemini-3.6-flash`).
- **Reproduction Steps:**
  1. Search for routing logic across `apps/api/mira/` -> no conditional model switcher found.
- **Root Cause:** Development focused on core correctness (pricing, RAG, A2UI, tests).
- **Business Impact:** Loses potential bonus assessment points (+3–5 points).
- **Proposed Fix:** Introduce a routing function in `provider.py`: route simple discovery/ranking turns to `gemini-3.1-flash-lite` and multi-day itinerary synthesis to `gemini-3.6-flash` or `gemini-1.5-pro`.
- **Acceptance Criteria:** `observability.py` records separate model names per turn type; eval suite logs performance across both models.
- **Estimated Complexity:** Medium (3–4 hours).

---

### GAP-06: Missing Bonus Feature — Browsing History Personalization
- **Severity:** **LOW**
- **Affected Area:** Optional Bonus Features (Take-Home Brief).
- **Evidence:**
  - `apps/api/mira/main.py`: Visitor session supports `remember: bool`, but does not record browsed tour URLs or view duration.
- **Reproduction Steps:**
  1. Inspect `visitors` table in SQLite -> schema has `context`, but no `browsed_history` column.
- **Root Cause:** Deferred in favor of robust trip notebook persistence.
- **Business Impact:** Loses potential bonus assessment points (+3–5 points).
- **Proposed Fix:** Add a `/api/session/browsed` endpoint, record tour views in `visitors.browsed` (with user consent), and feed browsed tags into `provider.rank()`.
- **Acceptance Criteria:** Evaluation cases demonstrate differential recommendations between consented and unconsented sessions.
- **Estimated Complexity:** Medium (4 hours).

---

### GAP-07: Static Pre-Shared Tokens in `.env`
- **Severity:** **LOW (Acceptable for Take-Home)**
- **Affected Area:** Requirement R8 (Staff RBAC & Governance), Production Readiness.
- **Evidence:**
  - `.env` contains static tokens: `MIRA_STAFF_TOKEN`, `MIRA_EDITOR_TOKEN`, `MIRA_APPROVER_TOKEN`.
- **Reproduction Steps:**
  1. Inspect `apps/api/mira/main.py` -> `role()` matches against environment variables.
- **Root Cause:** Standard pattern for self-contained, zero-dependency take-home evaluations.
- **Business Impact:** Not suitable for enterprise multi-user deployments (no password rotation, no per-user audit attribution).
- **Proposed Fix:** Replace with OIDC JWT token verification (e.g., Auth0 or Firebase Auth) for production.
- **Acceptance Criteria:** Staff authentication delegates to an external identity provider.
- **Estimated Complexity:** Medium (4–6 hours).

---

### GAP-08: Absence of Application-Level API Rate Limiting
- **Severity:** **LOW**
- **Affected Area:** API Resilience & Denial-of-Service Defense.
- **Evidence:**
  - `apps/api/mira/main.py`: No rate limiting middleware on `/api/agent` or `/api/session`.
- **Reproduction Steps:**
  1. Send 50 concurrent requests to `/api/agent` -> all are accepted and processed.
- **Root Cause:** Avoided extra dependencies to keep the project clean.
- **Business Impact:** Potential exposure to rate-limit exhaustion on upstream Gemini API under adversarial load.
- **Proposed Fix:** Add `slowapi` middleware enforcing 30 requests/minute per client IP.
- **Acceptance Criteria:** Exceeding 30 requests/min returns HTTP 429 Too Many Requests.
- **Estimated Complexity:** Low (1 hour).

---

### GAP-09: Keyword RAG Index Instead of Vector Embeddings
- **Severity:** **INFORMATIONAL**
- **Affected Area:** Requirement R4 (Grounded Content Retrieval).
- **Evidence:**
  - `apps/api/mira/agent.py`: Uses keyword set intersection (`words & set(re.findall(...))`) to select candidate passages.
- **Root Cause:** A curated catalog of 36 documents does not require the overhead of a heavy vector database (pgvector/Pinecone).
- **Business Impact:** Minimal for the existing dataset; may struggle if the catalog scales to 1,000+ tours.
- **Proposed Fix:** Integrate `sqlite-vec` or `fastembed` for lightweight local semantic embeddings.
- **Estimated Complexity:** Medium (3–4 hours).

---

### GAP-10: Pricing Requires Discrete Travel Dates
- **Severity:** **INFORMATIONAL**
- **Affected Area:** Requirement R5 (Pricing Engine UX).
- **Evidence:**
  - `mira.data.calculate`: Requires a discrete `start: date`. Conversational requests like *"somewhere in June"* require picking a specific date via `TravellerPicker`.
- **Root Cause:** Hotel rates and seasonal margins are strictly date-bounded.
- **Business Impact:** Requires traveller to select a specific date before seeing a price breakdown.
- **Proposed Fix:** Add a date-range price estimator previewing lowest and highest seasonal rates.
- **Estimated Complexity:** High (6–8 hours).
