"""Keep failed stream diagnostics separate from committed, replayable turns."""
from alembic import op

revision = "0004_failed_traces"
down_revision = "0003_auth_rbac"


def upgrade():
    op.execute("""CREATE TABLE failed_traces (
        id TEXT PRIMARY KEY, events TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP
    )""")


def downgrade():
    op.drop_table("failed_traces")
