"""Response composition node and focused internal handlers for Mira's LangGraph workflow."""
import json
import re
from time import perf_counter
from uuid import UUID, uuid4

from ..catalog import (
    Booking,
    Breakdown,
    Card,
    DayStop,
    Departure,
    Excerpt,
    Notice,
    Picker,
    Proposal,
    RouteMap,
    SourcePanel,
    Turn,
)
from ..data import as_of, public_text, tour_card
from ..observability import elapsed, event, truncate
from ..planner import get_grounded_day_experience, validate_itinerary
from ..store import db
from .enquiry import quote_enquiry
from .parsing import section
from .state import working


def _build_row_components(rows, action, w):
    """Build initial ``Excerpt``/``Card`` components and ``sources`` from retrieved rows."""
    components = []
    sources = []
    for row in rows:
        key = row["id"]
        if action in {"cancellation", "cancel_booking", "children", "dietary", "payment", "polonnaruwa"} or (action in {"destination", "general"} and row["type"] == "destination"):
            heading = None
            if action in {"cancellation", "cancel_booking"} and w["named"] in w["tours"]:
                heading = ("Multi-day tours and stays" if "nights" in w["tours"][w["named"]]["duration"]
                           else "Day and city tours")
            heading = {"dietary": "Can you cater for dietary needs?", "payment": "Payment"}.get(action, heading)
            body = (section(row, heading, "polonnaruwa" if action == "polonnaruwa" else None)
                    if action != "children" and not (action in {"cancellation", "cancel_booking"} and not heading)
                    else public_text(row["body"]))
            if body:
                sources.append(key)
                components.append(Excerpt(type="PolicySnippet" if row["type"] in {"policy", "faq"} else "DestinationHighlight",
                                          source=key, heading=heading or row["title"], text=body))
        elif row["type"] == "tour" and action not in {"accommodation", "tour_hotels"}:
            sources.append(key)
            components.append(Card(**tour_card(row)))
            if action == "discover":
                heading = next(iter(re.findall(r"^#+ ((?:Day 1\b|Highlights\b)[^\n]*)$", row["body"], re.M)), None)
                if heading and (body := section(row, heading)):
                    components.append(Excerpt(type="ItineraryDay", source=key, heading=heading, text=body))
            elif action == "tour_itinerary":
                tour_days = row.get("days", [])
                if tour_days:
                    for d in tour_days:
                        components.append(Excerpt(
                            type="ItineraryDay",
                            source=row["id"],
                            heading=f"Day {d['day']}: {d['title']}",
                            text=f"{d['description']}\n\n• Accommodation: {d.get('accommodation') or 'None'}\n• Meals: {d.get('meals') or 'None'}\n• Included tickets: {d.get('entrance_tickets') or 'None'}"
                        ))
                else:
                    summary_text = public_text(row.get("body", "")).strip()[:800]
                    if summary_text:
                        components.append(Excerpt(
                            type="ItineraryDay",
                            source=row["id"],
                            heading=f"{row['title']} ({row.get('duration', '')}) — Route & Highlights",
                            text=summary_text,
                        ))
    return components, sources


def _compose_verified_quote(q, components):
    """Prepend ``PriceBreakdown``, append ``BookingForm``, and format verified quote text."""
    components.insert(0, Breakdown(quote=q))
    components.append(Booking(quote=q.id))
    return (
        f"Verified quote: {q.currency} {q.total:,} total (deposit {q.currency} {q.deposit:,}) "
        f"for {q.title} on {q.date}. Private enquiry {q.enquiry_reference} is saved."
    )


def _compose_unavailable_quote(w, ctx, components):
    """Create or reuse an enquiry and prepend ``EnquiryNotice`` when automated pricing is unavailable."""
    quote_enquiry(w, w["reason"])
    enq_ref = w["enquiry_reference"]
    reason_code = w["reason"]
    if reason_code == "rate_import_invalid":
        text = notice_text = "The pricing service could not load the rate workbook. Please retry."
    elif reason_code in {"hotel_rate_missing_or_ambiguous", "unconfirmed_hotel_rate"}:
        text = (
            "We can’t verify an automated price for these travel dates because one or more contracted hotel rates "
            "for your dates are unconfirmed or have overlapping supplier revisions in our rate sheet. "
            "A travel specialist will confirm the exact rate for you. I’ve saved a private enquiry for our team."
        )
        notice_text = "Specialist confirmation required — hotel rate unconfirmed or ambiguous for selected dates"
    elif reason_code in {"tour", "tour_rate", "tour_rate_missing", "hotel_schedule"}:
        text = (
            "This journey does not have an automated package rate in our current rate sheet. "
            "A travel specialist will prepare a tailored quote for your dates. I’ve saved a private enquiry for our team."
        )
        notice_text = "Specialist confirmation required — no automated rate row for this tour"
    elif reason_code in {"group_size", "transport_rate", "date_or_fx_expired", "season_rate", "conflicting_tour_scope"}:
        reason_text = {
            "group_size": "The party exceeds the maximum group size in the rate workbook.",
            "transport_rate": "No transport tier matches the selected party size.",
            "date_or_fx_expired": "The selected date is outside the valid pricing window.",
            "season_rate": "No contracted season rate covers the selected travel date.",
            "conflicting_tour_scope": "The tour scope requires manual pricing.",
        }[reason_code]
        notice_text = reason_text
        text = reason_text + " A private enquiry has been saved for our team."
    else:
        text = "We can’t verify an automated price for these travel dates right now. A travel specialist will confirm the details. I’ve saved a private enquiry for our team."
        notice_text = "Specialist confirmation required"
    components.insert(
        0,
        Notice(
            reference=w["enquiry"],
            public_reference=enq_ref,
            outcome="PRICING_SERVICE_ERROR" if reason_code == "rate_import_invalid" else "PRICE_UNAVAILABLE",
            reason_code=reason_code,
            tour_id=ctx.get("tour"),
            text=notice_text,
        ),
    )
    return text


