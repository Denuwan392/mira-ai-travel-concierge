"""Add contact persistence fields, contactable flag, and enquiry_type to enquiries."""
from alembic import op
import sqlalchemy as sa

revision = "0006_enquiry_contact_fields"
down_revision = "0005_enquiry_metadata"


def _existing_columns(conn, table: str) -> set[str]:
    """Return the set of column names currently defined on ``table``."""
    rows = conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def upgrade():
    """Add contact fields, ``is_contactable``, and ``enquiry_type`` to ``enquiries`` and backfill."""
    conn = op.get_bind()
    cols = _existing_columns(conn, "enquiries")

    if "contact_name" not in cols:
        op.execute("ALTER TABLE enquiries ADD COLUMN contact_name TEXT DEFAULT '';")
    if "contact_email" not in cols:
        op.execute("ALTER TABLE enquiries ADD COLUMN contact_email TEXT DEFAULT '';")
    if "contact_phone" not in cols:
        op.execute("ALTER TABLE enquiries ADD COLUMN contact_phone TEXT DEFAULT '';")
    if "contact_notes" not in cols:
        op.execute("ALTER TABLE enquiries ADD COLUMN contact_notes TEXT DEFAULT '';")
    if "is_contactable" not in cols:
        op.execute("ALTER TABLE enquiries ADD COLUMN is_contactable INTEGER NOT NULL DEFAULT 0;")
    if "enquiry_type" not in cols:
        op.execute("ALTER TABLE enquiries ADD COLUMN enquiry_type TEXT NOT NULL DEFAULT 'auto';")

    # Backfill enquiry_type for existing records
    op.execute(
        """UPDATE enquiries SET enquiry_type = CASE
            WHEN reason = 'verified_quote' THEN 'verified_quote'
            WHEN reason = 'custom_or_unsupported' THEN 'custom_itinerary'
            ELSE 'missing_rate'
        END WHERE enquiry_type = 'auto' OR enquiry_type IS NULL OR enquiry_type = '';"""
    )

    # Backfill missing reference for legacy pre-0006 records
    op.execute(
        """UPDATE enquiries SET reference = 'ENQ-' || upper(substr(replace(id, '-', ''), 1, 8))
           WHERE reference IS NULL OR reference = '';"""
    )

    # Backfill is_contactable for records belonging to authenticated users
    has_users = conn.execute(
        sa.text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'")
    ).fetchone()
    if has_users:
        op.execute(
            """UPDATE enquiries SET is_contactable = 1
               WHERE id IN (
                   SELECT e.id FROM enquiries e
                   JOIN traces t ON t.id = e.trace
                   JOIN visitors v ON v.id = t.visitor
                   JOIN users u ON u.id = v.user_id
                   WHERE u.email IS NOT NULL AND u.email != ''
               );"""
        )

    op.execute("CREATE INDEX IF NOT EXISTS enquiries_status_idx ON enquiries(status);")
    op.execute("CREATE INDEX IF NOT EXISTS enquiries_contactable_idx ON enquiries(is_contactable);")
    op.execute("PRAGMA user_version = 6;")
