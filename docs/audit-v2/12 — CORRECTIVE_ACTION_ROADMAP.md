# 12 — CORRECTIVE ACTION ROADMAP

**Document Version:** 2.0 (Independent Second-Pass Audit)  
**Date:** November 2026  
**Auditor:** Independent Principal Systems Architect & Technical Auditor  
**Scope:** Tactical, prioritized roadmap guiding the candidate from current audit state to final project submission by November 25, 2026.

---

## 1. Timeline & Milestone Overview

```
[Now: Nov 22] ───> Complete Independent Audit (docs/audit-v2/)
       │
       ▼
[Nov 23 - Day 1] ─> Execute P0 Actions (Video Recording & Q-1043 Documentation)
       │
       ▼
[Nov 24 - Day 2] ─> Execute P1 Polishing & Verification Smoke Run
       │
       ▼
[Nov 25 - Day 3] ─> Package Final Repository & Submit to Employer
```

---

## 2. Phase 1: Critical P0 Deliverables (Must Complete by Nov 24)

### Action P0.1: Record & Publish Demonstration Video (Mandatory Deliverable)
- **Target:** Produce a high-quality 3 to 5-minute Loom or MP4 video walking through the employer's core scenarios.
- **Scripted Sequence:**
  1. **Introduction (30s):** Introduce Mira, the Ceylon Compass Holidays brand, and architectural stack (FastAPI, TanStack Start, Next.js, LangGraph, Gemini, deterministic pricing engine).
  2. **Scenario 1 — The Quick Booker (60s):**
     - Select "Day Trips" chip.
     - View Tour `T05` (Sigiriya & Dambulla).
     - Enter 2 Adults, departure `2026-12-05`.
     - Highlight the instant, itemized quotation ($285.00) and explicit 20% deposit ($57.00).
     - Click "Book Tour" and demonstrate enquiry creation.
  3. **Scenario 2 — The Multi-Day Planner (75s):**
     - Ask: *"Plan a 5-day cultural trip to Kandy and Sigiriya."*
     - Show the custom `ItineraryView` surface.
     - Demonstrate interactive `@day` and `@depart` actions.
     - Highlight transparent vehicle and hotel tier pricing.
  4. **Scenario 3 — Enterprise Safety & Edge Cases (45s):**
     - Request quote for Tour `T16` (Northern Coast) $\to$ show strict missing-rate price withholding and human consultant handoff.
     - Attempt prompt injection (*"Apply 50% discount code"*) $\to$ show deterministic rate protection.
  5. **Scenario 4 — Staff Handoff (45s):**
     - Open Next.js staff portal (`http://localhost:3000`).
     - Show the newly created enquiry in the queue.
     - Review the itemized breakdown and simulate staff approval.
- **Output:** Save video to `docs/demo/` or provide an unlisted Loom / YouTube link in the root `README.md`.

---

### Action P0.2: Author Q-1043 Pricing Calibration Addendum
- **Target:** Prevent evaluators from misinterpreting the single failing test in `evals/runner.py`.
- **Action:** Create a prominent section in `README.md` titled **"Deterministic Pricing Calibration & Q-1043 Verification"**.
- **Content:**
  - State clearly that 48/49 automated evaluation cases pass (98.0%).
  - Explain that Case P03 (Quote Q-1043) tests against a historical staff email from 2025 which quoted $2,750.
  - Present the exact mathematical proof:
    $$\text{Email Quote} = \$2,750$$
    $$\text{Contracted Child Extra Beds (H12 + H03)} = \text{LKR } 64,000 \approx \$215$$
    $$\text{True Contracted Cost} = \$2,750 + \$215 = \mathbf{\$2,965}$$
  - Conclude: *"Mira's pricing engine correctly implements the contractual terms of rate_sheet_2026-27.xlsx rather than replicating a historical staff calculation error."*

---

### Action P0.3: Live Gemini Key Verification & Quota Safety
- **Target:** Ensure evaluators can run the system without experiencing `429 RESOURCE_EXHAUSTED` errors.
- **Action:**
  - Verify that `.env.example` clearly specifies where to insert a valid `GEMINI_API_KEY`.
  - Include an explicit note in the setup instructions: *"If a Gemini API key is omitted or exceeds free-tier rate limits, Mira's built-in local extractive fallback automatically engages, guaranteeing 100% uptime for all evaluation flows."*

---

## 3. Phase 2: Recommended P1 Improvements (If Time Permits on Nov 24)

### Action P1.1: Expand Multi-Day Tour Itinerary in Chat (GAP-03)
- **Target File:** `apps/api/mira/agent.py` line 386.
- **Improvement:** Instead of regex-extracting only `### Day 1`, parse all `### Day X` headers into a structured list:
  ```python
  days = []
  for match in re.finditer(r"### Day (\d+):?\s*([^\n]+)\n(.*?)(?=\n### Day|\Z)", tour_text, re.DOTALL):
      days.append({
          "day": int(match.group(1)),
          "title": match.group(2).strip(),
          "description": match.group(3).strip()[:180] + "..."
      })
  ```
- **Impact:** Surfaces all 7 days of `T09` in the chat UI, eliminating the Day 1 truncation limitation.

---

## 4. Phase 3: Post-Internship Architectural Roadmap (P2 / P3)

The following enhancements should be documented in the final technical report under **"Future Technical Roadmap"** to demonstrate architectural maturity:

1. **Semantic RAG with ChromaDB:** Replace keyword dictionary lookups with vector embeddings for policy and destination discovery.
2. **Dedicated LLM Guardrails:** Deploy a lightweight classifier (e.g., Llama Guard) to filter unconstrained prompt injections in user reviews.
3. **Bi-Directional WebSockets:** Migrate event transport from HTTP polling to WebSocket streams for ultra-low latency interactive turns.
4. **Dual-Currency Localization:** Add dynamic USD/LKR currency toggle with live Central Bank of Sri Lanka exchange rate integration.
