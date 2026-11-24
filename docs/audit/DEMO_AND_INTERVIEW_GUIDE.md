# Live Technical Demo & Interview Defense Guide

> **Document Purpose:** Complete, step-by-step interview rehearsal script and defense manual for the Ceylon Compass Holidays / Mira project. Grounded in actual terminal commands, endpoints, and architectural principles.

---

## 1. Quick-Start Commands & Rehearsal Setup

### Step 1: Environment & Dependency Preparation
Ensure Node.js 22+, Python 3.13, and `uv` are available.

```bash
# Verify environment
python3 --version
node -v

# Activate python virtual environment
source .venv/bin/activate
export PYTHONPATH=apps/api
```

### Step 2: Start All Three Services with Make
The repository includes a unified Make supervisor that launches Vite (port 5175), Next.js (port 3000), and FastAPI (port 8000) concurrently:

```bash
make dev
```

*URLs to have open in your browser tabs:*
1. **Travel Workspace (Primary):** `http://127.0.0.1:5175/workspace/index.html`
2. **Staff Operations Console:** `http://127.0.0.1:5175/staff` (or `http://127.0.0.1:3000/staff`)
3. **FastAPI Interactive Docs:** `http://127.0.0.1:8000/docs`

---

## 2. Step-by-Step Live Demo Script

---

### Demo Scenario 1: Quick-Booker Flow (Deterministic Pricing in Action)
**Goal:** Show how conversational intent translates into a mathematically guaranteed quote.

1. **Navigate:** Open `http://127.0.0.1:5175/workspace/index.html#/tours`.
2. **Action:** Click **"Sigiriya and Minneriya Day Tour from Kandy"** (`T01`).
3. **Form Setup:**
   - Travel Date: `2027-01-10`.
   - Adults: `2` $\to$ click the `+` button twice to select `4` adults.
   - Children: `0`.
4. **Click:** **"Get verified quote"**.
5. **Point Out to the Interviewer:**
   - *"Notice the spinner says 'Checking verified rates for 4 adults...'."*
   - *"The returned price is USD 540 (Deposit USD 540, Balance USD 0). Let's prove where this number comes from: The contract vehicle for 4 adults is a Passenger Van at LKR 38,000/day, guide is LKR 8,000, 4 entrance fees are LKR 60,000, and 4 lunches are LKR 10,000. Total LKR 116,000. Divided by 300 FX times (1 - 0.284 margin) rounded up to 5 USD steps gives exactly USD 540."*
   - *"The LLM did not calculate this. Our Python pricing engine did."*

---

### Demo Scenario 2: Real-Time Quote Invalidation & Guardrails
**Goal:** Prove that stale prices cannot be abused.

1. **Action:** With the USD 540 quote displayed, click the `-` button on Adults (reducing from 4 to 3).
2. **Point Out to the Interviewer:**
   - *"Look immediately below: an amber banner appears: 'Quote Outdated — Configuration Changed'."*
   - *"Notice the 'Mock booking' button is instantly disabled. The system refuses to let a user book 3 adults for the 4-adult quote or vice versa."*
   - *"Clicking 'Recalculate quote' re-runs the deterministic engine for 3 adults."*

---

### Demo Scenario 3: Missing Rates & Specialist Referral
**Goal:** Show what happens when rates are missing or expired without hallucination.

1. **Navigate:** Go back to Tours and select **"Highlights of Sri Lanka"** (`T08`).
2. **Action:** Set Date: `2027-01-10`, Adults: `2`. Click "Get verified quote".
3. **Point Out to the Interviewer:**
   - *"Notice Mira does not make up a price. Because hotel rates for this package are uncontracted for this specific season, the pricing engine raised an `Unavailable` exception."*
   - *"Mira displays: 'We can’t verify an automated price for these travel dates right now. A travel specialist will confirm the details. I’ve saved a private enquiry for our team.'."*
   - *"Clicking 'View enquiry status' shows the enquiry ID recorded in our backend database."*

---

### Demo Scenario 4: Mock Payment & Booking Confirmation
**Goal:** Show the simulated booking lifecycle.

1. **Action:** On a verified quote (e.g. `T01`), open the Mock booking scenario dropdown.
2. **Test Failure First:** Select `"declined"` and click "Try mock booking".
   - An amber/red alert appears: *"Booking declined: Card authorization declined by issuer."* No booking row is added to the database.
3. **Test Success:** Select `"success"` and click "Try mock booking".
   - Status updates to green: **"Status: confirmed"**. Confirmation ID is emitted.
   - Database table `bookings` now links this verified quote to a confirmed reservation.

---

### Demo Scenario 5: Staff Operations & Trace Inspection
**Goal:** Show how the commercial and telemetry layers operate behind the scenes.

1. **Navigate:** Open `http://127.0.0.1:5175/staff` in another tab.
2. **Inspect Enquiries:**
   - Click the **Enquiries** tab.
   - Point to the top row: *"Here is the private enquiry created by our previous quote interaction. Notice that staff can see internal finance: Total Buy Cost (LKR 116,000), Target Margin (28.4%), and Realized Gross Profit (USD 153.33). None of this internal cost data was ever exposed to the guest."*
