# 01 — Independent Verdict: Second-Pass Adversarial Audit of Mira

**Audit Completion Date:** 22 November 2026  
**Auditor:** Independent Principal Software Architect, GenAI Systems Auditor & Technical Assessment Reviewer  
**Repository Target:** `/Users/denuwanwijesinghe/Documents/BSc. Artficial Intellligence/Competition/intern_assignment`  
**Assessment Date:** 19 November 2026 (`AS_OF_DATE=2026-11-19`)  
**Submission Deadline:** 25 November 2026, 23:59 (3 days remaining)

---

## 1. Executive Summary & Independent Verdict

The previous audit concluded that Mira is approximately **94% submission-ready**. This second-pass independent audit conducted an adversarial verification of that claim, inspecting the actual code, raw dataset files, runtime API responses, live Gemini API behavior, and browser UI components.

### Core Verdict:
> **Mira is a remarkably disciplined, mathematically flawless financial pricing engine wrapped in an impressive dual-frontend prototype. However, the claim that it is a 94% complete "conversational agent that generates its own interface" is an overstatement of the AI's actual autonomy.**

Specifically, this independent audit revealed the following critical realities:
1. **Pricing & Security are 100% Genuine and Exemplary:** The quotation engine (`mira/data.py`) does not use the LLM for arithmetic. It implements Decimal financial math directly from the Excel workbook, correctly identifies the LKR 64,000 extra-bed omission in historical quote Q-1043, and enforces append-only SQLite audit triggers and strict public/private financial data segregation.
2. **Generative UI is Deterministic Template Assembly, Not Agent-Generated:** The LLM does **not** choose, compose, or generate A2UI components. Component selection is executed 100% by deterministic Python `if/else` logic in `agent.py::compose()`. Furthermore, components use an unconventional "binderless index" pattern where props reside in a companion payload rather than inside canonical A2UI component schemas.
3. **Conversational Multi-Day Tour Itineraries are Truncated to Day 1:** While the markdown dataset provides rich, day-by-day itineraries (e.g., T09 has 7 detailed days, T08 has 8 days), the conversational agent's `compose()` function explicitly uses a regex that matches only `Day 1` or `Highlights`, completely discarding Days 2 through 7 from the chat surface.
4. **Custom Itinerary Planning Generates Synthetic Duplication:** When a planner requests a 10-day trip across Kandy, Ella, and the south coast, the system does not plan distinct activities, morning/afternoon schedules, or hotels. It simply repeats the destination overview paragraph across $n$ days (e.g., Kandy repeated 3 times, Ella repeated 3 times).
5. **RAG Policy Retrieval Relies on Hardcoded Routing:** The agent does not perform dynamic semantic retrieval for policy questions. In `agent.py::retrieve()`, requests for cancellation, child policies, dietary needs, and payments are hard-routed via a fixed Python dictionary (`{"cancellation": ["P02"], "children": ["P03"], "payment": ["P01"]}`).
6. **Live Gemini Integration is Rate-Limited by Free-Tier Quotas:** Live execution against the configured `gemini-3.6-flash` model encountered immediate HTTP 429 Resource Exhausted errors (20 requests/day limit on Free Tier). Fortunately, Mira's graceful fallback logic caught the exception and fell back to local extraction without crashing, disclosing limited service to the user.

---

## 2. Objective Readiness Scorecard

To provide an unvarnished assessment, we replace the previous audit's optimistic score with an objective, weighted rubric derived from the employer's assignment brief:

