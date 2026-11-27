"""Initial schema: visitors, traces, quotes, enquiries, notes, drafts, append-only audit, bookings, and rate_snapshots."""
from alembic import op

revision = '0001_catalogue'
down_revision = None

def upgrade():
    """Create core catalogue, quoting, enquiry, booking, and append-only audit tables."""
    op.execute("""CREATE TABLE IF NOT EXISTS visitors (
                id TEXT PRIMARY KEY, remember INTEGER NOT NULL, context TEXT NOT NULL DEFAULT '{}');""")
    op.execute("""CREATE TABLE IF NOT EXISTS traces (
                id TEXT PRIMARY KEY, visitor TEXT REFERENCES visitors(id) ON DELETE SET NULL,
                run TEXT NOT NULL, events TEXT NOT NULL, result TEXT NOT NULL,
                created TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(visitor, run));""")
    op.execute("""CREATE TABLE IF NOT EXISTS quotes (
                id TEXT PRIMARY KEY, visitor TEXT REFERENCES visitors(id) ON DELETE SET NULL,
                trace TEXT NOT NULL UNIQUE REFERENCES traces(id), public TEXT NOT NULL,
                internal TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP);""")
    op.execute("""CREATE TABLE IF NOT EXISTS enquiries (
                id TEXT PRIMARY KEY, trace TEXT NOT NULL UNIQUE REFERENCES traces(id),
                quote TEXT REFERENCES quotes(id), trip TEXT NOT NULL, reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new', created TEXT DEFAULT CURRENT_TIMESTAMP);""")
    op.execute("""CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY, enquiry TEXT NOT NULL REFERENCES enquiries(id),
                actor TEXT NOT NULL, body TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP);""")
    op.execute("""CREATE TABLE IF NOT EXISTS drafts (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL,
                source TEXT NOT NULL, author TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft',
                created TEXT DEFAULT CURRENT_TIMESTAMP, published TEXT);""")
    op.execute("""CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY, actor TEXT NOT NULL, action TEXT NOT NULL,
                target TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP);""")
    op.execute("""CREATE TABLE IF NOT EXISTS bookings (
                quote TEXT PRIMARY KEY REFERENCES quotes(id), id TEXT NOT NULL,
                created TEXT DEFAULT CURRENT_TIMESTAMP);""")
    op.execute("""CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit
                BEGIN SELECT RAISE(ABORT, 'append-only audit'); END;""")
    op.execute("""CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit
                BEGIN SELECT RAISE(ABORT, 'append-only audit'); END;""")
    op.execute("""CREATE TABLE IF NOT EXISTS rate_snapshots (
                digest TEXT PRIMARY KEY, workbook BLOB NOT NULL, imported TEXT DEFAULT CURRENT_TIMESTAMP);""")
