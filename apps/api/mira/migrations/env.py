"""Alembic migration environment configured to reuse ``store.init()``'s SQLite connection."""
from alembic import context

connection = context.config.attributes["connection"]
context.configure(connection=connection, transactional_ddl=True)
with context.begin_transaction():
    context.run_migrations()
