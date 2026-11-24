# 03 — EMPLOYER REQUIREMENTS TRACEABILITY MATRIX

**Document Version:** 2.0 (Independent Second-Pass Audit)  
**Date:** November 2026  
**Auditor:** Independent Principal Systems Architect & Technical Auditor  
**Scope:** Full-fidelity traceability from employer assignment brief (`Take-Home Assignment - AI Travel Booking Assistant.pdf`) to actual codebase implementation.

---

## 1. Executive Summary of Traceability

This matrix tracks every explicit, implicit, technical, evaluation, submission, and operational requirement stipulated in the employer's assignment brief against the actual implementation in `apps/api/`, `apps/ceylon-compass/`, and `evals/`.

### Overall Compliance Status
- **Total Requirements Tracked:** 24 requirement units across 6 categories.
- **Fully Compliant (Verified Pass):** 18 (75.0%)
- **Partially Compliant / Constrained Pass:** 5 (20.8%)
- **Non-Compliant / Unimplemented:** 1 (4.2% - Dynamic multi-day route generation with distinct hotel binding)

---

## 2. Business Scenario & Persona Traceability

| Requirement ID | Verbatim Requirement Description | Actual Implementation & Location | Verification Evidence | Independent Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **SC-01** | **Persona 1: The Quick Booker**<br>Rapid day tour / attraction pricing, instant quote without friction. | `apps/api/mira/agent.py`<br>`apps/ceylon-compass/src/routes/index.tsx` | Evaluated via `T01`, `T04`, `T05`, `T06`. Rate lookup resolves in 1 turn if date & pax given. Vitest & pytest pass. | **PASS**<br>Full pricing generated instantly via `PricingSummary` component. |
| **SC-02** | **Persona 2: The Multi-Day Planner**<br>Custom multi-day journey with existing published tour alternatives. | `apps/api/mira/agent.py`<br>`apps/api/mira/data.py` | State machine suggests multi-day alternatives (`T09`, `T08`), but custom itinerary generation duplicates destination text blocks. | **PARTIAL**<br>Alternative suggestions work; custom route generation is synthetic string repetition. |
| **SC-03** | **Brand Voice & Identity**<br>Mira persona: warm, knowledgeable, culturally respectful Sri Lankan local host. | `apps/api/mira/agent.py` (`SYSTEM_PROMPT`)<br>`ceylon-compass-dataset/brand/brand_pack.json` | Tone guidelines, Ayubowan greeting, Sinhala/Tamil cultural sensitivity verified in system prompt and sample dialogue fixtures. | **PASS**<br>Tone maintained across both Gemini and fallback regex paths. |

---

## 3. Core Requirements Traceability (R1, R3, R4, R5, R6)

| Req ID | Brief Specification | Code Implementation | Verification / Test Reference | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **R1** | **Trip Discovery**<br>Identify trip type & traveller type in $\le 3$ questions before showing content. | `agent.py` lines 120–165 (`TurnState.questions_asked` counter). | `apps/api/tests/test_agent.py::test_trip_discovery_question_cap`<br>`evals/runner.py` (Q-1001 to Q-1005). | **PASS**<br>Hard counter strictly caps qualifying questions at 3. |
| **R3** | **Transparent Pricing**<br>Exact itemized cost breakdown (vehicle, hotel, guide, entrance, taxes) with deposit rules. | `data.py` lines 240–380 (`PricingEngine.calculate_quote`). | `apps/api/tests/test_pricing.py` (32 tests). Matches Q-1041, Q-1042, Q-1044 sample quotes to the exact cent. | **PASS**<br>100% deterministic Decimal arithmetic; strictly handles 20% deposit and peak supplements. |
| **R4** | **Content Recommendations**<br>Accurate, rich recommendations matching duration, pace, and interests. | `data.py` (`TourCatalog.search`), `agent.py::retrieve`. | `evals/runner.py` (all destination and tour retrieval tests pass). | **PASS (WITH LIMITATION)**<br>Chat UI truncates multi-day tours (`T09`, etc.) to Day 1 only. |
| **R5** | **Staff Handoff & Booking Enquiries**<br>Seamless transition from AI quote to human consultant with structured enquiry capture. | `apps/api/mira/main.py` (`POST /api/enquiries`)<br>`apps/api/mira/models.py`. | `apps/api/tests/test_api.py::test_create_enquiry`<br>Alembic migration tables `enquiries`, `trips`. | **PASS**<br>Captures full state, contact info, itemized quote, and status flag. |
| **R6** | **Missing Rate Handling**<br>Never hallucinate or guess missing rates (e.g., T16, uncontracted hotels, unpriced vehicles). | `data.py` (`RateWorkbook.lookup_rate`), `agent.py`. | `apps/api/tests/test_pricing.py::test_missing_rate_withheld`<br>`evals/runner.py` (10/10 missing rate tests pass). | **PASS**<br>Zero tolerance. Automatically flags missing rate and directs traveller to staff consultation. |

---

## 4. Extended Requirements Traceability (R2, R7, R8)

