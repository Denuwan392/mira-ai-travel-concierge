import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB = Path(os.getenv("MIRA_DB", ".mira/mira.sqlite3"))


@contextmanager
def db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init():
    with db() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS visitors (
                id TEXT PRIMARY KEY, remember INTEGER NOT NULL, context TEXT NOT NULL DEFAULT '{}');
            CREATE TABLE IF NOT EXISTS traces (
                id TEXT PRIMARY KEY, visitor TEXT REFERENCES visitors(id) ON DELETE SET NULL,
                run TEXT NOT NULL, events TEXT NOT NULL, result TEXT NOT NULL,
                created TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(visitor, run));
            CREATE TABLE IF NOT EXISTS quotes (
                id TEXT PRIMARY KEY, visitor TEXT REFERENCES visitors(id) ON DELETE SET NULL,
                trace TEXT NOT NULL UNIQUE REFERENCES traces(id), public TEXT NOT NULL,
                internal TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS enquiries (
                id TEXT PRIMARY KEY, trace TEXT NOT NULL UNIQUE REFERENCES traces(id),
                quote TEXT REFERENCES quotes(id), trip TEXT NOT NULL, reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new', created TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY, enquiry TEXT NOT NULL REFERENCES enquiries(id),
                actor TEXT NOT NULL, body TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS drafts (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL,
                source TEXT NOT NULL, author TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft',
                created TEXT DEFAULT CURRENT_TIMESTAMP, published TEXT);
            CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY, actor TEXT NOT NULL, action TEXT NOT NULL,
                target TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS bookings (
                quote TEXT PRIMARY KEY REFERENCES quotes(id), id TEXT NOT NULL,
                created TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit
                BEGIN SELECT RAISE(ABORT, 'append-only audit'); END;
            CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit
                BEGIN SELECT RAISE(ABORT, 'append-only audit'); END;
            CREATE TABLE IF NOT EXISTS rate_snapshots (
                digest TEXT PRIMARY KEY, workbook BLOB NOT NULL, imported TEXT DEFAULT CURRENT_TIMESTAMP);
            PRAGMA user_version = 2;
        """)


def encode(value):
    return json.dumps(value, separators=(",", ":"))


def published_records():
    from .data import published
    original = published()
    with db() as conn:
        for row in conn.execute("SELECT * FROM drafts WHERE status = 'published'"):
            original[row["id"]] = {
                "id": row["id"], "title": row["title"], "body": row["body"],
                "type": "tour", "category": "Custom journey", "duration": "", "start": "",
                "destinations": [], "status": "published", "path": "Content studio",
            }
    return original
