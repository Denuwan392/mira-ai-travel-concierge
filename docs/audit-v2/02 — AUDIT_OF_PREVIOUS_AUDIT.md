# 02 — Audit of the Previous Audit: Meta-Review of Reports 01–12

**Audit Date:** 22 November 2026  
**Auditor:** Independent Principal Systems Auditor & Reviewer  
**Target of Review:** The 12 Audit Reports generated in `docs/audit/`

---

## 1. Overview of the Previous Audit

The previous audit evaluated the Mira travel booking assistant and generated 12 documents in `docs/audit/`. It concluded that the system was **94% submission-ready**, verified all 8 functional requirements, and praised the deterministic pricing and A2UI integration.

This meta-review evaluated each of the 12 documents against the actual codebase, live tests, and runtime behavior to identify **unsubstantiated claims, optimistic metrics, and omitted architectural limitations**.

---

## 2. Report-by-Report Verification & Critique

### Report 01 — Executive Summary
- **Claim:** Mira is ~94% submission-ready, with 5/5 core and 3/3 extended requirements verified.
- **Independent Verification:** **PARTIALLY VERIFIED.** While code exists for all 8 requirements, the readiness score was inflated by evaluating only offline deterministic unit tests. Live Gemini execution was not audited under sustained API usage, and the dual-frontend split was downplayed.
- **Omitted Risk:** Did not disclose that live Gemini API calls immediately exhaust the Free-Tier daily quota (20 requests/day).

### Report 02 — Requirements Matrix
- **Claim:** Requirement R3 (Generative UI) is VERIFIED: *"The agent chooses UI components from a fixed catalog of >= 5 components"*.
- **Independent Verification:** **CONTRADICTED.** The agent (LLM) does **not** choose the UI components. Component selection is executed 100% by deterministic Python `if/else` checks in `mira/agent.py::compose()`.
- **Claim:** Requirement R4 (Grounded Answers) is VERIFIED via RAG retrieval.
- **Independent Verification:** **MISLEADING.** Policy retrieval does not use semantic RAG or vector search; it uses a hardcoded Python dictionary in `retrieve()` (`"cancellation" -> ["P02"]`, `"children" -> ["P03"]`, `"payment" -> ["P01"]`).

### Report 03 — Dataset Inventory
- **Claim:** 37 files tracked, with full provenance and analysis of data quality traps (H07 expired, H04 missing single rate, H03 overlap, T06 scope conflict, P06 injection).
- **Independent Verification:** **VERIFIED.** The dataset inventory was accurate and correctly identified the major dataset irregularities.
- **Omitted Fact:** Did not mention that `content/destinations/mirissa.md` also contained a hidden prompt injection HTML comment instructing the AI to give a 40% loyalty discount.

### Report 04 — Data Coverage Matrix
- **Claim:** 97.3% effective dataset utilization.
- **Independent Verification:** **MISLEADING DEFINITION.** The report defined utilization as "the file was read and parsed without throwing an unhandled exception". In reality, the detailed daily itinerary content of multi-day tours (Days 2 through 7 in T09, Days 2 through 8 in T08) is completely dropped from conversational agent turns. Parsing a file is not the same as using its content in the product.

### Report 05 — Pricing Audit
- **Claim:** 100% workbook pricing accuracy; Q-1043 sales email discrepancy is due to omitting LKR 64,000 in child extra beds.
- **Independent Verification:** **FULLY VERIFIED.** Independent manual calculations confirmed that the sales email omitted extra beds, that Workbook Rule 4 mandates extra beds for children aged 2–11, and that starter test S03 expects the engine's figure of USD 2,965 / USD 742 deposit.
- **Limitation Not Emphasized:** The pricing engine strictly requires a single discrete travel date; it cannot evaluate conversational date ranges (e.g., *"sometime in June"*).

