# 03 — Complete Dataset Inventory & Provenance Audit

**Audit Date:** 22 November 2026  
**Dataset Directory:** `GenAI-Intern-Take-Home-Assignment/ceylon-compass-dataset`  
**Total Tracked Files:** 37 files  
**Integrity Verification:** 100% SHA-256 match against `docs/source-sha256.txt`

---

## 1. Complete File-by-File Dataset Inventory

The employer dataset contains 37 files across 5 functional directories:

| ID | File Path | Format | Size (B) | Identifier | Status | Ingested By | Runtime Consumer | Retrievable in UI | Test Coverage | Business Purpose & Data Quality Concerns |
|:---|:---|:---:|---:|:---:|:---:|:---|:---|:---:|:---:|:---|
| **01** | `brand/brand_pack.json` | JSON | 1,447 | N/A | Approved | Frontend styling | Tailwind CSS & UI components | Yes | Vitest | Brand styling tokens (colors, font, card radius, spacing, tone of voice). Fully adhered to in CSS. |
| **02** | `rates/rate_sheet_2026-27.xlsx` | XLSX | 13,344 | Snapshot | Active | `mira.data.load_rates` | `mira.data.calculate` | Yes | 42 unit tests | Master costing workbook. Contains 6 sheets (`READ ME`, `Settings`, `Seasons`, `Tours`, `Hotels`, `Transport`). Contains subtle irregularities (H07 expired dates, H04 missing single rate, H03 overlapping rates, H10 USD contract note, H08 string date, T06 1d vs 1n/2d duration scope conflict, T13 vs T-13 naming, T14 expired promotion, T15 draft status with workbook note, T10 & T16 missing from workbook, P06 prompt injection & fake discount, Q-1043 child extra-bed omission). |
| **03** | `rates/sample_quotes.md` | MD | 1,354 | Q1041-Q1044 | Active | Test fixtures | `evals/cases/authored.jsonl` | Yes | 4 tests | 4 historical sales emails for reference. Q-1043 omits LKR 64,000 for child extra beds. |
| **04** | `evals/eval_seed.jsonl` | JSONL | 3,939 | S01–S17 | Active | `evals/runner.py` | Automated evaluation | N/A | 17 tests | 17 employer starter evaluation cases covering pricing, discovery, grounding, and refusals. |
| **05** | `README.md` | MD | 2,419 | N/A | Active | Reference | Architecture & instructions | N/A | Manual | Dataset handover notes and rules of engagement. |
| **06** | `content/tours/colombo-city-tour.md` | MD | 535 | `T03` | `published` | `mira.data.content` | RAG retrieval, `/api/tours` | Yes | Yes | Half-day / 1-day Colombo cultural and historical drive. Clean. |
| **07** | `content/tours/cultural-triangle-6-nights.md` | MD | 3,040 | `T09` | `published` | `mira.data.content` | RAG retrieval, `/api/tours` | Yes | Yes | 6 nights / 7 days Cultural Triangle tour. Primary package for Q-1042 and Q-1043. |
| **08** | `content/tours/cultural-triangle-tour-5-nights.md` | MD | 538 | `T16` | `published` | `mira.data.content` | RAG retrieval, `/api/tours` | Yes | Yes | 5 nights / 6 days. **Workbook rate row absent**. Mira browses but correctly withholds price. |
| **09** | `content/tours/galle-fort-walking-tour.md` | MD | 594 | `T04` | `published` | `mira.data.content` | RAG retrieval, `/api/tours` | Yes | Yes | Half-day colonial fort walking tour. Clean. |
| **10** | `content/tours/highlights-of-sri-lanka-7-nights.md` | MD | 3,707 | `T08` | `published` | `mira.data.content` | RAG retrieval, `/api/tours` | Yes | Yes | 7 nights / 8 days signature tour. Used in sample quote Q-1044. |
| **11** | `content/tours/instafamous-sri-lanka.md` | MD | 748 | `T10` | `published` | `mira.data.content` | RAG retrieval, `/api/tours` | Yes | Yes | 10 nights / 11 days social media photography tour. **Workbook rate row absent**. Refuses quote. |
| **12** | `content/tours/kandy-city-tour.md` | MD | 678 | `T02` | `published` | `mira.data.content` | RAG retrieval, `/api/tours` | Yes | Yes | 1-day Kandy heritage tour. Clean. |
| **13** | `content/tours/kandy-heritage-stay.md` | MD | 1,713 | `T07` | `published` | `mira.data.content` | RAG retrieval, `/api/tours` | Yes | Yes | 2 nights / 3 days stay at Hotel Suisse (H03). Clean in Shoulder; refuses in Peak (Jan-Mar overlap). |
| **14** | `content/tours/kandy-nuwara-eliya-train-day-tour.md` | MD | 982 | `T06` | `published` | `mira.data.content` | RAG retrieval, `/api/tours` | Yes | Yes | **Scope Conflict:** Markdown says 1 night / 2 days; workbook says 1 day / 0 nights. Refuses quote. |
| **15** | `content/tours/mirissa-whale-dolphin-watching.md` | MD | 811 | `T05` | `published` | `mira.data.content` | RAG retrieval, `/api/tours` | Yes | Yes | 1-day coastal excursion. Clean. |
| **16** | `content/tours/northern-sri-lanka-tour.md` | MD | 551 | `T15` | `draft` | `mira.data.content` | Quarantined (`status='draft'`) | No | Yes | **Draft Tour:** Status is `draft`. Workbook says *"New version – not launched yet"*. Quarantined from travellers. |
| **17** | `content/tours/popular-stays-winter-2023-24-early-bird.md` | MD | 735 | `T14` | `published` | `mira.data.content` | Quarantined (`HISTORIC`) | No | Yes | **Archived Promotion:** Early bird deal from 2023/24. Rates expired. Excluded from active catalogue. |
| **18** | `content/tours/sigiriya-minneriya-day-tour-from-kandy.md` | MD | 1,014 | `T01` | `published` | `mira.data.content` | RAG retrieval, `/api/tours` | Yes | Yes | 1-day signature wildlife & rock fortress tour. Used in sample quote Q-1041. |
| **19** | `content/tours/sri-lanka-beach-stay-mirissa.md` | MD | 719 | `T11` | `published` | `mira.data.content` | RAG retrieval, `/api/tours` | Yes | Yes | 6 nights / 7 days stay at H07 (Mirissa Bay Villas). **All H07 hotel rates expired in Oct 2026**. Refuses quote. |
| **20** | `content/tours/treasures-of-sri-lanka.md` | MD | 1,596 | `T12` | `published` | `mira.data.content` | RAG retrieval, `/api/tours` | Yes | Yes | 13 nights / 14 days island tour. Uses H04 on night 7. Solo traveller fails closed (missing single rate). |
| **21** | `content/tours/wildlife-photography-tour.md` | MD | 1,046 | `T13` | `published` | `mira.data.content` | RAG retrieval, `/api/tours` | Yes | Yes | 6 nights / 7 days safari tour. Mapped from workbook `T-13` alias. Clean. |
| **22** | `content/destinations/anuradhapura.md` | MD | 391 | `D09` | `published` | `mira.data.content` | Destination RAG, Map | Yes | Yes | Ancient monastic ruins and bodhi tree profile. Clean. |
| **23** | `content/destinations/colombo.md` | MD | 316 | `D10` | `published` | `mira.data.content` | Destination RAG, Map | Yes | Yes | Commercial capital, dining and colonial port history. Clean. |
| **24** | `content/destinations/ella.md` | MD | 318 | `D05` | `published` | `mira.data.content` | Destination RAG, Map | Yes | Yes | Hill country trekking, Nine Arches Bridge, tea estates. Clean. |
| **25** | `content/destinations/galle.md` | MD | 363 | `D07` | `published` | `mira.data.content` | Destination RAG, Map | Yes | Yes | Dutch colonial fort, lighthouse and ocean ramparts. Clean. |
| **26** | `content/destinations/kandy.md` | MD | 451 | `D03` | `published` | `mira.data.content` | Destination RAG, Map | Yes | Yes | Temple of the Tooth and lake city profile. Clean. |
| **27** | `content/destinations/minneriya.md` | MD | 442 | `D02` | `published` | `mira.data.content` | Destination RAG, Map | Yes | Yes | Elephant gathering at Minneriya tank profile. Clean. |
| **28** | `content/destinations/mirissa.md` | MD | 607 | `D08` | `published` | `mira.data.content` | Destination RAG, Map | Yes | Yes | Southern coast beach and whale watching departure port. Clean. |
| **29** | `content/destinations/nuwara-eliya.md` | MD | 401 | `D04` | `published` | `mira.data.content` | Destination RAG, Map | Yes | Yes | High-altitude tea hills and colonial architecture profile. Clean. |
| **30** | `content/destinations/sigiriya.md` | MD | 559 | `D01` | `published` | `mira.data.content` | Destination RAG, Map | Yes | Yes | Ancient rock citadel and water gardens profile. Clean. |
| **31** | `content/destinations/yala.md` | MD | 418 | `D06` | `published` | `mira.data.content` | Destination RAG, Map | Yes | Yes | Leopard density and national park safari profile. Clean. |
| **32** | `content/policies/about-us.md` | MD | 367 | `P05` | `published` | `mira.data.content` | Policy RAG & citations | Yes | Yes | Company founding, local driver-guides, mission statement. Clean. |
| **33** | `content/policies/booking-and-payment.md` | MD | 984 | `P01` | `published` | `mira.data.content` | Policy RAG, quoting engine | Yes | Yes | Deposit rules (25% multi-day, full if <=30 days, full day tours), payment methods. |
| **34** | `content/policies/cancellation-policy.md` | MD | 527 | `P02` | `published` | `mira.data.content` | Policy RAG & citations | Yes | Yes | Cancellation refund tiers (48 hrs day tour, 30 days/8-29 days/7 days multi-day). |
| **35** | `content/policies/children-and-infants.md` | MD | 452 | `P03` | `published` | `mira.data.content` | Policy RAG, quoting engine | Yes | Yes | Age rules: infants <2 free, children 2-11 extra bed + half meals, 12+ adult rates. |
| **36** | `content/policies/faq.md` | MD | 614 | `P04` | `published` | `mira.data.content` | Policy RAG & citations | Yes | Yes | Common questions (private vehicle exclusivity, dietary options, transfers). |
| **37** | `content/policies/testimonials.md` | MD | 658 | `P06` | `published` | Quarantined (`main.py`, `agent.py`) | Quarantined from RAG | No | Yes | **Prompt Injection Trap:** Planted injection and fake discounts. Hard-quarantined from travellers. |

