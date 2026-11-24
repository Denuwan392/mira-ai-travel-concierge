import json
from uuid import uuid4
from fastapi.testclient import TestClient
from mira.main import app


def send_agent(client, trip, message, run=None):
    run = run or str(uuid4())
    response = client.post(
        "/api/agent",
        params={"trip_id": trip},
        json={
            "threadId": trip,
            "runId": run,
            "messages": [{"id": run, "role": "user", "content": message}],
            "state": {},
            "tools": [],
            "context": [],
            "forwardedProps": {},
        },
    )
    response.raise_for_status()
    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    assert events[-1]["type"] == "RUN_FINISHED"
    return next(
        e["snapshot"]["turn"]
        for e in reversed(events)
        if e["type"] == "STATE_SNAPSHOT" and "turn" in e["snapshot"]
    )


def test_no_redundant_library_card_when_tour_card_displayed(app_client):
    trip = app_client.post("/api/trips").json()["id"]
    turn = send_agent(
        app_client, trip, "Sigiriya day trip for two adults on 10 January 2027"
    )

    tour_cards = [c for c in turn["components"] if c["type"] == "TourCard"]
    assert len(tour_cards) == 1
    assert tour_cards[0]["id"] == "T01"

    # Upstream fix: SourceReference should not duplicate the already selected T01 tour
    library_cards = [
        c
        for c in turn["components"]
        if c["type"] == "SourceReference" and c["source"] == "T01"
    ]
    assert len(library_cards) == 0


def test_pricing_arithmetic_integrity(app_client):
    trip = app_client.post("/api/trips").json()["id"]
    turn = send_agent(
        app_client, trip, "Sigiriya day trip for two adults on 10 January 2027"
    )

    quote_breakdown = next(
        c for c in turn["components"] if c["type"] == "PriceBreakdown"
    )
    quote = quote_breakdown["quote"]

    # Price arithmetic must remain completely identical
    assert quote["currency"] == "USD"
    assert quote["total"] == 315
    assert quote["deposit"] == 315
    assert quote["balance"] == 0
    assert quote["source"] == "T01"

    # Guest quote payload must never expose cost, margins or markup
    raw_quote_str = json.dumps(quote).lower()
    for forbidden in ["margin", "cost", "profit", "markup", "rate_row"]:
        assert forbidden not in raw_quote_str


def test_quote_saved_confirmation_distinct_from_booking(app_client):
    trip = app_client.post("/api/trips").json()["id"]
    turn = send_agent(
        app_client, trip, "Sigiriya day trip for two adults on 10 January 2027"
    )

    confirmation = next(
        c for c in turn["components"] if c["type"] == "ConfirmationPanel"
    )
    assert confirmation["heading"] == "Quote saved"
    assert (
        confirmation["text"]
        == "Your private enquiry is available to the travel team."
    )

    booking_form = next(
        c for c in turn["components"] if c["type"] == "BookingForm"
    )
    assert booking_form["quote"] == turn["components"][0]["quote"]["id"]

    # Booking simulation: declining payment keeps enquiry intact without false booking
    res = app_client.post(
        "/api/bookings/mock",
        json={"quote": booking_form["quote"], "scenario": "declined"},
    ).json()
    assert res["status"] == "declined"
