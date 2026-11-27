"""Persistence operations and save node for Mira's LangGraph workflow."""
import asyncio
import logging
from time import perf_counter
from uuid import uuid4

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import AIMessage

from ..catalog import Turn
from ..data import as_of
from ..observability import elapsed, event, request_id
from ..store import db, encode
from ..surface import surface_messages
from .state import run_context, visitor_context, working


def persist():
    """Node 5 (sync worker): Atomically commit trace, quote, enquiry, and updated visitor/trip context.

    Uses ``BEGIN IMMEDIATE`` and checks that the stored context/revision still
    matches ``w["basis"]`` so concurrent requests on the same session fail fast
    instead of overwriting each other.
    """
    started = perf_counter()
    w = working.get()
    if "replay" in w:
        turn = w["replay"]
    else:
        turn = w["turn"]
        visitor, run = visitor_context.get(), run_context.get()
        enquiry = bool(w.get("reason") or w.get("quote"))
        stage = {"stage": "persistence", "enquiry": enquiry}
        if identifier := request_id.get():
            stage["request_id"] = identifier
        w["events"].append(stage)
        db_operations = ["BEGIN IMMEDIATE", "SELECT traces"]
        saved_records: dict = {}
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            previous = conn.execute("SELECT result FROM traces WHERE visitor=? AND run=?", (visitor, run)).fetchone()
            if previous:
                turn = Turn.model_validate_json(previous["result"])
                saved_records["trace_id"] = str(turn.trace)
            else:
                active = conn.execute("SELECT context FROM visitors WHERE id=?", (visitor,)).fetchone()
                trip_id = w.get("trip_id")
                db_operations.append("SELECT trips" if trip_id else "SELECT visitors")
                if trip_id:
                    uid = w.get("user_id")
                    if uid:
                        active = conn.execute(
                            """SELECT context FROM trips
                               WHERE id=? AND revision=? AND (
                                   visitor=?
                                   OR visitor IN (
                                       SELECT v2.id FROM visitors v1
                                       JOIN visitors v2 ON v1.user_id = v2.user_id
                                       WHERE v1.id=? AND v1.user_id=?
                                   )
                               )""",
                            (trip_id, w["revision"], visitor, visitor, uid),
                        ).fetchone()
                    else:
                        active = conn.execute(
                            """SELECT t.context FROM trips t
                               JOIN visitors v ON v.id = t.visitor
                               WHERE t.id=? AND t.visitor=? AND t.revision=? AND v.user_id IS NULL""",
                            (trip_id, visitor, w["revision"]),
                        ).fetchone()
                if not active or active["context"] != w["basis"]:
                    raise ValueError("Session changed during this turn")
                conn.execute("INSERT INTO traces(id, visitor, run, events, result) VALUES(?,?,?,?,?)",
                             (str(turn.trace), visitor, run, encode(w["events"]), turn.model_dump_json()))
                db_operations.append("INSERT traces")
                saved_records["trace_id"] = str(turn.trace)
                q = w.get("quote")
                if q:
                    conn.execute("INSERT INTO quotes(id, visitor, trace, public, internal) VALUES(?,?,?,?,?)",
                                 (str(q.id), visitor, str(turn.trace), q.model_dump_json(), encode(w["internal"])))
                    db_operations.append("INSERT quotes")
                    saved_records["quote_id"] = str(q.id)
                if trip_id and w.get("panel_action") == "date":
                    conn.execute("""UPDATE enquiries SET trip=? WHERE id=(
                        SELECT e.id FROM enquiries e JOIN trip_turns t ON t.trace=e.trace
                        WHERE t.trip=? AND e.reason='custom_or_unsupported' ORDER BY t.rowid DESC LIMIT 1)""",
                        (encode(w["context"].get("custom",{})),trip_id))
                    db_operations.append("UPDATE enquiries(trip)")
                if q or w.get("reason"):
                    enq_id = str(w.get("enquiry") or uuid4())
                    enq_ref = w.get("enquiry_reference") or f"ENQ-{as_of().year}-{enq_id.replace('-', '')[:8].upper()}"
                    reason_val = w.get("reason", "verified_quote")
                    enq_type = (
                        "verified_quote" if reason_val == "verified_quote"
                        else ("custom_itinerary" if reason_val == "custom_or_unsupported" else "missing_rate")
                    )
                    has_user = conn.execute(
                        "SELECT 1 FROM visitors v JOIN users u ON u.id=v.user_id WHERE v.id=? AND u.email!=''",
                        (visitor,),
                    ).fetchone() is not None
                    conn.execute(
                        """INSERT INTO enquiries(id, reference, trace, quote, trip, reason, enquiry_type, is_contactable, updated_at)
                           VALUES(?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
                           ON CONFLICT(id) DO UPDATE SET
                             reference=COALESCE(enquiries.reference, excluded.reference),
                             trace=excluded.trace,
                             trip=excluded.trip,
                             reason=excluded.reason,
                             quote=excluded.quote,
                             enquiry_type=CASE WHEN enquiries.enquiry_type='contact_request' THEN 'contact_request' ELSE excluded.enquiry_type END,
                             is_contactable=MAX(enquiries.is_contactable, excluded.is_contactable),
                             updated_at=CURRENT_TIMESTAMP""",
                        (
                            enq_id,
                            enq_ref,
                            str(turn.trace),
                            str(q.id) if q else None,
                            encode(w["context"].get("custom", {}) if w["action"] == "custom" else w["context"]),
                            reason_val,
                            enq_type,
                            1 if has_user else 0,
                        ),
                    )
                    db_operations.append("UPSERT enquiries")
                    saved_records["enquiry_id"] = enq_id
                    saved_records["enquiry_reference"] = enq_ref
                if trip_id:
                    if w.get("execute_cancellation") and w["execute_cancellation"].get("target_type") == "plan":
                        for field in ("proposal", "custom", "selected_day"):
                            w["context"].pop(field, None)
                    conn.execute("INSERT INTO trip_turns(trip,trace,prompt) VALUES(?,?,?)",(trip_id,str(turn.trace),w["prompt"]))
                    conn.execute("""UPDATE trips SET context=?,revision=revision+1,updated=CURRENT_TIMESTAMP,
                        title=CASE WHEN revision=0 THEN ? ELSE title END WHERE id=?""",
                        (encode(w["context"]),w["prompt"][:100],trip_id))
                    db_operations.extend(["INSERT trip_turns", "UPDATE trips"])
                    saved_records["trip_id"] = trip_id
                else:
                    conn.execute("UPDATE visitors SET context=? WHERE id=?", (encode(w["context"]), visitor))
                    db_operations.append("UPDATE visitors")
                if w.get("action") == "cancel_preview" and (pending_c := w.get("context", {}).get("pending_cancellation")):
                    if pending_c.get("target_type") == "booking":
                        from ..cancellation import create_pending_cancellation, evaluate_cancellation
                        from ..catalog import PublicQuote
                        b_row = conn.execute("SELECT * FROM bookings WHERE quote=?", (pending_c["target_id"],)).fetchone()
                        q_row = conn.execute("SELECT public FROM quotes WHERE id=?", (pending_c["target_id"],)).fetchone()
                        if b_row and q_row:
                            pq = PublicQuote.model_validate_json(q_row["public"])
                            ev = evaluate_cancellation(w["tours"].get(pq.source), pq, dict(b_row))
                            create_pending_cancellation(conn, pending_c["target_id"], visitor, w.get("user_id"), ev)
                            db_operations.append("INSERT cancellation_requests(pending)")
                if exec_cancel := w.get("execute_cancellation"):
                    if exec_cancel.get("target_type") == "booking":
                        from ..cancellation import execute_mock_cancellation
                        execute_mock_cancellation(
                            conn,
                            exec_cancel["target_id"],
                            visitor,
                            w.get("user_id"),
                            w["records"],
                        )
                        db_operations.append("EXECUTE_MOCK_CANCELLATION")
                stage["ms"] = elapsed(started)
                conn.execute("UPDATE traces SET events=? WHERE id=?", (encode(w["events"]), str(turn.trace)))
                db_operations.append("UPDATE traces")
        if not previous:
            event(
                "TRACE",
                "turn.persisted",
                quote_id=str(q.id) if q else None,
                enquiry=enquiry,
                db_operations=db_operations,
                saved_records=saved_records,
                replay_detected=False,
                transaction_result="committed",
                duration_ms=elapsed(started),
            )
    return {"turn": turn.model_dump(mode="json"), "surface": surface_messages(turn), "messages": [AIMessage(content=turn.text, id=str(turn.trace))]}


async def save(_):
    """Node 5 (async): Run ``persist()`` on a worker thread and emit the AG-UI message event."""
    started = perf_counter()
    w = working.get()
    if isinstance(w, dict):
        w.setdefault("execution_path", []).append("save")
    try:
        result = await asyncio.to_thread(persist)
    except Exception as exc:
        if isinstance(w, dict):
            w.setdefault("errors", []).append(f"save: {type(exc).__name__}")
        event("ERROR", "turn.persistence_failed", level=logging.ERROR, exception=True, transaction_result="failed")
        raise
    finally:
        if isinstance(w, dict):
            w.setdefault("node_durations", {})["save"] = elapsed(started)
    message = result["messages"][0]
    await adispatch_custom_event("manually_emit_message", {"message_id": message.id, "message": message.content})
    return result
