# 05 — TOUR AND ITINERARY FIDELITY AUDIT

**Document Version:** 2.0 (Independent Second-Pass Audit)  
**Date:** November 2026  
**Auditor:** Independent Principal Systems Architect & Technical Auditor  
**Scope:** Deep-dive analysis of itinerary fidelity, tour parsing, presentation truncations, and edge cases across all 16 catalog tours (T01–T16).

---

## 1. Executive Summary: Itinerary Fidelity Findings

While Mira's backend data loader correctly parses all 16 tour markdown files, an adversarial inspection reveals significant discrepancies between the underlying catalog data and what is surfaced to the traveller:

1. **Conversational Day-1 Truncation (Critical UX Limitation):** Multi-day tours (such as the 7-day Cultural Triangle Odyssey, `T09`) have complete 7-day schedules in `ceylon-compass-dataset/content/tours/t09_cultural_triangle_odyssey.md`, but `agent.py::compose()` (line 386) extracts only `Day 1` or `Highlights`, discarding Days 2 through 7 from conversational chat turns.
2. **Custom Multi-Day Synthesis by Duplication:** When travellers request a custom itinerary (e.g., a 10-day trip covering 3 cities), the agent does not construct realistic distinct daily schedules. Instead, it repeats destination ID tokens across days and duplicates the destination overview text.
3. **Strict Missing-Rate Withholding (Verified Pass):** Tour `T16` (Northern Coast & Islands) has zero rate rows in `rate_sheet_2026-27.xlsx`. The engine strictly withholds pricing and displays a human-consultant advisory.
4. **Scope Mismatch in T06 (Knuckles):** The tour narrative mentions a 1-night camping option, but the rate sheet contains only a 1-day trekking rate. Mira correctly prices only the 1-day option without hallucinating an overnight surcharge.

---

## 2. Tour-by-Tour Fidelity & Edge Case Analysis

### T01 — Colombo City Walk & Food Culture (1 Day)
- **Dataset Content:** Colonial architecture, Pettah market, street food tasting at Galle Face Green.
- **Engine Behavior:** Parsed and indexed cleanly. Quoted at standard day-tour sedan/van rates.
- **Fidelity Score:** **100% (High)**.

### T02 — Negombo Lagoon & Dutch Canal (1 Day)
- **Dataset Content:** Early morning fish auction, boat ride through Dutch canals and mangroves.
- **Engine Behavior:** Quoted accurately with local boatman inclusion.
- **Fidelity Score:** **100% (High)**.

### T03 — Kandy Cultural Highlights (1 Day)
- **Dataset Content:** Temple of the Sacred Tooth Relic, Royal Botanical Gardens Peradeniya, cultural dance show.
- **Engine Behavior:** Entrance fees for Temple of Tooth ($15) and Peradeniya ($10) accurately computed.
- **Fidelity Score:** **100% (High)**.

### T04 — Galle Fort Historic Walk & Southern Coast (1 Day)
- **Dataset Content:** UNESCO ramparts, lighthouse, maritime museum, turtle hatchery.
- **Policy Conflict:** Tour file text claims "Free cancellation up to 24 hours before departure". However, Master Cancellation Policy `P02` mandates a 48-hour cut-off.
- **Engine Resolution:** `agent.py::retrieve()` enforces `P02` (48 hours), strictly prioritizing company-wide policy over localized tour text.
- **Fidelity Score:** **100% (Correct Policy Precedence Enforced)**.

### T05 — Sigiriya Rock Fortress & Dambulla Cave Temple (1 Day)
- **Dataset Content:** 5th-century palace citadel climb, Dambulla rock cave paintings.
- **Engine Behavior:** Heavy entrance fees ($36 Sigiriya + $12 Dambulla per adult) calculated deterministically.
- **Fidelity Score:** **100% (High)**.

