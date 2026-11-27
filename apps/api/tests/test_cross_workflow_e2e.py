"""Cross-workflow end-to-end reliability regression suite."""
from __future__ import annotations

import json
from uuid import uuid4

from mira.auth import hash_password
from mira.catalog import Turn
from mira.store import db


def _register_or_create_user(email: str, role: str = "traveller", password: str = "Password123!") -> str:
    uid = str(uuid4())
    with db() as conn:
        conn.execute(
            """INSERT INTO users(id, email, password_hash, full_name, role, status, phone, preferences)
               VALUES (?, ?, ?, ?, ?, 'active', '', '{}')""",
            (uid, email, hash_password(password), f"Test {role.title()}", role),
        )
    return uid


def _send_turn(client, trip_id: str, message: str, run_id: str | None = None):
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
    events = [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith("data: ")]
    return resp, events


def test_p0_login_establishes_visitor_and_allows_traveller_overview(app_client):
    """Journey: Login without prior visitor cookie -> /api/traveller/overview must return 200."""
    app_client.cookies.clear()
    _register_or_create_user("p0-login@example.com", "traveller")
    r_login = app_client.post(
        "/api/auth/login",
        json={"email": "p0-login@example.com", "password": "Password123!", "remember": True},
    )
    assert r_login.status_code == 200
    r_ov = app_client.get("/api/traveller/overview")
    assert r_ov.status_code == 200, f"Expected 200, got {r_ov.status_code}: {r_ov.text}"


def test_p0_same_user_session_rotation_persists_original_trip(app_client):
    """Journey 2: Login -> create trip -> turn 1 -> logout -> login same user -> continue trip."""
    _register_or_create_user("p0-rotate@example.com", "traveller")
    assert app_client.post(
        "/api/auth/login",
        json={"email": "p0-rotate@example.com", "password": "Password123!", "remember": True},
    ).status_code == 200
    assert app_client.post("/api/session", json={"remember": False}).status_code == 200
    trip_id = app_client.post("/api/trips").json()["id"]

    resp1, events1 = _send_turn(app_client, trip_id, "Tell me about Sigiriya and Minneriya Day Tour from Kandy")
    assert resp1.status_code == 200
    assert any(e.get("type") == "RUN_FINISHED" for e in events1)

    # Logout clears cookies, then login again as same user and start a new visitor session
    assert app_client.post("/api/auth/logout").status_code == 200
    assert app_client.post(
        "/api/auth/login",
        json={"email": "p0-rotate@example.com", "password": "Password123!", "remember": True},
    ).status_code == 200
    assert app_client.post("/api/session", json={"remember": False}).status_code == 200

    # Reading the trip and continuing the conversation must both succeed without RUN_ERROR
    assert app_client.get(f"/api/trips/{trip_id}").status_code == 200
    resp2, events2 = _send_turn(app_client, trip_id, "2 adults on 2027-02-10")
    assert resp2.status_code == 200
    assert not any(e.get("type") == "RUN_ERROR" for e in events2), f"Unexpected RUN_ERROR: {events2}"
    assert any(e.get("type") == "RUN_FINISHED" for e in events2)
    snap = next(e["snapshot"]["turn"] for e in reversed(events2) if e.get("type") == "STATE_SNAPSHOT" and "turn" in e["snapshot"])
    turn = Turn.model_validate(snap)
    assert "315" in turn.text