def _compose_custom_handoff(w, ctx, components):
    """Deduplicate open custom enquiries in the same trip and prepend ``SPECIALIST_HANDOFF`` notice."""
    w["reason"] = "custom_or_unsupported"
    prior = None
    if w.get("trip_id"):
        with db() as conn:
            candidate = conn.execute("""SELECT e.id, e.trip FROM enquiries e JOIN trip_turns t ON t.trace=e.trace
                WHERE t.trip=? AND e.reason='custom_or_unsupported'
                  AND e.status NOT IN ('booked','closed','closed_lost','unqualified')
                ORDER BY t.rowid DESC LIMIT 1""", (w["trip_id"],)).fetchone()
            if candidate:
                if w.get("panel_action") == "date":
                    prior = candidate
                else:
                    try:
                        prev_custom = json.loads(candidate["trip"]) if candidate["trip"] else {}
                        curr_custom = ctx.get("custom", {})
                        if prev_custom.get("destinations") == curr_custom.get("destinations") or prev_custom.get("request") == curr_custom.get("request"):
                            prior = candidate
                    except (ValueError, TypeError):
                        pass
    w["enquiry"] = UUID(prior["id"]) if prior else uuid4()
    enq_ref = f"ENQ-{as_of().year}-{str(w['enquiry']).replace('-', '')[:8].upper()}"
    components.insert(
        0,
        Notice(
            reference=w["enquiry"],
            public_reference=enq_ref,
            outcome="SPECIALIST_HANDOFF",
            reason_code="custom_or_unsupported",
            tour_id=ctx.get("tour"),
            text="Specialist confirmation required",
        ),
    )
    return "A travel specialist will confirm the details. I’ve saved a private enquiry for our team."


def _compose_draft_handoff(w, components):
    """Handle unpublished draft tour requests with a specialist handoff notice."""
    text = "The Northern Sri Lanka Tour is currently an unpublished draft itinerary and cannot be booked directly. A travel specialist will be happy to prepare a custom northern proposal for you."
    w["reason"] = "draft_tour_unsupported"
    w["enquiry"] = uuid4()
    enq_ref = f"ENQ-{as_of().year}-{str(w['enquiry']).replace('-', '')[:8].upper()}"
    components.insert(
        0,
        Notice(
            reference=w["enquiry"],
            public_reference=enq_ref,
            outcome="SPECIALIST_HANDOFF",
            reason_code="draft_tour_unsupported",
            text="Draft package — specialist confirmation required",
        ),
    )
    return text


def _compose_accommodation_response(w, components):
    """Handle standalone hotel recommendations and rate-protection notices."""
    w["enquiry"] = uuid4()
    w["reason"] = "accommodation_confirmation"
    hotel = w.get("hotel_match")
    record = w["tours"].get(hotel.source_tour_id) if hotel else None
    if hotel and record and hotel.name in str(record.get("hotels", [])) + record["body"]:
        passage = next((line for line in public_text(record["body"]).splitlines()
                        if hotel.name in line), hotel.name)
        if w.get("is_alt_query"):
            for candidate in w["tours"].values():
                alternative = next((day["accommodation"] for day in candidate.get("days", [])
                    if hotel.name in (day.get("accommodation") or "") and "," in day["accommodation"]), None)
                if alternative:
                    record, passage = candidate, alternative
                    break
        sources = [record["id"]]
        passage = passage.removeprefix("- ").replace("**", "")
        components.append(SourcePanel(type="StayCard", source=record["id"],
                                      heading=hotel.name, text=passage))
        text = (f"Our published holiday packages include {record['title']}, which lists {passage}. "
                "Standalone room rates and availability are unconfirmed. A specialist can check your dates.")
    else:
        sources = []
        text = "I can’t confirm a property from our published itineraries. A specialist can check your request."
    components.append(Notice(reference=w["enquiry"], text="Specialist confirmation required for standalone hotel rates"))
    return text, sources


