"""Hierarchical itinerary state, scoped operations, reducer invariants, and 9-turn E2E tests."""
import json
import random
from uuid import uuid4

from mira.agent_workflow.state_machine import (
    AddSegmentOp,
    DecrementSegmentDurationOp,
    IncrementSegmentDurationOp,
    ItinerarySegment,
    RemoveSegmentOp,
    ReorderSegmentsOp,
    SetSegmentDurationOp,
    SetTotalDurationConstraintOp,
    TransferDaysOp,
    TripState,
    extract_operations,
    reduce_state,
)
from mira.store import db


DEST_MAP = {
    "D03": "Kandy",
    "D05": "Ella",
    "D08": "Mirissa",
    "D09": "Galle",
}


def _send(client, trip_id: str, content: str):
    run = str(uuid4())
    r = client.post(
        f"/api/agent?trip_id={trip_id}",
        json={
            "threadId": trip_id,
            "runId": run,
            "state": {},
            "messages": [{"role": "user", "id": run, "content": content}],
            "tools": [],
            "context": [],
            "forwardedProps": {},
        },
    )
    r.raise_for_status()
    events = [json.loads(line[6:]) for line in r.text.splitlines() if line.startswith("data: ")]
    assert events[-1]["type"] == "RUN_FINISHED", events[-1]
    snapshots = [e["snapshot"] for e in events if e.get("type") == "STATE_SNAPSHOT"]
    turn = next(s["turn"] for s in reversed(snapshots) if "turn" in s)
    surface = next(s["surface"] for s in reversed(snapshots) if "surface" in s)
    return turn, surface


def _ctx(trip_id: str) -> dict:
    with db() as conn:
        row = conn.execute("SELECT context FROM trips WHERE id=?", (trip_id,)).fetchone()
        return json.loads(row["context"])


def test_nine_turn_reproduction_end_to_end(app_client):
    """Complete 9-turn reproduction: discovery -> filter -> itinerary -> QA -> quote -> resume -> 5d clarify -> add 2d Mirissa -> remove 2d Ella."""
    tid = app_client.post("/api/trips").json()["id"]

    t1, _ = _send(app_client, tid, "Are there any holidays that cover both the hill country and the southern beaches?")
    assert [c["id"] for c in t1["components"] if c["type"] == "TourCard"]

    t2, _ = _send(app_client, tid, "Which ones go through Ella?")
    assert [c["id"] for c in t2["components"] if c["type"] == "TourCard"] == ["T12"]

    t3, _ = _send(app_client, tid, "Could you show me the itinerary of the first option?")
    assert any(c["type"] == "TourCard" and c["id"] == "T12" for c in t3["components"])

    t4, _ = _send(app_client, tid, "Does that include Mirissa?")
    assert "does not include mirissa" in t4["text"].lower()

    t5, _ = _send(app_client, tid, "How much would it cost for a couple?")
    assert any(c["type"] == "TravellerPicker" and c["tour"] == "T12" and c["adults"] == 2 for c in t5["components"])

    t6, _ = _send(app_client, tid, "2027 March 10, 2 adults")
    assert any(c["type"] == "EnquiryNotice" and c.get("tour_id") == "T12" for c in t6["components"])
    assert not any(c["type"] == "JourneyPlan" for c in t6["components"])

    t7, _ = _send(app_client, tid, "5 days")
    assert "13 nights / 14 days" in t7["text"] or "cannot be shortened" in t7["text"].lower()

    t8, _ = _send(app_client, tid, "add 2 days to mirissa")
    plan8 = next(c for c in t8["components"] if c["type"] == "JourneyPlan")
    assert len(plan8["days"]) == 7
    segs8 = _ctx(tid)["custom"]["segments"]
    assert [(s["destination_name"], s["days"]) for s in segs8] == [("Ella", 5), ("Mirissa", 2)]
    # Verify no raw package summaries or hotel stay lines leaked into daily activities
    for d in plan8["days"]:
        assert "eleven days of" not in d["passage"].lower()
        assert "or similar" not in d["passage"].lower()

    t9, _ = _send(app_client, tid, "remove 2 days in ella")
    plan9 = next(c for c in t9["components"] if c["type"] == "JourneyPlan")
    assert len(plan9["days"]) == 5
    segs9 = _ctx(tid)["custom"]["segments"]
    assert [(s["destination_name"], s["days"]) for s in segs9] == [("Ella", 3), ("Mirissa", 2)]