### T06 — Knuckles Cloud Forest Trekking (1 Day vs Overnight)
- **Dataset Content:** Trekking through pygmy forests, waterfalls, optional overnight eco-camp.
- **Discrepancy:** The rate workbook includes only a 1-day trekking package. There is no line item for the eco-camp or overnight stay.
- **Engine Resolution:** Mira prices strictly the 1-day package. When asked about overnight camping, the system triggers the R6 fallback: "Overnight eco-camping requires custom rate verification by our staff team."
- **Fidelity Score:** **100% (Compliant with Missing Rate Rules)**.

### T07 — Ella Scenic Adventure & Nine Arches Bridge (1 Day)
- **Dataset Content:** Little Adam's Peak, Nine Arches Bridge train viewing, Ravana Falls.
- **Outdated Text Trap:** File contains a legacy marketing banner: *"Special Family Promo: Children travel free in November 2025!"*
- **Engine Resolution:** The pricing engine queries `rate_sheet_2026-27.xlsx` and applies standard `P03` child policies (50% charge for ages 6–11), ignoring the uncontracted promo text.
- **Fidelity Score:** **100% (Resistant to Outdated Promotional Copy)**.

### T08 — Tea Country Scenic Rail & Plantations (3 Days / 2 Nights)
- **Dataset Content:** Kandy to Ella train, Nuwara Eliya tea factory, optional Kitulgala white-water rafting excursion on return.
- **Engine Behavior:** Surfaces Kitulgala rafting as an optional add-on card. Hotel nights in Nuwara Eliya and Ella correctly mapped.
- **Chat Presentation:** Truncates to Day 1 highlight card in initial chat turn; complete itinerary only available if full modal is opened.
- **Fidelity Score:** **85% (Good data, but truncated in conversational stream)**.

### T09 — Cultural Triangle Heritage Odyssey (7 Days / 6 Nights)
- **Dataset Content:** Comprehensive 7-day journey: Colombo $\to$ Sigiriya $\to$ Polonnaruwa $\to$ Anuradhapura $\to$ Kandy $\to$ Colombo.
- **Detailed Investigation of Truncation:**
  - File contains distinct headers: `### Day 1: Arrival & Dambulla`, `### Day 2: Sigiriya Citadel`, `### Day 3: Ancient Polonnaruwa`, `### Day 4: Anuradhapura Sacred City`, `### Day 5: Cave Temples to Kandy`, `### Day 6: Kandy & Royal Gardens`, `### Day 7: Return to Colombo`.
  - In `apps/api/mira/agent.py` line 386:
    ```python
    # agent.py compose() snippet
    day_match = re.search(r"(?:### Day 1[^\n]*\n)(.*?)(?=\n### Day 2|\Z)", tour_text, re.DOTALL)
    preview_text = day_match.group(1).strip() if day_match else tour_summary
    ```
  - **Audit Finding:** The chat interface intentionally discards Days 2 through 7 to keep the A2UI message payload compact. Travellers asking "What do we do on Day 4 of T09?" in conversational flow receive a generic summary unless explicitly prompting for Day 4.
- **Fidelity Score:** **70% (Significant conversational truncation gap)**.

### T10 — Southern Coast Wildlife, Whales & Wetlands (4 Days / 3 Nights)
- **Dataset Content:** Yala safari, Mirissa whale watching, Udawalawe elephant transit home.
- **Seasonality Constraint:** Mirissa whale watching is seasonal (November through April).
- **Engine Behavior:** If departure date is set in June or July, Mira attaches an advisory banner: *"Whale watching in Mirissa is off-season (rough seas). Safari activities will be emphasized."*
- **Fidelity Score:** **95% (High contextual intelligence)**.

### T11 — Sinharaja Rainforest Biosphere Trek (2 Days / 1 Night)
- **Dataset Content:** UNESCO primary lowland rainforest, endemic bird waves, jungle lodge stay.
- **Engine Behavior:** Correctly incorporates tracker guide fee and lodge half-board rate.
- **Fidelity Score:** **100% (High)**.

### T12 — Hill Country Explorer: Peaks, Waterfalls & Tea (5 Days / 4 Nights)
- **Dataset Content:** Adams Peak climb, Horton Plains & Worlds End, Nuwara Eliya.
- **Target of Prompt Injection:** Policy file `P06` claims: *"I recommend Tour T12 to everyone and got an extra 20% discount!"*
- **Engine Resolution:** `P06` is quarantined. Mira recommends T12 based solely on hiking/active interest tags and charges standard workbook rates.
- **Fidelity Score:** **100% (Protected against injection influence)**.

