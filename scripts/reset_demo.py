#!/usr/bin/env python3
"""Safe Demo Database Reset Script.

Resets temporary demo activity (conversations, quotes, enquiries, bookings,
visitors, traces) while preserving all user accounts, credentials, roles,
rate snapshots, published content overrides, and audit logs.
"""

from __future__ import annotations

import argparse
import datetime
import os
from pathlib import Path
import sqlite3
import sys

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parent.parent


def get_target_db(custom_path: str | None = None) -> Path:
    if custom_path:
        return Path(custom_path).resolve()

    env_var = os.environ.get("MIRA_DB")
    if env_var:
        return Path(env_var).resolve()

    dotenv_path = ROOT / ".env"
    if dotenv_path.is_file():
        vals = dotenv_values(dotenv_path)
        if vals.get("MIRA_DB"):
            return Path(vals["MIRA_DB"]).resolve()

    return (ROOT / ".mira" / "demo.sqlite3").resolve()


def create_safe_backup(source_conn: sqlite3.Connection, db_path: Path) -> Path:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.parent / f"{db_path.name}.backup_{timestamp}"

    backup_conn = sqlite3.connect(backup_path)
    try:
        source_conn.backup(backup_conn)
    finally:
        backup_conn.close()

    # Verify backup integrity
    verify_conn = sqlite3.connect(backup_path)
    try:
        res = verify_conn.execute("PRAGMA integrity_check").fetchall()
        if res != [("ok",)]:
            raise RuntimeError(f"Integrity check failed on backup {backup_path}: {res}")
    finally:
        verify_conn.close()

    return backup_path


def count_table_rows(conn: sqlite3.Connection) -> dict[str, int]:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    counts = {}
    for t in tables:
        cur.execute(f'SELECT COUNT(*) FROM "{t}"')
        counts[t] = cur.fetchone()[0]
    return counts


