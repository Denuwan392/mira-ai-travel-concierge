"""Context loading and idempotent trace replay validation helpers."""
import json

from ..catalog import Booking, Breakdown, Turn
from ..data import Unavailable, as_of, price
from ..observability import event
from ..rates_repository import current_rates
from ..store import db, is_current_notebook_turn
from .state import working


def load_context_and_replay(visitor: str, run: str):
    """Load visitor/trip context and check for an existing trace matching ``(visitor, run)``.

    Returns:
        Tuple of ``(saved_row, replay_row)``.
    """
    with db() as conn:
        saved = conn.execute("SELECT context FROM visitors WHERE id = ?", (visitor,)).fetchone()
        if trip_id := working.get().get("trip_id"):
            saved = conn.execute("""
                SELECT context, revision FROM trips
                WHERE id=? AND (visitor=? OR visitor IN (
                    SELECT v2.id FROM visitors v1 JOIN visitors v2 ON v1.user_id = v2.user_id WHERE v1.id=? AND v1.user_id IS NOT NULL
                ))
            """, (trip_id, visitor, visitor)).fetchone()
            if not saved:
                raise ValueError("Journey unavailable")
            working.get()["revision"] = saved["revision"]
        replay = conn.execute("SELECT result FROM traces WHERE visitor = ? AND run = ?", (visitor, run)).fetchone()
    return saved, replay


def validate_replay_turn(replay_row) -> Turn:
    """Validate a replayed ``Turn``, stripping stale quotes if rates or notebook turn changed."""
    turn = Turn.model_validate_json(replay_row["result"])
    # Re-validate any embedded quote against live rates and latest notebook turn.
    old_quote = next((component.quote for component in turn.components if isinstance(component, Breakdown)), None)
    stale_stripped = False
    if old_quote:
        try:
            value = price(old_quote.source, old_quote.date, old_quote.adults, old_quote.ages, as_of(), current_rates())
            with db() as conn:
                latest = is_current_notebook_turn(conn, str(turn.trace))
                stored = conn.execute("SELECT internal FROM quotes WHERE id=?", (str(old_quote.id),)).fetchone()
            snapshot = json.loads(stored["internal"])["snapshot"]
            current = latest and (value["total"], value["deposit"], value["snapshot"]) == (
                old_quote.total, old_quote.deposit, snapshot)
        except (Unavailable, KeyError, TypeError):
            current = False
        if not current:
            stale_stripped = True
            turn = turn.model_copy(update={"text": "This saved quote needs to be refreshed. Check current rates.",
                "components": [c for c in turn.components if not isinstance(c, (Breakdown, Booking))]})
    event(
        "TRACE",
        "turn.replayed",
        replay_detected=True,
        stale_quote_stripped=stale_stripped,
        saved_records={"trace_id": str(turn.trace)},
        transaction_result="replayed",
    )
    return turn
