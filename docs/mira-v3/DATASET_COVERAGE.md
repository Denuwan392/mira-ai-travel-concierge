# Dataset Coverage — Ceylon Compass Holidays

This report details how every document, policy, spreadsheet, and asset in the canonical dataset is ingested, parsed, indexed, and presented to travellers across Mira's full-stack architecture.

---

## 1. Document Coverage Matrix

| Category | Dataset Entity | Ingested | Structured Parser | RAG Vector / Semantic Index | UI Presentation Component |
|----------|----------------|:--------:|:-----------------:|:---------------------------:|:-------------------------:|
| **Tours** | T01 Sigiriya & Minneriya Day | Yes | Yes (`DaySchedule`) | Yes | `TourCard`, `ItineraryDay`, `QuoteCard` |
| | T02 Kandy Cultural & Tea Heritage | Yes | Yes (`DaySchedule`) | Yes | `TourCard`, `ItineraryDay`, `QuoteCard` |
| | T03 Colombo City & Food | Yes | Yes (`DaySchedule`) | Yes | `TourCard`, `ItineraryDay`, `QuoteCard` |
| | T04 Galle Fort & Coast | Yes | Yes (`DaySchedule`) | Yes | `TourCard`, `ItineraryDay`, `QuoteCard` |
| | T05 Mirissa Whale Watching | Yes | Yes (`DaySchedule`) | Yes | `TourCard`, `ItineraryDay`, `QuoteCard` |
| | T06 Scenic Train Day Tour | Yes | Yes (`DaySchedule`) | Yes | `TourCard`, `ItineraryDay`, `QuoteCard` |
| | T07 Kandy Heritage 3D | Yes | Yes (`DaySchedule` 3 days) | Yes | `TourCard`, `ItineraryDay`, `QuoteCard` |
| | T08 Highlights of Sri Lanka 8D | Yes | Yes (`DaySchedule` 8 days) | Yes | `TourCard`, `ItineraryDay`, `QuoteCard` |
| | T09 Cultural Triangle 7D | Yes | Yes (`DaySchedule` 7 days) | Yes | `TourCard`, `ItineraryDay`, `QuoteCard` |
| | T10 Instafamous Sri Lanka 11D | Yes | Yes (`DaySchedule` 11 days) | Yes | `TourCard`, `ItineraryDay`, `EnquiryNotice` (Unpriced) |
| | T11 Southern Beach Stay 5D | Yes | Yes (`DaySchedule` 5 days) | Yes | `TourCard`, `ItineraryDay`, `EnquiryNotice` (Unpriced) |
| | T12 Complete Sri Lanka 14D | Yes | Yes (`DaySchedule` 14 days) | Yes | `TourCard`, `ItineraryDay`, `EnquiryNotice` (Unpriced) |
| | T13 Wildlife Safari 6D | Yes | Yes (`DaySchedule` 6 days) | Yes | `TourCard`, `ItineraryDay`, `EnquiryNotice` (Unpriced) |
| | T14 Winter Sun 8D (Historic) | Yes | Yes (`DaySchedule` 8 days) | Yes | `TourCard`, `EnquiryNotice` (Historic) |
| | T15 Northern Cultural 6D (Draft) | Yes | Yes (`DaySchedule` 6 days) | Filtered (Draft) | Refusal Notice + `EnquiryNotice` (Draft isolation) |
| | T16 Cultural Short Break 5D | Yes | Yes (`DaySchedule` 5 days) | Yes | `TourCard`, `ItineraryDay`, `EnquiryNotice` (No rates) |
| **Destinations** | D01 Sigiriya & Triangle | Yes | Yes (Activity Bank $\ge 3$) | Yes | `DestinationCard`, `LiveCanvas` Notebook |
| | D02 Kandy & Central Highlands | Yes | Yes (Activity Bank $\ge 3$) | Yes | `DestinationCard`, `LiveCanvas` Notebook |
| | D03 Nuwara Eliya & Tea Country | Yes | Yes (Activity Bank $\ge 3$) | Yes | `DestinationCard`, `LiveCanvas` Notebook |
| | D04 Ella & Badulla Region | Yes | Yes (Activity Bank $\ge 3$) | Yes | `DestinationCard`, `LiveCanvas` Notebook |
| | D05 Galle & Southern Coast | Yes | Yes (Activity Bank $\ge 3$) | Yes | `DestinationCard`, `LiveCanvas` Notebook |
| | D06 Yala Wildlife | Yes | Yes (Activity Bank $\ge 3$) | Yes | `DestinationCard`, `LiveCanvas` Notebook |
| | D07 Colombo Commercial Capital | Yes | Yes (Activity Bank $\ge 3$) | Yes | `DestinationCard`, `LiveCanvas` Notebook |
| | D08 Mirissa & Weligama Bay | Yes | Yes (Activity Bank $\ge 3$) | Yes | `DestinationCard`, `LiveCanvas` Notebook |
| | D09 Jaffna & Northern Province | Yes | Yes (Activity Bank $\ge 3$) | Yes | `DestinationCard`, `LiveCanvas` Notebook |
| | D10 Trincomalee & East Coast | Yes | Yes (Activity Bank $\ge 3$) | Yes | `DestinationCard`, `LiveCanvas` Notebook |
| **Policies** | P01 Booking Terms & Deposits | Yes | Yes | Yes | `SourceDisclosure`, Agent Knowledge |
| | P02 Cancellation & Refunds | Yes | Yes (Precedence Rules) | Yes | `SourceDisclosure`, Agent Knowledge |
| | P03 Child & Family Policy | Yes | Yes (Bed Pricing Rules) | Yes | `SourceDisclosure`, Agent Knowledge |
| | P04 Vehicles & Transport | Yes | Yes | Yes | `SourceDisclosure`, Agent Knowledge |
| | P05 Wildlife & Safari Safety | Yes | Yes | Yes | `SourceDisclosure`, Agent Knowledge |
| | P06 Weather & Monsoons | Yes | Yes | Yes | `SourceDisclosure`, Agent Knowledge |

---

## 2. Ingestion Pipeline & Parsing Architecture

1. **Tour Itinerary Ingestion (`apps/api/mira/itinerary_parser.py`)**:
   - Rather than treating tour documents as unstructured blobs of text, `itinerary_parser.py` breaks markdown headings matching `### Day X: ...` into structured Pydantic models (`TourItinerary`, `DaySchedule`).
   - Extracts structured metadata for each day:
     - `day`: Integer day number (1-based).
     - `title`: Extracted title of the day.
     - `description`: Narrative description of morning, afternoon, and evening activities.
     - `meals`: Breakfast, Lunch, Dinner flags parsed from document inclusions.
     - `accommodation`: Hotel tier and property names mentioned.
     - `tickets`: Listed entrance tickets and safari permits.
2. **Deterministic Rate Parsing (`apps/api/mira/pricing.py`)**:
   - Ingests `rate_sheet_2026-27.xlsx` at application startup.
   - Binds seasons, room types, adult per-person rates, child extra bed surcharges, and group discounts into in-memory indexing tables.
   - Flags missing rate combinations explicitly (`missing_rate`, `unsupported_dates`, `draft_package`).
3. **Draft Package Isolation**:
   - `T15` (Northern Sri Lanka Cultural Circuit) is marked as `status: draft` in frontmatter.
   - When a user asks to book or view pricing for T15, the agent intercepts the request, explains that T15 is an unreleased draft route, and routes the traveller to the bespoke specialist enquiry flow via `EnquiryNotice`.
