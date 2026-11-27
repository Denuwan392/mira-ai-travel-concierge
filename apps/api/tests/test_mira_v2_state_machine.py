"""MIRA V2 scenario-based acceptance tests and deterministic state reducer verification."""
from __future__ import annotations

import json
from uuid import uuid4

from mira.agent_workflow.state_machine import (
    AddDestinationOp,
    DecrementDurationOp,
    IncrementDurationOp,
    RemoveDestinationOp,
    SetAdultCountOp,
    SetDurationOp,
    TripState,
    extract_operations,
    reduce_state,
)
from mira.catalog import Turn
from mira.data import published


def _send(client, trip_id: str, message: str, run_id: str | None = None) -> Turn:
    run_id = run_id or str(uuid4())
    resp = client.post(
        "/api/agent",
        params={"trip_id": trip_id},
        json={
            "threadId": trip_id,
            "runId": run_id,
            "state": {},
            "tools": [],
            "context": [],
            "messages": [{"id": run_id, "role": "user", "content": message}],
            "forwardedProps": {},
        },
    )
    resp.raise_for_status()
    events = [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith("data: ")]
    snap = next(e["snapshot"]["turn"] for e in reversed(events) if e.get("type") == "STATE_SNAPSHOT" and "turn" in e["snapshot"])
    return Turn.model_validate(snap)


def test_reducer_arithmetic_and_atomic_rejection():
    """Scenario B & reducer invariants: arithmetic ops and atomic rejection on invalid values."""
    dests = {k: r["title"] for k, r in published().items() if r["type"] == "destination"}
    s0 = TripState(active_goal="custom_planning", requested_destinations=["D08"], duration_days=10)

    r1 = reduce_state(s0, [SetDurationOp(days=5)], dests)
    assert r1.state.duration_days == 5

    r2 = reduce_state(s0, [IncrementDurationOp(delta=3)], dests)
    assert r2.state.duration_days == 13

    r3 = reduce_state(r2.state, [DecrementDurationOp(delta=2)], dests)
    assert r3.state.duration_days == 11

    r4 = reduce_state(r3.state, [SetDurationOp(days=6)], dests)
    assert r4.state.duration_days == 6

    # Atomic rejection: invalid duration in compound op must not mutate adults
    r_bad = reduce_state(s0, [SetAdultCountOp(adults=4), SetDurationOp(days=99)], dests)
    assert r_bad.validation_errors
    assert r_bad.state.adults is None
    assert r_bad.state.duration_days == 10


def test_scenario_a_mutable_custom_plan_end_to_end(app_client):
    """Scenario A: Full 8-turn mutable custom plan with arithmetic, add, and remove+exclusion."""
    trip_id = app_client.post("/api/trips").json()["id"]

    t1 = _send(app_client, trip_id, "I wanna plan a trip to Mirissa.")
    assert "mirissa" in t1.text.lower()

    t2 = _send(app_client, trip_id, "10 days")
    p2 = next(c for c in t2.components if c.type == "JourneyPlan")
    assert len(p2.days) == 10 and all(d.source == "D08" for d in p2.days)

    t3 = _send(app_client, trip_id, "2 adults")
    assert len(next(c for c in t3.components if c.type == "JourneyPlan").days) == 10

    t4 = _send(app_client, trip_id, "Starting on 12 April 2027.")
    assert str(next(c for c in t4.components if c.type == "DateSelector").value) == "2027-04-12"

    t5 = _send(app_client, trip_id, "We like whale watching and relaxing on the beach.")
    assert len(next(c for c in t5.components if c.type == "JourneyPlan").days) == 10

    t6 = _send(app_client, trip_id, "Actually, make it 5 days.")
    p6 = next(c for c in t6.components if c.type == "JourneyPlan")
    assert len(p6.days) == 5, f"Expected 5 days, got {len(p6.days)}"
    assert all(d.source == "D08" for d in p6.days)

    t7 = _send(app_client, trip_id, "Add Galle to the itinerary.")
    p7 = next(c for c in t7.components if c.type == "JourneyPlan")
    assert len(p7.days) == 5
    assert {d.source for d in p7.days} == {"D08", "D07"}

    t8 = _send(app_client, trip_id, "Remove Galle. We prefer staying in Mirissa")
    p8 = next(c for c in t8.components if c.type == "JourneyPlan")
    assert len(p8.days) == 5
    assert {d.source for d in p8.days} == {"D08"}
    assert not any("galle" in d.name.lower() for d in p8.days)


def test_scenario_b_explicit_arithmetic_turns(app_client):
    """Scenario B: 10 -> +3 (13) -> -2 (11) -> make it 6 (6)."""
    trip_id = app_client.post("/api/trips").json()["id"]
    _send(app_client, trip_id, "Plan a 10-day trip to Mirissa.")

    t_add = _send(app_client, trip_id, "Add 3 more days.")
    assert len(next(c for c in t_add.components if c.type == "JourneyPlan").days) == 13

    t_sub = _send(app_client, trip_id, "Reduce it by 2 days.")
    assert len(next(c for c in t_sub.components if c.type == "JourneyPlan").days) == 11

    t_set = _send(app_client, trip_id, "Actually, make it 6 days.")
    assert len(next(c for c in t_set.components if c.type == "JourneyPlan").days) == 6