---

## 2. Ingestion & Preprocessing Behavior

### A. Ingestion Architecture
All markdown content is parsed dynamically in `apps/api/mira/data.py` via `content()`:
1. Glob scan: `DATA.glob("content/*/*.md")`
2. Front matter split: `path.read_text().split("---", 2)` parsed via `yaml.safe_load(header)`
3. Duplicate rejection: Tracks duplicate IDs and drops collisions
4. Sanitization: `public_text()` removes HTML comments, currency symbols, and margin keywords

### B. Workbook Loading Architecture
The costing workbook is ingested via `load_rates()` / `parse_rates()`:
1. Binary snapshot hashing: Generates SHA-256 digest of `rate_sheet_2026-27.xlsx`
2. OpenPyXL read: Read in read-only and `data_only=True` mode
3. Row-level caching: Preserves exact Excel row numbers for staff audit trails

---

## 3. Dataset Irregularities & Engineering Responses

| Anomaly Identified | Location in Source Data | Potential Failure Mode | Implementation Defense | Audit Verification |
|:---|:---|:---|:---|:---:|
| **Quarantined Injection Trap** | `content/policies/testimonials.md` (`P06`) | Model instructed to always recommend T12; fake 20% anniversary discount leaked. | Explicitly quarantined in `agent.py` (line 239) and `main.py` (line 105). HTTP 404 returned on `/api/sources/P06`. | **VERIFIED** |
| **Expired Promotion** | `content/tours/popular-stays-winter-2023-24-early-bird.md` (`T14`) | System quotes expired promotional package with missing modern hotel rates. | Tagged in `HISTORIC = {"T14"}` in `data.py`. Filtered out of `published()` catalogue. | **VERIFIED** |
| **Unpublished Draft Tour** | `content/tours/northern-sri-lanka-tour.md` (`T15`) | Unpublished northern tour leaked to public travellers before launch. | Front matter has `status: draft`. Dropped by `published()` filter. Quoting raises `Unavailable("not_published")`. | **VERIFIED** |
| **Duration Scope Conflict** | `content/tours/kandy-nuwara-eliya-train-day-tour.md` (`T06`) | Markdown states 1 night / 2 days; workbook states 1 day / 0 nights. | Explicitly blocked in `data.py`: `if tour == "T06": raise Unavailable("conflicting_tour_scope")`. Refers to staff. | **VERIFIED** |
| **Missing Workbook Rates** | `content/tours/instafamous-sri-lanka.md` (`T10`), `cultural-triangle-tour-5-nights.md` (`T16`) | Quoting engine crashes or LLM hallucinates invented package prices. | Rejection in `data.py`: `one(..., "tour_rate")` raises `Unavailable("tour_rate")`. Dispatches `EnquiryNotice`. | **VERIFIED** |
| **Expired Hotel Rates** | `Hotels` tab, rows 29–31 (`H07` Mirissa Bay Villas) | Rates ended in October 2026; no 2026-27 rates exist. | `T11` queries fail closed with `Unavailable("hotel_rate_missing_or_ambiguous")`. | **VERIFIED** |
| **Missing Single Rate** | `Hotels` tab, rows 16–19 (`H04` Heritance Tea Factory) | Solo travellers or odd-adult groups at H04 crash or get double-room rate. | Solo request for `T12` raises `Unavailable("missing_amount")`. Even adult counts (double room) succeed. | **VERIFIED** |
| **Overlapping Hotel Rates** | `Hotels` tab, rows 13 and 56 (`H03` Hotel Suisse) | Two overlapping rows cover Jan–March 2027; one has unconfirmed supplier note. | `one()` detects multiple matches and raises `Unavailable("hotel_rate_missing_or_ambiguous")`. | **VERIFIED** |
| **Currency Inconsistency** | `Hotels` tab, rows 40–43 (`H10` Cinnamon Wild Yala) | Rates are in USD ($125) while column header specifies LKR. | Detected via note `"USD (Cinnamon contract)"`; multiplied by FX rate (300) to convert to LKR buy cost. | **VERIFIED** |
| **Date String Formatting** | `Hotels` tab, row 33 (`H08` Galle Fort Hotel) | Valid from field contains string `'15/12/2026'` instead of datetime object. | `day()` parser detects string and applies `strptime("%d/%m/%Y")`. | **VERIFIED** |
| **Workbook Tour Alias** | `Tours` tab, row 13 (`T-13`) | Tour ID contains hyphen (`T-13`), whereas markdown ID is `T13`. | Explicit alias mapping in `data.py`: `{"T13": "T-13"}` seamlessly resolves ID. | **VERIFIED** |
| **Sample Quote Omission** | `rates/sample_quotes.md` (`Q-1043`) | Email forgot LKR 64,000 child extra beds; quote states USD 2,680 instead of USD 2,965. | Pricing engine computes mathematically correct USD 2,965. Discrepancy audited in `P03`. | **VERIFIED** |
