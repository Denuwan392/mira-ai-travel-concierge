# Comprehensive Evaluation Benchmark Results

This document records the exact, reproducible evaluation results across the full test and benchmark suite for Mira v3.

---

## 1. Overall Test Execution Summary

| Suite / Benchmark | Tool / Runner | Total Cases / Tests | Passed | Failed | Pass Rate |
|-------------------|---------------|:-------------------:|:------:|:------:|:---------:|
| **Backend Unit & Integration Tests** | `pytest apps/api/tests` | 118 | 118 | 0 | **100.0%** |
| **Mira v3 Core Acceptance Tests** | `pytest apps/api/tests/test_mira_v3.py` | 9 | 9 | 0 | **100.0%** |
| **Itinerary Parser Tests** | `pytest apps/api/tests/test_itinerary_parser.py` | 4 | 4 | 0 | **100.0%** |
| **Lovable Frontend Tests** | `vitest apps/ceylon-compass` | 33 | 33 | 0 | **100.0%** |
| **Lovable Frontend Build** | `vite build (Nitro SSR)` | Full App | Done | 0 | **100.0%** |
| **System Evaluation Benchmark** | `python evals/runner.py` | 49 | 48 | 1* | **98.0%** |

*\*Note on Evaluation Case P03*: As documented in `evals/report/report.json` and `PRICING_SAFETY.md`, P03 tests against the uncorrected sample email Q-1043 which omitted child extra beds ($2,680). The official rate sheet formulas yield $2,965, matching employer starter case S03.

---

## 2. Evaluation Suite Breakdown by Category (`evals/runner.py`)

- **Total Test Turns Evaluated**: 58 turns across 49 test conversations.
- **Valid UI Turns**: **58 / 58 (100.0%)** validated against Pydantic schemas.
- **Multi-Turn Conversations**: 7 distinct multi-turn dialogs.
- **Employer Starter Cases**: 17 cases.
- **Authored Verification Cases**: 32 cases.

### Category Results:
1. **Discovery (S01, D01–D03)**:
   - 4 / 4 passed (100%).
   - Verified relevant tour cards and destination previews surfaced with grounded citations.
2. **Pricing & Quotes (S02, S03, S15, P01, P02, P04, P07–P12, P14, P15)**:
   - 14 / 15 passed (93.3% — only P03 differs due to the child extra bed discrepancy).
   - Validated day tour 100% deposit, multi-day 25% deposit, and currency conversions.
3. **Rates & Missing Rate Safety (S04–S06, S11, P05, P06, P13, P16)**:
   - **8 / 8 passed (100%)**.
   - Strictly zero invented prices for unpriced tours (T10, T11, T12, T16) and custom routes.
4. **Grounding & Citations (S07–S10, S16, S17, G01–G04)**:
   - 10 / 10 passed (100%).
   - All citations match existing canonical markdown source IDs.
5. **Multi-Turn Route Adjustments (S13, M01–M05)**:
   - 6 / 6 passed (100%).
   - Verified conversational additions ("Add day in Ella"), reductions, and duration modifications.
6. **Safety, Off-Topic & Adversarial Defense (S12, S14, X01–X04)**:
   - 6 / 6 passed (100%).
   - Rebuffed prompt injections (40% discount hack), off-topic coding questions, and policy manipulations.

---

## 3. Mandatory Acceptance Scenarios Verified in `test_mira_v3.py`

1. **Quick Booker Scenario**: Day tour (T01 Sigiriya) priced immediately with 100% deposit requirement ($240 USD) and `QuoteCard`.
2. **Multi-Day Published Tour**: T08 Highlights of Sri Lanka priced with 25% deposit ($545 USD) and full day-by-day itinerary.
3. **Multi-Day Full Itinerary Query**: T09 Cultural Triangle full itinerary requested; all 7 days surfaced with structured `ItineraryDay` components.
4. **Day-Specific Query**: "What happens on Day 4 of T09?" correctly returns Day 4 Sigiriya morning climb and Habarana village tour.
5. **Family Quote Q-1043 Reconciliation**: 2 adults + 2 children on T09 computes $2,965 ($742 deposit) adhering to mandatory child extra bed fees.
6. **Custom Multi-Day Route Planning**: 6-day journey across Sigiriya, Kandy, Nuwara Eliya, Ella, Mirissa, Galle generates 6 distinct, non-repetitive activity descriptions.
7. **Custom Route Pricing Withholding**: Custom multi-day route refuses to invent prices and generates an `EnquiryNotice`.
8. **Cancellation Policy Precedence**: Galle Fort day tour (T04) enforces strict 48-hour cancellation cut-off (P02).
9. **Prompt Injection Defense**: 40% loyalty discount injection on Mirissa Whale Watching is rejected with standard rates applied.
10. **Draft Tour Isolation**: T15 Northern Sri Lanka cannot be booked or priced; draft status is explained and enquiry offered.
