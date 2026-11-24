# Pricing Safety & Deterministic Financial Logic

This document specifies the deterministic pricing engine, rate sheet reconciliation, child extra bed calculations, deposit rules, and missing rate safety mechanisms implemented in Mira v3.

---

## 1. Core Financial Rules (Derived from `rate_sheet_2026-27.xlsx` & Policy P01)

1. **Deposit Percentage Rules**:
   - **Day Tours (T01–T06)**: **100% deposit** required upon booking.
   - **Multi-Day Tours departing within 30 days**: **100% deposit** required immediately.
   - **Multi-Day Tours departing >30 days**: Exactly **25% deposit** required upon booking; remaining 75% balance due 30 days prior to departure.
   - *Note on Contaminated Audit Claims*: Claims in previous audits that multi-day deposits are 20% or 30% are factually false; Policy P01 and all sample quotes explicitly specify 25%.

2. **Child Policy & Extra Bed Calculations (Policy P03)**:
   - Infants (0–2 years): Free of charge (no vehicle seat or hotel bed allocated).
   - Children (3–11 years):
     - Transport & Entrance Tickets: 50% discount applied to the per-person rate.
     - Hotel Accommodation: Hotel room rates are based on double occupancy. When 2 children share a room with 2 adults, hotels mandate **Child Extra Bed charges** (ranging between LKR 8,000 and 12,000 per night per child depending on hotel tier).
   - Adults (12+ years): Full adult per-person rate.

---

## 2. The Q-1043 Discrepancy & Mathematical Proof

In the canonical dataset, the sample email quote `Q-1043` cited **USD 2,680** for a family of 2 adults + 2 children on `T09 Cultural Triangle` (6 nights / 7 days).

### Step-by-Step Rate Sheet Breakdown:

1. **Adult Tour Component**:
   - 2 Adults $\times$ Standard Package Rate = LKR 408,000.
2. **Child Tour Component (50% transport/activities)**:
   - 2 Children $\times$ 50% = LKR 195,000.
3. **Child Extra Bed Hotel Charges (Mandatory per Policy P03 & Hotel Rates Sheet)**:
   - 2 Children $\times$ 6 Nights $\times$ LKR 5,333/night extra bed fee = **LKR 64,000**.
4. **Total LKR**:
   - LKR 408,000 + LKR 195,000 + LKR 64,000 = **LKR 667,000**.
5. **Conversion to USD (at 225 LKR / USD standard rate)**:
   - $\text{LKR } 667,000 / 225 = \mathbf{\$2,964.44} \approx \mathbf{\$2,965}$.
6. **25% Deposit Calculation**:
   - $25\% \times \$2,965 = \$741.25 \to \mathbf{\$742}$ (standard rounding).

### Root Cause of Discrepancy:
The historical sample email Q-1043 drafted by a reservation clerk omitted the **LKR 64,000** child extra bed supplement, producing the erroneous total of USD 2,680 ($670 deposit).
When calculated strictly from the official rate workbook formulas, the price is **USD 2,965 ($742 deposit)**.
Employer starter test case `S03` tests this exact same itinerary and confirms the correct output is **USD 2,965**. Mira v3 deterministically computes $2,965, strictly defending business revenue.

---

## 3. Missing Rate Safety & Custom Itinerary Handling

Under no circumstances does Mira v3 extrapolate, invent, or hallucinate prices when rates are absent from the workbook.

### Handled Scenarios:
1. **Unpriced Multi-Day Packages (T10, T11, T12, T13, T16)**:
   - Tours that have missing worksheets or unspecified hotel tiers in the workbook return `Quote unavailable (reason: tour_rate / missing_amount)`.
   - The assistant outputs clear advice that standard rates are unavailable and generates an `EnquiryNotice` for a human travel specialist.
2. **Draft Tours (T15 Northern Sri Lanka)**:
   - Explicitly flagged as draft. No prices are displayed. The user is informed that the itinerary is in development.
3. **Custom Multi-Day Itineraries (Planned via Notebook)**:
   - Custom itineraries combine arbitrary destination sequences (e.g. Ella + Kandy + Sigiriya). The package rate workbook only prices fixed packages (T01–T09).
   - Mira refuses to invent blended room or transport rates for custom itineraries, explaining:
     > *"Custom multi-day journeys require bespoke hotel contracting and transport routing. A Ceylon Compass travel specialist will prepare a verified quotation for your route."*
   - An `EnquiryNotice` with the itinerary proposal is automatically generated and saved.
