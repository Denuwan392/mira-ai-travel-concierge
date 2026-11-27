"""Enquiry lookup, deduplication, and reference assignment helpers."""
import json
from uuid import UUID, uuid4

from ..data import as_of
from ..store import db


def matching_enquiry(w, reason):
    """Find an existing open enquiry in the same trip notebook with matching parameters to avoid duplicates."""
    if not w.get("trip_id"):
        return None
    with db() as conn:
        candidates = conn.execute(
            """SELECT e.id, e.reference, e.trip FROM enquiries e JOIN trip_turns t ON t.trace=e.trace
               WHERE t.trip=? AND e.reason=?
                 AND e.status NOT IN ('booked','closed','closed_lost','unqualified')
                 AND (e.quote IS NULL OR e.quote NOT IN (SELECT quote FROM bookings))
               ORDER BY t.rowid DESC""",
            (w["trip_id"], reason),
        ).fetchall()

    keys = ("tour", "date", "adults", "ages") if w.get("explicit_quote") else ("tour",)
    ctx = w["context"]
    for candidate in candidates:
        try:
            previous = json.loads(candidate["trip"])
            if isinstance(previous, dict) and all(previous.get(key) == ctx.get(key) for key in keys):
                return candidate
        except (ValueError, TypeError):
            continue
    return None


def quote_enquiry(w, reason):
    """Assign or reuse an enquiry UUID and public ``ENQ-YYYY-...`` reference for the current turn."""
    previous = matching_enquiry(w, reason)
    identifier = UUID(previous["id"]) if previous else uuid4()
    reference = previous["reference"] if previous else None
    w["enquiry"] = identifier
    w["enquiry_reference"] = reference or f"ENQ-{as_of().year}-{identifier.hex[:8].upper()}"
