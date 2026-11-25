#!/usr/bin/env python3
"""Initialize a clean, isolated demonstration SQLite database for Ceylon Compass / Mira.

Usage:
    PYTHONPATH=apps/api .venv/bin/python scripts/init_demo_db.py [--db .mira/demo.sqlite3] [--force]

Creates a fresh database containing:
- Full Alembic schema (0006_enquiry_contact_fields)
- Synthetic demo accounts (admin, approver, editor, staff, and a clearly synthetic traveller)
- Zero historical evaluation rows, zero real PII, zero stray test enquiries/traces/bookings.
"""
from __future__ import annotations

import argparse
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "apps" / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from mira import auth, store  # noqa: E402


def _create_or_update_user(conn, email: str, password: str, full_name: str, role: str, phone: str = "") -> None:
    now = datetime.now(timezone.utc).isoformat()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    pw_hash = auth.hash_password(password)
    if existing:
        conn.execute(
            "UPDATE users SET password_hash=?, full_name=?, role=?, status='active', phone=? WHERE id=?",
            (pw_hash, full_name, role, phone, existing["id"]),
        )
    else:
        conn.execute(
            """INSERT INTO users(id, email, password_hash, full_name, role, status, phone, preferences, created_at)
               VALUES(?, ?, ?, ?, ?, 'active', ?, '{}', ?)""",
            (str(uuid4()), email, pw_hash, full_name, role, phone, now),
        )


def init_demo_database(db_path: Path, force: bool = False) -> dict[str, str]:
    db_path = db_path.resolve()
    if db_path.exists():
        if not force:
            raise SystemExit(
                f"Refusing to overwrite existing database at {db_path}. Pass --force to recreate."
            )
        db_path.unlink()

    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Point store.DB to the target demo DB without touching .mira/mira.sqlite3
    store.DB = db_path
    os.environ["MIRA_DB"] = str(db_path)

    # Use env overrides or standard predictable demo credentials
    admin_email = os.environ.get("MIRA_ADMIN_EMAIL", "admin.demo@ceyloncompass.example").strip().lower()
    admin_password = os.environ.get("MIRA_ADMIN_PASSWORD") or "Admin#2026!Compass"
    approver_password = os.environ.get("MIRA_DEMO_APPROVER_PASSWORD") or "Approver#2026!Demo"
    editor_password = os.environ.get("MIRA_DEMO_EDITOR_PASSWORD") or "Editor#2026!Demo"
    staff_password = os.environ.get("MIRA_DEMO_STAFF_PASSWORD") or "Staff#2026!Demo"
    traveller_password = os.environ.get("MIRA_DEMO_TRAVELLER_PASSWORD") or "Traveller#2026!Demo"

    os.environ["MIRA_ADMIN_EMAIL"] = admin_email
    os.environ["MIRA_ADMIN_PASSWORD"] = admin_password

    store.init()

    with store.db() as conn:
        _create_or_update_user(conn, admin_email, admin_password, "Demo Administrator", "admin")
        _create_or_update_user(conn, "admin@ceyloncompass.com", admin_password, "System Administrator", "admin")
        _create_or_update_user(
            conn,
            "approver.demo@ceyloncompass.example",
            approver_password,
            "Demo Content Approver",
            "approver",
        )
        _create_or_update_user(
            conn,
            "editor.demo@ceyloncompass.example",
            editor_password,
            "Demo Content Editor",
            "staff",
        )
        _create_or_update_user(
            conn,
            "staff.demo@ceyloncompass.example",
            staff_password,
            "Demo Travel Specialist",
            "staff",
        )
        _create_or_update_user(
            conn,
            "traveller.demo@ceyloncompass.example",
            traveller_password,
            "Demo Traveller (Synthetic)",
            "traveller",
            phone="+94 77 000 0100",
        )

    return {
        "db_path": str(db_path),
        "admin_email": admin_email,
        "admin_password": admin_password,
        "approver_email": "approver.demo@ceyloncompass.example",
        "approver_password": approver_password,
        "staff_email": "staff.demo@ceyloncompass.example",
        "staff_password": staff_password,
        "traveller_email": "traveller.demo@ceyloncompass.example",
        "traveller_password": traveller_password,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize a clean demonstration SQLite database.")
    parser.add_argument("--db", default=str(ROOT / ".mira" / "demo.sqlite3"), help="Target demo SQLite path")
    parser.add_argument("--force", action="store_true", help="Recreate target database if it exists")
    args = parser.parse_args()

    creds = init_demo_database(Path(args.db), force=args.force)
    print(f"Initialized clean demo database at: {creds['db_path']}")
    print(f"  Admin:     {creds['admin_email']} / {creds['admin_password']}")
    print(f"  Approver:  {creds['approver_email']} / {creds['approver_password']}")
    print(f"  Staff:     {creds['staff_email']} / {creds['staff_password']}")
    print(f"  Traveller: {creds['traveller_email']} / {creds['traveller_password']}")
    print("Run with: MIRA_DB=" + creds["db_path"] + " make dev")


if __name__ == "__main__":
    main()
