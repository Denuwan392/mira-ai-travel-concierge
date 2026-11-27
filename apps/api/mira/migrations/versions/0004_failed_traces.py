"""Keep failed stream diagnostics separate from committed, replayable turns."""
from alembic import op

revision = "0004_failed_traces"
down_revision = "0003_auth_rbac"


def upgrade():
    """Create the ``failed_traces`` table for failed streaming turns."""
    op.execute("""CREATE TABLE failed_traces (
        id TEXT PRIMARY KEY, events TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP
    )""")


def downgrade():
    """Drop the ``failed_traces`` table."""
    op.drop_table("failed_traces")
