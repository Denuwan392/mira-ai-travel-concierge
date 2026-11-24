"""Automated regression checks demonstrating resolved UI defects:
1. Safe Markdown rendering without raw markup or unescaped injection leaks.
2. Friendly source labels without leaked internal IDs in user-facing summaries.
3. Semantic deduplication preventing duplicate tour cards and redundant library references.
4. Protection against internal pricing and financial leaks.
"""
import json
import re
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from mira.main import app
from mira.catalog import Breakdown, Card, SourcePanel


def send_turn(client, trip_id, message):
    run_id = str(uuid4())
    res = client.post(
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
    res.raise_for_status()
    events = [
        json.loads(line[6:])
        for line in res.text.splitlines()
        if line.startswith("data: ")
    ]
    assert events[-1]["type"] == "RUN_FINISHED"
    return next(
        e["snapshot"]["turn"]
        for e in reversed(events)
        if e["type"] == "STATE_SNAPSHOT" and "turn" in e["snapshot"]
    )


def test_regression_semantic_deduplication(app_client):
    """Verify that when a tour card is shown, redundant library source cards for the same tour are omitted."""
    trip = app_client.post("/api/trips").json()["id"]
    turn = send_turn(app_client, trip, "Sigiriya day trip for two adults on 10 January 2027")

    # Tour card for T01 must exist exactly once
    tour_cards = [c for c in turn["components"] if c["type"] == "TourCard"]
    assert len(tour_cards) == 1
    assert tour_cards[0]["id"] == "T01"

    # Redundant SourceReference or duplicate library card for T01 must not appear
    duplicate_refs = [
        c for c in turn["components"]
        if c["type"] == "SourceReference" and c.get("source") == "T01"
    ]
    assert len(duplicate_refs) == 0


def test_regression_no_raw_internal_ids_in_guest_headings(app_client):
    """Verify that guest-facing headings, summaries, and component titles do not leak bare internal IDs."""
    trip = app_client.post("/api/trips").json()["id"]
    turn = send_turn(app_client, trip, "Tell me about Ella")

    # Inspect all textual components
    for comp in turn["components"]:
        heading = comp.get("heading", "")
        title = comp.get("title", "")
        # Bare internal IDs like T01, T09, P02, D05 should not be presented as user headings
        for internal_id in ["T01", "T05", "T09", "T10", "T12", "P01", "P02", "P03", "D05"]:
            assert heading != internal_id, f"Bare internal ID {internal_id} used as component heading"
            assert title != internal_id, f"Bare internal ID {internal_id} used as component title"


def test_regression_safe_markdown_and_no_html_injections(app_client):
    """Verify that user queries with script or HTML tags do not cause unescaped HTML injection in agent responses."""
    trip = app_client.post("/api/trips").json()["id"]
    malicious_prompt = 'Hi <script>alert("xss")</script> <img src=x onerror=alert(1)> What tours do you have?'
    turn = send_turn(app_client, trip, malicious_prompt)

    # Response text must not contain executable HTML tags
    assert "<script>" not in turn["text"]
    assert "<img" not in turn["text"]
    assert "onerror=" not in turn["text"]


def test_regression_protection_against_financial_leaks(app_client):
    """Verify that guest quote payloads and text never expose internal margins, buy costs, or staff notes."""
    trip = app_client.post("/api/trips").json()["id"]
    turn = send_turn(app_client, trip, "Sigiriya day trip for two adults on 10 January 2027")

    quote_comp = next(c for c in turn["components"] if c["type"] == "PriceBreakdown")
    quote = quote_comp["quote"]

    # Public breakdown contains customer-facing fields only
    assert "total" in quote
    assert "deposit" in quote
    assert "balance" in quote

    # Strictly forbidden internal metadata
    quote_json = json.dumps(quote).lower()
    for forbidden in ["margin", "markup", "buy_cost", "cost_lkr", "gross_profit", "rate_row"]:
        assert forbidden not in quote_json, f"Internal financial term '{forbidden}' leaked in quote payload"
        assert forbidden not in turn["text"].lower(), f"Internal financial term '{forbidden}' leaked in turn text"
