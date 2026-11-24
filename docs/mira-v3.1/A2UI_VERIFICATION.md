# A2UI Verification & Generative UI Architecture

This document describes the actual runtime architecture of Generative UI and A2UI component delivery in Mira v3.1.

---

## 1. Architectural Reality: Hybrid Constrained A2UI

The user prompt asked whether component selection is:
- **A. Fully deterministic**
- **B. Constrained model-assisted**
- **C. A hybrid of the two**

### Honest Architectural Description:
The current production implementation is **Option C: A Hybrid of the Two**:
1. **Model-Assisted Planning Layer**:
   - `provider.py::plan_ui()` and `provider.py::notebook_intent()` call Gemini (when available) with strict Pydantic schemas (`UIPlan`, `NotebookIntent`).
   - The model recommends up to 5 component types from an approved allowlist.
   - The model **never** generates arbitrary JSX, HTML, JavaScript, CSS, or monetary values.
2. **Server-Side Deterministic Guardrails**:
   - Every recommended component type is validated against `mira.catalog` Pydantic models (`TourCard`, `ItineraryDay`, `PriceBreakdown`, `Booking`, `Notice`, `Proposal`, `InteractiveMap`, `DateSelector`, `Picker`, `Excerpt`).
   - If Gemini is unconfigured, rate-limited, or blocked, the agent smoothly falls back to deterministic rule-based composition without user disruption.
   - All monetary amounts, dates, and package inclusions are populated exclusively by the backend pricing engine and canonical markdown parser.

---

## 2. Interactive Component State Transitions

Every interactive component in the Lovable frontend triggers genuine state transitions:

| Component | Trigger Action | Backend Endpoint / Event | Resulting State Transition |
|-----------|----------------|--------------------------|----------------------------|
| `TourCard` | Click "Explore Itinerary" | `/api/agent` (`@tour <ID>`) | Opens journey details & triggers day-by-day itinerary view. |
| `TravellerPicker` | Adjust Adult/Child counts | `/api/agent` (form state) | Recomputes pricing; updates party context. |
| `DateSelector` | Select Travel Date | `/api/agent` (`@depart <date>`) | Re-evaluates season and deposit percentage (100% vs 25%). |
| `PriceBreakdown` | View Deposit Breakdown | Renders `QuoteCard` | Displays total, deposit, and balance due dates. |
| `Booking` | Click "Proceed to Booking" | `POST /api/bookings/mock` | Reserves quote; disables re-booking if quote becomes stale. |
| `EnquiryNotice` | Click "Connect with Specialist" | `POST /api/enquiries` | Persists bespoke request to database; staff console visibility. |
| `InteractiveMap` | Click Day Pin | `/api/agent` (`@day <N>`) | Pans camera to geographic coordinates; selects active day stop. |

---

## 3. UI Regression Protection

1. **Semantic Deduplication**:
   - Redundant library cards are suppressed when specific tour cards or itineraries are displayed.
2. **No Raw Internal IDs**:
   - Guest-facing headings display natural titles (*"Cultural Triangle Sri Lanka Package"*) instead of internal slugs or IDs (*"T09"* or `"cultural-triangle-6-nights"`).
3. **Bounded Component Payloads**:
   - Turn payloads are strictly capped ($\le 12$ components, $\le 6$ citations) to guarantee fast client rendering.
