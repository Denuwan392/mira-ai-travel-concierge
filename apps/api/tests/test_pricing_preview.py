"""Regression tests for read-only staff pricing preview (POST /api/staff/pricing/preview)."""
from __future__ import annotations

import json
from uuid import uuid4

from conftest import headers, quotes, turn
from mira.store import db


def _table_counts() -> dict[str, int]:
    """Return row counts across core transactional tables to assert zero DB side effects."""
    with db() as conn:
        return {
            tbl: conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            for tbl in ("quotes", "enquiries", "trips", "traces", "bookings", "audit")
        }


def test_pricing_preview_auth_and_csrf_guards(app_client):
    """Verify ``/api/staff/pricing/preview`` requires staff auth (401) and valid Origin (403)."""
    payload = {"tour_id": "T01", "date": "2027-01-10", "adults": 2}
    assert app_client.post("/api/staff/pricing/preview", json=payload).status_code == 401
    assert app_client.post(
        "/api/staff/pricing/preview",
        json=payload,
        headers=headers("staff") | {"Origin": "https://untrusted.invalid"},
    ).status_code == 403


def test_pricing_preview_valid_cases_and_no_db_writes(app_client):
    """Verify valid preview quotes match workbook pricing and perform zero SQLite writes."""
    before = _table_counts()

    # 1. Valid 2-adult day tour (T01)
    r2 = app_client.post(
        "/api/staff/pricing/preview",
        json={"tour_id": "T01", "date": "2027-01-10", "adults": 2},
        headers=headers("staff"),
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["preview_only"] is True
    assert d2["outcome"] == "PRICE_VERIFIED"
    assert d2["total_usd"] == 315
    assert d2["deposit_usd"] == 315
    assert d2["balance_usd"] == 0
    assert d2["finance"] is not None and d2["finance"]["cost_lkr"]

    # 2. Valid 4-adult day tour (T01)
    r4 = app_client.post(
        "/api/staff/pricing/preview",
        json={"tour_id": "T01", "date": "2027-01-10", "adults": 4},
        headers=headers("staff"),
    ).json()
    assert r4["preview_only"] is True
    assert r4["outcome"] == "PRICE_VERIFIED"
    assert r4["total_usd"] == 540

    # 3. Family with child ages + infant (T09, 2027-04-12, 2 adults, [7, 10], 1 infant -> same USD 2,965)
    rfam = app_client.post(
        "/api/staff/pricing/preview",
        json={"tour_id": "T09", "date": "2027-04-12", "adults": 2, "child_ages": [7, 10], "infants": 1},
        headers=headers("staff"),
    ).json()
    assert rfam["preview_only"] is True
    assert rfam["outcome"] == "PRICE_VERIFIED"
    assert rfam["total_usd"] == 2965
    assert rfam["deposit_usd"] == 742

    after = _table_counts()
    assert before == after


def test_pricing_preview_unavailable_expired_unsupported_and_invalid(app_client, monkeypatch):
    """Verify preview returns ``PRICE_UNAVAILABLE`` with reason codes and 422 on invalid input, with no DB writes."""
    before = _table_counts()

    # 4. Missing hotel rate (T12 single adult 2027-04-10)
    miss = app_client.post(
        "/api/staff/pricing/preview",
        json={"tour_id": "T12", "date": "2027-04-10", "adults": 1},
        headers=headers("staff"),
    ).json()
    assert miss["preview_only"] is True
    assert miss["outcome"] == "PRICE_UNAVAILABLE"
    assert miss["reason_code"] == "missing_amount"
    assert miss["total_usd"] is None

    # 5. Ambiguous overlapping hotel rates (T09, 2027-01-10, 4 adults, [7, 7, 7])
    ambig = app_client.post(
        "/api/staff/pricing/preview",
        json={"tour_id": "T09", "date": "2027-01-10", "adults": 4, "child_ages": [7, 7, 7]},
        headers=headers("staff"),
    ).json()
    assert ambig["preview_only"] is True
    assert ambig["outcome"] == "PRICE_UNAVAILABLE"
    assert ambig["reason_code"] == "hotel_rate_missing_or_ambiguous"

    # 6. Unsupported tour (T16 / unknown T99)
    unsup = app_client.post(
        "/api/staff/pricing/preview",
        json={"tour_id": "T16", "date": "2027-01-10", "adults": 2},
        headers=headers("staff"),
    ).json()
    assert unsup["outcome"] == "PRICE_UNAVAILABLE"
    assert unsup["reason_code"] == "tour_rate"

    unk = app_client.post(
        "/api/staff/pricing/preview",
        json={"tour_id": "T99", "date": "2027-01-10", "adults": 2},
        headers=headers("staff"),
    ).json()
    assert unk["outcome"] == "PRICE_UNAVAILABLE"
    assert unk["reason_code"] == "not_published"

    # 7. Expired rates (AS_OF_DATE past travel date)
    monkeypatch.setenv("AS_OF_DATE", "2027-01-11")
    exp = app_client.post(
        "/api/staff/pricing/preview",
        json={"tour_id": "T01", "date": "2027-01-10", "adults": 2},
        headers=headers("staff"),
    ).json()
    assert exp["outcome"] == "PRICE_UNAVAILABLE"
    assert exp["reason_code"] == "date_or_fx_expired"

    # 8. Invalid inputs
    for bad in (
        {"tour_id": "T01", "date": "2027-02-31", "adults": 2},
        {"tour_id": "T01", "date": "2027-01-10", "adults": 0},
        {"tour_id": "T01", "date": "2027-01-10", "adults": 2, "child_ages": [150]},
    ):
        assert app_client.post("/api/staff/pricing/preview", json=bad, headers=headers("staff")).status_code == 422

    assert _table_counts() == before


def test_pricing_preview_matches_official_quote_exactly(app_client):
    """Verify staff preview totals and internal finance match an official saved quote for identical inputs."""
    # Official quote via agent
    out = turn(app_client, "Cultural Triangle Sri Lanka Package for 4 adults and 3 children aged 7, 7, 7 on 12 April 2027", str(uuid4()))
    [official_q] = quotes(out)
    [enq] = app_client.get("/api/staff/enquiries", headers=headers("staff")).json()
    detail = app_client.get(f"/api/staff/enquiries/{enq['id']}", headers=headers("staff")).json()

    counts_before_preview = _table_counts()

    # Preview for identical configuration
    prev = app_client.post(
        "/api/staff/pricing/preview",
        json={"tour_id": "T09", "date": "2027-04-12", "adults": 4, "child_ages": [7, 7, 7]},
        headers=headers("staff"),
    ).json()

    assert prev["preview_only"] is True
    assert prev["outcome"] == "PRICE_VERIFIED"
    assert prev["total_usd"] == official_q.total
    assert prev["deposit_usd"] == official_q.deposit
    assert prev["balance_usd"] == official_q.balance
    assert prev["finance"]["cost_lkr"] == detail["finance"]["cost_lkr"]
    assert prev["finance"]["gross_profit_pct"] == detail["finance"]["gross_profit_pct"]
    assert _table_counts() == counts_before_preview