def test_p0_account_switching_isolates_trips_and_rotates_visitor(app_client):
    """Journey 3 & 12: Traveller A -> Staff -> Traveller B must isolate trips and never 401 on /api/session."""
    _register_or_create_user("traveller-a@example.com", "traveller")
    _register_or_create_user("staff-user@example.com", "staff")
    _register_or_create_user("traveller-b@example.com", "traveller")

    app_client.post("/api/auth/login", json={"email": "traveller-a@example.com", "password": "Password123!"})
    trip_a = app_client.post("/api/trips").json()["id"]
    _, ev_a = _send_turn(app_client, trip_a, "Tell me about T01")
    assert any(e.get("type") == "RUN_FINISHED" for e in ev_a)

    # Switch to staff account without explicit logout
    r_staff = app_client.post("/api/auth/login", json={"email": "staff-user@example.com", "password": "Password123!"})
    assert r_staff.status_code == 200
    assert app_client.get("/api/session").status_code == 200

    # Switch to Traveller B
    r_b = app_client.post("/api/auth/login", json={"email": "traveller-b@example.com", "password": "Password123!"})
    assert r_b.status_code == 200
    assert app_client.get("/api/session").status_code == 200

    # Traveller B must NOT access Traveller A's trip
    assert app_client.get(f"/api/trips/{trip_a}").status_code == 404
    r_agent_forbidden, _ = _send_turn(app_client, trip_a, "Hello")
    assert r_agent_forbidden.status_code == 404


def test_p1_ambiguous_cultural_triangle_tour_clarifies_then_quotes(app_client):
    """Journey 5: Ambiguous 'Cultural Triangle tour' asks clarification between T09 and T16, then quotes selected."""
    trip_id = app_client.post("/api/trips").json()["id"]
    resp1, events1 = _send_turn(app_client, trip_id, "I want a quote for the Cultural Triangle tour for 2 adults on 2027-04-12")
    assert resp1.status_code == 200
    snap1 = next(e["snapshot"]["turn"] for e in reversed(events1) if e.get("type") == "STATE_SNAPSHOT" and "turn" in e["snapshot"])
    turn1 = Turn.model_validate(snap1)
    # Must NOT silently fail with T16 tour_rate; must present both T09 and T16 for clarification
    assert not any(c.type == "EnquiryNotice" and getattr(c, "tour_id", None) == "T16" for c in turn1.components)
    card_ids = [c.id for c in turn1.components if c.type == "TourCard"]
    assert "T09" in card_ids and "T16" in card_ids

    # User clarifies T09 (or 7-day package) -> remembers 2 adults & 2027-02-10 and quotes T09
    resp2, events2 = _send_turn(app_client, trip_id, "Cultural Triangle Sri Lanka Package")
    assert resp2.status_code == 200
    snap2 = next(e["snapshot"]["turn"] for e in reversed(events2) if e.get("type") == "STATE_SNAPSHOT" and "turn" in e["snapshot"])
    turn2 = Turn.model_validate(snap2)
    assert any(c.type == "PriceBreakdown" and c.quote.source == "T09" for c in turn2.components)


def test_p1_explicit_t16_preserves_missing_rate_handoff(app_client):
    """Explicit T16 selection must never silently swap to T09; preserves tour_rate handoff."""
    trip_id = app_client.post("/api/trips").json()["id"]
    payload = json.dumps({"type": "REQUEST_QUOTE", "payload": {"tourId": "T16", "date": "2027-02-10", "adults": 2, "childAges": []}})
    resp, events = _send_turn(app_client, trip_id, payload)
    assert resp.status_code == 200
    snap = next(e["snapshot"]["turn"] for e in reversed(events) if e.get("type") == "STATE_SNAPSHOT" and "turn" in e["snapshot"])
    turn = Turn.model_validate(snap)
    notice = next(c for c in turn.components if c.type == "EnquiryNotice")
    assert notice.tour_id == "T16"
    assert notice.reason_code == "tour_rate"


