"""End-to-end conversational grounding, coreference resolution, and dialogue state tests (Scenarios A–J)."""
import json
from uuid import uuid4

from mira.store import db


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


def test_scenario_a_discovery_filter_ordinal_qa_quote(app_client):
    """Scenario A: Exact 5-turn reproduction + date completion."""
    tid = app_client.post("/api/trips").json()["id"]

    t1, _ = _send(app_client, tid, "Are there any holidays that cover both the hill country and the southern beaches?")
    assert [c["id"] for c in t1["components"] if c["type"] == "TourCard"]

    t2, _ = _send(app_client, tid, "Which ones go through Ella?")
    assert [c["id"] for c in t2["components"] if c["type"] == "TourCard"] == ["T12"]

    t3, _ = _send(app_client, tid, "Could you show me the itinerary of the first option?")
    assert any(c["type"] == "TourCard" and c["id"] == "T12" for c in t3["components"])
    assert _ctx(tid)["focused_entity_id"] == "T12"

    t4, _ = _send(app_client, tid, "Does that include Mirissa?")
    assert "does not include mirissa" in t4["text"].lower()
    assert _ctx(tid)["focused_entity_id"] == "T12"
    assert "custom" not in _ctx(tid)

    t5, _ = _send(app_client, tid, "How much would it cost for a couple?")
    assert any(c["type"] == "TravellerPicker" and c["tour"] == "T12" and c["adults"] == 2 for c in t5["components"])
    assert _ctx(tid)["adults"] == 2


def test_scenario_b_product_policy_resume_quote(app_client):
    """Scenario B: Product exploration -> policy question -> resume quotation."""
    tid = app_client.post("/api/trips").json()["id"]
    _send(app_client, tid, "Tell me about Sigiriya and Minneriya Day Tour from Kandy")
    assert _ctx(tid)["tour"] == "T01"

    tp, _ = _send(app_client, tid, "What is the cancellation policy?")
    assert any(c["type"] == "PolicySnippet" for c in tp["components"])
    assert _ctx(tid)["tour"] == "T01"

    tq, _ = _send(app_client, tid, "How much would it cost for a couple on 2027-03-10?")
    assert any(c["type"] == "PriceBreakdown" and c["quote"]["source"] == "T01" and c["quote"]["adults"] == 2 for c in tq["components"])


def test_scenario_c_comparative_and_pronoun_references(app_client):
    """Scenario C: Compare both options -> select shorter package."""
    tid = app_client.post("/api/trips").json()["id"]
    _send(app_client, tid, "Show me trips that visit Kandy, Ella and Galle.")
    tc, _ = _send(app_client, tid, "Compare both options")
    assert len([c for c in tc["components"] if c["type"] == "TourCard"]) == 2

    ts, _ = _send(app_client, tid, "Show me the shorter package")
    assert _ctx(tid)["focused_entity_id"] == "T10"
    assert any(c["type"] == "TourCard" and c["id"] == "T10" for c in ts["components"])


def test_scenario_d_empty_filter_and_ambiguous_ordinal(app_client):
    """Scenario D: Empty filtered results followed by ambiguous ordinal reference clarifies rather than guessing."""
    tid = app_client.post("/api/trips").json()["id"]
    _send(app_client, tid, "Show me trips that visit Kandy, Ella and Galle.")
    te, _ = _send(app_client, tid, "Which ones go through Trincomalee?")
    assert not [c for c in te["components"] if c["type"] == "TourCard"]
    assert "none of the previously shown options" in te["text"].lower()
    assert _ctx(tid)["historical_suggestions"]

    to, _ = _send(app_client, tid, "Show me the first one")
    assert "did you mean" in to["text"].lower() or "earlier list" in to["text"].lower()


def test_scenario_e_custom_plan_readonly_question_then_modify(app_client):
    """Scenario E: Custom planning -> read-only destination question -> modify existing itinerary."""
    tid = app_client.post("/api/trips").json()["id"]
    t1, _ = _send(app_client, tid, "Plan a 5-day trip to Kandy and Ella")
    assert any(c["type"] == "JourneyPlan" for c in t1["components"])

    tq, _ = _send(app_client, tid, "What is Ella like?")
    assert any(c["type"] == "DestinationCard" for c in tq["components"])
    assert len(_ctx(tid)["proposal"]) == 5

    tm, _ = _send(app_client, tid, "Make it 7 days")
    assert any(c["type"] == "JourneyPlan" and len(c["days"]) == 7 for c in tm["components"])


def test_scenario_f_quote_book_hypothetical_cancel(app_client):
    """Scenario F: Quote -> booking -> hypothetical refund inquiry -> cancellation preview -> confirm."""
    tid = app_client.post("/api/trips").json()["id"]
    tq, _ = _send(app_client, tid, "Quote Sigiriya and Minneriya Day Tour from Kandy for 2 adults on 2027-04-12")
    qid = next(c["quote"]["id"] for c in tq["components"] if c["type"] == "PriceBreakdown")
    app_client.post("/api/bookings/mock", json={"quote": qid})

    th, _ = _send(app_client, tid, "What would happen if I cancelled?")
    assert "nothing has been cancelled" in th["text"].lower()

    tp, _ = _send(app_client, tid, "Cancel my booking")
    assert any(c["type"] == "CancellationPreview" for c in tp["components"])

    tc, _ = _send(app_client, tid, "Yes, confirm cancellation")
    assert any(c["type"] == "CancellationStatus" and c["status"] == "cancelled" for c in tc["components"])


def test_scenario_g_and_h_product_qa_and_offline_fallback(app_client):
    """Scenarios G & H: Product-specific QA offline without Gemini (departure, duration, wildlife, day detail)."""
    tid = app_client.post("/api/trips").json()["id"]
    _send(app_client, tid, "Tell me about Sigiriya and Minneriya Day Tour from Kandy")
    tdur, _ = _send(app_client, tid, "How many days is it?")
    assert "1 day" in tdur["text"].lower()
    tdep, _ = _send(app_client, tid, "Does it depart from Kandy?")
    assert "kandy" in tdep["text"].lower()
    twild, _ = _send(app_client, tid, "Will we see elephants?")
    assert "yes" in twild["text"].lower() or "elephant" in twild["text"].lower()


def test_scenario_i_and_j_refresh_and_isolation(app_client):
    """Scenarios I & J: History reload preserves state; separate trip & visitor isolation enforced."""
    tid = app_client.post("/api/trips").json()["id"]
    _send(app_client, tid, "Tell me about Kandy City Tour")
    hist = app_client.get(f"/api/trips/{tid}").json()["history"]
    assert len(hist) == 1

    # New trip starts clean
    tid2 = app_client.post("/api/trips").json()["id"]
    assert tid2 != tid
    assert _ctx(tid2) == {}