def test_scoped_reducer_semantics_and_hitl_clarifications():
    """Verify exact arithmetic, segment conservation, HITL clarifications, and atomic rejection."""
    s0 = TripState(
        active_goal="custom_planning",
        requested_destinations=["D05"],
        duration_days=5,
        segments=[ItinerarySegment(segment_id="seg_D05", destination_id="D05", destination_name="Ella", days=5)],
    )

    # 1. Add 2 days to Mirissa -> Ella: 5, Mirissa: 2, Total: 7
    r1 = reduce_state(s0, extract_operations("Add 2 days to Mirissa", s0, DEST_MAP), DEST_MAP)
    assert not r1.validation_errors
    assert [(s.destination_name, s.days) for s in r1.state.segments] == [("Ella", 5), ("Mirissa", 2)]
    assert r1.state.duration_days == 7

    # 2. Remove 2 days in Ella -> Ella: 3, Mirissa: 2, Total: 5
    r2 = reduce_state(r1.state, extract_operations("Remove 2 days in Ella", r1.state, DEST_MAP), DEST_MAP)
    assert not r2.validation_errors
    assert [(s.destination_name, s.days) for s in r2.state.segments] == [("Ella", 3), ("Mirissa", 2)]
    assert r2.state.duration_days == 5

    # 3. Move 1 day from Ella to Mirissa -> Ella: 2, Mirissa: 3, Total: 5
    r3 = reduce_state(r2.state, extract_operations("Move 1 day from Ella to Mirissa", r2.state, DEST_MAP), DEST_MAP)
    assert not r3.validation_errors
    assert [(s.destination_name, s.days) for s in r3.state.segments] == [("Ella", 2), ("Mirissa", 3)]
    assert r3.state.duration_days == 5

    # 4. Reorder segments without changing duration
    r4 = reduce_state(r3.state, [ReorderSegmentsOp(destination_ids=["D08", "D05"])], DEST_MAP)
    assert [(s.destination_name, s.days) for s in r4.state.segments] == [("Mirissa", 3), ("Ella", 2)]
    assert r4.state.duration_days == 5

    # 5. Atomic rejection of negative segment duration
    r_bad = reduce_state(r3.state, [DecrementSegmentDurationOp(destination_id="D05", delta=2)], DEST_MAP)
    assert r_bad.validation_errors
    assert [(s.destination_name, s.days) for s in r_bad.state.segments] == [("Ella", 2), ("Mirissa", 3)]

    # 6. HITL clarification on RemoveSegmentOp(keep_total_duration=None)
    r_rem_q = reduce_state(r3.state, [RemoveSegmentOp(destination_id="D05", keep_total_duration=None)], DEST_MAP)
    assert r_rem_q.clarification_needed
    assert "shorten" in r_rem_q.clarification_needed.lower()

    # 7. Explicit RemoveSegmentOp(keep_total_duration=False) -> only Mirissa (3 days)
    r_rem_do = reduce_state(r3.state, [RemoveSegmentOp(destination_id="D05", keep_total_duration=False)], DEST_MAP)
    assert [(s.destination_name, s.days) for s in r_rem_do.state.segments] == [("Mirissa", 3)]
    assert r_rem_do.state.duration_days == 3

    # 8. Fixed total constraint + AddSegmentOp(days=None) -> HITL clarification
    r_fixed = reduce_state(r3.state, [SetTotalDurationConstraintOp(days=5, fixed=True), AddSegmentOp(destination_id="D09", days=None)], DEST_MAP)
    assert r_fixed.clarification_needed
    assert "fixed at 5 days" in r_fixed.clarification_needed.lower()


def test_property_based_segment_conservation_and_atomicity():
    """Randomized property test: segment durations remain positive, sum == duration_days == len(proposal), invalid ops atomic."""
    rng = random.Random(42)
    state = TripState(
        active_goal="custom_planning",
        requested_destinations=["D03", "D05", "D09"],
        duration_days=7,
        segments=[
            ItinerarySegment(segment_id="seg_D03", destination_id="D03", destination_name="Kandy", days=2),
            ItinerarySegment(segment_id="seg_D05", destination_id="D05", destination_name="Ella", days=3),
            ItinerarySegment(segment_id="seg_D09", destination_id="D09", destination_name="Galle", days=2),
        ],
    )
    for _ in range(50):
        choice = rng.choice(["inc", "dec", "set", "transfer", "add", "reorder"])
        d1, d2 = rng.sample(list(DEST_MAP.keys()), 2)
        if choice == "inc":
            op = IncrementSegmentDurationOp(destination_id=d1, delta=rng.randint(1, 3))
        elif choice == "dec":
            op = DecrementSegmentDurationOp(destination_id=d1, delta=rng.randint(1, 4))
        elif choice == "set":
            op = SetSegmentDurationOp(destination_id=d1, days=rng.randint(1, 4))
        elif choice == "transfer":
            op = TransferDaysOp(from_id=d1, to_id=d2, days=rng.randint(1, 3))
        elif choice == "add":
            op = AddSegmentOp(destination_id=d1, days=rng.randint(1, 3))
        else:
            ids = [s.destination_id for s in state.segments]
            rng.shuffle(ids)
            op = ReorderSegmentsOp(destination_ids=ids)

        res = reduce_state(state, [op], DEST_MAP)
        if res.validation_errors:
            assert res.state == state
        else:
            state = res.state
            assert all(s.days >= 1 for s in state.segments)
            assert sum(s.days for s in state.segments) == state.duration_days
            assert len(state.proposal) == state.duration_days