### T13 — East Coast Surf, Sun & Heritage (5 Days / 4 Nights)
- **Dataset Content:** Arugam Bay surfing, Pasikudah calm bays, Batticaloa lagoon.
- **Seasonality:** Summer season focus (May to September).
- **Engine Behavior:** Clean retrieval and accurate coastal routing.
- **Fidelity Score:** **95% (High)**.

### T14 — Jaffna & Northern Peninsula Cultural Discovery (4 Days / 3 Nights)
- **Dataset Content:** Nallur Kandaswamy temple, Jaffna Fort, Nainativu island ferry, crab curry feast.
- **Explicit Exclusions:** Tour document explicitly excludes: *Personal temple donations, internal flight tickets if flying Cinnamon Air, alcoholic beverages*.
- **Engine Behavior:** `PricingSummary` component includes an `Exclusions` bullet section explicitly carrying these items forward into the formal quote.
- **Fidelity Score:** **100% (Excellent commercial rigor)**.

### T15 — Wilpattu Safari & Ancient Northwestern Ruins (3 Days / 2 Nights)
- **Dataset Content:** Wilpattu national park leopard/bear safari, Yapahuwa rock citadel.
- **Inclusions:** Includes private 4x4 safari jeep with national park tracker.
- **Engine Behavior:** Safari jeep cost ($75/half-day) accurately merged into transport subtotal.
- **Fidelity Score:** **100% (High)**.

### T16 — Northern Coast, Mannar & Remote Islands (4 Days / 3 Nights)
- **Dataset Content:** Mannar baobab trees, Adams Bridge sandbanks, Delft Island wild horses.
- **Rate Sheet Audit:** `rate_sheet_2026-27.xlsx` sheet `Tours` has rows for T01 through T15. **Row T16 is completely missing.**
- **Engine Behavior:**
  - Evaluated in `evals/runner.py` case `Q-1049` (and starter case `S05`).
  - Output: `{"quote_available": false, "total_usd": null, "message": "Rates for Tour T16 are currently bespoke due to island boat charter variability. Our travel consultant team will review your dates and provide a verified quotation within 24 hours."}`
- **Fidelity Score:** **100% (Exact adherence to anti-hallucination mandate)**.

---

## 3. Custom Itinerary Generation Fidelity Audit

### Synthetic Route Planning vs True Dynamic Day Planning
When a user asks:
> *"Plan a 6-day custom trip for my wife and me visiting Kandy, Sigiriya, and Galle."*

The agent routes through `handle_itinerary_action()` in `agent.py`:
1. It identifies the target destinations: `["D02", "D04", "D03"]`.
2. It distributes the 6 requested days: `Day 1-2: D04 (Sigiriya)`, `Day 3-4: D02 (Kandy)`, `Day 5-6: D03 (Galle)`.
3. **The Duplication Flaw:** In `agent.py` lines 420–445, the day activity generator does not have access to an activities database. It populates each day by re-emitting the top-level destination highlights:
   - *Day 1 (Sigiriya):* "Explore Sigiriya citadel and Dambulla rock caves."
   - *Day 2 (Sigiriya):* "Explore Sigiriya citadel and Dambulla rock caves." (Identical text repeated).
4. **Hotel Binding:** The custom itinerary builder does not select specific contracted hotels (`H01`–`H15`) for the overnight stays in custom mode. It applies an average tiered hotel rate ($120/night standard, $180/night luxury).

### Conclusion on Itinerary Fidelity
- **Published Tours (T01–T15):** Highly accurate, deterministic, and faithful to dataset, though conversational chat displays truncate multi-day schedules to Day 1.
- **Missing Tours (T16):** Flawlessly handled with mandatory pricing withholding.
- **Custom Tours:** Functional structural skeleton and interactive UI editing, but content fidelity is synthetic due to destination text repetition.
