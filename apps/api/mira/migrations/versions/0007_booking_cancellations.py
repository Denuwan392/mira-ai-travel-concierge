"""Add booking lifecycle/refund columns and cancellation_requests table."""
from alembic import op
import sqlalchemy as sa

revision = "0007_booking_cancellations"
down_revision = "0006_enquiry_contact_fields"


def _existing_columns(conn, table: str) -> set[str]:
    rows = conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def upgrade():
    conn = op.get_bind()
    op.execute(
        """CREATE TABLE IF NOT EXISTS bookings (
            quote TEXT PRIMARY KEY REFERENCES quotes(id), id TEXT NOT NULL,
            created TEXT DEFAULT CURRENT_TIMESTAMP
        );"""
    )
    cols = _existing_columns(conn, "bookings")
    additions = [
        ("status", "TEXT NOT NULL DEFAULT 'confirmed'"),
        ("paid_amount", "TEXT"),
        ("cancelled_at", "TEXT"),
        ("cancelled_by", "TEXT"),
        ("cancellation_reason", "TEXT"),
        ("refund_amount", "TEXT"),
        ("refund_status", "TEXT NOT NULL DEFAULT 'none'"),
        ("policy_version", "TEXT"),
        ("version", "INTEGER NOT NULL DEFAULT 0"),
    ]
    for col, ddl in additions:
        if col not in cols:
            op.execute(f"ALTER TABLE bookings ADD COLUMN {col} {ddl};")

    op.execute(
        """CREATE TABLE IF NOT EXISTS cancellation_requests (
            id TEXT PRIMARY KEY,
            booking_id TEXT REFERENCES bookings(quote),
            enquiry_id TEXT REFERENCES enquiries(id),
            visitor_id TEXT,
            user_id TEXT,
            target_type TEXT NOT NULL,
            status TEXT NOT NULL,
            policy_version TEXT,
            paid_amount TEXT,
            refund_amount TEXT,
            refund_status TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );"""
    )
