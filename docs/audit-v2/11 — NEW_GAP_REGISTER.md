# 11 — INDEPENDENT GAP REGISTER

**Document Version:** 2.0 (Independent Second-Pass Audit)  
**Date:** November 2026  
**Auditor:** Independent Principal Systems Architect & Technical Auditor  
**Scope:** Prioritized register of confirmed defects, architectural limitations, fidelity gaps, and submission blockers.

---

## 1. Summary of Gap Severity Distribution

| Priority Level | Description | Count | Action Required Before 25 Nov Deadline |
| :---: | :--- | :---: | :--- |
| **P0 (Critical)** | Direct threat to submission validity or scoring. | **2** | **MUST RESOLVE PRIOR TO SUBMISSION.** |
| **P1 (High)** | Core functional or user experience limitation. | **3** | Document transparently in submission notes or patch if low-risk. |
| **P2 (Medium)**| Architectural constraint or edge-case limitation. | **6** | Include in future improvement roadmap. |
| **P3 (Low)** | Minor polish, cosmetic, or non-blocking enhancement. | **3** | Nice-to-have backlog items. |

---

## 2. Comprehensive Gap Register

### P0 — Critical Submission Blockers

#### GAP-01: Missing Demonstration Video
- **Category:** Submission Deliverable.
- **Affected Artifacts:** Submission root directory.
- **Evidence:** The employer brief explicitly mandates a 3–5 minute demonstration video showcasing both the Quick Booker and Multi-Day Planner workflows. No video file or hosted URL is currently present in the repository.
- **Impact:** Immediate loss of critical submission points.
- **Remediation:** Record and upload a 3–5 minute walkthrough video prior to the November 25 submission deadline.

#### GAP-02: Documented Calibration Needed for Q-1043 Discrepancy
- **Category:** Evaluation Benchmark & Technical Report.
- **Affected Artifacts:** `evals/eval_seed.jsonl` (P03), `evals/runner.py`.
- **Evidence:** `evals/runner.py` reports 48/49 cases passed because test P03 fails against the historical email quote ($2,750 vs $2,965).
- **Impact:** Reviewers running `evals/runner.py` will see 1 failing test and may assume the pricing engine is broken.
- **Remediation:** Do NOT tamper with the pricing engine. Provide a dedicated calibration section in the submission README proving that the email omitted LKR 64,000 in child extra beds.

---

### P1 — High-Priority Functional & UX Discrepancies

#### GAP-03: Chat Truncation of Multi-Day Tour Itineraries to Day 1
- **Category:** UI / Presentation Fidelity.
- **Affected Artifacts:** `apps/api/mira/agent.py` line 386, `TourCard.tsx`.
- **Evidence:** In `compose()`, a regular expression splits tour markdown text and extracts only Day 1 (`re.search(r"### Day 1(.*?)(?=\n### Day 2|\Z)")`), completely discarding Days 2–7 in the conversational stream.
- **Impact:** Travellers inspecting a 7-day tour in chat see only Day 1 unless they open the full modal.
- **Remediation:** Update `compose()` to pass the full structured day array to `TourCard`, allowing expandable accordion views in chat.

#### GAP-04: Custom Itinerary Builder Duplicates Destination Text
- **Category:** Itinerary Synthesis Fidelity.
- **Affected Artifacts:** `apps/api/mira/agent.py` (`handle_itinerary_action`).
- **Evidence:** When generating custom 5–10 day itineraries, the backend repeats the top-level destination overview text across consecutive days spent in the same region.
- **Impact:** Custom itineraries lack granular daily activities (e.g., Day 1: Citadel, Day 2: Village tour).
- **Remediation:** Build a secondary activity bank indexed by destination ID to distribute distinct activities across multi-day stays.

#### GAP-05: Gemini API Quota Exhaustion on Free Tier
- **Category:** Production Resilience / Live Demo Risk.
- **Affected Artifacts:** `apps/api/mira/agent.py`.
- **Evidence:** Live testing confirmed Gemini `gemini-2.5-flash` throws `429 RESOURCE_EXHAUSTED` when daily free quotas (20 req/day) are reached.
- **Impact:** A live demonstration to evaluators could fail if relying on an unmonitored free-tier API key.
- **Remediation:** Ensure a paid/funded API key is configured in `.env`, or rely on the validated local fallback mode.