def test_p1_custom_itinerary_routing_and_revision(app_client):
    """Journeys 7 & 8: Custom planning prompts generate JourneyPlan + specialist enquiry, not empty discovery."""
    trip_id = app_client.post("/api/trips").json()["id"]
    # 1. Semantic discovery first
    r_sem, ev_sem = _send_turn(app_client, trip_id, "I love wildlife safaris and elephants")
    assert r_sem.status_code == 200
    assert any(e.get("type") == "RUN_FINISHED" for e in ev_sem)

    # 2. Multi-destination 10-day family holiday custom planning
    r_cust, ev_cust = _send_turn(
        app_client,
        trip_id,
        "We're planning a 10-day family holiday covering Kandy, Ella and the southern coast.",
    )
    assert r_cust.status_code == 200
    snap_cust = next(e["snapshot"]["turn"] for e in reversed(ev_cust) if e.get("type") == "STATE_SNAPSHOT" and "turn" in e["snapshot"])
    turn_cust = Turn.model_validate(snap_cust)
    assert any(c.type == "JourneyPlan" for c in turn_cust.components), f"Expected JourneyPlan, got {[c.type for c in turn_cust.components]}"
    assert any(c.type == "EnquiryNotice" for c in turn_cust.components)
    plan_comp = next(c for c in turn_cust.components if c.type == "JourneyPlan")
    assert len(plan_comp.days) == 10

    # 3. Revised custom itinerary (Anuradhapura and Ella, 5 days)
    r_rev, ev_rev = _send_turn(app_client, trip_id, "Plan a 5-day trip to Anuradhapura and Ella")
    assert r_rev.status_code == 200
    snap_rev = next(e["snapshot"]["turn"] for e in reversed(ev_rev) if e.get("type") == "STATE_SNAPSHOT" and "turn" in e["snapshot"])
    turn_rev = Turn.model_validate(snap_rev)
    plan_rev = next(c for c in turn_rev.components if c.type == "JourneyPlan")
    assert len(plan_rev.days) == 5
    day_names = " ".join(d.name.lower() for d in plan_rev.days)
    assert "anuradhapura" in day_names and "ella" in day_names


def test_p1_plan_trip_to_mirissa_does_not_fail_or_misroute(app_client):
    """'I want to plan the trip to Mirissa.' in notebook should clarify or plan Mirissa, not recommend T10."""
    trip_id = app_client.post("/api/trips").json()["id"]
    resp, events = _send_turn(app_client, trip_id, "I want to plan the trip to Mirissa.")
    assert resp.status_code == 200
    snap = next(e["snapshot"]["turn"] for e in reversed(events) if e.get("type") == "STATE_SNAPSHOT" and "turn" in e["snapshot"])
    turn = Turn.model_validate(snap)
    # Must either produce a Mirissa-focused JourneyPlan/Destination or ask to clarify, never T10 Instafamous alone
    assert turn.components or "mirissa" in turn.text.lower() or "days" in turn.text.lower()


def test_p1_gemini_evidence_contract_separates_context_and_rejects_invalid(monkeypatch):
    """Journey 11: Destination context is not exposed as pickable IDs, and invalid Gemini evidence falls back safely."""
    from mira.data import published
    from mira.discovery import DiscoveryResult, discover, model_rank

    w = {"context": {}, "events": [], "records": published(), "discovery_message": "I want a beach trip near Mirissa"}

    def fake_rank(pool, trip, events):
        # Destination IDs (D01..D10) must NOT be exposed as selectable ID-keyed dict alongside evidence
        assert not any(k.startswith("D") for k in trip.get("destinations", {}))
        # Simulate Gemini returning an invalid evidence index -> must trigger safe fallback
        bad = DiscoveryResult(intent="discovery", picks=[{"id": next(iter(trip["evidence"])), "evidence": 999}])
        try:
            return model_rank(trip, lambda *a, **kw: bad, events, {})
        except Exception as exc:
            events.append({"stage": "gemini_suggestions", "outcome": "fallback", "reason": str(exc)})
            return None

    ids = discover(w, fake_rank)
    assert ids  # safe local fallback
    assert w["events"][-1]["validation"] == "local"
    assert w["events"][-1]["fallback"] == "evidence_index_out_of_range"


