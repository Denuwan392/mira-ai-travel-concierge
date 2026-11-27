"""Characterization tests capturing baseline LangGraph workflow behavior before modularization.

Verifies deterministic quotes, A2UI component ordering, surface structure,
trace stages, intent precedence, optimistic concurrency, ContextVar identity,
and zero extra LLM calls.
"""
from __future__ import annotations

import json
from uuid import uuid4

import pytest

from conftest import quotes, turn
from mira import agent, main, provider, store
from mira.catalog import Booking, Breakdown, Card, Excerpt, Notice, Picker, SourcePanel
from mira.provider import NotebookIntent


def test_characterization_quick_booker_a2ui_and_trace_stages(app_client):
    """Capture exact A2UI component ordering, surface, sources, and trace stages for T01."""
    out = turn(app_client, "Sigiriya and Minneriya day tour for two adults on 10 January 2027")
    assert [c.type for c in out.components] == ["PriceBreakdown", "TourCard", "ItineraryDay", "BookingForm"]
    assert out.sources == ["T01"]
    [q] = quotes(out)
    assert (q.total, q.deposit, q.balance) == (315, 315, 0)

    with store.db() as conn:
        row = conn.execute("SELECT events FROM traces WHERE id=?", (str(out.trace),)).fetchone()
    stages = [e["stage"] for e in json.loads(row["events"])]
    assert stages == ["interpret", "retrieval", "pricing", "validated_ui", "persistence"]


def test_characterization_overlapping_intent_precedence(app_client):
    """Capture exact intent precedence across accommodation, package discovery, day detail, and full itinerary."""
    # 1. Hotel recommendation -> StayCard + Notice, zero TourCards
    h = turn(app_client, "Suggest me a hotel in Mirissa.")
    assert any(isinstance(c, SourcePanel) and c.type == "StayCard" for c in h.components)
    assert not any(isinstance(c, Card) for c in h.components)

    # 2. Beach stay package -> TourCard for T11
    pkg = turn(app_client, "Recommend a beach stay package in Mirissa")
    assert any(isinstance(c, Card) and c.id == "T11" for c in pkg.components)

    # 3. Specific day query -> single ItineraryDay
    d4 = turn(app_client, "On the Cultural Triangle Sri Lanka Package, what happens on Day 4?")
    days = [c for c in d4.components if isinstance(c, Excerpt) and c.type == "ItineraryDay"]
    assert len(days) == 1 and "Day 4" in days[0].heading

    # 4. Complete itinerary -> TourCard + 7 ItineraryDay components
    full = turn(app_client, "Show me the complete itinerary for Cultural Triangle Sri Lanka Package")
    full_days = [c for c in full.components if isinstance(c, Excerpt) and c.type == "ItineraryDay"]
    assert len(full_days) == 7


def test_characterization_contextvar_identity_and_graph_nodes():
    """Verify ContextVars and graph node names are canonical between main.py and mira.agent."""
    assert main.visitor_context is agent.visitor_context
    assert main.run_context is agent.run_context
    assert main.working is agent.working
    assert {"interpret", "retrieve", "quote", "compose", "save"}.issubset(set(agent.graph.nodes.keys()))


def test_characterization_optimistic_concurrency_protection(app_client):
    """Verify persist() aborts with 'Session changed during this turn' if visitor context mutates mid-turn."""
    with store.db() as conn:
        vid = conn.execute("SELECT id FROM visitors LIMIT 1").fetchone()["id"]

    tok_v = agent.visitor_context.set(vid)
    tok_r = agent.run_context.set(str(uuid4()))
    tok_w = agent.working.set({
        "basis": '{"stale": true}',
        "context": {"tour": "T01"},
        "action": "discover",
        "events": [],
        "turn": turn(app_client, "Hi Mira"),
    })
    try:
        with pytest.raises(ValueError, match="Session changed during this turn"):
            agent.persist()
    finally:
        agent.working.reset(tok_w)
        agent.run_context.reset(tok_r)
        agent.visitor_context.reset(tok_v)


def test_characterization_controlled_llm_call_count(app_client, monkeypatch):
    """Verify exact LLM call count (at most 1 rank + 1 notebook_intent) under controlled provider fixture."""
    calls = []

    def fake_rank(tours, trip, events):
        calls.append("rank")
        return ["T01"]

    def fake_intent(prompt, previous, destinations, events, evidence=None):
        calls.append("notebook_intent")
        return NotebookIntent(operation="catalogue")

    monkeypatch.setattr(agent, "rank", fake_rank)
    monkeypatch.setattr(agent, "notebook_intent", fake_intent)

    trip_id = app_client.post("/api/trips").json()["id"]
    run_id = str(uuid4())
    resp = app_client.post(
        "/api/agent",
        params={"trip_id": trip_id},
        json={
            "threadId": trip_id,
            "runId": run_id,
            "messages": [{"id": run_id, "role": "user", "content": "Show me tours in Sri Lanka"}],
            "state": {},
            "tools": [],
            "context": [],
            "forwardedProps": {},
        },
    )
    resp.raise_for_status()
    assert calls.count("notebook_intent") <= 1
    assert calls.count("rank") <= 1
