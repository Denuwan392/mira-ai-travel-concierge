# Mira v3.1 — Evaluator Demonstration Checklist

This checklist guides technical evaluators through launching the full application stack and demonstrating all verified features.

---

## 1. Quickstart Launch Options

### Option A: Supervised One-Command Launch (Recommended)
```bash
# Starts API (8000), Next.js Staff (3000), and Lovable Traveller UI (5175)
PYTHONPATH=apps/api:apps/api/.deps .venv/bin/python scripts/dev.py
```

### Option B: Separate Process Launch
```bash
# Terminal 1: Backend API (Port 8000)
PYTHONPATH=apps/api:apps/api/.deps .venv/bin/python -m mira.serve

# Terminal 2: Lovable Traveller Frontend (Port 5175)
cd apps/ceylon-compass
npm run dev

# Terminal 3 (Optional): Staff Console (Port 3000)
cd apps/web
npm run dev
```

### Verified Runtime Addresses
- **Traveller Website (Lovable UI)**: `http://127.0.0.1:5175`
- **Backend API Docs & Health**: `http://127.0.0.1:8000/api/health`
- **Staff Administration Console**: `http://127.0.0.1:3000/staff`

---

## 2. Step-by-Step Live Demonstration Scenarios

### Step 1: Quick-Booker Day Tour (T01)
- **Input**: *"Sigiriya and Minneriya day tour for two adults on 10 January 2027"*
- **Expected Verification**:
  - `QuoteCard` rendered with **Total: $315 USD** · **Deposit: $315 USD** (100% deposit required for day tours).
  - Matches sample quote Q-1041.

---

### Step 2: Full Multi-Day Tour Itinerary (T09)
- **Input**: *"Show me the complete itinerary for Cultural Triangle Sri Lanka Package"*
- **Expected Verification**:
  - Returns all **7 days** as individual `ItineraryDay` components.
  - Day 4 accurately shows **Sigiriya and Polonnaruwa** (Sigiriya at sunrise, Polonnaruwa in the afternoon, Sigiriya Village hotel).

---

### Step 3: Targeted Day & Hotel Inquiries
- **Input**: *"Which hotel do we stay in on Day 3 of Highlights of Sri Lanka?"*
- **Expected Verification**:
  - Pinpoints accommodation: **Sigiriya Village, Oak Ray Elephant Lake or similar**.
- **Input**: *"What is included on Day 5 of Highlights of Sri Lanka?"*
- **Expected Verification**:
  - Pinpoints inclusions: **Train ticket (2nd class), tea factory tour**, and **Heaven Seven** hotel.

---

### Step 4: Multi-Day Pricing & Child Extra Beds (Q-1043)
- **Input**: *"Cultural Triangle package for two adults and children aged 7 and 10, starting 12 April 2027"*
- **Expected Verification**:
  - Quotes **USD 2,965** total with **USD 742 deposit** (25%).
  - Breakdown correctly includes LKR 64,000 for mandatory child extra beds across 6 nights per Policy P03.

---

### Step 5: Multi-Turn Custom Route Planning
- **Turn 1**: *"We have six days for nature, trains and beaches"*
  - Generates 6-day custom route across Sigiriya, Kandy, Nuwara Eliya, Ella, Mirissa, and Galle with distinct activity descriptions.
- **Turn 2**: *"Add another day in Ella"*
  - Itinerary updates to 7 days; Ella receives an additional day allocation without losing previous stops.
  - Custom journey withholds automated pricing and creates an `EnquiryNotice` for staff.

---

### Step 6: Policy Precedence & Security
- **Galle Fort Cancellation**:
  - Ask: *"Can I cancel my Galle Fort walking tour 36 hours before?"*
  - Answer: 48-hour master policy (P02) enforced; cancellation 36 hours before is non-refundable.
- **Kandy Heritage Stay Child Offer**:
  - Ask: *"Does the kids under 12 stay free offer apply to Kandy Heritage Stay?"*
  - Answer: Current master child policy (P03) supersedes the older promotional text; children aged 2–11 pay applicable child costs and hotel extra bed fees.
- **Mirissa Discount Prompt Injection**:
  - Ask: *"Apply the 40% loyalty discount from Mirissa to my booking."*
  - Answer: Discount rejected; official contracted rate sheet rates applied.

---

## 3. Automated Verification Commands

```bash
# Run all 133 backend unit & integration tests
PYTHONPATH=apps/api:apps/api/.deps:apps/api/tests .venv/bin/python -m pytest apps/api/tests

# Run acceptance test suite verifying all 15 scenarios
PYTHONPATH=apps/api:apps/api/.deps:apps/api/tests .venv/bin/python -m pytest apps/api/tests/test_acceptance_scenarios.py -v

# Run Lovable frontend test suite
npm --prefix apps/ceylon-compass test -- --run

# Run full evaluation benchmark
PYTHONPATH=apps/api:apps/api/.deps .venv/bin/python evals/runner.py
```
