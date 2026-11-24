import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB = Path(os.getenv("MIRA_DB", ".mira/mira.sqlite3"))
_DEV_DB = Path(".mira/mira.sqlite3").resolve()


def _guard_dev_db():
    if os.getenv("PYTEST_CURRENT_TEST") and DB.resolve() == _DEV_DB:
        raise RuntimeError("Tests must use an isolated temporary database, not .mira/mira.sqlite3")


@contextmanager
def db():
    _guard_dev_db()
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
    _guard_dev_db()
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import URL, create_engine

    DB.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(URL.create("sqlite", database=str(DB)),connect_args={"timeout":10})
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA journal_mode=WAL")
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            config = Config()
            config.set_main_option("script_location", str(Path(__file__).with_name("migrations")))
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            connection.commit()
    finally:
        engine.dispose()


def is_current_notebook_turn(conn, trace):
    latest = conn.execute("""SELECT trace FROM trip_turns WHERE trip=(
        SELECT trip FROM trip_turns WHERE trace=?) ORDER BY rowid DESC LIMIT 1""", (trace,)).fetchone()
    return latest is None or latest["trace"] == trace


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
