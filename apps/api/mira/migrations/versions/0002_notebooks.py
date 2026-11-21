from alembic import op

revision = '0002_notebooks'
down_revision = '0001_catalogue'

def upgrade():
    op.execute("""CREATE TABLE IF NOT EXISTS trips (
                id TEXT PRIMARY KEY, visitor TEXT NOT NULL REFERENCES visitors(id) ON DELETE CASCADE,
                title TEXT NOT NULL DEFAULT 'New journey', context TEXT NOT NULL DEFAULT '{}',
                revision INTEGER NOT NULL DEFAULT 0, updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);""")
    op.execute("""CREATE TABLE IF NOT EXISTS trip_turns (
                trip TEXT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
                trace TEXT PRIMARY KEY REFERENCES traces(id), prompt TEXT NOT NULL);""")
    op.execute("""CREATE INDEX IF NOT EXISTS trips_owner ON trips(visitor,updated);""")
    op.execute("""PRAGMA user_version = 3;""")