def _compose_discovery_or_clarification(action, w, ctx, rows, components):
    """Compose response text (and optional ``TravellerPicker``) for discovery, search, and clarification."""
    if action == "disambiguate_tour" and rows:
        options = " and ".join(f"{r['title']} ({r.get('duration', '')})" for r in rows)
        return f"We have multiple matching tours: {options}. Which one would you like to explore or quote?"
    if action == "discover" and rows:
        text = "Here’s a published tour for your journey. What’s your travel date and who’s coming?"
        if ctx.get("date"):
            text = "Who’s coming? Please include the ages of any children."
        elif "adults" in ctx:
            text = "What date would you like to travel?"
        components.append(Picker(tour=ctx["tour"], date=ctx.get("date"),
                                 adults=ctx.get("adults") or 2, ages=ctx.get("ages", [])))
        return text
    if ctx.get("adults") and action == "discover":
        return "I’ve noted your group. Which tour or part of Sri Lanka would you like to explore?"
    if action == "clarify_reference":
        return w.get("clarification_question") or "Could you clarify which tour or option you mean?"
    if action == "clarify_duration_choice":
        return w.get("clarification_question") or "Would you like to see shorter published tours or build a custom itinerary?"
    if w.get("empty_scoped_filter"):
        titles = ", ".join(w.get("scoped_pool_titles") or [])
        return (
            f"None of the previously shown options ({titles}) match that requirement. "
            "Would you like me to search the rest of our published catalogue or plan a custom itinerary?"
        )
    if w.get("no_matching_tours"):
        if ctx.get("discovery_questions", 0) >= 3:
            return "I couldn’t find a matching published itinerary. A specialist can help with a custom enquiry."
        search = ctx.get("search") or {}
        if search.get("trip_type") == "day tour" and search.get("departure"):
            return (
                f"I couldn’t find any published day tours departing from {search['departure'].title()}. "
                "Our published day tours currently depart from Kandy, Colombo, Galle, or Mirissa. "
                "Would you like to explore those or request a custom itinerary?"
            )
        return (
            "I couldn’t find any published tours matching those exact criteria. "
            "Which matters most for your Sri Lanka trip — the activity, duration or departure point? You can also request a custom enquiry."
        )
    if action == "clarify_plan":
        custom = ctx.get("custom") or {}
        if pending_q := (custom.get("pending_clarification") or {}).get("question"):
            return pending_q
        dests = custom.get("destinations") or []
        days_n = custom.get("days")
        dest_phrase = f" to {', '.join(dests)}" if dests else ""
        missing = []
        if not days_n:
            missing.append("1. How many days you’d like to travel (or your preferred dates)?")
        elif not custom.get("date"):
            missing.append("1. Your preferred departure date?")
        if not custom.get("adults"):
            missing.append(f"{len(missing) + 1}. How many adults and the ages of any children?")
        if not dests:
            missing.append(f"{len(missing) + 1}. Which destinations or interests appeal most (for example, Mirissa, Ella, Kandy, or wildlife safaris)?")
        if missing:
            intro = (
                f"I’d love to help plan your Sri Lanka family holiday{dest_phrase}."
                if ctx.get("traveller_type") == "family"
                else f"I’d be happy to help plan your trip{dest_phrase}."
            )
            reply = intro + " Could you share:\n" + "\n".join(missing)
            if not dests and ctx.get("traveller_type") == "family":
                reply += (
                    "\n\nWhile you decide, these published tours are popular with families: "
                    "Sigiriya & Minneriya (fortress + elephant safari), Mirissa Whale Watching (short morning boat trip), "
                    "and Cultural Triangle (multi-day heritage loop)."
                )
            return reply
        return "I’d be happy to help plan your Sri Lanka journey. Which destinations and how many days would you like?"
    if action == "general" and rows and w.get("partial_place_matches"):
        places_str = ", ".join(p.replace("-", " ").title() for p in (ctx.get("search") or {}).get("places", []))
        return (
            f"No single published tour covers all of {places_str} together, but these partial matches visit some of those stops. "
            "Which would you like to explore, or would you prefer a custom itinerary?"
        )
    if action == "general" and rows and not w.get("broad_discovery") and not ctx.get("search"):
        return "These published options match your interests. Which would you like to explore?"
    if action == "general" and ctx.get("search") and rows:
        search = ctx["search"]
        trip_type = search.get("trip_type")
        departure = search.get("departure")
        theme = search.get("theme")
        days = search.get("days")
        if trip_type == "day tour":
            if departure:
                return (
                    f"Here are our published day tours departing from {departure.title()}. "
                    "Which one would you like to explore, and what’s your travel date?"
                )
            return (
                "Here are our published day tours. Which departure location suits you best "
                "(for example, Kandy, Colombo, Galle, or Mirissa), and what date are you considering?"
            )
        if trip_type == "multi-day":
            if theme == "cultural" and days:
                return f"Here are our published multi-day cultural tours around {days} days. Which itinerary would you like to explore?"
            if days:
                return f"Here are our published multi-day tours around {days} days. Which itinerary would you like to explore?"
            return "Here are our published multi-day tours. Which itinerary would you like to explore?"
        if theme:
            return f"Here are our published {theme} tours. Would you like to explore one of these itineraries?"
        return "Here are our published tours matching your request. Which itinerary would you like to explore?"
    return "I’m Mira, your Sri Lanka travel companion. Where would you like your journey to begin?"


