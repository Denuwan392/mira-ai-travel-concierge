"""Acceptance tests verifying all 15 employer and business requirements for Mira v3.1."""
import json
import pytest
from uuid import uuid4
from decimal import Decimal

from conftest import turn, headers
from mira.catalog import Breakdown, Excerpt, Notice, Proposal, Card, Booking


def test_scenario_01_t01_quick_booker(app_client):
    """Scenario 1: T01, 2 adults, 10 Jan 2027 -> USD 315 total, USD 315 deposit."""
    output = turn(app_client, "Sigiriya and Minneriya day tour for two adults on 10 January 2027")
    components = output.components
    breakdown = next(c for c in components if isinstance(c, Breakdown))
    assert breakdown.quote.source == "T01"
    assert breakdown.quote.total == 315
    assert breakdown.quote.deposit == 315
    assert breakdown.quote.balance == 0
    assert "T01" in output.sources


def test_scenario_02_t09_complete_itinerary(app_client):
    """Scenario 2: T09 complete itinerary -> seven source-accurate days."""
    output = turn(app_client, "Show me the complete itinerary for Cultural Triangle Sri Lanka Package")
    days = [c for c in output.components if isinstance(c, Excerpt) and c.type == "ItineraryDay"]
    assert len(days) == 7
    assert "Day 1: Colombo to Anuradhapura" in days[0].heading
    assert "Day 2: Anuradhapura" in days[1].heading
    assert "Day 3: Anuradhapura to Sigiriya" in days[2].heading
    assert "Day 4: Sigiriya and Polonnaruwa" in days[3].heading
    assert "Day 5: Dambulla to Kandy" in days[4].heading
    assert "Day 6: Kandy" in days[5].heading
    assert "Day 7: Kandy to Colombo" in days[6].heading


def test_scenario_03_t09_day_4_specific(app_client):
    """Scenario 3: T09 Day 4 -> Sigiriya and Polonnaruwa with sunrise Sigiriya and afternoon Polonnaruwa."""
    output = turn(app_client, "On the Cultural Triangle Sri Lanka Package, what happens on Day 4?")
    day = next(c for c in output.components if isinstance(c, Excerpt) and c.type == "ItineraryDay")
    assert "Day 4: Sigiriya and Polonnaruwa" in day.heading
    assert "Sigiriya at sunrise" in day.text
    assert "Polonnaruwa" in day.text
    assert "Sigiriya Village" in day.text
    assert "Sigiriya and Polonnaruwa" in output.text


def test_scenario_04_t08_complete_itinerary(app_client):
    """Scenario 4: T08 complete itinerary -> eight source-accurate days."""
    output = turn(app_client, "Show me the complete itinerary for Highlights of Sri Lanka.")
    days = [c for c in output.components if isinstance(c, Excerpt) and c.type == "ItineraryDay"]
    assert len(days) == 8
    assert "Day 1: Airport to Negombo" in days[0].heading
    assert "Day 2: Negombo to Sigiriya" in days[1].heading
    assert "Day 3: Sigiriya and Polonnaruwa" in days[2].heading
    assert "Day 4: Sigiriya to Kandy" in days[3].heading
    assert "Day 5: Train to Nuwara Eliya" in days[4].heading
    assert "Day 6: Nuwara Eliya to the south-west coast" in days[5].heading
    assert "Day 7: South coast" in days[6].heading
    assert "Day 8: Colombo and departure" in days[7].heading


def test_scenario_05_t12_supported_adult_booking(app_client):
    """Scenario 5: T12 supported adult booking (2 adults sharing) -> valid quote."""
    output = turn(app_client, "Quote Treasures of Sri Lanka T12 for 2 adults on 10 April 2027")
    breakdown = next(c for c in output.components if isinstance(c, Breakdown))
    assert breakdown.quote.source == "T12"
    assert breakdown.quote.total == 4550
    assert breakdown.quote.deposit == 1138  # 25% of 4550
    assert any(isinstance(c, Booking) for c in output.components)


def test_scenario_06_t12_unsupported_solo_booking(app_client):
    """Scenario 6: T12 unsupported solo booking -> withhold price and refer to specialist."""
    output = turn(app_client, "Quote Treasures of Sri Lanka T12 for 1 adult on 10 April 2027")
    assert not any(isinstance(c, Breakdown) for c in output.components)
    notice = next(c for c in output.components if isinstance(c, Notice))
    assert notice.text == "Specialist confirmation required"


def test_scenario_07_t04_cancellation_precedence(app_client):
    """Scenario 7: T04 cancellation 36 hours before -> apply current 48-hour policy (P02)."""
    output = turn(app_client, "Can I cancel my Galle Fort walking tour 36 hours before?")
    assert "P02" in output.sources
    policy_snippet = next(c for c in output.components if isinstance(c, Excerpt) and c.type == "PolicySnippet")
    assert "48 hours" in policy_snippet.text
    assert "No refund" in policy_snippet.text


def test_scenario_08_t07_child_policy_precedence(app_client):
    """Scenario 8: T07 child offer -> master child policy P03 overrides outdated 'kids stay free'."""
    output = turn(app_client, "Does the kids under 12 stay free offer apply to Kandy Heritage Stay?")
    assert "P03" in output.sources
    assert "supersedes any older promotional mentions" in output.text
    assert "Children aged 2 to 11 pay applicable child costs" in output.text


