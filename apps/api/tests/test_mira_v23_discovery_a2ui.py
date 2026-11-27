"""MIRA V2.3 — Intent-aware discovery, multi-destination retrieval, and A2UI regression tests."""
import json
from uuid import uuid4


def send_turn(client, trip_id: str, content: str):
    run = str(uuid4())
    response = client.post(
        f"/api/agent?trip_id={trip_id}",
        json={
            "threadId": trip_id,
            "runId": run,
            "state": {},
            "tools": [],
            "context": [],
            "messages": [{"role": "user", "id": run, "content": content}],
            "forwardedProps": {},
        },
    )
    response.raise_for_status()
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert events[-1]["type"] == "RUN_FINISHED", events[-1]
    snapshots = [e["snapshot"] for e in events if e.get("type") == "STATE_SNAPSHOT"]
    turn = next(s["turn"] for s in reversed(snapshots) if "turn" in s)
    surface = next(s["surface"] for s in reversed(snapshots) if "surface" in s)
    return turn, surface


def test_v23_ella_and_mirissa_discovery_and_course_synonym(app_client):
    """Both standard phrasing and 'course' synonym retrieve T10 (covering Ella and Mirissa) with TourCard."""
    for prompt in [
        "What tours include Ella and Mirissa?",
        "what are the course that include Ella and Mirissa",
    ]:
        trip_id = app_client.post("/api/trips").json()["id"]
        turn, surface = send_turn(app_client, trip_id, prompt)
        cards = [c for c in turn["components"] if c["type"] == "TourCard"]
        assert [c["id"] for c in cards] == ["T10"], (prompt, turn)
        assert not any(c["type"] == "JourneyPlan" for c in turn["components"])
        assert any(m.get("updateComponents") for m in surface)


def test_v23_mountains_and_southern_coast_discovery(app_client):
    """Broad regional phrasing retrieves published TourCards instead of forcing custom planning."""
    trip_id = app_client.post("/api/trips").json()["id"]
    turn, _ = send_turn(
        app_client,
        trip_id,
        "Do you have any packages covering both the mountains and the southern coast?",
    )
    cards = [c for c in turn["components"] if c["type"] == "TourCard"]
    assert len(cards) >= 1
    assert not any(c["type"] == "JourneyPlan" for c in turn["components"])


def test_v23_partial_match_labeling_and_zero_match_honesty(app_client):
    """Multi-destination queries with no single exact tour label partial matches; zero-match returns none."""
    trip_id = app_client.post("/api/trips").json()["id"]
    # No single tour covers Jaffna + Mirissa? Jaffna is unknown/excluded, try Trincomalee/Anuradhapura + Mirissa
    turn_partial, _ = send_turn(app_client, trip_id, "What tours include Anuradhapura and Mirissa?")
    cards = [c for c in turn_partial["components"] if c["type"] == "TourCard"]
    assert cards
    assert "partial" in turn_partial["text"].lower()

    trip_id2 = app_client.post("/api/trips").json()["id"]
    turn_zero, _ = send_turn(app_client, trip_id2, "Show me tours that include downhill skiing in Ella")
    assert not [c for c in turn_zero["components"] if c["type"] == "TourCard"]


def test_v23_multi_turn_discovery_to_selection_to_custom_plan(app_client):
    """Multi-turn transition: Kandy/Ella/Galle discovery -> 2nd tour itinerary -> custom holiday -> 7 days."""
    trip_id = app_client.post("/api/trips").json()["id"]

    t4, _ = send_turn(app_client, trip_id, "Show me trips that visit Kandy, Ella and Galle.")
    assert {c["id"] for c in t4["components"] if c["type"] == "TourCard"} == {"T10", "T12"}

    t6, _ = send_turn(app_client, trip_id, "Can I see the itinerary of the second one?")
    assert any(c["type"] == "TourCard" and c["id"] == "T10" for c in t6["components"])
    assert any(c["type"] == "ItineraryDay" for c in t6["components"])
    assert "0-day" not in t6["text"]

    t7, _ = send_turn(app_client, trip_id, "Actually, I would prefer a custom holiday.")
    assert "how many days" in t7["text"].lower() or "destinations" in t7["text"].lower()

    t8, _ = send_turn(app_client, trip_id, "Let's make that holiday seven days.")
    assert "departure date" in t8["text"].lower() or "how many" in t8["text"].lower()