def _apply_custom_proposal_panels(w, ctx, action, sources, components):
    """Prepend ``JourneyPlan``, ``InteractiveMap``, and ``DateSelector`` for bespoke notebook routes."""
    used_passages = set()
    days = []
    route = ctx["proposal"]
    custom = ctx.get("custom", {})
    interests = custom.get("interests") or []
    excluded_interests = custom.get("excluded_interests") or []
    excluded_dests = {
        w["records"][d]["title"].lower()
        for d in (custom.get("excluded_destination_ids") or [])
        if d in w["records"]
    }
    for idx, k in enumerate(route):
        dest_title = w["records"][k]["title"]
        passage, src = get_grounded_day_experience(
            w["records"],
            k,
            used_passages,
            allow_departure=(idx == len(route) - 1),
            day_num=idx + 1,
            interests=interests,
            excluded_interests=excluded_interests,
        )
        used_passages.add(passage)
        days.append(DayStop(source=k, evidence=src, name=dest_title, passage=passage))
    valid, reason = validate_itinerary(
        days,
        len(route),
        custom.get("destination_ids", []),
        w["records"],
        excluded_terms=excluded_dests | set(excluded_interests),
    )
    if not valid:
        w.setdefault("warnings", []).append(f"itinerary_validation:{reason}")
    selected = min(ctx.get("selected_day", 0), len(days) - 1)
    components[:0] = [Proposal(days=days, selected=selected), RouteMap(days=days, selected=selected),
                      Departure(value=ctx.get("custom", {}).get("date"))]
    sources = list(dict.fromkeys([days[selected].source, *sources, *(d.evidence or d.source for d in days)]))[:6]
    custom = ctx.get("custom", {})
    dest_names = ", ".join(custom.get("destinations") or [days[0].name])
    reduced = w.get("reducer_result")
    segs = custom.get("segments") or []
    seg_summary = ", ".join(f"{s['days']} in {s['destination_name']}" for s in segs) if segs else ""
    if reduced and segs and any(c.startswith(("segment_", "transfer=")) for c in (reduced.changes or [])) and action != "proposal_view":
        missing = []
        if not custom.get("adults"):
            missing.append("traveller count")
        if not custom.get("date"):
            missing.append("departure date")
        suffix = f" Please share your {' and '.join(missing)} so a specialist can confirm availability and pricing." if missing else ""
        text = f"I’ve updated your holiday to {len(days)} days: {seg_summary}.{suffix}"
    elif reduced and not reduced.replan_required and reduced.changes and action != "proposal_view":
        ack_parts = []
        if custom.get("adults"):
            ack_parts.append(f"{custom['adults']} adult{'s' if custom['adults'] != 1 else ''}")
        if custom.get("date"):
            ack_parts.append(f"departure {custom['date']}")
        ack = ", ".join(ack_parts)
        if custom.get("readiness") == "ready":
            text = f"Got it — {ack}. Your provisional {len(days)}-day {dest_names} plan is ready and saved for specialist confirmation."
        else:
            missing = []
            if not custom.get("adults"):
                missing.append("how many adults and children are travelling")
            if not custom.get("date"):
                missing.append("when you would like to travel")
            q_tail = f" {' and '.join(missing).capitalize()}?" if missing else ""
            text = f"Got it — {ack}. I've kept your {len(days)}-day {dest_names} plan.{q_tail}"
    elif custom.get("readiness") == "ready":
        text = f"Your provisional {len(days)}-day itinerary for {dest_names} is ready and saved for specialist confirmation."
    else:
        missing = []
        if not custom.get("adults"):
            missing.append("traveller count")
        if not custom.get("date"):
            missing.append("departure date")
        suffix = f" Please share your {' and '.join(missing)} so a specialist can confirm availability and pricing." if missing else ""
        text = f"Here is a provisional {len(days)}-day itinerary for {dest_names} (subject to specialist confirmation).{suffix}"
    if action == "proposal_view":
        d = days[selected]
        text = (f"Day {selected + 1} takes you to {d.name}." if w["panel_action"] == "day"
                else f"I’ve updated your proposed departure to {ctx['custom']['date']}. Your route still needs specialist confirmation.")
    return text, sources