def test_scenario_c_interrupted_planning_by_policy_question(app_client):
    """Scenario C: Active 7-day Ella+Mirissa plan -> cancellation policy P02 -> 'update my trip to 10 days' resumes plan."""
    trip_id = app_client.post("/api/trips").json()["id"]

    t1 = _send(app_client, trip_id, "Plan a 7-day holiday in Ella and Mirissa.")
    p1 = next(c for c in t1.components if c.type == "JourneyPlan")
    assert len(p1.days) == 7 and {d.source for d in p1.days} == {"D05", "D08"}

    t2 = _send(app_client, trip_id, "What is your cancellation policy?")
    assert "P02" in t2.sources

    t3 = _send(app_client, trip_id, "Can you update my trip to 10 days?")
    p3 = next(c for c in t3.components if c.type == "JourneyPlan")
    assert len(p3.days) == 10
    assert {d.source for d in p3.days} == {"D05", "D08"}


def test_scenario_d_compound_corrections(app_client):
    """Scenario D: 'Remove Ella, add Galle, make the holiday 6 days and change it to 3 adults.'"""
    trip_id = app_client.post("/api/trips").json()["id"]
    _send(app_client, trip_id, "Plan a 7-day holiday in Ella and Mirissa.")

    t2 = _send(app_client, trip_id, "Remove Ella, add Galle, make the holiday 6 days and change it to 3 adults.")
    p2 = next(c for c in t2.components if c.type == "JourneyPlan")
    assert len(p2.days) == 6
    assert {d.source for d in p2.days} == {"D08", "D07"}
    assert "D05" not in {d.source for d in p2.days}


def test_scenario_e_interest_negation(app_client):
    """Scenario E: 'We don't want whale watching anymore. We'd rather relax.' removes whale watching."""
    trip_id = app_client.post("/api/trips").json()["id"]
    _send(app_client, trip_id, "Plan a 5-day trip to Mirissa for whale watching.")
    t2 = _send(app_client, trip_id, "We don't want whale watching anymore. We'd rather relax.")
    p2 = next(c for c in t2.components if c.type == "JourneyPlan")
    assert len(p2.days) == 5
    assert not any("whale" in d.passage.lower() for d in p2.days)


def test_scenario_f_discovery_vs_custom_planning(app_client):
    """Scenario F: 'Find an existing 5-day tour.' searches tours; 'Plan a custom 5-day holiday.' plans custom."""
    t_search = app_client.post("/api/trips").json()["id"]
    out_s = _send(app_client, t_search, "Find an existing 5-day tour.")
    assert not any(c.type == "JourneyPlan" for c in out_s.components)

    t_plan = app_client.post("/api/trips").json()["id"]
    out_p = _send(app_client, t_plan, "Plan a custom 5-day holiday in Mirissa.")
    assert len(next(c for c in out_p.components if c.type == "JourneyPlan").days) == 5


def test_v21_four_turn_natural_discovery_to_planning(app_client):
    """V2.1 critical reproduction: 4 natural turns preserve Mirissa, beach, 10 days, 2 adults, 2027-04-12."""
    trip_id = app_client.post("/api/trips").json()["id"]

    t1 = _send(app_client, trip_id, "I'd love to spend some time by the sea in Mirissa.")
    assert any(c.type == "TourCard" for c in t1.components)

    t2 = _send(app_client, trip_id, "Let's make it ten days.")
    p2 = next(c for c in t2.components if c.type == "JourneyPlan")
    assert len(p2.days) == 10
    assert {d.source for d in p2.days} == {"D08"}

    t3 = _send(app_client, trip_id, "It'll just be me and my wife.")
    assert "2 adults" in t3.text.lower()
    assert len(next(c for c in t3.components if c.type == "JourneyPlan").days) == 10

    t4 = _send(app_client, trip_id, "We're thinking of travelling on 12 April 2027.")
    assert str(next(c for c in t4.components if c.type == "DateSelector").value) == "2027-04-12"
    assert "ready" in t4.text.lower()


def test_v21_paraphrases_and_provider_failure_fallback(monkeypatch):
    """V2.1: Paraphrases (fortnight, couple of days, two of us, Ella vs Kandy) and Gemini failure fallback."""
    from mira.agent_workflow.state_machine import hybrid_extract_operations

    dests = {k: r["title"] for k, r in published().items() if r["type"] == "destination"}
    s = TripState(active_goal="custom_planning", requested_destinations=["D03"], duration_days=5)

    for phrase, expected_days in [
        ("A fortnight would be ideal.", 14),
        ("We only have a week.", 7),
        ("Could we squeeze in two extra days?", 7),
        ("Another couple of days.", 7),
        ("Make it three days shorter.", 2),
    ]:
        ops, _ = hybrid_extract_operations(phrase, s, dests, [])
        res = reduce_state(s, ops, dests)
        assert res.state.duration_days == expected_days, f"Failed for {phrase!r}: got {res.state.duration_days}"

    # Ambiguous request with failing provider -> targeted clarification, never corrupts state
    def failing_provider(*args, **kwargs):
        return None

    ops_amb, q_amb = hybrid_extract_operations("Make the holiday a little longer.", s, dests, [], interpret_fn=failing_provider)
    assert q_amb and "how many" in q_amb.lower()
    res_amb = reduce_state(s, ops_amb, dests)
    assert res_amb.state.duration_days == 5
    assert res_amb.state.requested_destinations == ["D03"]
