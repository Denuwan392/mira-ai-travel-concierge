"""Regression tests for Mira's tour-category relevance and state consistency."""
import json
from uuid import uuid4

from mira.data import published
from mira.search import is_day_tour, is_multi_day_tour


def send_turn(client, trip_id, message):
    run_id = str(uuid4())
    resp = client.post(
        "/api/agent",
        params={"trip_id": trip_id},
        json={
            "threadId": trip_id,
            "runId": run_id,
            "messages": [{"id": run_id, "role": "user", "content": message}],
            "state": {},
            "tools": [],
            "context": [],
            "forwardedProps": {},
        },
    )
    resp.raise_for_status()
    events = [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith("data: ")]
    assert events[-1]["type"] == "RUN_FINISHED"
    snap = next(
        e["snapshot"]
        for e in reversed(events)
        if e["type"] == "STATE_SNAPSHOT" and "turn" in e["snapshot"]
    )
    return snap["turn"], snap["surface"]


def _cards(turn):
    return [c for c in turn["components"] if c["type"] == "TourCard"]


def _assert_valid_a2ui(turn, surface):
    assert surface[0]["version"] == "v0.9"
    assert surface[0]["createSurface"]["surfaceId"] == "journey"
    nodes = surface[1]["updateComponents"]["components"]
    assert nodes[0]["component"] == "JourneyColumn"
    all_tours = published()
    for card in _cards(turn):
        assert card["id"] in all_tours
        assert card["title"] == all_tours[card["id"]]["title"]
        assert card["category"] == all_tours[card["id"]]["category"]


def test_01_find_a_day_tour(app_client):
    trip_id = app_client.post("/api/trips").json()["id"]
    turn, surface = send_turn(app_client, trip_id, "Find a day tour")
    _assert_valid_a2ui(turn, surface)
    cards = _cards(turn)
    assert len(cards) >= 1
    tours = published()
    for card in cards:
        assert is_day_tour(tours[card["id"]]), f"Unexpected non-day tour {card['id']}"
    assert "day tour" in turn["text"].lower()
    assert "departure" in turn["text"].lower()


def test_02_one_day_trip_from_kandy(app_client):
    trip_id = app_client.post("/api/trips").json()["id"]
    turn, surface = send_turn(app_client, trip_id, "I want a one-day trip from Kandy")
    _assert_valid_a2ui(turn, surface)
    cards = _cards(turn)
    assert {c["id"] for c in cards} <= {"T01", "T02"}
    assert len(cards) == 2
    assert not any(c["type"] == "JourneyPlan" for c in turn["components"])


def test_03_seven_day_cultural_tour(app_client):
    trip_id = app_client.post("/api/trips").json()["id"]
    turn, surface = send_turn(app_client, trip_id, "Show me a seven-day cultural tour")
    _assert_valid_a2ui(turn, surface)
    cards = _cards(turn)
    assert len(cards) >= 1
    assert cards[0]["id"] == "T09"
    tours = published()
    for card in cards:
        assert is_multi_day_tour(tours[card["id"]])


def test_04_two_week_family_holiday(app_client):
    trip_id = app_client.post("/api/trips").json()["id"]
    turn, surface = send_turn(app_client, trip_id, "We want a two-week family holiday")
    _assert_valid_a2ui(turn, surface)
    cards = _cards(turn)
    assert len(cards) >= 1
    assert cards[0]["id"] == "T12"
    tours = published()
    for card in cards:
        assert is_multi_day_tour(tours[card["id"]])


def test_05_sigiriya_day_tour(app_client):
    trip_id = app_client.post("/api/trips").json()["id"]
    turn, surface = send_turn(app_client, trip_id, "Find a Sigiriya day tour")
    _assert_valid_a2ui(turn, surface)
    cards = _cards(turn)
    assert [c["id"] for c in cards] == ["T01"]
    assert any(c["type"] == "TravellerPicker" for c in turn["components"])


