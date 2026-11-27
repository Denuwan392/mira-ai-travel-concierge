"""Workflow tests for family holiday clarification, grounded custom plans, and package switching."""
import json
import sqlite3
from uuid import uuid4

from mira import agent, store
from mira.provider import NotebookIntent


def _send(client, trip_id: str, content: str, run_id: str | None = None):
    """Post a turn to ``/api/agent`` for ``trip_id`` and return the ``turn`` snapshot dict."""
    rid = run_id or str(uuid4())
    resp = client.post(
        "/api/agent",
        params={"trip_id": trip_id},
        json={
            "threadId": trip_id,
            "runId": rid,
            "messages": [{"id": rid, "role": "user", "content": content}],
            "state": {},
            "tools": [],
            "context": [],
            "forwardedProps": {},
        },
    )
    resp.raise_for_status()
    events = [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith("data: ")]
    return next(e["snapshot"]["turn"] for e in reversed(events) if e["type"] == "STATE_SNAPSHOT" and "turn" in e["snapshot"])


def test_broad_family_holiday_clarifies_without_default_two_days_or_enquiry(app_client, monkeypatch):
    """Even if LLM returns operation='plan' with no days/destinations, never invent 2 days or create a premature enquiry."""
    monkeypatch.setattr(
        agent,
        "notebook_intent",
        lambda *args, **kwargs: NotebookIntent(operation="plan", days=None, destinations=[]),
    )
    trip = app_client.post("/api/trips").json()["id"]
    turn = _send(app_client, trip, "Plan a family holiday")

    assert not any(c["type"] == "JourneyPlan" for c in turn["components"])
    assert not any(c["type"] == "EnquiryNotice" for c in turn["components"])
    assert "how many days" in turn["text"].lower()
    assert "ages of any children" in turn["text"].lower()
    assert "popular with families" in turn["text"].lower()

    with store.db() as conn:
        enq_count = conn.execute("SELECT COUNT(*) FROM enquiries").fetchone()[0]
    assert enq_count == 0


def test_complete_family_request_builds_grounded_itinerary_without_unrelated_cards(app_client):
    """A complete family request builds a grounded JourneyPlan with non-empty days and no unrelated T08/T10/T12 cards."""
    trip = app_client.post("/api/trips").json()["id"]
    turn = _send(app_client, trip, "We have 6 days for nature, scenic trains and beaches for 2 adults and a 7-year-old")

    plan = next(c for c in turn["components"] if c["type"] == "JourneyPlan")
    assert len(plan["days"]) == 6
    for idx, day in enumerate(plan["days"], start=1):
        assert isinstance(day.get("name"), str) and len(day["name"].strip()) > 0, f"Empty day {idx} name"
        assert isinstance(day.get("passage"), str) and len(day["passage"].strip()) > 0, f"Empty day {idx} passage"

    # Unrelated tour cards must not be mixed into the custom itinerary
    places = app_client.get("/api/guide").json()["places"]
    slugs = {slug for slug, place in places.items() if place["id"] in {day["source"] for day in plan["days"]}}
    tours = {t["id"]: t for t in app_client.get("/api/guide").json()["tours"]}
    for card in (c for c in turn["components"] if c["type"] == "TourCard"):
        assert slugs.intersection(tours[card["id"]]["places"])
    notice = next(c for c in turn["components"] if c["type"] == "EnquiryNotice")
    assert notice["public_reference"].startswith("ENQ-")

    # Minor edit (@day 2) must not duplicate the enquiry
    _send(app_client, trip, "@day 2")
    with store.db() as conn:
        enq_count = conn.execute("SELECT COUNT(*) FROM enquiries").fetchone()[0]
    assert enq_count == 1

def test_custom_to_published_package_preserves_only_current_quote_requirements(app_client):
    """Verify switching from a custom proposal to a published package clears custom state while keeping history."""
    trip = app_client.post("/api/trips").json()["id"]
    plan = _send(app_client, trip, "Design a 10-day custom journey across Kandy and Ella for a family of four")
    components = plan["components"]
    route = next(c for c in components if c["type"] == "InteractiveMap")
    assert {d["source"] for d in route["days"]} == {"D03", "D05"}
    assert not any(c["type"] == "PriceBreakdown" for c in components)
    guide = app_client.get("/api/guide").json()
    tours = {t["id"]: t for t in guide["tours"]}
    cards = [c for c in components if c["type"] == "TourCard"]
    assert cards
    assert all({"kandy", "ella"}.intersection(tours[c["id"]]["places"]) for c in cards)
    result = _send(app_client, trip, "Cultural Triangle Sri Lanka Package for 2 adults on 3 May 2027")
    quote = next(c["quote"] for c in result["components"] if c["type"] == "PriceBreakdown")
    assert (quote["source"], quote["date"], quote["adults"], quote["ages"]) == ("T09", "2027-05-03", 2, [])
    assert (quote["total"], quote["deposit"]) == (2125, 532)
    with store.db() as conn:
        ctx = json.loads(conn.execute("SELECT context FROM trips WHERE id=?", (trip,)).fetchone()[0])
    assert ctx["tour"] == "T09"
    assert "custom" not in ctx and "proposal" not in ctx
    # The switch updates active state while preserving the earlier itinerary in history.
    assert len(app_client.get("/api/trips/" + trip).json()["history"]) == 2


def test_date_edit_keeps_child_age_until_a_new_package_replaces_party(app_client):
    """Verify date-only updates retain child ages, while switching to a new adult-only package clears them."""
    trip = app_client.post("/api/trips").json()["id"]

    def quote(prompt):
        turn = _send(app_client, trip, prompt)
        return next(c["quote"] for c in turn["components"] if c["type"] == "PriceBreakdown")

    january = quote("Sigiriya day trip for 2 adults and 1 child aged 7 on 10 January 2027")
    assert january["ages"] == [7]
    updated = quote("Update the quote for this tour to 12 January 2027")
    assert (updated["date"], updated["adults"], updated["ages"]) == ("2027-01-12", 2, [7])
    package = quote("Cultural Triangle Sri Lanka Package for 2 adults on 3 May 2027")
    assert (package["date"], package["adults"], package["ages"], package["total"]) == ("2027-05-03", 2, [], 2125)