3. **Inspect Trace:**
   - Expand the **Trace** accordion.
   - Point out the stage execution latencies: `interpret (0ms)`, `retrieve (1ms)`, `quote (1ms)`, `save (2ms)`.
   - Explain that each turn carries an `X-Trace-Id` header correlating the browser network request to this exact SQLite record.

---

### Demo Scenario 6: Content Governance (Editor $\to$ Approver Publication)
**Goal:** Show strict role-based access control and content review.

1. **Login as Editor:** Log in with editor token or account.
2. **Create Draft:** In Content Review, enter: *"Prepare a private itinerary using published Ella material."* Click "Create Draft".
   - Draft `D-xxx` is created with status `draft`.
   - Explain: *"This draft is strictly isolated in the `drafts` table. If a traveller asks Mira for this tour right now, RAG returns 404 because it is unpublished."*
3. **Try Unauthorized Publication:** Show that the Editor has no "Publish" button (or clicking returns 403 Forbidden).
4. **Login as Approver:** Switch credentials to the Approver role.
5. **Approve & Publish:** Click "Approve Content", then "Approve & Publish".
   - Status transitions to `published`.
   - The database trigger writes an immutable event into `audit`.
   - The tour immediately becomes active in the public catalog!

---

### Demo Scenario 7: Running the Test & Evaluation Suites
**Goal:** Show production-grade automated verification.

```bash
# 1. Run full FastAPI backend pytest suite (162 tests)
PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests

# 2. Run React frontend Vitest suite (46 tests)
npm --prefix apps/ceylon-compass test

# 3. Run Playwright End-to-End browser suite (8 integration tests)
./scripts/test-workspace.sh

# 4. Run deterministic evals benchmark (54 cases)
PYTHONPATH=apps/api .venv/bin/python evals/runner.py
```

---

## 3. Top Interview Questions & Concise Answers

### Q1: "Why did you use LangGraph instead of a simple OpenAI or Claude completion API?"
> **Answer:**  
> *"In a multi-turn booking assistant, conversational state must be explicitly managed as a deterministic state machine rather than relying on unstructured LLM prompt loops. LangGraph allows us to define rigid nodes (`interpret`, `retrieve`, `quote`, `compose`, `save`) and conditional routing edges (`quote_route`). If critical booking parameters (tour, date, adult count) are missing, execution deterministically bypasses pricing and asks for clarification. Most importantly, it allows us to decouple entity extraction from financial calculation so the model never does math."*

---

### Q2: "How do you guarantee that Mira never hallucinates a tour price?"
> **Answer:**  
> *"Through architectural separation of concerns. In `agent.py`, the `quote` node does not pass prompts to an LLM. Instead, it invokes `mira.data.price()`, a pure Python function that queries an immutable snapshot of our contracted Excel rate sheets using Python's `Decimal` library. The model only receives the pre-calculated quote DTO to assemble the final A2UI turn. If a rate is missing, expired, or ambiguous, the pricing function raises an `Unavailable` exception, which gracefully triggers an enquiry notice instead of a price."*

---

### Q3: "What is A2UI and why not just stream plain text markdown?"
> **Answer:**  
> *"A2UI stands for Agent-to-User Interface. Modern booking assistants shouldn't force users to read walls of text when selecting holidays. A2UI uses Server-Sent Events to stream typed JSON payloads representing rich interactive React components—such as `TourCard`, `PriceBreakdown`, `TravellerPicker`, and `BookingForm`. This gives the traveller interactive date pickers and increment buttons while preserving complete conversational history in the same stream."*

---

### Q4: "What is the difference between a quote, an enquiry, and a booking?"
> **Answer:**  
> *"A **quote** is a verified, point-in-time price calculation for an exact party configuration and travel date. An **enquiry** is a private lead saved in SQLite for human staff follow-up, automatically created whenever a quote is computed, when rates are unavailable, or for bespoke multi-day itineraries. A **booking** in this project is a simulated reservation linking an active quote to a confirmation ID via `POST /api/bookings/mock` without live payment processing."*

---

### Q5: "How does the system handle concurrent users or race conditions when modifying trip options?"
> **Answer:**  
> *"We address this at three levels:  
> 1. Client-side: Every quote request carries a UUID `currentRequestId`. If a user modifies party size while a request is in flight, responses from older requests are dropped.  
> 2. Database level: SQLite connections use `BEGIN IMMEDIATE` transaction locking to prevent write contention, with optimistic concurrency revision counters on trips.  
> 3. Cache level: Any change to traveller count or date immediately invalidates the active quote on the client, rendering an amber 'Quote Outdated' badge and locking checkout."*

---

### Q6: "Why does case P03 / Q-1043 fail in the evaluations report?"
> **Answer:**  
> *"It's not a bug; it is an intentional, documented historical discrepancy. The original sample email for Q-1043 omitted LKR 64,000 for child extra beds across 6 hotel nights. Our authoritative workbook contract rules strictly require extra beds for children aged 2–11. Adding LKR 64,000 to the buy cost yields LKR 667,000, producing USD 2,965 instead of the email's USD 2,680. Rather than fabricating the engine to match an erroneous email, our codebase calculates the true contract price and keeps the historical email disagreement visible in the audit report."*