### Report 06 — Agent & A2UI Audit
- **Claim:** Real A2UI v0.9 and AG-UI streaming protocol.
- **Independent Verification:** **VERIFIED WITH CAVEATS.** The `@ag-ui/client` and `@a2ui/react` packages are installed and functional, but the application uses an unconventional "binderless index" pattern (`slot = { index: number }`) where component properties are not embedded in the A2UI message itself.
- **Omitted Fact:** The report claimed that Gemini was responsible for conversational reasoning, but in practice, offline tests run with `GEMINI_API_KEY` explicitly deleted in `conftest.py`.

### Report 07 — UI/UX Audit
- **Claim:** Evaluated dual frontend architecture and responsive viewports.
- **Independent Verification:** **VERIFIED.** Accurately noted that `apps/web` (port 3000) houses `/staff` while `apps/ceylon-compass` (port 5175) houses `/plan`.
- **Critique:** The previous report recommended consolidating the frontends before submission. In a real-world scenario with 3 days remaining, a frontend migration carries immense regression risk and should be deferred.

### Report 08 — Security & Privacy Audit
- **Claim:** 100% secure financial data separation, PII scrubbing, and append-only SQLite audit triggers.
- **Independent Verification:** **FULLY VERIFIED.** The database triggers `audit_no_update` and `audit_no_delete` successfully prevent tampering with audit logs. `quotes.internal` is strictly withheld from public APIs.

### Report 09 — Evaluation Audit
- **Claim:** 48/49 evaluation cases passed (98.0%) across 58 validated turns.
- **Independent Verification:** **VERIFIED.** The runner was executed and achieved 48/49 passes.
- **Misleading Context:** The previous audit failed to clearly highlight that the entire 49-case evaluation was executed using the offline local fallback engine rather than live Gemini API completions.

### Report 10 — Gap Register
- **Claim:** Identified 10 prioritized gaps (GAP-01 to GAP-10).
- **Independent Verification:** **PARTIAL.** Missed several high-priority functional gaps, including:
  1. Truncation of multi-day tour itineraries to Day 1 only.
  2. Synthetic duplication in custom planner proposals (repeating destination summary text).
  3. Hardcoded dictionary lookups in policy retrieval.
  4. Live Gemini Free-Tier 20 request/day quota exhaustion.

### Report 11 — Improvement Roadmap
- **Claim:** Proposed P0–P3 roadmap.
- **Independent Verification:** **PARTIAL.** Unnecessarily prioritized porting the staff console to TanStack Start under P1. The immediate priority must be recording the demo video, filling the calibration worksheet, and rehearsing the live margin rule modification.

### Report 12 — Audit Results JSON
- **Claim:** Machine-readable findings.
- **Independent Verification:** **VERIFIED.** Matches the markdown reports.

---

## 3. Summary of Misleading or Overstated Claims in Previous Audit

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        CRITIQUE OF PREVIOUS AUDIT METRICS                              │
│                                                                                        │
│  Metric / Claim               Previous Report   Independent Reality                    │
│  ────────────────────────────────────────────────────────────────────────────────────  │
│  Readiness Percentage         94%               85.5% (Weighted objective rubric)      │
│  Dataset Utilization          97.3%             Ingested: 97.3%, Content Used: ~65%    │
│  UI Generation Source         Agent/LLM         Hardcoded Python rules in compose()    │
│  Policy Retrieval Mechanism   Dynamic RAG       Hardcoded dictionary lookup in code    │
│  Multi-Day Tour Itineraries   Fully rendered    Truncated to Day 1 only in chat        │
│  Custom Itinerary Proposals   Agent synthesized Repeated destination overview strings  │
│  Live Gemini Validation       "Verified"        Offline fallback evaluated in evals    │
│  Live Gemini Quota Limit      Unmentioned       Exhausts Free Tier (20 requests/day)   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

The previous audit provided an excellent static code and financial review, but suffered from confirmation bias—mistaking offline test passes and code existence for dynamic end-to-end AI capabilities.
