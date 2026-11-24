# Tour Itinerary Fidelity & Day-by-Day Grounding

This document demonstrates the structural fidelity, Day-by-Day parsing accuracy, and retrieval capabilities of Mira v3 across published multi-day packages and custom route planners.

---

## 1. Multi-Day Tour Itinerary Parser Implementation

Tour markdown files in the canonical dataset contain detailed, day-by-day schedules under `### Day <N>: <Title>` sections. Previously, systems frequently collapsed these into a single truncated summary or lost day boundaries entirely.

In Mira v3:
- Every tour document is parsed using `apps/api/mira/itinerary_parser.py`.
- Parsed schedules are retained in `content()["tours"][tour_id]["itinerary"]`.
- When a traveller asks to see the full itinerary of a tour (e.g., "Show me the full Cultural Triangle Sri Lanka Package itinerary" or "What is the day-by-day schedule for T08?"), Mira surfaces **every single day** as an individual, structured `ItineraryDay` component.

### Example: T09 Cultural Triangle (6N / 7D) Day Breakdown

| Day | Title | Key Activities | Accommodation |
|:---:|-------|----------------|---------------|
| **1** | Arrival & Negombo Relaxation | Airport transfer, Negombo lagoon sunset | Jetwing Sea / Goldi Sands |
| **2** | Sacred City of Anuradhapura | Ruwanwelisaya, Sri Maha Bodhi, Jetavanaramaya | Heritage Hotel Anuradhapura |
| **3** | Mihintale & Journey to Sigiriya | Cradle of Buddhism at Mihintale, Dambulla Cave Temple | Cinnamon Lodge Habarana |
| **4** | Sigiriya Rock Fortress & Village Tour | Morning Sigiriya climb, Habarana traditional ox-cart village experience | Cinnamon Lodge Habarana |
| **5** | Ancient Polonnaruwa & Minneriya Safari | Royal Palace, Gal Vihara stone Buddhas, afternoon elephant safari | Cinnamon Lodge Habarana |
| **6** | Matale Spice Gardens to Kandy | Spice garden tour, Temple of the Sacred Tooth Relic, cultural dance show | Earl's Regency Kandy |
| **7** | Peradeniya Botanical Gardens & Departure | Royal Botanical Gardens orchids, scenic transit to Colombo/BIA airport | Departure |

---

## 2. Day-Specific Querying

When travellers ask targeted questions about a specific day:
- Query: *"What happens on Day 4 of T09?"*
- System Behavior:
  1. Detects `day 4` and tour `T09`.
  2. Retrieves `itinerary.days[3]` from the parsed document.
  3. Returns a focused narrative describing the early morning Sigiriya Rock climb and afternoon Habarana village tour.
  4. Attaches an `ItineraryDay` component with `day_number = 4`, `title = "Sigiriya Rock Fortress & Habarana Village Tour"`, and exact inclusions.

---

## 3. Grounded Custom Route Generation (No Text Duplication)

In custom travel planning (via `apps/ceylon-compass/` Notebook & LiveCanvas):
- When a traveller plans a custom trip spanning multiple days (e.g. 6 days covering Sigiriya, Kandy, Nuwara Eliya, Ella, Mirissa, Galle):
  - Previously, systems would reuse the generic destination overview paragraph for every day spent in that region, causing repetitive text.
  - In Mira v3, `apps/api/mira/planner.py` maintains an activity bank (`DESTINATION_ACTIVITIES`) containing **at least 3 distinct, grounded experiences** for each of the 10 destinations (D01–D10).
  - When allocating multiple days to a destination (e.g. 2 days in Ella or 3 days in Sigiriya), the planner indexes distinct activities:
    - *Sigiriya Day 1*: Lion Rock morning climb and Pidurangala sunset view.
    - *Sigiriya Day 2*: Minneriya / Kaudulla National Park elephant gathering safari.
    - *Sigiriya Day 3*: Dambulla cave temple painted murals and traditional Habarana village tour.
- Every generated passage is distinct, geographically accurate, and grounded in canonical dataset attractions.