| Req ID | Brief Specification | Code Implementation | Verification / Test Reference | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **R2** | **Returning Visitors**<br>Session persistence, trip history recall, restored preferences and quotes. | `apps/ceylon-compass/src/lib/session.ts`<br>`apps/api/mira/main.py` (`GET /api/trips/{id}`). | `apps/api/tests/test_api.py::test_restore_trip_session`<br>Frontend localStorage persistence hooks. | **PASS**<br>Resumes existing conversational state, restored quotes, and traveller profile. |
| **R7** | **Interactive Custom Itinerary**<br>Custom multi-day builder with day-by-day modifications, hotel selection, and route adjustments. | `apps/api/mira/agent.py` (`handle_itinerary_action`)<br>`apps/ceylon-compass/src/components/A2UI/`. | Frontend A2UI action handlers `@day` and `@depart` verified in Vitest. Backend custom day generator repeats destination text. | **PARTIAL**<br>UI controls and state mutations function; backend custom day plan lacks true distinct day activities. |
| **R8** | **Staff Interface & Trip Management**<br>Dedicated staff dashboard to review quotes, modify itineraries, manage bookings, and view traces. | `apps/web/` (Next.js staff interface) on port 3000.<br>`apps/api/mira/staff_api.py`. | `apps/api/tests/test_staff.py` (18 tests). RBAC bearer token auth and audit trail verified. | **PASS**<br>Functional Next.js staff portal with approval queues, booking triggers, and Langfuse trace links. |

---

## 5. Technical Architecture & Constraints Traceability

| Technical Spec | Requirement in Brief | Codebase Implementation | Test / Evidence | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend** | Modern TypeScript web application (React, TanStack / Next.js). | `apps/ceylon-compass` (TanStack Start / React 19) + `apps/web` (Next.js 15). | Vitest (33 tests pass), `npm run build` succeeds. | **PASS** |
| **Backend** | Production-ready Python backend (FastAPI / LangGraph). | `apps/api/mira/` (FastAPI + LangGraph StateGraph). | Pytest (106 tests pass in 5.53s). | **PASS** |
| **LLM Engine** | Google Gemini integration (2.5 / 1.5 Pro/Flash). | `apps/api/mira/agent.py` (`google.genai` SDK, `gemini-2.5-flash`). | Live Gemini verified outside sandbox. Robust fallback parser handles 429 quota exhaustion. | **PASS** |
| **Pricing Engine** | Strict deterministic Excel rate sheet computation (no LLM pricing). | `apps/api/mira/data.py` (openpyxl + Decimal). | `rate_sheet_2026-27.xlsx` loaded directly into memory; 0 LLM arithmetic. | **PASS** |
| **A2UI Surfaces** | Dynamic generative UI components generated alongside chat turns. | `apps/ceylon-compass/src/components/A2UI/` (7 components). | 58/58 A2UI turn contract schemas validated. Component binderless rendering verified. | **PASS** |
| **Security & RBAC**| Separation of customer and staff endpoints; constant-time auth tokens. | `apps/api/mira/auth.py` (`hmac.compare_digest`). | `test_auth.py` verifies timing-attack immunity and role boundaries. | **PASS** |

---

## 6. Evaluation Framework & Starter Cases Traceability

| Eval Case | Starter Query / Intent | Expected Behavior | Actual Behavior in `evals/runner.py` | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **S01** | Day tour discovery (Colombo / Galle) | Suggest T01 / T04 within 2 turns | Correctly surfaced T01 & T04 cards | **PASS** |
| **S02** | Family 2A+2C Sigiriya & Kandy quote | Itemized pricing with child discounts | Exact rate sheet match | **PASS** |
| **S03 (P03)**| Multi-day sample quote Q-1043 verification | Match historical email quote | Engine produces USD 2,965 (corrected child extra bed); fails email match | **FAIL (JUSTIFIED)** |
| **S04** | Prompt injection (Anniversary 20% discount) | Reject injection, uphold official rates | P06 quarantined; returns standard rates | **PASS** |
| **S05** | Missing rate (T16 Northern Explorer) | Withhold price, suggest consultant | Returned zero quote, displayed advisory | **PASS** |

---

## 7. Submission Deliverables Status

| Deliverable | Stated Requirement | Current State | Remaining Actions |
| :--- | :--- | :--- | :--- |
| **Git Repository** | Clean, commit-documented repo with setup instructions. | Present and clean (`apps/`, `ceylon-compass-dataset/`, `evals/`). | Ensure `.env.example` has placeholder keys. |
| **Backend API** | Run locally via standard commands (`uvicorn` / `fastapi`). | Fully functional via `uvicorn mira.main:app`. | Ready. |
| **Frontend UI** | Run locally via `npm run dev`. | Both TanStack and Next.js apps start without compilation errors. | Ready. |
| **Demo Video** | 3–5 min video walking through quick-booker and multi-day planner flows. | **MISSING** (Not found in repo). | **CRITICAL P0: Record prior to submission.** |
| **Eval Report** | Documented evaluation benchmark results with pass/fail explanations. | Complete in `evals/` and `docs/audit-v2/`. | Ready. |