| Evaluation Dimension | Weight | Claimed Score | Verified Score | Justification |
|:---|:---:|:---:|:---:|:---|
| **Core 1: Trip Discovery (R1)** | 10% | 100% | **85%** | Successfully discovers trip/traveller type in $\le 3$ questions, but relies on rigid keyword regexes if Gemini fails. |
| **Core 2: Generative UI (R3)** | 15% | 100% | **75%** | Streams valid A2UI v0.9 via AG-UI, but component selection is hardcoded in Python, not agent-selected. |
| **Core 3: Grounded Answers (R4)** | 10% | 100% | **80%** | Facts are strictly grounded with citations, but policy RAG uses a hardcoded dictionary rather than semantic search. |
| **Core 4: Correct Pricing (R5)** | 15% | 100% | **100%** | 100% mathematically correct. Audited against all workbook rules, seasons, vehicle tiers, and room occupancies. |
| **Core 5: Missing Rates (R6)** | 10% | 100% | **100%** | 10/10 test cases correctly fail closed without invented amounts; specialist enquiries created. |
| **Extended: Visitor Memory (R2)** | 5% | 100% | **95%** | Cookie session management restores previous quotes and context; forget endpoint works. |
| **Extended: Enquiries (R7)** | 5% | 100% | **90%** | Private enquiries, staff review, notes with PII guards work; staff console currently isolated on port 3000. |
| **Extended: Approval Gate (R8)** | 5% | 100% | **95%** | Editor draft creation, Approver-only publication gate, and dynamic catalogue updates verified. |
| **Technical Architecture** | 10% | 90% | **75%** | LangGraph 5-node graph works; dual-frontend architecture (Next.js + TanStack) introduces operational friction. |
| **Observability & Tracing** | 5% | 90% | **85%** | Per-turn SQLite tracing with child spans and PII redaction verified; Langfuse export structured cleanly. |
| **Evaluation Suite & Evals** | 10% | 95% | **80%** | 48/49 automated cases pass offline; LLM judge human calibration worksheet remains unpopulated. |
| **TOTAL WEIGHTED READINESS** | **100%** | **94%** | **85.5%** | **Solid submission-ready foundation, but with notable AI autonomy and content presentation gaps.** |

---

## 3. What Works Brilliantly (Confirmed Strengths)

1. **Provable Financial Determinism:** The separation of concerns between conversational NLU and financial quotation is absolute. Mira never lets an LLM hallucinate or calculate prices.
2. **Defensive Ingestion of Poisoned Data:** Mira successfully neutralizes both the indirect prompt injection in `testimonials.md` (`P06`) and the hidden HTML comment discount injection in `mirissa.md` (`D08`).
3. **Resilient Failure Recovery:** When Gemini throws HTTP 429 or 504 errors, Mira does not crash or return HTTP 500. It logs `gemini.failed`, discloses limited service, and completes the turn using deterministic local extraction.
4. **Idempotent Mock Booking & Payment:** Payment decline and network failure scenarios display empathetic, non-technical recovery messages and retry buttons without leaving the page.
5. **Security & Audit Immutability:** SQLite database triggers strictly forbid updating or deleting rows in the `audit` table, ensuring an append-only compliance log.

---

## 4. What Was Overstated or Incomplete (The Gaps)

1. **"The Agent Generates the Interface":** In reality, LangGraph node `compose()` hardcodes the component layout. If a quote exists, it inserts `Breakdown` and `Booking`; if custom, it inserts `Proposal` and `Notice`. The LLM has zero influence over UI layout or component selection.
2. **"97.3% Dataset Utilization":** While 36 of 37 files are parsed without errors, the detailed itinerary content of multi-day tours (Days 2 through 7) is never shown in conversational responses.
3. **Custom Planner Itineraries:** Custom proposals do not contain daily activities or hotel assignments; they are simply repeated destination summary blocks.
4. **Dual Frontend Architecture:** Having `apps/web` on port 3000 (Next.js) for staff management and `apps/ceylon-compass` on port 5175 (TanStack Start) for traveller planning causes confusion during setup and testing.
5. **LLM Judge Calibration:** The human calibration worksheet (`calibration_template.json`) has null scores, leaving the requirement for human-judge agreement unfulfilled.

---

## 5. Final Bottom-Line Conclusion

**Mira is a high-scoring, technically impressive submission that prioritizes safety, financial correctness, and protocol compliance over risky generative autonomy.**

It fulfills all mandatory requirements of the employer's assignment and handles the complex financial workbook with masterly precision. However, candidates must be completely honest during the live demo: **the UI generation and policy retrieval are deterministic backend rules rather than autonomous LLM decisions.** Describing this openly as a deliberate architectural safety choice will score far higher than falsely claiming end-to-end generative autonomy.
