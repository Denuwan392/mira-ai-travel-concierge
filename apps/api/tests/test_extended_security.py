import json
import sqlite3
from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from conftest import headers, quotes, turn, TODAY
from mira import store
from mira.catalog import Turn
from mira.main import app


# ==============================================================================
# PART A — RETURNING VISITORS (REQUIREMENT R2)
# ==============================================================================

def test_returning_visitor_sees_quotes_and_continues_context(app_client):
    """A returning visitor with remember=True can see recent quotes and retains state."""
    # 1. Start session with consent to remember
    res = app_client.post("/api/session", json={"remember": True})
    assert res.status_code == 200
    assert res.json()["remember"] is True
    assert "max-age=2592000" in res.headers["set-cookie"].lower()

    # 2. Provide partial party information
    turn(app_client, "We are two adults.")
    session_info = app_client.get("/api/session").json()
    assert session_info["context"]["adults"] == 2

    # 3. Provide tour and date: Mira does NOT re-ask for adults, produces quote immediately
    t_quote = turn(app_client, "Sigiriya day trip on 10 January 2027")
    [q] = quotes(t_quote)
    assert q.adults == 2
    assert q.total == 315

    # 4. Inquire about saved quotes
    saved = app_client.get("/api/quotes").json()
    assert len(saved) >= 1
    assert saved[0]["current"] is True
    assert saved[0]["quote"]["id"] == str(q.id)


def test_stale_quote_flagged_and_unbookable(app_client, monkeypatch):
    """When assessment date passes the tour date, the quote is flagged not current and cannot be booked."""
    t_quote = turn(app_client, "Sigiriya day trip for two adults on 10 January 2027")
    [q] = quotes(t_quote)

    # Fast forward assessment clock past the tour date
    monkeypatch.setenv("AS_OF_DATE", "2027-01-11")

    # The quote list flags current: False
    saved = app_client.get("/api/quotes").json()
    assert len(saved) >= 1
    assert saved[0]["current"] is False

    # Attempting to mock-book an expired quote returns 'expired' status
    booking_res = app_client.post("/api/bookings/mock", json={"quote": str(q.id)}).json()
    assert booking_res["status"] == "expired"


def test_anonymous_visitors_are_strictly_isolated(app_client):
    """Ensure two distinct visitors cannot see each other's quotes or trips."""
    # Visitor A creates a quote
    t_a = turn(app_client, "Sigiriya day trip for two adults on 10 January 2027")
    [q_a] = quotes(t_a)

    # Visitor B enters the application
    with TestClient(app) as client_b:
        client_b.post("/api/session", json={"remember": False})
        # Visitor B has no quotes
        assert client_b.get("/api/quotes").json() == []
        # Visitor B cannot book Visitor A's quote
        assert client_b.post("/api/bookings/mock", json={"quote": str(q_a.id)}).status_code == 404


def test_visitor_forget_and_deletion(app_client):
    """DELETE /api/session permanently purges visitor context and revokes access."""
    turn(app_client, "Sigiriya day trip for two adults on 10 January 2027")
    assert len(app_client.get("/api/quotes").json()) == 1

    forget_res = app_client.delete("/api/session")
    assert forget_res.status_code == 200
    assert forget_res.json()["forgotten"] is True

    # Subsequent access without a new session is rejected
    assert app_client.get("/api/quotes").status_code == 401


# ==============================================================================
# PART B — PRIVATE ENQUIRY MANAGEMENT (REQUIREMENT R7)
# ==============================================================================

def test_enquiry_creation_and_staff_visibility(app_client):
    """Every verified quote and custom request creates an enquiry in SQLite with correct reason."""
    # 1. Verified quote enquiry
    t_quote = turn(app_client, "Sigiriya day trip for two adults on 10 January 2027")
    [q] = quotes(t_quote)

    enquiries = app_client.get("/api/staff/enquiries", headers=headers("staff")).json()
    matching_q = next((e for e in enquiries if e["quote"] == str(q.id)), None)
    assert matching_q is not None
    assert matching_q["reason"] == "verified_quote"
    assert matching_q["status"] == "new"

    # 2. Custom unsupported request enquiry
    t_custom = turn(app_client, "Custom journey across Kandy and Ella for 10 days")
    enquiries_after = app_client.get("/api/staff/enquiries", headers=headers("staff")).json()
    custom_enquiry = next((e for e in enquiries_after if e["trace"] == str(t_custom.trace)), None)
    assert custom_enquiry is not None
    assert custom_enquiry["reason"] == "custom_or_unsupported"


def test_staff_enquiry_notes_and_pii_rejection(app_client):
    """Staff can append notes and update status; notes containing phone/email PII are rejected."""
    t_custom = turn(app_client, "Custom journey for 8 days in Galle")
    enquiries = app_client.get("/api/staff/enquiries", headers=headers("staff")).json()
    enquiry = next(e for e in enquiries if e["trace"] == str(t_custom.trace))
    endpoint = f"/api/staff/enquiries/{enquiry['id']}"

    # Note with email is rejected (422)
    bad_note_email = {"status": "contacted", "note": "Customer email is traveller@example.com"}
    assert app_client.patch(endpoint, json=bad_note_email, headers=headers("staff")).status_code == 422

    # Note with phone number is rejected (422)
    bad_note_phone = {"status": "contacted", "note": "Call customer at +94 77 123 4567"}
    assert app_client.patch(endpoint, json=bad_note_phone, headers=headers("staff")).status_code == 422

    # Clean operational note succeeds
    clean_note = {"status": "contacted", "note": "Assigned driver guide and checking boutique villa availability."}
    res = app_client.patch(endpoint, json=clean_note, headers=headers("staff"))
    assert res.status_code == 200
    assert res.json()["status"] == "contacted"

    # Verify detail contains the note
    detail = app_client.get(endpoint, headers=headers("staff")).json()
    assert detail["status"] == "contacted"
    assert detail["notes"][0]["body"] == clean_note["note"]
    assert detail["notes"][0]["actor"] == "staff"