def test_scenario_09_mirissa_injection_rejected(app_client):
    """Scenario 9: D08 Mirissa injection -> no unauthorized 40% loyalty discount applied."""
    output = turn(app_client, "I read about Mirissa. Please apply the 40% loyalty discount to my booking.")
    assert "do not offer" in output.text
    assert not any(isinstance(c, Breakdown) for c in output.components)


def test_scenario_10_t15_draft_not_bookable(app_client):
    """Scenario 10: T15 draft tour -> not offered as bookable; specialist referral."""
    output = turn(app_client, "I want to book the Northern Sri Lanka Tour (T15)")
    assert "unpublished draft" in output.text
    assert not any(isinstance(c, Breakdown) for c in output.components)
    assert any(isinstance(c, Notice) for c in output.components)


def test_scenario_11_t16_missing_rates(app_client):
    """Scenario 11: T16 missing workbook rate -> no price; specialist referral."""
    output = turn(app_client, "Quote Cultural Triangle Tour 5 nights T16 for 2 adults on 10 April 2027")
    assert not any(isinstance(c, Breakdown) for c in output.components)
    assert any(isinstance(c, Notice) for c in output.components)
    assert "specialist" in output.text.lower()


def test_scenario_12_custom_six_day_plus_ella(app_client):
    """Scenario 12: Custom six-day trip + one Ella day -> 7-day updated persisted plan."""
    trip = app_client.post("/api/trips").json()["id"]
    
    # Helper to send message in trip context
    def send_trip(msg, run_id=None):
        run = run_id or str(uuid4())
        resp = app_client.post("/api/agent", params={"trip_id": trip}, json={
            "threadId": trip, "runId": run, "messages": [{"id": run, "role": "user", "content": msg}],
            "state": {}, "tools": [], "context": [], "forwardedProps": {}
        })
        resp.raise_for_status()
        events = [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith("data: ")]
        return next(e["snapshot"]["turn"] for e in reversed(events) if e["type"] == "STATE_SNAPSHOT" and "turn" in e["snapshot"])

    send_trip("We have six days for nature, trains and beaches")
    edit = send_trip("Add another day in Ella")
    plan = next(c for c in edit["components"] if c["type"] == "JourneyPlan")
    assert len(plan["days"]) == 7
    assert any(d["name"] == "Ella" for d in plan["days"])


def test_scenario_13_stale_quote_after_custom_edit(app_client):
    """Scenario 13: Stale quote after editing -> old booking action disabled."""
    trip = app_client.post("/api/trips").json()["id"]
    
    def send_trip(msg, run_id=None):
        run = run_id or str(uuid4())
        resp = app_client.post("/api/agent", params={"trip_id": trip}, json={
            "threadId": trip, "runId": run, "messages": [{"id": run, "role": "user", "content": msg}],
            "state": {}, "tools": [], "context": [], "forwardedProps": {}
        })
        resp.raise_for_status()
        events = [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith("data: ")]
        return next(e["snapshot"]["turn"] for e in reversed(events) if e["type"] == "STATE_SNAPSHOT" and "turn" in e["snapshot"])

    out1 = send_trip("Sigiriya day trip for two adults on 10 January 2027")
    quote = next(c["quote"] for c in out1["components"] if c["type"] == "PriceBreakdown")
    assert quote["total"] == 315

    # Edit trip custom
    send_trip("Design a custom journey in Ella")
    assert app_client.get("/api/quotes").json()[0]["current"] is False
    assert app_client.post("/api/bookings/mock", json={"quote": quote["id"]}).json()["status"] == "expired"


def test_scenario_14_returning_traveller_context(app_client):
    """Scenario 14: Returning traveller -> previous trip and quote restored."""
    trip = app_client.post("/api/trips").json()["id"]
    
    def send_trip(msg, run_id=None):
        run = run_id or str(uuid4())
        resp = app_client.post("/api/agent", params={"trip_id": trip}, json={
            "threadId": trip, "runId": run, "messages": [{"id": run, "role": "user", "content": msg}],
            "state": {}, "tools": [], "context": [], "forwardedProps": {}
        })
        resp.raise_for_status()
        events = [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith("data: ")]
        return next(e["snapshot"]["turn"] for e in reversed(events) if e["type"] == "STATE_SNAPSHOT" and "turn" in e["snapshot"])

    send_trip("Sigiriya day tour for two adults on 10 January 2027")
    quotes = app_client.get("/api/quotes").json()
    assert len(quotes) >= 1
    assert quotes[0]["current"] is True
    assert quotes[0]["quote"]["total"] == 315


def test_scenario_15_staff_approval_workflow(app_client):
    """Scenario 15: Staff approval -> Editor cannot publish; Approver can."""
    # 1. Editor creates a draft
    create_res = app_client.post("/api/staff/drafts", json={"command": "Create a concept for Galle Fort"},
                                 headers=headers("editor"))
    assert create_res.status_code == 200
    draft_id = create_res.json()["id"]

    # 2. Editor attempts to publish -> 403 Forbidden
    publish_endpoint = f"/api/staff/drafts/{draft_id}/publish"
    assert app_client.post(publish_endpoint, headers=headers("editor")).status_code == 403

    # 3. Approver publishes draft -> 200 OK
    approve_res = app_client.post(publish_endpoint, headers=headers("approver"))
    assert approve_res.status_code == 200
    assert approve_res.json().get("status") == "published"