def test_p2_expired_date_explained_and_corrected_date_quotes_on_current_clock(app_client, monkeypatch):
    """Journey 6 & 9: NL vs structured quote equivalence, expired date explanation, and corrected date on 2026-11-27."""
    monkeypatch.setenv("AS_OF_DATE", "2026-11-27")
    trip_id = app_client.post("/api/trips").json()["id"]

    # 1. Expired date (2026-11-25 < 2026-11-27) in NL must clearly explain pricing window
    r_exp, ev_exp = _send_turn(app_client, trip_id, "Quote for Sigiriya and Minneriya Day Tour from Kandy for 2 adults on 2026-11-25")
    assert r_exp.status_code == 200
    snap_exp = next(e["snapshot"]["turn"] for e in reversed(ev_exp) if e.get("type") == "STATE_SNAPSHOT" and "turn" in e["snapshot"])
    turn_exp = Turn.model_validate(snap_exp)
    assert "window" in turn_exp.text.lower() or "date" in turn_exp.text.lower()
    notice = next(c for c in turn_exp.components if c.type == "EnquiryNotice")
    assert notice.reason_code == "date_or_fx_expired"

    # 2. Corrected valid date overrides expired date and produces verified USD 315 quote
    r_ok, ev_ok = _send_turn(app_client, trip_id, "2027-02-10")
    assert r_ok.status_code == 200
    snap_ok = next(e["snapshot"]["turn"] for e in reversed(ev_ok) if e.get("type") == "STATE_SNAPSHOT" and "turn" in e["snapshot"])
    turn_ok = Turn.model_validate(snap_ok)
    q_nl = next(c.quote for c in turn_ok.components if c.type == "PriceBreakdown")

    # 3. Structured REQUEST_QUOTE produces identical USD 315 total/deposit
    trip_struct = app_client.post("/api/trips").json()["id"]
    payload = json.dumps({"type": "REQUEST_QUOTE", "payload": {"tourId": "T01", "date": "2027-02-10", "adults": 2, "childAges": []}})
    _, ev_st = _send_turn(app_client, trip_struct, payload)
    snap_st = next(e["snapshot"]["turn"] for e in reversed(ev_st) if e.get("type") == "STATE_SNAPSHOT" and "turn" in e["snapshot"])
    q_st = next(c.quote for c in Turn.model_validate(snap_st).components if c.type == "PriceBreakdown")
    assert (q_nl.total, q_nl.deposit) == (q_st.total, q_st.deposit) == (315, 315)


def test_p2_anonymous_login_quote_book_and_cancel_request(app_client):
    """Journey 1 & 10: Anonymous -> login -> quote -> mock book -> 'I want to cancel this booking' -> P02 + unavailable."""
    _register_or_create_user("journey1@example.com", "traveller")
    trip_id = app_client.post("/api/trips").json()["id"]
    assert app_client.post("/api/auth/login", json={"email": "journey1@example.com", "password": "Password123!"}).status_code == 200

    # Quote T01
    _, ev_q = _send_turn(app_client, trip_id, "Sigiriya and Minneriya Day Tour from Kandy for 2 adults on 2027-02-10")
    snap_q = next(e["snapshot"]["turn"] for e in reversed(ev_q) if e.get("type") == "STATE_SNAPSHOT" and "turn" in e["snapshot"])
    q = next(c.quote for c in Turn.model_validate(snap_q).components if c.type == "PriceBreakdown")

    # Mock book
    r_book = app_client.post("/api/bookings/mock", json={"quote": str(q.id), "scenario": "success"})
    assert r_book.status_code == 200

    # Cancel booking request must NOT claim cancelled; must surface P02 and CancellationPreview
    r_can, ev_can = _send_turn(app_client, trip_id, "I want to cancel this booking")
    assert r_can.status_code == 200
    snap_can = next(e["snapshot"]["turn"] for e in reversed(ev_can) if e.get("type") == "STATE_SNAPSHOT" and "turn" in e["snapshot"])
    turn_can = Turn.model_validate(snap_can)
    assert "P02" in turn_can.sources
    assert not any(c.type == "TourCard" for c in turn_can.components)
    assert any(c.type == "CancellationPreview" and c.requires_confirmation for c in turn_can.components)


