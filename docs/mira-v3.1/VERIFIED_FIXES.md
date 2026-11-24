# Mira v3.1 — Verified Fixes & Defect Investigation Report

This document records the exact investigation, root cause analysis, code changes, and test verification for each defect identified in the Mira v3 report and audit review.

---

## 1. Defect Candidate 1: T01 Quick-Booker Quotation Discrepancy

### Observation in v3 Report
- The v3 documentation text reported: *"T01 quick-booker quote: USD 240."*
- Original sample quote Q-1041 specified:
  - Tour: T01 (Sigiriya and Minneriya Day Tour from Kandy)
  - Party: 2 adults
  - Date: 10 January 2027
  - Total: **USD 315**, Deposit: **USD 315**

### Investigation & Root Cause
- Investigated all 4 layers:
  1. `mira.data.price("T01", date(2027, 1, 10), 2, [], TODAY)` -> returns `cost_lkr=66000, total=315, deposit=315`.
  2. LangGraph agent `/api/agent` with prompt *"Sigiriya and Minneriya day tour for two adults on 10 January 2027"* -> returns `Breakdown(quote=Quote(total=315, deposit=315))`.
  3. Public API `/api/quotes` -> returns `{"total": 315, "deposit": 315}`.
  4. Lovable UI `QuoteCard` / `LiveCanvas` -> renders **USD 315**.
- **Root Cause**: The pricing engine was already computing the correct amount (**USD 315**) matching Q-1041. The previous report documentation text mistakenly copied a draft test parameter ($240) from an earlier draft report instead of the genuine workbook calculation ($315).
- **Corrective Action**: Corrected documentation across all reports to authoritatively state **USD 315 / USD 315 deposit**. Added explicit regression test `test_scenario_01_t01_quick_booker`.

---

## 2. Defect Candidate 2: T09 Day 4 Description Inaccuracy

### Observation in v3 Report
- The v3 documentation text stated that Day 4 of T09 was *"Sigiriya Rock Fortress & Habarana Village Tour"*.
- The original canonical tour document `content/tours/cultural-triangle-6-nights.md` states:
  - **Day 4: Sigiriya and Polonnaruwa**
  - Activities: *"Sigiriya at sunrise, Polonnaruwa in the afternoon."*
  - Accommodation: *"Sigiriya Village or similar"*
  - Entrance tickets: *"Sigiriya, Polonnaruwa"*

### Investigation & Root Cause
- In the codebase, `itinerary_parser.py` correctly parsed `Day 4: Sigiriya and Polonnaruwa` with sunrise Sigiriya and afternoon Polonnaruwa.
- The previous author had hallucinated a different itinerary table in the markdown documentation `TOUR_ITINERARY_FIDELITY.md` and `DEMO_RUNBOOK.md` without cross-checking the actual markdown document.
- In addition, agent regex for full itineraries originally matched only `\bfull\b`, causing queries using *"complete itinerary"* to fall back to a single day.
- **Corrective Action**:
  - Updated regex in `apps/api/mira/agent.py` to match `\b(?:full|complete|entire|whole)\b.*?\b(?:itinerary|package|tour|schedule|days|plan)\b|\ball\s+days\b|\bday[- ]by[- ]day\b|\bcomplete\s+itinerary\b`.
  - Added targeted question answering in `agent.py` for day hotels and inclusions.
  - Added regression tests `test_scenario_02_t09_complete_itinerary` and `test_scenario_03_t09_day_4_specific`.

---

## 3. Defect Candidate 3: T12 Pricing Classification

### Observation in v3 Report
- The v3 report classified T12 (*Treasures of Sri Lanka*) as universally unpriced alongside T10, T11, and T16.

### Investigation & Root Cause
- Investigated `rate_sheet_2026-27.xlsx` worksheet `Tours`:
  - Row 12: `T12, Treasures of Sri Lanka, Multi-day, 14, 13, 10000, 60000, 30000, 4500, H01, H12, H02, H02, H03, H03, H04, H06, H06, H10, H08, H08, H09`.
  - Double occupancy (2 adults sharing): All 13 hotel nights have valid contracted double-room rates in the `Hotels` worksheet. Price calculation yields **USD 4,550 total / USD 1,138 deposit** (`cost_lkr=1,023,500`).
  - Solo occupancy (1 adult): Fails with `Unavailable: missing_amount` because one of the contracted hotels lacks a single room supplement.
- **Root Cause**: The report author conflated solo-room unpriced behavior with general unpriced status. T12 is fully supported and priced for double occupancy, but correctly withheld for solo travelers.
- **Corrective Action**:
  - Preserved deterministic workbook behavior: 2 adults receive a valid quote ($4,550 / $1,138 deposit); solo travelers receive an `EnquiryNotice` with `missing_amount`.
  - Added regression tests `test_scenario_05_t12_supported_adult_booking` and `test_scenario_06_t12_unsupported_solo_booking`.

---

## 4. Defect Candidate 4: Server Ports & Runtime Route Configuration

### Observation in v3 Report
- The v3 runbook instructed evaluators to open `http://localhost:3000` to view the Lovable traveller frontend.

### Investigation & Root Cause
- Inspecting `scripts/dev.py`:
  - `API`: Port 8000 (`.` running `mira.serve`)
  - `NEXT`: Port 3000 (`apps/web` running Next.js staff console)
  - `WEB`: Port 5175 (`apps/ceylon-compass` running Vite / TanStack Start Lovable traveller frontend)
- Directing evaluators to port 3000 launched the internal staff console, leading to confusion that the Lovable frontend had been replaced.
- **Corrective Action**:
  - Updated documentation to specify **Port 5175** (`http://127.0.0.1:5175`) for the Lovable traveller frontend and **Port 3000** (`http://127.0.0.1:3000`) for the staff console.
  - Documented one-command supervisor: `.venv/bin/python scripts/dev.py`.
