"""Regression tests for tour-context preservation, date/age parsing, DB migration, dashboard counts, and staff enquiry management."""
import json
import sqlite3
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from conftest import headers
from mira import store
from mira.agent import parse_date
from mira.main import app


def send_turn(client, trip_id, message, run=None):
    run = run or str(uuid4())
    resp = client.post(
        "/api/agent",
        params={"trip_id": trip_id},
        json={
            "threadId": trip_id,
            "runId": run,
            "messages": [{"id": run, "role": "user", "content": message}],
            "state": {},
            "tools": [],
            "context": [],
            "forwardedProps": {},
        },
    )
    resp.raise_for_status()
    events = [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith("data: ")]
    assert events[-1]["type"] == "RUN_FINISHED"
    snap = next(
        e["snapshot"]
        for e in reversed(events)
        if e["type"] == "STATE_SNAPSHOT" and "turn" in e["snapshot"]
    )
    return snap["turn"], snap["surface"]


def test_a_preserve_selected_tour_on_followup_quote_and_missing_rate(app_client):
    trip_id = app_client.post("/api/trips").json()["id"]
    t1, _ = send_turn(app_client, trip_id, "Cultural Triangle Tour")
    assert [c["id"] for c in t1["components"] if c["type"] == "TourCard"] == ["T16"]

    t2, surface2 = send_turn(
        app_client,
        trip_id,
        "Price for January 10, 2027, for two adults and three children aged 7, 7, and 7",
    )
    cards = [c for c in t2["components"] if c["type"] == "TourCard"]
    assert [c["id"] for c in cards] == ["T16"]
    notice = next(c for c in t2["components"] if c["type"] == "EnquiryNotice")
    assert notice["reference"]
    assert surface2[0]["version"] == "v0.9"


def test_date_and_child_age_extraction_variants(app_client):
    assert parse_date("January 10, 2027") == "2027-01-10"
    assert parse_date("10 January 2027") == "2027-01-10"
    assert parse_date("2027-01-10") == "2027-01-10"
    # Ambiguous numeric dates must not be guessed
    assert parse_date("01/10/2027") is None

    trip_id = app_client.post("/api/trips").json()["id"]
    t_ambig, _ = send_turn(app_client, trip_id, "Sigiriya day trip for 2 adults on 01/10/2027")
    assert "valid travel date" in t_ambig["text"].lower()
    assert not any(c["type"] == "PriceBreakdown" for c in t_ambig["components"])

    # Oxford comma child ages: 7, 7, and 7 on T01
    trip2 = app_client.post("/api/trips").json()["id"]
    t_ox, _ = send_turn(
        app_client,
        trip2,
        "Sigiriya day trip on January 10, 2027 for two adults and three children aged 7, 7, and 7",
    )
    breakdown = next(c for c in t_ox["components"] if c["type"] == "PriceBreakdown")
    assert breakdown["quote"]["source"] == "T01"
    assert breakdown["quote"]["ages"] == [7, 7, 7]


def test_b_d_e_f_g_h_enquiry_lifecycle_isolation_and_staff_update(app_client):
    app_client.post(
        "/api/auth/register",
        json={"email": "alice@example.com", "password": "Password123!", "full_name": "Alice Perera"},
    ).raise_for_status()

    trip_id = app_client.post("/api/trips").json()["id"]
    run_id = str(uuid4())
    turn1, _ = send_turn(app_client, trip_id, "@trip T16 2027-01-10 2 7,7,7", run=run_id)
    # Retry deduplication (same run_id)
    turn2, _ = send_turn(app_client, trip_id, "@trip T16 2027-01-10 2 7,7,7", run=run_id)
    assert turn1["trace"] == turn2["trace"]

    ref = next(c["reference"] for c in turn1["components"] if c["type"] == "EnquiryNotice")
    assert app_client.get(f"/api/enquiries/{ref}").status_code == 200

    # Account isolation
    with TestClient(app) as other:
        other.post("/api/session", json={"remember": False}).raise_for_status()
        other.post(
            "/api/auth/register",
            json={"email": "bob@example.com", "password": "Password123!", "full_name": "Bob Silva"},
        ).raise_for_status()
        assert other.get(f"/api/enquiries/{ref}").status_code == 404
        assert other.get("/api/traveller/overview").json()["total_enquiries"] == 0

    # Staff inspection & update with follow_up_date
    with TestClient(app) as staff:
        detail = staff.get(f"/api/staff/enquiries/{ref}", headers=headers("staff")).json()
        assert detail["tour_id"] == "T16"
        assert detail["tour_name"] == "Cultural Triangle Tour"
        assert detail["adults"] == 2
        assert detail["children_count"] == 3
        assert detail["child_ages"] == [7, 7, 7]
        assert detail["traveller_name"] == "Alice Perera"
        assert detail["reference"].startswith("ENQ-")
        assert detail["created"].endswith("Z")

        patch = staff.patch(
            f"/api/staff/enquiries/{ref}",
            headers=headers("staff"),
            json={"status": "contacted", "note": "Confirmed availability", "follow_up_date": "2026-12-01"},
        )
        assert patch.status_code == 200
        updated = staff.get(f"/api/staff/enquiries/{ref}", headers=headers("staff")).json()
        assert updated["status"] == "contacted"
        assert updated["follow_up_date"] == "2026-12-01"
        assert any("Confirmed availability" in n["body"] for n in updated["notes"])

    # Session restoration for Alice
    with TestClient(app) as restored:
        restored.post("/api/session", json={"remember": False}).raise_for_status()
        restored.post(
            "/api/auth/login",
            json={"email": "alice@example.com", "password": "Password123!"},
        ).raise_for_status()
        ov = restored.get("/api/traveller/overview").json()
        assert ov["total_enquiries"] == 1
        assert ov["enquiries"][0]["status"] == "contacted"
        assert ov["enquiries"][0]["tour_name"] == "Cultural Triangle Tour"


