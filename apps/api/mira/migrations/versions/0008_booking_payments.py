"""Add booking_payments table for simulated deposit, balance, and partial payment tracking."""
from alembic import op

revision = "0008_booking_payments"
down_revision = "0007_booking_cancellations"


def upgrade():
    op.execute(
        """CREATE TABLE IF NOT EXISTS booking_payments (
            id TEXT PRIMARY KEY,
            booking_id TEXT NOT NULL REFERENCES bookings(quote),
            booking_ref TEXT NOT NULL,
            visitor_id TEXT,
            user_id TEXT,
            payment_type TEXT NOT NULL,
            amount TEXT NOT NULL,
            currency TEXT NOT NULL DEFAULT 'USD',
            status TEXT NOT NULL,
            scenario TEXT NOT NULL DEFAULT 'success',
            idempotency_key TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );"""
    )
    op.execute(
        """CREATE UNIQUE INDEX IF NOT EXISTS idx_booking_payments_idem
           ON booking_payments(booking_id, idempotency_key)
           WHERE idempotency_key IS NOT NULL;"""
    )
