"""Safely add and backfill enquiries.updated_at, reference, and follow_up_date."""
from alembic import op
import sqlalchemy as sa

revision = "0005_enquiry_metadata"
down_revision = "0004_failed_traces"


def _existing_columns(conn, table: str) -> set[str]:
    rows = conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def upgrade():
    conn = op.get_bind()
    cols = _existing_columns(conn, "enquiries")

    if "assigned_to" not in cols:
        op.execute("ALTER TABLE enquiries ADD COLUMN assigned_to TEXT REFERENCES users(id) ON DELETE SET NULL;")
    if "assigned_name" not in cols:
        op.execute("ALTER TABLE enquiries ADD COLUMN assigned_name TEXT DEFAULT '';")
    if "updated_at" not in cols:
        op.execute("ALTER TABLE enquiries ADD COLUMN updated_at TEXT;")
    op.execute("UPDATE enquiries SET updated_at = COALESCE(created, CURRENT_TIMESTAMP) WHERE updated_at IS NULL OR updated_at = '';")

    if "reference" not in cols:
        op.execute("ALTER TABLE enquiries ADD COLUMN reference TEXT;")
    op.execute(
        "UPDATE enquiries SET reference = 'ENQ-' || COALESCE(NULLIF(substr(created, 1, 4), ''), '2026') || '-' || upper(substr(replace(id, '-', ''), 1, 8)) "
        "WHERE reference IS NULL OR reference = '';"
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS enquiries_reference_idx ON enquiries(reference);")

    if "follow_up_date" not in cols:
        op.execute("ALTER TABLE enquiries ADD COLUMN follow_up_date TEXT;")
    op.execute("PRAGMA user_version = 5;")