def test_06_only_have_one_day(app_client):
    trip_id = app_client.post("/api/trips").json()["id"]
    turn, surface = send_turn(app_client, trip_id, "I only have one day")
    _assert_valid_a2ui(turn, surface)
    cards = _cards(turn)
    assert len(cards) >= 1
    tours = published()
    for card in cards:
        assert is_day_tour(tours[card["id"]])
    assert not any(c["type"] == "JourneyPlan" for c in turn["components"])


def test_07_short_trip_not_multiday(app_client):
    trip_id = app_client.post("/api/trips").json()["id"]
    turn, surface = send_turn(app_client, trip_id, "I want a short trip, not a multi-day package")
    _assert_valid_a2ui(turn, surface)
    cards = _cards(turn)
    assert len(cards) >= 1
    tours = published()
    for card in cards:
        assert is_day_tour(tours[card["id"]])


def test_08_beach_tours(app_client):
    trip_id = app_client.post("/api/trips").json()["id"]
    turn, surface = send_turn(app_client, trip_id, "Show me beach tours")
    _assert_valid_a2ui(turn, surface)
    cards = _cards(turn)
    assert len(cards) >= 2
    ids = {c["id"] for c in cards}
    assert {"T11", "T05"}.issubset(ids)


def test_09_switch_to_multiday_instead(app_client):
    trip_id = app_client.post("/api/trips").json()["id"]
    turn1, _ = send_turn(app_client, trip_id, "Find a day tour")
    tours = published()
    assert all(is_day_tour(tours[c["id"]]) for c in _cards(turn1))

    turn2, surface2 = send_turn(app_client, trip_id, "Actually, I want a multi-day trip instead")
    _assert_valid_a2ui(turn2, surface2)
    cards2 = _cards(turn2)
    assert len(cards2) >= 1
    for card in cards2:
        assert is_multi_day_tour(tours[card["id"]])


def test_10_day_trip_four_adults_from_colombo(app_client):
    trip_id = app_client.post("/api/trips").json()["id"]
    turn, surface = send_turn(app_client, trip_id, "Find a day trip for four adults from Colombo")
    _assert_valid_a2ui(turn, surface)
    cards = _cards(turn)
    assert [c["id"] for c in cards] == ["T03"]
    picker = next(c for c in turn["components"] if c["type"] == "TravellerPicker")
    assert picker["tour"] == "T03"
    assert picker["adults"] == 4


def test_stale_selection_and_proposal_do_not_overwrite_day_tour_intent(app_client):
    trip_id = app_client.post("/api/trips").json()["id"]
    send_turn(app_client, trip_id, "Show me Highlights of Sri Lanka")
    turn2, surface2 = send_turn(app_client, trip_id, "Find a day tour")
    _assert_valid_a2ui(turn2, surface2)
    tours = published()
    cards2 = _cards(turn2)
    assert len(cards2) >= 1
    assert all(is_day_tour(tours[c["id"]]) for c in cards2)
    assert "T08" not in {c["id"] for c in cards2}


def test_no_matching_day_tour_explains_clearly(app_client):
    trip_id = app_client.post("/api/trips").json()["id"]
    turn, surface = send_turn(app_client, trip_id, "Find a day tour from Ella")
    _assert_valid_a2ui(turn, surface)
    assert _cards(turn) == []
    assert "couldn’t find" in turn["text"].lower()


def test_deterministic_filter_blocks_llm_multiday_leak(app_client, monkeypatch):
    from mira import agent

    monkeypatch.setattr(agent, "rank", lambda tours, trip, events: ["T08", "T10", "T12"])
    trip_id = app_client.post("/api/trips").json()["id"]
    turn, surface = send_turn(app_client, trip_id, "Find a day tour")
    _assert_valid_a2ui(turn, surface)
    tours = published()
    cards = _cards(turn)
    assert len(cards) >= 1
    assert all(is_day_tour(tours[c["id"]]) for c in cards)
    assert not {"T08", "T10", "T12"} & {c["id"] for c in cards}