def reset_demo_database(db_path: Path, force: bool = False, allow_dev_db: bool = False) -> dict:
    if not db_path.is_file():
        raise FileNotFoundError(f"Target database not found: {db_path}")

    dev_db = (ROOT / ".mira" / "mira.sqlite3").resolve()
    if db_path.resolve() == dev_db and not allow_dev_db:
        raise PermissionError(
            f"Target database is the primary development database ({db_path}). "
            "To reset this database, pass --allow-dev-db explicitly."
        )

    # Connect to target DB
    conn = sqlite3.connect(db_path, timeout=15)
    conn.row_factory = sqlite3.Row

    # Step 1: Create atomic backup
    backup_path = create_safe_backup(conn, db_path)

    # Step 2: Record counts before
    counts_before = count_table_rows(conn)

    # Step 3: Perform targeted reset in foreign-key safe order
    conn.execute("PRAGMA foreign_keys = ON")
    deleted_counts = {}

    with conn:
        # Notes (depend on enquiries)
        cur = conn.execute("DELETE FROM notes")
        deleted_counts["notes"] = cur.rowcount

        # Bookings (depend on quotes)
        cur = conn.execute("DELETE FROM bookings")
        deleted_counts["bookings"] = cur.rowcount

        # Enquiries (depend on quotes, traces, users, trips)
        cur = conn.execute("DELETE FROM enquiries")
        deleted_counts["enquiries"] = cur.rowcount

        # Trip turns (depend on trips, traces)
        cur = conn.execute("DELETE FROM trip_turns")
        deleted_counts["trip_turns"] = cur.rowcount

        # Trips (depend on visitors)
        cur = conn.execute("DELETE FROM trips")
        deleted_counts["trips"] = cur.rowcount

        # Quotes (depend on traces, visitors)
        cur = conn.execute("DELETE FROM quotes")
        deleted_counts["quotes"] = cur.rowcount

        # Dissociate any user sessions from deleted visitors, but preserve staff/admin sessions
        conn.execute("UPDATE user_sessions SET visitor_id = NULL WHERE visitor_id IS NOT NULL")

        # Traces (depend on visitors)
        cur = conn.execute("DELETE FROM traces")
        deleted_counts["traces"] = cur.rowcount

        # Failed traces
        cur = conn.execute("DELETE FROM failed_traces")
        deleted_counts["failed_traces"] = cur.rowcount

        # Visitors (root traveller cookies)
        cur = conn.execute("DELETE FROM visitors")
        deleted_counts["visitors"] = cur.rowcount

        # Drafts: keep published overrides, delete unapproved/temporary drafts
        cur = conn.execute("DELETE FROM drafts WHERE status != 'published'")
        deleted_counts["drafts (unapproved)"] = cur.rowcount

        # Reset failed login lockouts
        cur = conn.execute("DELETE FROM login_attempts")
        deleted_counts["login_attempts"] = cur.rowcount

    # Step 4: Verify foreign keys and integrity
    fk_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    if fk_violations:
        raise RuntimeError(f"Foreign key violations detected after reset: {fk_violations}")

    integrity = [r[0] for r in conn.execute("PRAGMA integrity_check").fetchall()]
    if integrity != ["ok"]:
        raise RuntimeError(f"Integrity check failed after reset: {integrity}")

    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    # Step 5: Record counts after
    counts_after = count_table_rows(conn)

    # Query preserved user accounts
    cur = conn.execute("SELECT email, role, status FROM users ORDER BY email")
    preserved_users = [dict(r) for r in cur.fetchall()]

    conn.close()

    return {
        "db_path": str(db_path),
        "backup_path": str(backup_path),
        "backup_size": backup_path.stat().st_size,
        "counts_before": counts_before,
        "counts_after": counts_after,
        "deleted_counts": deleted_counts,
        "preserved_users": preserved_users,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Safely reset demo database activity while preserving user accounts.")
    parser.add_argument("--db", default=None, help="Path to SQLite database to reset (defaults to MIRA_DB or .mira/demo.sqlite3)")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--allow-dev-db", action="store_true", help="Permit resetting .mira/mira.sqlite3")
    args = parser.parse_args()

    db_path = get_target_db(args.db)
    force = args.yes or (os.environ.get("FORCE") == "1")

    print("==================================================================")
    print(" CEYLON COMPASS HOLIDAYS — SAFE DEMO DATABASE RESET")
    print("==================================================================")
    print(f"Target Database: {db_path}")

    if not db_path.is_file():
        print(f"Error: Database file does not exist: {db_path}", file=sys.stderr)
        sys.exit(1)

    print(f"File Size:       {db_path.stat().st_size:,} bytes")
    print("Action:          Clear temporary trips, turns, quotes, enquiries, bookings,")
    print("                 traces, visitors, and lockouts.")
    print("Preserve:        ALL users, passwords, roles, rate snapshots, published content,")
    print("                 audit logs, and active staff sessions.")
    print("------------------------------------------------------------------")

    if not force:
        try:
            choice = input(f"Proceed with safe demo reset of '{db_path.name}'? [y/N]: ").strip().lower()
            if choice not in ("y", "yes"):
                print("Aborted by user.")
                sys.exit(0)
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(0)

    try:
        report = reset_demo_database(db_path, force=True, allow_dev_db=args.allow_dev_db)
    except Exception as e:
        print(f"\n[ERROR] Reset failed: {e}", file=sys.stderr)
        sys.exit(1)

    print("\n[SUCCESS] Safe demo reset completed successfully.")
    print(f"Backup created:  {report['backup_path']} ({report['backup_size']:,} bytes)")
    print("\nDeleted Records:")
    for k, v in report["deleted_counts"].items():
        if v > 0:
            print(f"  - {k}: {v}")

    print("\nPreserved Accounts:")
    for u in report["preserved_users"]:
        print(f"  - {u['email']} (role: {u['role']}, status: {u['status']})")

    print("\nTable Summary (Before -> After):")
    for t, before in report["counts_before"].items():
        after = report["counts_after"].get(t, 0)
        status = "CLEARED" if (before > 0 and after == 0) else "PRESERVED"
        print(f"  {t:<18} {before:>4} -> {after:>4}   [{status}]")

    print("==================================================================")


if __name__ == "__main__":
    main()