---

### P2 — Medium-Priority Architectural Constraints

#### GAP-06: Hardcoded RAG Routing Dictionaries
- **Category:** Retrieval Architecture.
- **Affected Artifacts:** `apps/api/mira/agent.py` lines 210–245 (`retrieve()`).
- **Evidence:** Policy queries rely on literal keyword checks (`"cancellation" -> ["P02"]`, `"children" -> ["P03"]`) rather than semantic embeddings.
- **Impact:** Unanticipated phrasing (e.g., "What happens if I pull out?") might bypass the keyword filter.
- **Remediation:** Integrate a lightweight vector retrieval model (e.g., ChromaDB with sentence-transformers).

#### GAP-07: Custom Itinerary Hotel Tier Averaging
- **Category:** Pricing Engine Rigor.
- **Affected Artifacts:** `apps/api/mira/data.py` (`PricingEngine.calculate_custom_quote`).
- **Evidence:** Published tours bind to specific contracted hotels (H01–H15). Custom itineraries apply a flat blended average rate ($120 standard / $180 luxury) rather than resolving specific contracted properties.
- **Impact:** Slight variance from true contracted rate when custom itineraries are designed.
- **Remediation:** Allow custom planners to select specific contracted hotels per night.

#### GAP-08: Generalization Vulnerability in Prompt Injection Defense
- **Category:** Security.
- **Affected Artifacts:** `apps/api/mira/data.py` (`public_text`).
- **Evidence:** Sanitization relies on removing HTML comments and blacklisting P06. Sophisticated non-HTML prompt injections are not semantically filtered.
- **Impact:** Low in current dataset; moderate in production with user-submitted reviews.
- **Remediation:** Deploy an LLM guardrail classification check on all retrieved text.

#### GAP-09: Tour T06 Knuckles Camping Scope Mismatch
- **Category:** Content Consistency.
- **Affected Artifacts:** `ceylon-compass-dataset/content/tours/t06_knuckles_cloud_forest_trek.md`.
- **Evidence:** Narrative mentions overnight camping; rate sheet contains only 1-day trek rates.
- **Impact:** Travellers requesting camping must be manually routed to staff.
- **Remediation:** Clarify in the tour description that camping is an uncontracted bespoke request.

#### GAP-10: Lack of Discrete Date Picker in Conversational UI
- **Category:** UX Friction.
- **Affected Artifacts:** `apps/ceylon-compass/src/routes/index.tsx`.
- **Evidence:** Travellers must type travel dates in chat (`2026-12-05`). Ambiguous natural language strings require clarification turns.
- **Impact:** Minor delay during quick booking.
- **Remediation:** Embed an interactive calendar date-picker chip in the `TripDiscovery` surface.

#### GAP-11: Large Group (>15 Pax) Bus Charter Rates Missing
- **Category:** Edge-Case Pricing.
- **Affected Artifacts:** `rate_sheet_2026-27.xlsx` Sheet `Vehicles`.
- **Evidence:** Workbook specifies Sedan, Van, and Mini-Coach (up to 15 pax). Groups $>15$ have no automated vehicle rate.
- **Impact:** Large groups must be handled as bespoke staff quotes.
- **Remediation:** Handled correctly by R6 missing rate rule; document explicitly in assumptions.

---

### P3 — Low-Priority Cosmetic & Non-Blocking Gaps

#### GAP-12: Absence of Dual-Currency Display (USD / LKR)
- **Category:** UI Polish.
- **Evidence:** Quotes display exclusively in USD. Displaying approximate LKR equivalents would enhance local authenticity.

#### GAP-13: HTTP Polling vs Full WebSocket / SSE Transport
- **Category:** Network Architecture.
- **Evidence:** AG-UI events stream over standard HTTP chunked transfer rather than bidirectional WebSockets. Sufficient for chat, but less optimal for high concurrency.

#### GAP-14: Mobile Viewport Overflow on Complex Itinerary Tables
- **Category:** Responsive Design.
- **Evidence:** The 7-day itinerary comparison table horizontally scrolls on mobile viewports $<375$px.