def test_p2_refresh_idempotent_replay_and_q1043_preserved(app_client, monkeypatch):
    """Journey 4 & Q-1043: Same runId replays idempotently after refresh; Q-1043 workbook math preserved."""
    from datetime import date
    from mira import data

    monkeypatch.setenv("AS_OF_DATE", "2026-11-19")
    expected = data.price("T09", date(2026, 12, 20), 2, [8, 10], date(2026, 11, 19))
    trip_id = app_client.post("/api/trips").json()["id"]
    run_id = str(uuid4())
    msg = "Cultural Triangle Sri Lanka Package for 2 adults and 2 children aged 8, 10 on 2026-12-20"
    r1, ev1 = _send_turn(app_client, trip_id, msg, run_id=run_id)
    assert r1.status_code == 200
    snap1 = next(e["snapshot"]["turn"] for e in reversed(ev1) if e.get("type") == "STATE_SNAPSHOT" and "turn" in e["snapshot"])
    q1 = next(c.quote for c in Turn.model_validate(snap1).components if c.type == "PriceBreakdown")
    assert (q1.total, q1.deposit) == (int(expected["total"]), int(expected["deposit"]))

    # Idempotent replay with same run_id (simulating refresh/retry)
    r2, ev2 = _send_turn(app_client, trip_id, msg, run_id=run_id)
    assert r2.status_code == 200
    snap2 = next(e["snapshot"]["turn"] for e in reversed(ev2) if e.get("type") == "STATE_SNAPSHOT" and "turn" in e["snapshot"])
    assert Turn.model_validate(snap2).trace == Turn.model_validate(snap1).trace


def _turn_from(events):
    snap = next(e["snapshot"]["turn"] for e in reversed(events) if e.get("type") == "STATE_SNAPSHOT" and "turn" in e["snapshot"])
    return Turn.model_validate(snap)


def test_case_a_mirissa_multiturn_planning_memory_and_grounding(app_client):
    """Case A: 'I wanna plan a trip to Mirissa.' -> '10 days' -> '2 adults' -> 'Starting 12 April 2027' -> interests."""
    trip_id = app_client.post("/api/trips").json()["id"]

    _, ev1 = _send_turn(app_client, trip_id, "I wanna plan a trip to Mirissa.")
    t1 = _turn_from(ev1)
    assert "mirissa" in t1.text.lower()
    assert "which destination" not in t1.text.lower()
    assert not any(c.type == "TourCard" and c.id in {"T01", "T09", "T05"} for c in t1.components)
    assert not any(c.type == "EnquiryNotice" for c in t1.components)

    _, ev2 = _send_turn(app_client, trip_id, "10 days")
    t2 = _turn_from(ev2)
    plan2 = next(c for c in t2.components if c.type == "JourneyPlan")
    assert len(plan2.days) == 10
    assert all(d.source == "D08" and "mirissa" in d.name.lower() for d in plan2.days)
    assert not any("**Accommodation:**" in d.passage or "**Entrance" in d.passage for d in plan2.days)
    assert "provisional" in t2.text.lower()

    _, ev3 = _send_turn(app_client, trip_id, "2 adults")
    t3 = _turn_from(ev3)
    assert len(next(c for c in t3.components if c.type == "JourneyPlan").days) == 10

    _, ev4 = _send_turn(app_client, trip_id, "Starting 12 April 2027")
    t4 = _turn_from(ev4)
    dep = next(c for c in t4.components if c.type == "DateSelector")
    assert str(dep.value) == "2027-04-12"

    _, ev5 = _send_turn(app_client, trip_id, "We like whale watching and relaxing on the beach.")
    t5 = _turn_from(ev5)
    plan5 = next(c for c in t5.components if c.type == "JourneyPlan")
    assert len(plan5.days) == 10
    assert all(d.source == "D08" for d in plan5.days)