def test_c_dashboard_counts_exceed_10_and_100(app_client):
    app_client.post(
        "/api/auth/register",
        json={"email": "poweruser@example.com", "password": "Password123!", "full_name": "Power User"},
    ).raise_for_status()
    me = app_client.get("/api/auth/me").json()
    with store.db() as conn:
        vid = conn.execute("SELECT id FROM visitors WHERE user_id=?", (me["id"],)).fetchone()["id"]
        for i in range(105):
            tid = str(uuid4())
            eid = str(uuid4())
            conn.execute(
                "INSERT INTO traces(id, visitor, run, events, result) VALUES (?,?,?,?,?)",
                (tid, vid, f"run-{i}", "[]", "{}"),
            )
            conn.execute(
                "INSERT INTO enquiries(id, reference, trace, trip, reason, status) VALUES (?,?,?,?,?,?)",
                (eid, f"ENQ-2026-{eid[:8].upper()}", tid, '{"tour":"T16"}', "tour_rate", "new"),
            )
    ov = app_client.get("/api/traveller/overview").json()
    assert ov["total_enquiries"] == 105
    assert ov["active_enquiries"] == 105
    assert len(ov["enquiries"]) == 20  # paginated list stays bounded while count is exact


def test_migration_0005_repairs_missing_updated_at_idempotently(tmp_path, monkeypatch):
    legacy_db = tmp_path / "legacy.sqlite3"
    conn = sqlite3.connect(legacy_db)
    conn.executescript(
        """
        CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL);
        INSERT INTO alembic_version VALUES ('0004_failed_traces');
        CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, full_name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'traveller', status TEXT NOT NULL DEFAULT 'active', phone TEXT NOT NULL DEFAULT '', preferences TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE visitors (id TEXT PRIMARY KEY, remember INTEGER NOT NULL, context TEXT NOT NULL DEFAULT '{}', user_id TEXT);
        CREATE TABLE traces (id TEXT PRIMARY KEY, visitor TEXT, run TEXT NOT NULL, events TEXT NOT NULL, result TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE quotes (id TEXT PRIMARY KEY, visitor TEXT, trace TEXT NOT NULL UNIQUE, public TEXT NOT NULL, internal TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE enquiries (id TEXT PRIMARY KEY, trace TEXT NOT NULL UNIQUE, quote TEXT, trip TEXT NOT NULL, reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'new', created TEXT DEFAULT CURRENT_TIMESTAMP, assigned_to TEXT, assigned_name TEXT DEFAULT '');
        INSERT INTO enquiries(id, trace, trip, reason) VALUES ('11111111-1111-1111-1111-111111111111', 't-1', '{"tour":"T16"}', 'tour_rate');
        """
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(store, "DB", legacy_db)
    store.init()
    store.init()  # idempotent second run

    with store.db() as migrated:
        cols = {r[1] for r in migrated.execute("PRAGMA table_info(enquiries)").fetchall()}
        assert {"updated_at", "reference", "follow_up_date"}.issubset(cols)
        row = migrated.execute("SELECT reference, updated_at FROM enquiries").fetchone()
        assert row["reference"].startswith("ENQ-")
        assert row["updated_at"]


def test_dev_db_isolation_guard(monkeypatch):
    monkeypatch.setattr(store, "DB", store._DEV_DB)
    with pytest.raises(RuntimeError, match="isolated temporary database"):
        with store.db():
            pass