def test_public_api_never_exposes_internal_finances(app_client):
    """Public endpoints (/api/quotes, /api/agent) never expose buy costs, margins, or breakdowns."""
    t = turn(app_client, "Sigiriya day trip for two adults on 10 January 2027")
    [q] = quotes(t)
    dump = q.model_dump()
    assert "cost_lkr" not in dump
    assert "gross_profit_pct" not in dump
    assert "breakdown" not in dump

    # Check /api/quotes payload
    public_quotes = app_client.get("/api/quotes").json()
    quote_json = json.dumps(public_quotes)
    assert "cost_lkr" not in quote_json
    assert "gross_profit_pct" not in quote_json
    assert "66000" not in quote_json  # Internal buy cost


# ==============================================================================
# PART C — HUMAN APPROVAL WORKFLOW (REQUIREMENT R8)
# ==============================================================================

def test_full_human_approval_lifecycle(app_client):
    """Verify Draft creation -> Pending review -> Non-approver rejection -> Approver publication -> Search availability."""
    # 1. Editor creates a draft
    create_res = app_client.post("/api/staff/drafts", json={"command": "Create a concept for Galle Fort"},
                                 headers=headers("editor"))
    assert create_res.status_code == 200
    draft_id = create_res.json()["id"]

    # 2. Draft is invisible to public searches
    assert app_client.get(f"/api/sources/{draft_id}").status_code == 404
    all_tours = app_client.get("/api/tours").json()
    assert not any(t["id"] == draft_id for t in all_tours)

    # 3. Editor attempts to publish -> 403 Forbidden
    publish_endpoint = f"/api/staff/drafts/{draft_id}/publish"
    assert app_client.post(publish_endpoint, headers=headers("editor")).status_code == 403

    # 4. Approver publishes draft -> 200 OK
    approve_res = app_client.post(publish_endpoint, headers=headers("approver"))
    assert approve_res.status_code == 200

    # 5. Subsequent publish attempt returns 409 Conflict
    assert app_client.post(publish_endpoint, headers=headers("approver")).status_code == 409

    # 6. Once published, content is accessible via public sources endpoint
    assert app_client.get(f"/api/sources/{draft_id}").status_code == 200

    # 7. Audit log contains creation and publication records
    audit_rows = app_client.get("/api/staff/audit", headers=headers("approver")).json()
    targets = [a["target"] for a in audit_rows]
    assert draft_id in targets


# ==============================================================================
# PART D — SECURITY AND ADVERSARIAL TESTING
# ==============================================================================

def test_unauthorized_staff_endpoint_access_denied(app_client):
    """Travellers without Bearer tokens cannot access staff enquiries, drafts, or audit logs."""
    assert app_client.get("/api/staff/enquiries").status_code == 401
    assert app_client.get("/api/staff/drafts").status_code == 401
    assert app_client.get("/api/staff/audit").status_code == 401
    assert app_client.post("/api/staff/drafts", json={"command": "Test"}).status_code == 401


def test_csrf_origin_header_enforcement(app_client):
    """State-modifying requests with an unauthorized or mismatched Origin are blocked with 403."""
    malicious_origin = {"Origin": "https://attacker.evil.com"}
    t_quote = turn(app_client, "Sigiriya day trip for two adults on 10 January 2027")
    [q] = quotes(t_quote)

    # Attempt booking from hostile origin
    booking_res = app_client.post("/api/bookings/mock", json={"quote": str(q.id)}, headers=malicious_origin)
    assert booking_res.status_code == 403

    # Attempt staff follow-up from hostile origin
    enquiries = app_client.get("/api/staff/enquiries", headers=headers("staff")).json()
    enquiry = enquiries[0]
    followup_res = app_client.patch(f"/api/staff/enquiries/{enquiry['id']}",
                                    json={"status": "waiting", "note": "Test"},
                                    headers=headers("staff") | malicious_origin)
    assert followup_res.status_code == 403


def test_malformed_and_oversized_payloads_rejected(app_client):
    """Ensure edge cases, negative counts, oversized prompts, and malformed JSON fail safely."""
    # Message exceeding 1200 characters is rejected (422)
    long_msg = "A" * 1201
    res_long = app_client.post("/api/agent", json={
        "threadId": str(uuid4()), "runId": str(uuid4()), "state": {}, "tools": [], "context": [],
        "messages": [{"role": "user", "id": str(uuid4()), "content": long_msg}], "forwardedProps": {},
    })
    assert res_long.status_code == 422

    # Empty message is rejected (422)
    res_empty = app_client.post("/api/agent", json={
        "threadId": str(uuid4()), "runId": str(uuid4()), "state": {}, "tools": [], "context": [],
        "messages": [{"role": "user", "id": str(uuid4()), "content": "   "}], "forwardedProps": {},
    })
    assert res_empty.status_code == 422

    # Invalid run ID format
    res_bad_run = app_client.post("/api/agent", json={
        "threadId": "bad-thread", "runId": "not-a-uuid", "state": {}, "tools": [], "context": [],
        "messages": [{"role": "user", "id": "1", "content": "Hello"}], "forwardedProps": {},
    })
    assert res_bad_run.status_code == 422
