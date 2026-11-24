# Remaining Gaps & Technical Audit Transparency

In adherence to strict engineering honesty, this document catalogs the remaining architectural constraints and known considerations in Mira v3.1.

---

## 1. The P03 Evaluation Discrepancy (Rate Sheet vs. Historical Email)

- **Summary**: Evaluation case `P03` expects total `USD 2,680` ($670 deposit) based on historical email `Q-1043`. The actual rate workbook calculation yields `USD 2,965` ($742 deposit) due to mandatory child extra bed costs (LKR 64,000).
- **Engineering Decision**: The system adheres to the authoritative rate sheet workbook and Policy P03 rather than hardcoding an artificial override to match an erroneous historical email. Employer test case `S03` tests the identical itinerary and confirms $2,965 is correct.
- **Impact**: Overall automated evaluation pass rate is 48 / 49 (98.0%).

---

## 2. Solo Traveler Room Rates for Complex Multi-Day Tours

- **Summary**: For `T12 Treasures of Sri Lanka`, quotes for 2 adults and 4 adults sharing double rooms calculate accurately ($4,550 and $7,855). For solo travelers (1 adult), pricing is withheld because single room supplements are missing for several boutique hotels in the workbook.
- **Mitigation**: Rather than hallucinating a generic single supplement, Mira safely withholds the quotation and generates an `EnquiryNotice` routing the solo traveler to a human destination specialist.

---

## 3. Human Evaluation Set Protocol

- The assignment brief specifies comparing LLM-assisted outputs against 10 human-labeled review cases.
- A calibration worksheet (`evals/judges/calibration_worksheet.md`) and template (`evals/judges/calibration_template.json`) have been prepared with complete instructions for human evaluators.
- No artificial human scores have been fabricated; genuine evaluations await manual human grading.
