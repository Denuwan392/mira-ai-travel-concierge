# Itinerary Fidelity Results — Source Accuracy & Day-by-Day Grounding

This document records the exact parsed itinerary schedules for published multi-day packages and confirms that daily activities, accommodations, meal plans, and entrance tickets match the canonical documents.

---

## 1. Cultural Triangle Sri Lanka Package (T09) — 6 Nights / 7 Days

Source document: `content/tours/cultural-triangle-6-nights.md`

| Day | Canonical Title | Activities & Highlights | Meals | Accommodation | Entrance Tickets Included |
|:---:|-----------------|-------------------------|-------|---------------|---------------------------|
| **1** | Colombo to Anuradhapura | Drive north; visit Wilpattu's edge villages on the way. | Dinner | Anuradhapura Heritage Lodge or similar | None |
| **2** | Anuradhapura | The sacred city by bicycle: Sri Maha Bodhi, Ruwanwelisaya, and great dagobas. | Breakfast, Lunch, Dinner | Anuradhapura Heritage Lodge or similar | Anuradhapura sacred city |
| **3** | Anuradhapura to Sigiriya | Mihintale on the way; afternoon village tour. | Breakfast, Dinner | Sigiriya Village or similar | Mihintale, village tour |
| **4** | Sigiriya and Polonnaruwa | Sigiriya at sunrise, Polonnaruwa in the afternoon. | Breakfast, Dinner | Sigiriya Village or similar | Sigiriya, Polonnaruwa |
| **5** | Dambulla to Kandy | Dambulla cave temple and spice garden; evening Temple of the Tooth. | Breakfast, Dinner | Hotel Suisse, Hotel Topaz or similar | Dambulla, spice garden, Temple of the Tooth |
| **6** | Kandy | Peradeniya gardens and a Kandyan dance show. | Breakfast, Dinner | Hotel Suisse, Hotel Topaz or similar | Peradeniya gardens, cultural show |
| **7** | Kandy to Colombo | Drive back to Colombo or airport. | Breakfast | None | None |

---

## 2. Highlights of Sri Lanka (T08) — 7 Nights / 8 Days

Source document: `content/tours/highlights-of-sri-lanka-7-nights.md`

| Day | Canonical Title | Activities & Highlights | Meals | Accommodation | Entrance Tickets Included |
|:---:|-----------------|-------------------------|-------|---------------|---------------------------|
| **1** | Airport to Negombo | Airport meet-and-greet, coastal lagoon relaxation. | Dinner | Suriya Resort, Amaluna or similar | None |
| **2** | Negombo to Sigiriya | Drive through coconut plantations to Cultural Triangle. | Breakfast, Dinner | Sigiriya Village, Oak Ray Elephant Lake | Dambulla cave temple |
| **3** | Sigiriya and Polonnaruwa | Climb Sigiriya at sunrise; village tour with lotus leaf lunch; afternoon Polonnaruwa. | Breakfast, Lunch, Dinner | Sigiriya Village, Oak Ray Elephant Lake | Sigiriya, village tour, Polonnaruwa |
| **4** | Sigiriya to Kandy | Matale spice garden, Temple of the Sacred Tooth Relic. | Breakfast, Dinner | Hotel Suisse, Hotel Topaz or similar | Spice garden, Temple of the Tooth |
| **5** | Train to Nuwara Eliya | Scenic hill country train ride, Pedro tea estate, Little England tour. | Breakfast, Dinner | Heaven Seven or similar | Train ticket (2nd class), tea factory |
| **6** | Nuwara Eliya to South-West Coast | Descend tea hills past Devon and St. Clair's waterfalls to south-west beach. | Breakfast, Dinner | Hikka Tranz by Cinnamon, Avani Kalutara | None |
| **7** | South Coast | Full beach relaxation day or optional Galle Fort excursion. | Breakfast, Dinner | Hikka Tranz by Cinnamon, Avani Kalutara | None |
| **8** | Colombo and Departure | Colombo city sights and airport transfer. | Breakfast | None | None |

---

## 3. Targeted Itinerary Question Answering Verification

The following targeted inquiries were executed through `/api/agent` and verified:

1. **Query**: *"Show me the complete itinerary for Highlights of Sri Lanka."*
   - **Response**: Returns all 8 days as structured `ItineraryDay` UI components.
2. **Query**: *"What happens on Day 4 of T09?"*
   - **Response**: Details Day 4 (Sigiriya at sunrise, Polonnaruwa in the afternoon, Sigiriya Village accommodation, Sigiriya & Polonnaruwa entrance tickets).
3. **Query**: *"Which hotel do we stay in on Day 3 of Highlights of Sri Lanka?"*
   - **Response**: Pinpoints Day 3 accommodation: *Sigiriya Village, Oak Ray Elephant Lake or similar*.
4. **Query**: *"What is included on Day 5 of Highlights of Sri Lanka?"*
   - **Response**: Pinpoints Day 5 tickets: *Train ticket (2nd class), tea factory*, and *Heaven Seven* hotel.
5. **Query**: *"Are entrance tickets included on Highlights of Sri Lanka?"*
   - **Response**: Affirms all listed entrance tickets are included (except optional activities).
