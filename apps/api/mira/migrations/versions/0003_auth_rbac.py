"""Add user accounts, sessions, brute-force lockout tracking, and RBAC/review metadata columns."""
from alembic import op

revision = '0003_auth_rbac'
down_revision = '0002_notebooks'


def upgrade():
    """Create auth tables and idempotently add assignment/review columns to enquiries and drafts."""
    op.execute("""CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'traveller' CHECK (role IN ('guest', 'traveller', 'staff', 'approver', 'admin')),
                status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'deactivated')),
                phone TEXT NOT NULL DEFAULT '',
                preferences TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);""")

    op.execute("""CREATE TABLE IF NOT EXISTS user_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                visitor_id TEXT REFERENCES visitors(id) ON DELETE SET NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT NOT NULL,
                revoked INTEGER NOT NULL DEFAULT 0,
                ip_address TEXT NOT NULL DEFAULT '',
                user_agent TEXT NOT NULL DEFAULT '');""")

    op.execute("""CREATE TABLE IF NOT EXISTS login_attempts (
                key TEXT PRIMARY KEY,
                attempts INTEGER NOT NULL DEFAULT 1,
                last_attempt REAL NOT NULL,
                locked_until REAL NOT NULL DEFAULT 0);""")

    op.execute("""CREATE INDEX IF NOT EXISTS user_sessions_user ON user_sessions(user_id, revoked, expires_at);""")

    try:
        op.execute("ALTER TABLE visitors ADD COLUMN user_id TEXT REFERENCES users(id) ON DELETE SET NULL;")
    except Exception:
        pass

    try:
        op.execute("ALTER TABLE enquiries ADD COLUMN assigned_to TEXT REFERENCES users(id) ON DELETE SET NULL;")
    except Exception:
        pass

    try:
        op.execute("ALTER TABLE enquiries ADD COLUMN assigned_name TEXT DEFAULT '';")
    except Exception:
        pass

    try:
        op.execute("ALTER TABLE enquiries ADD COLUMN updated_at TEXT DEFAULT CURRENT_TIMESTAMP;")
    except Exception:
        pass

    try:
        op.execute("ALTER TABLE drafts ADD COLUMN reviewer TEXT DEFAULT '';")
    except Exception:
        pass

    try:
        op.execute("ALTER TABLE drafts ADD COLUMN review_notes TEXT DEFAULT '';")
    except Exception:
        pass

    try:
        op.execute("ALTER TABLE drafts ADD COLUMN reviewed_at TEXT;")
    except Exception:
        pass

    op.execute("PRAGMA user_version = 4;")