def _apply_notebook_source_panels(w, action, rows, sources, components):
    """Attach contextual notebook side panels (``ComparisonPanel``, ``StayCard``, ``ActivityCard``, ``ConfirmationPanel``, ``SourceReference``)."""
    first = sources[0]
    if action == "compare" and len(rows) > 1:
        components.insert(0, SourcePanel(type="ComparisonPanel", source=first, heading="Compare journeys",
            text=" · ".join(r["title"] + " (" + r["duration"] + ")" for r in rows)))
    if action == "discover" and rows and rows[0]["type"] == "tour":
        record = rows[0]
        for kind, pattern in [("StayCard", r"Accommodation:\*\* ([^\n]+)"), ("ActivityCard", r"Entrance tickets included:\*\* ([^\n]+)")]:
            hit = re.search(pattern, public_text(record["body"]))
            if hit and hit[1].strip().lower() not in {"none", "n/a"}:
                components.append(SourcePanel(type=kind, source=first, heading="Published stay" if kind == "StayCard" else "Included visits", text=hit[1]))
    if w.get("quote"):
        components.append(SourcePanel(type="ConfirmationPanel", source=first, heading="Quote saved", text="Your private enquiry is available to the travel team."))
    if not any(getattr(c, "type", None) == "TourCard" and getattr(c, "id", None) == first for c in components):
        components.append(SourcePanel(type="SourceReference", source=first, heading="From the travel library", text=w["records"][first]["title"]))
    for i, item in enumerate(components):
        if isinstance(item, Excerpt) and item.type == "DestinationHighlight":
            components[i] = SourcePanel(**(item.model_dump() | {"type": "DestinationCard"}))