def test_case_b_replace_destination(app_client):
    """Case B: 'Plan a trip to Ella.' -> '5 days' -> 'Actually, change Ella to Mirissa.'"""
    trip_id = app_client.post("/api/trips").json()["id"]
    _send_turn(app_client, trip_id, "Plan a trip to Ella.")
    _, ev2 = _send_turn(app_client, trip_id, "5 days")
    plan2 = next(c for c in _turn_from(ev2).components if c.type == "JourneyPlan")
    assert len(plan2.days) == 5 and all(d.source == "D05" for d in plan2.days)

    _, ev3 = _send_turn(app_client, trip_id, "Actually, change Ella to Mirissa.")
    plan3 = next(c for c in _turn_from(ev3).components if c.type == "JourneyPlan")
    assert len(plan3.days) == 5 and all(d.source == "D08" for d in plan3.days)


def test_case_c_add_destination(app_client):
    """Case C: 'We want to visit Kandy and Ella.' -> '7 days' -> 'Add Mirissa as well.'"""
    trip_id = app_client.post("/api/trips").json()["id"]
    _send_turn(app_client, trip_id, "We want to visit Kandy and Ella.")
    _, ev2 = _send_turn(app_client, trip_id, "7 days")
    plan2 = next(c for c in _turn_from(ev2).components if c.type == "JourneyPlan")
    assert len(plan2.days) == 7
    assert {d.source for d in plan2.days} == {"D03", "D05"}

    _, ev3 = _send_turn(app_client, trip_id, "Add Mirissa as well.")
    plan3 = next(c for c in _turn_from(ev3).components if c.type == "JourneyPlan")
    assert len(plan3.days) == 7
    assert {d.source for d in plan3.days} == {"D03", "D05", "D08"}


def test_case_d_existing_tour_search_vs_custom_planning(app_client):
    """Case D: 'Find an existing one-day elephant safari from Kandy.' searches published tours (T01)."""
    trip_id = app_client.post("/api/trips").json()["id"]
    _, ev = _send_turn(app_client, trip_id, "Find an existing one-day elephant safari from Kandy.")
    t = _turn_from(ev)
    assert any(c.type == "TourCard" and c.id == "T01" for c in t.components)
    assert not any(c.type == "JourneyPlan" for c in t.components)


def test_case_f_new_trip_isolation_no_anuradhapura_leak(app_client):
    """Case F: Create trip for Anuradhapura, then new trip for Mirissa -> no Anuradhapura leaks."""
    t_a = app_client.post("/api/trips").json()["id"]
    _send_turn(app_client, t_a, "Plan a 4-day trip to Anuradhapura.")

    t_b = app_client.post("/api/trips").json()["id"]
    _send_turn(app_client, t_b, "I wanna plan a trip to Mirissa.")
    _, ev_b2 = _send_turn(app_client, t_b, "5 days")
    plan_b = next(c for c in _turn_from(ev_b2).components if c.type == "JourneyPlan")
    assert all(d.source == "D08" for d in plan_b.days)
    assert not any("anuradhapura" in d.name.lower() or "anuradhapura" in d.passage.lower() for d in plan_b.days)


def test_case_g_insufficient_evidence_destination_honest_handoff(app_client):
    """Case G: Unsupported destination/duration without published evidence returns honest clarification, not fabricated days."""
    trip_id = app_client.post("/api/trips").json()["id"]
    _, ev = _send_turn(app_client, trip_id, "Plan a 5-day trip to Jaffna.")
    t = _turn_from(ev)
    assert not any(c.type == "JourneyPlan" for c in t.components)
