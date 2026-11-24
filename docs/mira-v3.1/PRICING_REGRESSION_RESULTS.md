# Pricing Regression Results — Financial Integrity Verification

This document provides independent verification of pricing calculations across sample quotes Q-1041 through Q-1044, child extra bed formulas, group size tiers, and missing rate handling.

---

## 1. Independent Sample Quote Computations

### Q-1041: Sigiriya and Minneriya Day Tour from Kandy (T01)
- **Parameters**: 2 adults, departure 10 January 2027.
- **Cost Breakdown**:
  - Guide: LKR 9,000
  - Vehicle (Car): LKR 18,000
  - Entrance: LKR 33,000 ($2 \times 16,500$)
  - Meals: LKR 6,000 ($2 \times 3,000$)
  - **Total Cost**: **LKR 66,000**
- **Margin & Currency Conversion**:
  - Net cost converted with markup formula yields **USD 315**.
  - Deposit: Day tour rule mandates **100% deposit = USD 315**.
- **Runtime Verification**: `apps/api/tests/test_pricing.py` and `test_scenario_01_t01_quick_booker` confirm **USD 315 total / USD 315 deposit**.

---

### Q-1042: Cultural Triangle Sri Lanka Package (T09)
- **Parameters**: 2 adults, departure 03 May 2027 (Standard Season).
- **Cost Breakdown**:
  - Guide: LKR 66,500 ($7 \times 9,500$)
  - Vehicle (Car): LKR 126,000 ($7 \times 18,000$)
  - Entrance: LKR 76,000 ($2 \times 38,000$)
  - Meals: LKR 63,000 ($2 \times 7 \times 4,500$)
  - Hotels: LKR 146,000 (6 nights double room)
  - **Total Cost**: **LKR 477,500**
- **Selling Price & Deposit**:
  - **Total: USD 2,125**
  - Departure >30 days $\implies$ **25% deposit: USD 532** (Balance $1,593 due 30 days prior).

---

### Q-1043: Cultural Triangle Sri Lanka Package (T09) — Family Reconciliation
- **Parameters**: 2 adults, 2 children (aged 7 and 10), departure 12 April 2027 (High Season).
- **Workbook Calculation**:
  - Guide: LKR 66,500
  - Vehicle (Mini-van for 4 pax): LKR 182,000 ($7 \times 26,000$)
  - Entrance: LKR 114,000 (2 adults $\times$ 38,000 + 2 children $\times$ 19,000)
  - Meals: LKR 94,500 (2 adults $\times$ 31,500 + 2 children $\times$ 15,750)
  - Hotel Double Room: LKR 146,000
  - **Child Extra Beds (Policy P03 & Hotel Rate Sheet)**:
    - 2 children $\times$ 6 nights $\times$ LKR 5,333/night = **LKR 64,000**.
  - **Total Cost**: $477,500 + 56,000 + 38,000 + 31,500 + 64,000 = \mathbf{LKR\ 667,000}$.
- **Selling Price**: **USD 2,965** · **Deposit: USD 742** (25%).
- **Reconciliation with Historical Sales Email**:
  - The historical email quoted $2,680 by failing to add the LKR 64,000 extra bed buy cost.
  - The workbook formula and employer test case `S03` both confirm **USD 2,965 / USD 742**.

---

### Q-1044: Highlights of Sri Lanka (T08)
- **Parameters**: 2 adults, departure 01 December 2026.
- **Cost Breakdown**: Total cost LKR 563,000 $\implies$ **USD 2,505**.
- **Deposit**: Departure is within 30 days of booking window $\implies$ **100% deposit = USD 2,505**.

---

## 2. Treasures of Sri Lanka (T12) Verification

- **2 Adults Sharing (Double Room)**:
  - Total: **USD 4,550**
  - Deposit: **USD 1,138** (25%)
  - Status: Valid verified quote with booking action.
- **1 Adult (Solo Traveler)**:
  - Status: Withheld (`Unavailable: missing_amount`).
  - Reason: Single-room supplement missing in workbook contract rows.
  - UI Component: `Notice` with specialist referral.

---

## 3. Financial Privacy & Non-Leakage
- Public API responses (`/api/agent`, `/api/quotes`, `/api/sources/{id}`) were verified to ensure internal buy costs (LKR totals), guide day-rates, vehicle base rates, and gross profit margins are strictly omitted from traveller-facing payloads.
- Verified in `apps/api/tests/test_extended_security.py::test_public_api_never_exposes_internal_finances`.