def compose(_):
    """Node 4: Assemble the validated ``Turn`` text, source citations, and A2UI component list."""
    started = perf_counter()
    w = working.get()
    if "replay" in w:
        return {}
    trace = w.get("trace") or uuid4()
    ctx, rows, action = w["context"], w["rows"], w["action"]
    user_text = w.get("user_text", "")
    components, sources = _build_row_components(rows, action, w)

    if w.get("quote"):
        branch = "verified_quote"
        text = _compose_verified_quote(w["quote"], components)
    elif w.get("reason"):
        branch = "unavailable_quote"
        text = _compose_unavailable_quote(w, ctx, components)
    elif action == "custom":
        branch = "custom_handoff"
        text = _compose_custom_handoff(w, ctx, components)
    elif action == "draft_tour":
        branch = "draft_handoff"
        text = _compose_draft_handoff(w, components)
    elif action == "mirissa_discount":
        branch = "mirissa_discount"
        text = "Mirissa is a scenic crescent beach on the south coast, celebrated for blue-whale watching between November and April. We quote official contracted rates from our rate sheet and do not offer a 40% loyalty discount."
        sources = ["D08"]
        components.append(Excerpt(type="DestinationHighlight", source="D08", heading="Mirissa",
                                  text=public_text(w["records"]["D08"]["body"])))
    elif action == "cancel_clarify_target":
        branch = "cancel_clarify_target"
        choices = (ctx.get("pending_cancellation") or {}).get("choices") or w.get("cancel_choices") or []
        opts = "; ".join(f"{c['tour_title']} on {c['travel_date']} (ref {c['booking_reference'][:8]})" for c in choices)
        sources = ["P02"]
        text = f"You have multiple active bookings: {opts}. Which booking would you like to cancel?"
    elif action == "cancel_preview":
        from ..cancellation import evaluate_cancellation
        from ..catalog import CancellationPreview, PublicQuote

        branch = "cancel_preview"
        sources = ["P02"]
        pending = ctx.get("pending_cancellation") or {}
        if pending.get("target_type") == "booking":
            booking = next((b for b in (w.get("owned_bookings") or []) if b["quote"] == pending.get("target_id")), None)
            if booking:
                pq = PublicQuote.model_validate_json(booking["public"])
                ev = evaluate_cancellation(w["tours"].get(pq.source), pq, booking)
                components.append(
                    CancellationPreview(
                        target_type="booking",
                        target_id=booking["quote"],
                        booking_reference=booking["id"],
                        tour_title=pq.title,
                        travel_date=pq.date.isoformat(),
                        travellers=pq.adults + len(pq.ages),
                        status=booking.get("status", "confirmed"),
                        terms=ev.terms_summary,
                        paid_amount=f"USD {ev.paid_amount}",
                        refund_amount=f"USD {ev.refund_amount}",
                        refund_status="eligible" if ev.eligible else "non_refundable",
                        requires_confirmation=True,
                    )
                )
                text = (
                    f"Cancellation preview for {pq.title} on {pq.date.isoformat()} (ref {booking['id'][:8]}): "
                    f"{ev.terms_summary} {ev.consequences} Reply 'Yes, go ahead' to confirm cancellation or 'Keep my booking' to keep it."
                )
            else:
                text = "I couldn’t find that active booking. Please check your bookings or contact our team."
        else:
            dests = ", ".join((ctx.get("custom") or {}).get("destinations") or ["your itinerary"])
            components.append(
                CancellationPreview(
                    target_type="plan",
                    target_id=str(pending.get("target_id") or "current_plan"),
                    tour_title=f"Provisional itinerary ({dests})",
                    travellers=(ctx.get("custom") or {}).get("adults") or 1,
                    status="provisional_unbooked",
                    terms="No payment or confirmed booking exists for this provisional itinerary.",
                    paid_amount="USD 0",
                    refund_amount="USD 0",
                    refund_status="not_applicable",
                    requires_confirmation=True,
                )
            )
            text = f"You don’t have a confirmed booking yet—only a provisional itinerary for {dests}. Reply 'Yes, go ahead' to abandon this plan, or 'Keep it' to continue."
    elif action == "cancel_confirm":
        from ..cancellation import evaluate_cancellation
        from ..catalog import CancellationStatus, PublicQuote

        branch = "cancel_confirm"
        sources = ["P02"]
        exec_c = w.get("execute_cancellation") or {}
        if exec_c.get("target_type") == "booking":
            booking = next((b for b in (w.get("owned_bookings") or []) if b["quote"] == exec_c.get("target_id")), None)
            if booking:
                pq = PublicQuote.model_validate_json(booking["public"])
                ev = evaluate_cancellation(w["tours"].get(pq.source), pq, booking)
                status_val = "pending_staff" if ev.escalate_to_staff else "cancelled"
                ref_status = "pending" if ev.escalate_to_staff else "simulated_completed"
                summary = (
                    f"Cancellation request submitted for specialist review (ref {booking['id'][:8]})."
                    if ev.escalate_to_staff
                    else f"Simulated booking {booking['id'][:8]} ({pq.title}) has been cancelled. Simulated refund: USD {ev.refund_amount}."
                )
                components.append(
                    CancellationStatus(
                        target_id=booking["quote"],
                        booking_reference=booking["id"],
                        status=status_val,
                        refund_amount=f"USD {ev.refund_amount}",
                        refund_status=ref_status,
                        summary=summary,
                    )
                )
                text = summary
            else:
                text = "This booking has already been cancelled or is unavailable."
        else:
            components.append(
                CancellationStatus(
                    target_id=str(exec_c.get("target_id") or "current_plan"),
                    status="abandoned",
                    summary="Your provisional itinerary has been abandoned.",
                )
            )
            text = "Your provisional itinerary has been abandoned. No bookings or payments were affected."
    elif action == "cancel_decline":
        from ..catalog import CancellationStatus

        branch = "cancel_decline"
        sources = ["P02"]
        components.append(
            CancellationStatus(
                target_id="kept",
                status="kept",
                summary="Your booking and itinerary remain active and unchanged.",
            )
        )
        text = "No problem — I’ve kept your booking and itinerary active. Nothing has been cancelled."
    elif action == "refund_inquiry":
        from ..cancellation import evaluate_cancellation
        from ..catalog import PublicQuote

        branch = "refund_inquiry"
        sources = ["P02"]
        bookings = w.get("owned_bookings") or []
        if bookings:
            pq = PublicQuote.model_validate_json(bookings[0]["public"])
            ev = evaluate_cancellation(w["tours"].get(pq.source), pq, bookings[0])
            text = (
                f"Under our Cancellation policy, if you cancelled {pq.title} on {pq.date.isoformat()}: "
                f"{ev.terms_summary} {ev.consequences} Nothing has been cancelled."
            )
        else:
            text = (
                "Under our Cancellation policy: day and city tours receive a full refund up to 48 hours before start; "
                "multi-day tours receive a full refund minus USD 50 (30+ days), 50% (8–29 days), or no refund (7 days or less)."
            )
    elif action == "cancel_booking":
        branch = "cancel_booking"
        sources = ["P02"]
        text = (
            "Online booking cancellation is not available directly in chat, so your booking has not been cancelled. "
            "Under our master cancellation policy (P02), please contact our travel team with your booking or enquiry "
            "reference so a specialist can process your cancellation or refund request."
        )
    elif action == "galle_cancellation":
        branch = "galle_cancellation"
        text = "Under our master cancellation policy (P02), day and city tours require at least 48 hours notice before departure for a full refund. Cancellations made 36 hours before start fall within the 48-hour window and are non-refundable."
        sources = ["P02"]
        components.append(Excerpt(type="PolicySnippet", source="P02", heading="Day and city tours",
                                  text="Full refund if cancelled at least 48 hours before the tour start. No refund if cancelled less than 48 hours before start."))
    elif action == "tour_day_detail" and w.get("day_detail"):
        branch = "tour_day_detail"
        d = w["day_detail"]
        tour_id = w.get("named") or ctx.get("tour") or "T09"
        tour_title = w["records"].get(tour_id, {}).get("title", "tour")
        heading = f"Day {d['day']}: {d['title']}"
        detail_text = f"{d['description']}\n\n• Accommodation: {d.get('accommodation') or 'None'}\n• Meals: {d.get('meals') or 'None'}\n• Included tickets: {d.get('entrance_tickets') or 'None'}"
        components.append(Excerpt(type="ItineraryDay", source=tour_id, heading=heading, text=detail_text))
        if re.search(r"\b(?:hotel|accommodation|stay in|stay at)\b", user_text):
            text = f"On Day {d['day']} ({d['title']}) of the {tour_title}, accommodation is at: {d.get('accommodation') or 'None'}.\n\n{d['description']}\n\n• Meals: {d.get('meals') or 'None'}\n• Included tickets: {d.get('entrance_tickets') or 'None'}"
        elif re.search(r"\b(?:tickets?|included|entrance)\b", user_text):
            text = f"On Day {d['day']} ({d['title']}) of the {tour_title}, included tickets are: {d.get('entrance_tickets') or 'None'}.\n\n{d['description']}\n\n• Accommodation: {d.get('accommodation') or 'None'}\n• Meals: {d.get('meals') or 'None'}"
        else:
            text = f"Here is what happens on Day {d['day']} ({d['title']}) of the {tour_title}:\n\n{d['description']}\n\n• Accommodation: {d.get('accommodation') or 'None'}\n• Meals: {d.get('meals') or 'None'}\n• Included tickets: {d.get('entrance_tickets') or 'None'}"
        sources = [tour_id]
    elif action == "tour_inclusions" and rows:
        branch = "tour_inclusions"
        row = rows[0]
        included = public_text("\n".join(row.get("inclusions", []))).strip()
        text = included or "I can’t confirm the inclusions from the published itinerary. You can request an enquiry."
        sources = [row["id"]]
    elif action == "accommodation":
        branch = "accommodation"
        text, sources = _compose_accommodation_response(w, components)
    elif action == "tour_hotels" and rows:
        branch = "tour_hotels"
        row = rows[0]
        tour_hotels = row.get("hotels", [])
        if not tour_hotels:
            tour_hotels = list(dict.fromkeys(
                d["accommodation"] for d in row.get("days", [])
                if d.get("accommodation") and d["accommodation"].lower() != "none"
            ))
        hotels_summary = ", ".join(tour_hotels) or "Unconfirmed. You can request a specialist enquiry."
        text = f"The {row['title']} published accommodation details: {hotels_summary}."
        sources = [row["id"]]
        for h_name in tour_hotels[:3]:
            clean_name = re.sub(r"\s*\([^)]*\)", "", h_name).strip()
            components.append(SourcePanel(
                type="StayCard",
                source=row["id"],
                heading=clean_name,
                text=f"Selected partner property for {row['title']}."
            ))
    elif action == "tour_itinerary" and rows:
        branch = "tour_itinerary"
        row = rows[0]
        tour_days = row.get("days", [])
        if tour_days:
            text = f"Here is the complete {len(tour_days)}-day itinerary for {row['title']}. Each day's route, accommodation, and inclusions are shown below."
        else:
            text = (
                f"Here are the published route and highlights for {row['title']} ({row.get('duration', '')}). "
                "A day-by-day breakdown is not published for this package, so a specialist can share the full schedule."
            )
        sources = [row["id"]]
    elif action == "product_qa" and rows:
        branch = "product_qa"
        row = rows[0]
        sources = [row["id"]]
        facts = set(w.get("requested_facts") or [])
        dests = [d.replace("-", " ").title() for d in row.get("destinations", [])]
        body_l = public_text(row.get("body", "")).lower()
        # Check if a specific destination is asked about
        asked_dest = next(
            (r["title"] for r in w["records"].values() if r.get("type") == "destination" and r["title"].lower() in user_text),
            None,
        )
        if asked_dest:
            included = asked_dest.lower().replace(" ", "-") in row.get("destinations", []) or asked_dest.lower() in body_l
            if included:
                text = f"Yes — {row['title']} includes {asked_dest}. Its published route covers {', '.join(dests)}."
            else:
                text = f"No — {row['title']} does not include {asked_dest}. Its published route covers {', '.join(dests)}."
        elif "duration" in facts:
            text = f"{row['title']} is {row.get('duration', 'duration not specified')}."
        elif "departure" in facts:
            text = f"{row['title']} departs from {row.get('start') or 'a location confirmed on enquiry'}."
        elif "accommodation" in facts:
            hotels = row.get("hotels") or list(dict.fromkeys(
                d["accommodation"] for d in row.get("days", [])
                if d.get("accommodation") and d["accommodation"].lower() != "none"
            ))
            if hotels:
                text = f"Accommodation in {row['title']} includes: {', '.join(hotels)}."
            else:
                text = f"{row['title']} ({row.get('duration', '')}) does not list overnight hotel accommodation in its published summary."
        elif "meals" in facts:
            meals = [d["meals"] for d in row.get("days", []) if d.get("meals") and d["meals"].lower() != "none"]
            inclusions = "\n".join(row.get("inclusions", []))
            if meals:
                text = f"Meals listed in {row['title']}: {', '.join(dict.fromkeys(meals))}."
            elif "breakfast" in inclusions.lower() or "meal" in inclusions.lower():
                text = f"Inclusions for {row['title']}: {public_text(inclusions)[:300]}"
            else:
                text = f"Meals are not specified in the published summary for {row['title']}."
        elif "wildlife" in facts:
            wildlife_hits = [k for k in ("elephant", "leopard", "whale", "dolphin", "safari", "minneriya", "yala", "udawalawe") if k in body_l or k in " ".join(row.get("destinations", []))]
            if wildlife_hits:
                text = f"Yes — {row['title']} includes wildlife/safari experiences ({', '.join(wildlife_hits)})."
            else:
                text = f"{row['title']} does not list wildlife safaris or elephant sightings in its published itinerary."
        elif "train" in facts:
            if "train" in body_l or "railway" in body_l:
                text = f"Yes — {row['title']} includes a scenic train journey."
            else:
                text = f"No — {row['title']} does not include a train journey in its published itinerary."
        else:
            text = f"{row['title']} ({row.get('duration', '')}) covers {', '.join(dests)}."
    elif action == "reject":
        branch = "reject"
        text = "I can help with a standard quote using our published tours and current rates. Which tour are you considering?"
    elif action == "off_topic":
        branch = "off_topic"
        text = "I’m Mira, your Sri Lanka travel companion. I can help you explore tours or plan a trip."
    elif action == "unknown":
        branch = "unknown"
        text = "I can’t confirm that from our published travel information. You can ask me to create a custom enquiry."
    elif action == "compare" and rows:
        branch = "compare"
        text = "Here are the published routes from your last results. Compare the duration, starting point and destinations, then choose a tour to plan."
    elif action == "destination" and len(ctx.get("suggestions", [])) > 1:
        branch = "destination_multi"
        text = f"I found {len(ctx['suggestions'])} published journeys that visit {w['records'][w['named']]['title']}. Would you like to compare their routes or explore one itinerary?"
    elif action == "children" and sources:
        branch = "children_policy"
        if re.search(r"\b(?:t07|kandy heritage|stay free|kids under 12)\b", user_text) or w.get("named") == "T07":
            text = "Our current master child policy (P03) supersedes any older promotional mentions. Children aged 2 to 11 pay applicable child costs (half-price meals, entrance tickets, and extra bed fees in hotel stays), while infants under 2 travel free."
        else:
            text = "Here’s what our published travel information says."
    elif action in {"cancellation", "dietary", "payment", "polonnaruwa", "destination"} and sources:
        branch = "policy_or_destination"
        text = "Here’s what our published travel information says."
    elif action == "invalid_party":
        branch = "invalid_party"
        text = "Please enter a valid adult count and give each child’s age."
    elif action == "invalid_date":
        branch = "invalid_date"
        text = "Please enter a valid travel date with the year included."
    else:
        branch = f"discovery:{action}"
        text = _compose_discovery_or_clarification(action, w, ctx, rows, components)

    if w.get("trip_id") and action in {"custom", "proposal_view"} and ctx.get("proposal"):
        branch = "custom_proposal_panels"
        text, sources = _apply_custom_proposal_panels(w, ctx, action, sources, components)
    if action == "sourced_answer":
        branch = "sourced_answer"
        source, passage = w["evidence"]
        sources = [source]
        components = [Excerpt(type="PolicySnippet", source=source, heading=w["records"][source]["title"], text=passage)]
        text = "Here is the passage from our published travel library that answers your question."
    if w.get("trip_id") and sources:
        _apply_notebook_source_panels(w, action, rows, sources, components)
    if any(e["stage"].startswith("gemini") and e.get("outcome") in {"fallback", "unavailable", "unconfigured"} for e in w["events"]):
        text += " Limited service: I’m using the published catalogue."
    sources = list(dict.fromkeys(sources))[:6]
    if "optional_panels" in w:
        optional = {"InteractiveMap", "DateSelector", "ComparisonPanel", "ActivityCard", "StayCard"}
        components = [item for item in components if item.type not in optional or item.type in w["optional_panels"]]
    components = components[:12]
    w["turn"] = Turn(trace=trace, text=text, sources=sources, components=components)
    duration = elapsed(started)
    component_types = [c.type for c in components]
    w["events"].append({"stage": "validated_ui", "components": component_types, "ms": duration})
    event(
        "AGENT",
        "compose.completed",
        branch=branch,
        sources=sources,
        component_types=component_types,
        generated_text=truncate(text, 300),
        duration_ms=duration,
    )
    event("RAG", "grounding.completed", sources=sources, documents=len(sources))
    event("AGENT", "ui.validated", components=len(components), duration_ms=duration)
    return {}
