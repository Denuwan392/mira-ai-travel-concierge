# P0 Repair: Family Holiday Planning & Custom Itinerary Consistency

**Project:** Ceylon Compass Holidays — Mira AI Travel Booking Assistant  
**Document ID:** `docs/system-audit/FAMILY_PLANNING_WORKFLOW_REPAIR.md`  
**Date:** November 25, 2026

---

## 1. Confirmed Root Causes (Verified from Trace & Code)

1. **Where the 2-day duration came from (`apps/api/mira/agent.py:468-476`):**
   - When `GEMINI_API_KEY` is configured, `notebook_intent("Plan a family holiday", ...)` returns `operation="plan"` with `days=None` and `destinations=[]`.
   - `interpret()` fell through to `ids = list(destinations)[:2]` (the first two destinations: `D01` Anuradhapura and `D02`) and computed `n = len(ids) = 2`, producing `"Your proposed journey now has 2 days"` without user input or prior session contamination.
2. **Why chat `Day 1:` and `Day 2:` were empty while the workspace showed Anuradhapura (`Workspace.jsx:3737` vs `3496`):**
   - Backend `DayStop` objects store `name` (destination title) and `passage` (grounded description).
   - `JourneyPlanPanel` (right-side workspace) read `day.name` and `day.passage`, whereas chat `UIComponentRenderer` (`JourneyPlan`) read `d.title || d.summary || ''`, rendering empty `Day 1:` and `Day 2:` lines.
3. **Why a premature enquiry was created (`agent.py:484` & `compose`):**
   - Unconditionally setting `action = "custom"` for a broad initial `"Plan a family holiday"` message caused `compose()` to generate `Notice(outcome="SPECIALIST_HANDOFF", reason_code="custom_or_unsupported")` and persist an enquiry in SQLite before duration, party ages, or interests were collected.
4. **Why unrelated tours (`T08`, `T10`, `T12`) appeared alongside custom itineraries (`agent.py:504, 622`):**
   - `retrieve()` returned `["T08", "T10", "T12"]` for `action == "custom"`, and `compose()` emitted them as `TourCard`s alongside `JourneyPlan`.
5. **Why complete family requests with `"2 adults"` skipped `plan_request` (`agent.py:322, 446`):**
   - Including `"2 adults"` kept `action == "discover"` (skipping `action = "general"`), while `plan_request` only matched `action in {"general", "custom", "destination"}`.

---

## 2. Fixes Implemented

1. **Broad Discovery Clarification (`apps/api/mira/agent.py`):**
   - Added `action = "clarify_plan"` when a broad planning prompt (e.g. `"Plan a family holiday"`) lacks both duration/dates and destinations/interests — regardless of whether Gemini returns `operation="plan"`.
   - Asks up to 3 concise clarification questions (duration/dates, adults + children's ages, interests/destinations), explains why suggested family-friendly published tours fit (`T01`, `T09`, `T05`), and creates **zero** premature `JourneyPlan` or `enquiries` rows.
2. **Immediate Grounded Itinerary on Complete Family Requests (`apps/api/mira/agent.py`):**
   - Included `"discover"` (when `named not in tours`) in `plan_request` so requests like `"We have 6 days for nature, scenic trains and beaches for 2 adults and a 7-year-old"` generate a grounded 6-day `JourneyPlan` immediately.
   - Suppressed unrelated `TourCard`s (`T08`, `T10`, `T12`) when `action == "custom"` and `ctx.get("proposal")` is present.
3. **Unified Chat & Workspace Itinerary Rendering (`apps/ceylon-compass/workspace/Workspace.jsx`):**
   - Updated `UIComponentRenderer` (`JourneyPlan`) and `JourneyPlanPanel` to read `d.name || d.title` and `d.passage || d.experience || d.summary`, ensuring every day displays its real destination title and grounded passage in both chat and workspace.

---

## 3. Verification Results

- **Backend & Frontend Lint/Typecheck (`make lint`):** **Passed** (`compileall`, `apps/web` `tsc --noEmit`, `apps/ceylon-compass` `tsc --noEmit`).
- **Automated Tests (`make test`):**
  - **Vitest (`apps/ceylon-compass`):** **70 / 70 passed** (8 files), including `UIComponentRenderer` `JourneyPlan` non-empty day rendering.
  - **Pytest (`apps/api/tests`):** **220 / 220 passed**, including `apps/api/tests/test_family_planning_workflow.py` verifying:
    - Broad `"Plan a family holiday"` clarifies without 2-day default or premature enquiry (`enquiries = 0`).
    - Complete 6-day family request builds grounded 6-day `JourneyPlan` with zero unrelated `TourCard`s and zero duplicate enquiries on `@day 2`.
- **Playwright Browser E2E (`make workspace-browser`):** **10 / 10 passed** (`14.7s`), including **`Test F`** verifying `"Plan a family holiday"` clarification followed by complete 6-day grounded itinerary rendering in Chrome.
