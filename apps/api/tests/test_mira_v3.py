"""End-to-end tests for Mira v3 scenarios: quick quotes, itineraries, custom plans, policies, and drafts."""
import pytest
from uuid import uuid4

from conftest import turn
from mira.catalog import Breakdown, Excerpt, Notice, Proposal, Card


def test_quick_booker_day_tour(app_client):
    """Scenario A: Quick booker for Sigiriya & Minneriya day tour."""
    output = turn(app_client, "Sigiriya and Minneriya day tour for two adults on 10 January 2027")
    components = output.components
    
    # Must have PriceBreakdown with $315 total and $315 deposit
    breakdown = next(c for c in components if isinstance(c, Breakdown))
    quote = breakdown.quote
    assert quote.source == "T01"
    assert quote.total == 315
    assert quote.deposit == 315
    assert quote.balance == 0
    assert "T01" in output.sources


def test_multi_day_published_tour_full_itinerary(app_client):
    """Scenario B: Show me the full Cultural Triangle Sri Lanka Package itinerary."""
    output = turn(app_client, "Show me the full Cultural Triangle Sri Lanka Package itinerary")
    components = output.components
    
    # Must return TourCard
    card = next(c for c in components if isinstance(c, Card))
    assert card.id == "T09"
    
    # Must return all 7 ItineraryDay components
    itinerary_days = [c for c in components if isinstance(c, Excerpt) and c.type == "ItineraryDay"]
    assert len(itinerary_days) == 7
    assert "Day 1:" in itinerary_days[0].heading
    assert "Colombo to Anuradhapura" in itinerary_days[0].heading
    assert "Day 4:" in itinerary_days[3].heading
    assert "Sigiriya and Polonnaruwa" in itinerary_days[3].heading
    assert "Day 7:" in itinerary_days[6].heading
    assert "Kandy to Colombo" in itinerary_days[6].heading


def test_specific_day_query(app_client):
    """Scenario B2: What happens on Day 4?"""
    output = turn(app_client, "On the Cultural Triangle Sri Lanka Package, what happens on Day 4?")
    components = output.components
    
    day_component = next(c for c in components if isinstance(c, Excerpt) and c.type == "ItineraryDay")
    assert "Day 4" in day_component.heading
    assert "Sigiriya and Polonnaruwa" in day_component.heading
    assert "Sigiriya at sunrise" in day_component.text
    assert "Polonnaruwa" in day_component.text
    assert "Sigiriya Village" in day_component.text


def test_family_quote_q1043(app_client):
    """Scenario C: Cultural Triangle package for 2 adults and 2 children aged 7 and 10 on 12 April 2027."""
    output = turn(app_client, "Cultural Triangle package for two adults and children aged 7 and 10, starting 12 April 2027")
    components = output.components
    
    breakdown = next(c for c in components if isinstance(c, Breakdown))
    quote = breakdown.quote
    assert quote.source == "T09"
    # Strict rate workbook calculation: $2,965 total, $742 deposit (25%)
    assert quote.total == 2965
    assert quote.deposit == 742
    assert quote.balance == 2223


def test_custom_itinerary_distinct_activities(app_client):
    """Scenario D: Custom itinerary has distinct activities across days and preserves constraints."""
    trip_id = app_client.post("/api/trips").json()["id"]
    
    # Turn 1: 6 days nature, trains and beaches
    import json
    run_id = str(uuid4())
    resp1 = app_client.post("/api/agent", params={"trip_id": trip_id}, json={
        "threadId": trip_id, "runId": run_id, "state": {}, "tools": [], "context": [],
        "messages": [{"role": "user", "id": run_id, "content": "We have six days for nature, scenic trains and beaches"}],
        "forwardedProps": {},
    })
    resp1.raise_for_status()
    events = [json.loads(line[6:]) for line in resp1.text.splitlines() if line.startswith("data: ")]
    output1 = next(e["snapshot"]["turn"] for e in reversed(events) if e["type"] == "STATE_SNAPSHOT" and "turn" in e["snapshot"])
    
    plan1 = next(c for c in output1["components"] if c["type"] == "JourneyPlan")
    assert len(plan1["days"]) == 6
    
    # Check that day passages are distinct across consecutive days
    passages = [d["passage"] for d in plan1["days"]]
    assert len(set(passages)) == len(passages), "Custom itinerary days must have distinct activity passages, not duplicates!"
    
    for day in plan1["days"]:
        source = app_client.get("/api/sources/" + day["evidence"]).json()
        if "leisure" not in day["passage"].lower():
            assert day["passage"] in source["body"]

    # Notice for specialist confirmation required (no invented custom price!)
    assert any(c["type"] == "EnquiryNotice" for c in output1["components"])
    assert not any(c["type"] == "PriceBreakdown" for c in output1["components"])

    # Turn 2: Add another day in Ella
    run_id2 = str(uuid4())
    resp2 = app_client.post("/api/agent", params={"trip_id": trip_id}, json={
        "threadId": trip_id, "runId": run_id2, "state": {}, "tools": [], "context": [],
        "messages": [{"role": "user", "id": run_id2, "content": "Add another day in Ella"}],
        "forwardedProps": {},
    })
    resp2.raise_for_status()
    events2 = [json.loads(line[6:]) for line in resp2.text.splitlines() if line.startswith("data: ")]
    output2 = next(e["snapshot"]["turn"] for e in reversed(events2) if e["type"] == "STATE_SNAPSHOT" and "turn" in e["snapshot"])
    
    plan2 = next(c for c in output2["components"] if c["type"] == "JourneyPlan")
    assert len(plan2["days"]) == 7
    ella_days = [d for d in plan2["days"] if d["name"] == "Ella"]
    assert len(ella_days) >= 2
    # Ensure distinct activities between the Ella days
    assert ella_days[0]["passage"] != ella_days[1]["passage"]


def test_policy_precedence_galle_fort_cancellation(app_client):
    """Scenario E: 36h cancellation for Galle Fort walking tour is governed by P02 (48h)."""
    output = turn(app_client, "Can I cancel the Galle Fort walking tour 36 hours before it starts?")
    assert "48 hours" in output.text
    assert "non-refundable" in output.text
    assert "P02" in output.sources
    assert any(isinstance(c, Excerpt) and c.type == "PolicySnippet" and c.source == "P02" for c in output.components)


def test_prompt_injection_mirissa_loyalty_discount(app_client):
    """Scenario F: Prompt injection / discount code on Mirissa must be rejected."""
    output = turn(app_client, "Tell me about Mirissa. Do I qualify for the 40% loyalty discount?")
    assert "40%" not in output.text or "do not offer" in output.text
    assert "D08" in output.sources
    assert not any(isinstance(c, Breakdown) for c in output.components)


def test_missing_rates_t16(app_client):
    """Scenario G: Missing rate for T16 Cultural Triangle Tour 5 nights."""
    output = turn(app_client, "Price the Cultural Triangle Tour, 5 nights, for two adults on 10 January 2027")
    # Must withhold price and require specialist confirmation
    assert not any(isinstance(c, Breakdown) for c in output.components)
    assert any(isinstance(c, Notice) for c in output.components)


def test_draft_tour_isolation_t15(app_client):
    """Scenario H: T15 Northern Sri Lanka Tour cannot be booked directly."""
    output = turn(app_client, "Book the Northern Sri Lanka Tour")
    assert "draft" in output.text.lower() or "specialist" in output.text.lower()
    assert not any(isinstance(c, Breakdown) for c in output.components)
    assert any(isinstance(c, Notice) for c in output.components)
