"""Regression tests for Mira's tour-category relevance and state consistency."""
import json
from uuid import uuid4

from mira.data import published
from mira.search import is_day_tour, is_multi_day_tour


def send_turn(client, trip_id, message):
    """Post a turn to ``/api/agent`` for ``trip_id`` and return ``(turn_dict, surface_list)``."""
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
    """Extract all ``TourCard`` dicts from a turn's component list."""
    return [c for c in turn["components"] if c["type"] == "TourCard"]


def _assert_valid_a2ui(turn, surface):
    """Assert v0.9 A2UI surface structure and that all ``TourCard`` metadata matches published records."""
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


def test_paraphrased_mountain_scenery_cool_weather_offline(app_client):
    """Gemini-unavailable fallback must still recommend hill-country/scenic tours, not generic T01/T09/T05."""
    trip_id = app_client.post("/api/trips").json()["id"]
    turn, surface = send_turn(
        app_client,
        trip_id,
        "I want a peaceful holiday somewhere surrounded by mountains, with beautiful scenery and cool weather.",
    )
    _assert_valid_a2ui(turn, surface)
    card_ids = [c["id"] for c in _cards(turn)]
    assert len(card_ids) >= 1
    assert card_ids != ["T01", "T09", "T05"]
    tours = published()
    assert any(
        any(dest in {"nuwara-eliya", "ella"} for dest in tours[tid]["destinations"])
        for tid in card_ids
    ), f"Expected hill-country tours, got {card_ids}"


def test_paraphrased_preferences_preserved_to_rank_without_limited_service(app_client, monkeypatch):
    """Semantic preferences must reach provider.rank() and avoid 'Limited service' when Gemini succeeds."""
    from mira import agent, provider

    captured = {}

    def fake_intent(prompt, previous, destinations, events, evidence=None):
        events.append({"stage": "gemini_intent", "outcome": "ok", "ms": 1})
        return provider.NotebookIntent(operation="catalogue", destinations=[])

    def fake_rank(tours, trip, events):
        captured["trip"] = dict(trip)
        events.append({"stage": "gemini_suggestions", "outcome": "ok", "ms": 1})
        return [tid for tid in ("T06", "T08", "T12") if tid in tours]

    monkeypatch.setattr(agent, "notebook_intent", fake_intent)
    monkeypatch.setattr(agent, "rank", fake_rank)

    trip_id = app_client.post("/api/trips").json()["id"]
    turn, surface = send_turn(
        app_client,
        trip_id,
        "I want a peaceful holiday somewhere surrounded by mountains, with beautiful scenery and cool weather.",
    )
    _assert_valid_a2ui(turn, surface)
    assert "preferences" in captured["trip"]
    assert "mountains" in captured["trip"]["preferences"]
    assert "limited service" not in turn["text"].lower()
    assert [c["id"] for c in _cards(turn)] == ["T06", "T08", "T12"]


def test_malformed_or_empty_suggestions_rejected_and_falls_back(app_client, monkeypatch):
    """Empty or malformed Suggestions JSON must fail schema validation and fall back to relevant tours."""
    import pytest
    from pydantic import ValidationError
    from mira import agent, provider

    with pytest.raises(ValidationError):
        provider.Suggestions.model_validate_json('{"tour_ids": []}')

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setattr(
        provider,
        "generate_structured",
        lambda schema, instructions, usage_out=None: (_ for _ in ()).throw(ValueError("empty or malformed")),
    )
    # Use default agent.rank -> provider.rank which calls provider.generate_structured
    monkeypatch.setattr(agent, "rank", provider.rank)

    trip_id = app_client.post("/api/trips").json()["id"]
    turn, surface = send_turn(
        app_client,
        trip_id,
        "I want a peaceful holiday somewhere surrounded by mountains, with beautiful scenery and cool weather.",
    )
    _assert_valid_a2ui(turn, surface)
    card_ids = [c["id"] for c in _cards(turn)]
    assert card_ids != ["T01", "T09", "T05"]
    assert "limited service" in turn["text"].lower()


def test_irrelevant_llm_recommendations_filtered_by_constraints(app_client, monkeypatch):
    """Irrelevant LLM tour IDs outside filtered scenic pool must be rejected."""
    from mira import agent

    monkeypatch.setattr(agent, "rank", lambda tours, trip, events: ["T03", "T05", "T11"])
    trip_id = app_client.post("/api/trips").json()["id"]
    turn, surface = send_turn(
        app_client,
        trip_id,
        "I want a peaceful holiday somewhere surrounded by mountains, with beautiful scenery and cool weather.",
    )
    _assert_valid_a2ui(turn, surface)
    card_ids = [c["id"] for c in _cards(turn)]
    assert not {"T03", "T05", "T11"} & set(card_ids)
    tours = published()
    assert any(
        any(dest in {"nuwara-eliya", "ella"} for dest in tours[tid]["destinations"])
        for tid in card_ids
    )
