"""Deterministic P02 cancellation policy engine and atomic simulated cancellation execution."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4
from zoneinfo import ZoneInfo

from .auth import audit_log
from .catalog import PublicQuote
from .data import as_of
from .observability import event
from .search import is_day_tour

SL_TZ = ZoneInfo("Asia/Colombo")
POLICY_EFFECTIVE_DATE = date(2026, 11, 1)
POLICY_VERSION = "P02-2026-11-01"
MULTI_DAY_ADMIN_FEE_USD = Decimal("50")


def _extract_departure_time(tour_record: dict | None) -> time | None:
    """Parse an authoritative departure time (e.g. ``5:30 am``) from published tour markdown."""
    if not tour_record:
        return None
    body = tour_record.get("body") or ""
    if m := re.search(r"\b(?:pick-?up at|boats? leave at|starts? at|departs? at)\s+(\d{1,2}):(\d{2})\s*(am|pm)\b", body, re.I):
        hour, minute = int(m[1]), int(m[2])
        ampm = m[3].lower()
        if ampm == "pm" and hour != 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        return time(hour, minute)
    return None


@dataclass(frozen=True)
class CancellationEvaluation:
    policy_version: str
    tour_category: str
    paid_amount: Decimal
    refund_amount: Decimal
    admin_fee: Decimal
    eligible: bool
    escalate_to_staff: bool
    terms_summary: str
    consequences: str
    reason: str


def _parse_created_date(created_str: str | None) -> date | None:
    if not created_str:
        return None
    try:
        return date.fromisoformat(str(created_str).strip()[:10])
    except ValueError:
        return None


def evaluate_cancellation(
    tour_record: dict | None,
    quote: PublicQuote,
    booking_row: dict | None = None,
    *,
    now_dt: datetime | None = None,
) -> CancellationEvaluation:
    """Compute exact P02 cancellation eligibility and Decimal refund amount.

    P02 rules (effective for bookings made from 1 November 2026):
    - Day and city tours: Free cancellation up to 48 hours before start; no refund after that.
    - Multi-day tours and stays:
      * 30 days or more before start: full refund minus USD 50 admin fee.
      * 8 to 29 days before start: 50% refund.
      * 7 days or less: no refund.
    """
    if now_dt is None:
        now_dt = datetime.combine(as_of(), time(9, 0), tzinfo=SL_TZ)
    elif now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=SL_TZ)
    else:
        now_dt = now_dt.astimezone(SL_TZ)

    paid_amount = Decimal(str(booking_row["paid_amount"])) if (booking_row and booking_row.get("paid_amount")) else Decimal(str(quote.deposit))
    booking_status = (booking_row or {}).get("status", "confirmed")

    if booking_status == "cancelled":
        prev_refund = Decimal(str(booking_row["refund_amount"])) if booking_row and booking_row.get("refund_amount") else Decimal("0")
        return CancellationEvaluation(
            policy_version=booking_row.get("policy_version") or POLICY_VERSION,
            tour_category=tour_record.get("category", "Tour") if tour_record else "Tour",
            paid_amount=paid_amount,
            refund_amount=prev_refund,
            admin_fee=Decimal("0"),
            eligible=False,
            escalate_to_staff=False,
            terms_summary="This simulated booking is already cancelled.",
            consequences="No further cancellation or refund will be issued.",
            reason="already_cancelled",
        )

    created_date = _parse_created_date((booking_row or {}).get("created"))
    if created_date and created_date < POLICY_EFFECTIVE_DATE:
        return CancellationEvaluation(
            policy_version="legacy_pre_2026_11_01",
            tour_category=tour_record.get("category", "Tour") if tour_record else "Tour",
            paid_amount=paid_amount,
            refund_amount=Decimal("0"),
            admin_fee=Decimal("0"),
            eligible=False,
            escalate_to_staff=True,
            terms_summary="Booking predates the 1 November 2026 policy; specialist review required.",
            consequences="A travel specialist will confirm applicable legacy cancellation terms.",
            reason="legacy_policy_escalation",
        )

    day_tour = is_day_tour(tour_record) if tour_record else (quote.balance == 0)

    if day_tour:
        dep_time = _extract_departure_time(tour_record)
        if dep_time is None:
            days_diff = (quote.date - now_dt.date()).days
            if 1 <= days_diff <= 3:
                return CancellationEvaluation(
                    policy_version=POLICY_VERSION,
                    tour_category="Day and city tours",
                    paid_amount=paid_amount,
                    refund_amount=Decimal("0"),
                    admin_fee=Decimal("0"),
                    eligible=False,
                    escalate_to_staff=True,
                    terms_summary="Departure time is not published for this tour near the 48-hour cutoff; specialist review required.",
                    consequences="A travel specialist will confirm your exact start time and 48-hour refund eligibility.",
                    reason="departure_time_unavailable_near_48h_boundary",
                )
            dep_time = time(0, 0)
        start_dt = datetime.combine(quote.date, dep_time, tzinfo=SL_TZ)
        delta = start_dt - now_dt
        if delta >= timedelta(hours=48):
            return CancellationEvaluation(
                policy_version=POLICY_VERSION,
                tour_category="Day and city tours",
                paid_amount=paid_amount,
                refund_amount=paid_amount,
                admin_fee=Decimal("0"),
                eligible=True,
                escalate_to_staff=False,
                terms_summary="Free cancellation up to 48 hours before the start.",
                consequences=f"Full simulated refund of USD {paid_amount} on USD {paid_amount} paid.",
                reason="day_tour_ge_48h_full_refund",
            )
        return CancellationEvaluation(
            policy_version=POLICY_VERSION,
            tour_category="Day and city tours",
            paid_amount=paid_amount,
            refund_amount=Decimal("0"),
            admin_fee=Decimal("0"),
            eligible=False,
            escalate_to_staff=False,
            terms_summary="No refund within 48 hours of start.",
            consequences=f"USD 0 simulated refund (within 48 hours of departure; USD {paid_amount} forfeited).",
            reason="day_tour_lt_48h_no_refund",
        )

    days_before = (quote.date - now_dt.date()).days
    if days_before >= 30:
        admin_fee = min(paid_amount, MULTI_DAY_ADMIN_FEE_USD)
        refund = max(Decimal("0"), paid_amount - admin_fee)
        return CancellationEvaluation(
            policy_version=POLICY_VERSION,
            tour_category="Multi-day tours and stays",
            paid_amount=paid_amount,
            refund_amount=refund,
            admin_fee=admin_fee,
            eligible=refund > 0,
            escalate_to_staff=False,
            terms_summary="30 days or more before start: full refund minus a USD 50 admin fee.",
            consequences=f"Simulated refund of USD {refund} (USD {paid_amount} paid minus USD {admin_fee} admin fee).",
            reason="multi_day_ge_30d_minus_50",
        )
    if 8 <= days_before <= 29:
        refund = (paid_amount * Decimal("0.5")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return CancellationEvaluation(
            policy_version=POLICY_VERSION,
            tour_category="Multi-day tours and stays",
            paid_amount=paid_amount,
            refund_amount=refund,
            admin_fee=Decimal("0"),
            eligible=refund > 0,
            escalate_to_staff=False,
            terms_summary="8 to 29 days before start: 50% refund.",
            consequences=f"Simulated 50% refund of USD {refund} on USD {paid_amount} paid.",
            reason="multi_day_8_to_29d_50pct",
        )
    return CancellationEvaluation(
        policy_version=POLICY_VERSION,
        tour_category="Multi-day tours and stays",
        paid_amount=paid_amount,
        refund_amount=Decimal("0"),
        admin_fee=Decimal("0"),
        eligible=False,
        escalate_to_staff=False,
        terms_summary="7 days or less before start: no refund.",
        consequences=f"USD 0 simulated refund (7 days or less before departure; USD {paid_amount} forfeited).",
        reason="multi_day_le_7d_no_refund",
    )


def find_owned_bookings(conn, visitor_id: str, user_id: str | None) -> list[dict]:
    """Return all bookings owned by ``visitor_id`` or authenticated ``user_id``."""
    if user_id:
        rows = conn.execute(
            """SELECT b.*, q.public, q.trace, q.visitor
               FROM bookings b
               JOIN quotes q ON q.id = b.quote
               WHERE q.visitor=? OR q.visitor IN (SELECT id FROM visitors WHERE user_id=?)
               ORDER BY b.rowid DESC""",
            (visitor_id, user_id),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT b.*, q.public, q.trace, q.visitor
               FROM bookings b
               JOIN quotes q ON q.id = b.quote
               JOIN visitors v ON v.id = q.visitor
               WHERE q.visitor=? AND v.user_id IS NULL
               ORDER BY b.rowid DESC""",
            (visitor_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def create_pending_cancellation(
    conn,
    booking_quote_id: str,
    visitor_id: str,
    user_id: str | None,
    eval_res: CancellationEvaluation,
) -> str:
    """Persist a ``pending_confirmation`` record for Phase 1 preview."""
    req_id = str(uuid4())
    conn.execute(
        """INSERT INTO cancellation_requests(id, booking_id, visitor_id, user_id, target_type, status, policy_version, paid_amount, refund_amount, refund_status)
           VALUES (?, ?, ?, ?, 'booking', 'pending_confirmation', ?, ?, ?, 'pending')""",
        (req_id, booking_quote_id, visitor_id, user_id, eval_res.policy_version, str(eval_res.paid_amount), str(eval_res.refund_amount)),
    )
    return req_id


def execute_mock_cancellation(
    conn,
    booking_quote_id: str,
    visitor_id: str,
    user_id: str | None,
    records: dict,
    *,
    reason: str = "traveller_requested",
    now_dt: datetime | None = None,
    require_pending: bool = False,
) -> dict:
    """Atomically and idempotently cancel a confirmed mock booking inside ``BEGIN IMMEDIATE``."""
    if user_id:
        row = conn.execute(
            """SELECT b.*, q.public, q.trace, q.visitor
               FROM bookings b
               JOIN quotes q ON q.id = b.quote
               WHERE (b.quote=? OR b.id=?)
                 AND (q.visitor=? OR q.visitor IN (SELECT id FROM visitors WHERE user_id=?))""",
            (booking_quote_id, booking_quote_id, visitor_id, user_id),
        ).fetchone()
    else:
        row = conn.execute(
            """SELECT b.*, q.public, q.trace, q.visitor
               FROM bookings b
               JOIN quotes q ON q.id = b.quote
               JOIN visitors v ON v.id = q.visitor
               WHERE (b.quote=? OR b.id=?) AND q.visitor=? AND v.user_id IS NULL""",
            (booking_quote_id, booking_quote_id, visitor_id),
        ).fetchone()
    if not row:
        raise PermissionError("Booking not found or unauthorized")

    booking = dict(row)
    quote = PublicQuote.model_validate_json(booking["public"])
    tour_rec = records.get(quote.source)

    if booking.get("status") == "cancelled":
        return {
            "status": "cancelled",
            "idempotent": True,
            "booking_reference": booking["id"],
            "quote_id": booking["quote"],
            "refund_amount": booking.get("refund_amount") or "0",
            "refund_status": booking.get("refund_status") or "simulated_completed",
            "policy_version": booking.get("policy_version") or POLICY_VERSION,
        }

    pending_row = None
    if user_id:
        pending_row = conn.execute(
            """SELECT id FROM cancellation_requests
               WHERE booking_id=? AND status='pending_confirmation' AND (user_id=? OR visitor_id=?)
               ORDER BY rowid DESC LIMIT 1""",
            (booking["quote"], user_id, visitor_id),
        ).fetchone()
    else:
        pending_row = conn.execute(
            """SELECT id FROM cancellation_requests
               WHERE booking_id=? AND status='pending_confirmation' AND visitor_id=?
               ORDER BY rowid DESC LIMIT 1""",
            (booking["quote"], visitor_id),
        ).fetchone()
    if require_pending and not pending_row:
        raise ValueError("Preview cancellation and confirm before executing")

    eval_res = evaluate_cancellation(tour_rec, quote, booking, now_dt=now_dt)
    actor = user_id or visitor_id

    if eval_res.escalate_to_staff:
        conn.execute(
            "UPDATE bookings SET status='cancellation_pending', version=version+1 WHERE quote=?",
            (booking["quote"],),
        )
        if pending_row:
            conn.execute(
                """UPDATE cancellation_requests
                   SET status='pending_staff', policy_version=?, paid_amount=?, refund_amount=?, refund_status='pending', updated_at=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (eval_res.policy_version, str(eval_res.paid_amount), str(eval_res.refund_amount), pending_row["id"]),
            )
        else:
            req_id = str(uuid4())
            conn.execute(
                """INSERT INTO cancellation_requests(id, booking_id, visitor_id, user_id, target_type, status, policy_version, paid_amount, refund_amount, refund_status)
                   VALUES (?, ?, ?, ?, 'booking', 'pending_staff', ?, ?, ?, 'pending')""",
                (req_id, booking["quote"], visitor_id, user_id, eval_res.policy_version, str(eval_res.paid_amount), str(eval_res.refund_amount)),
            )
        audit_log(conn, actor, "booking_cancellation_requested", booking["quote"])
        return {
            "status": "pending_staff",
            "idempotent": False,
            "booking_reference": booking["id"],
            "quote_id": booking["quote"],
            "refund_amount": str(eval_res.refund_amount),
            "refund_status": "pending",
            "policy_version": eval_res.policy_version,
        }

    refund_str = str(eval_res.refund_amount)
    conn.execute(
        """UPDATE bookings
           SET status='cancelled',
               paid_amount=?,
               cancelled_at=CURRENT_TIMESTAMP,
               cancelled_by=?,
               cancellation_reason=?,
               refund_amount=?,
               refund_status='simulated_completed',
               policy_version=?,
               version=version+1
           WHERE quote=? AND version=?""",
        (str(eval_res.paid_amount), actor, reason[:200], refund_str, eval_res.policy_version, booking["quote"], booking.get("version", 0)),
    )
    if pending_row:
        conn.execute(
            """UPDATE cancellation_requests
               SET status='cancelled', policy_version=?, paid_amount=?, refund_amount=?, refund_status='simulated_completed', updated_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            (eval_res.policy_version, str(eval_res.paid_amount), refund_str, pending_row["id"]),
        )
    else:
        req_id = str(uuid4())
        conn.execute(
            """INSERT INTO cancellation_requests(id, booking_id, visitor_id, user_id, target_type, status, policy_version, paid_amount, refund_amount, refund_status)
               VALUES (?, ?, ?, ?, 'booking', 'cancelled', ?, ?, ?, 'simulated_completed')""",
            (req_id, booking["quote"], visitor_id, user_id, eval_res.policy_version, str(eval_res.paid_amount), refund_str),
        )
    if quote.enquiry:
        conn.execute("UPDATE enquiries SET status='closed', updated_at=CURRENT_TIMESTAMP WHERE id=?", (str(quote.enquiry),))
        conn.execute(
            "INSERT INTO notes(enquiry, actor, body) VALUES (?, ?, ?)",
            (str(quote.enquiry), actor, f"Simulated booking {booking['id']} cancelled ({eval_res.policy_version}); simulated refund USD {refund_str}."),
        )
    audit_log(conn, actor, "booking_cancelled_simulated", booking["quote"])
    event(
        "BOOKING",
        "cancellation.executed",
        booking_reference=booking["id"],
        quote_id=booking["quote"],
        policy_version=eval_res.policy_version,
        refund_amount=refund_str,
        refund_status="simulated_completed",
    )
    return {
        "status": "cancelled",
        "idempotent": False,
        "booking_reference": booking["id"],
        "quote_id": booking["quote"],
        "refund_amount": refund_str,
        "refund_status": "simulated_completed",
        "policy_version": eval_res.policy_version,
    }
