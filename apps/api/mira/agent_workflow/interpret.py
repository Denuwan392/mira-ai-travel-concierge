"""Intent interpretation node and focused internal helpers for Mira's LangGraph workflow."""
import json
import re
from datetime import date
from time import perf_counter

from langchain_core.messages import HumanMessage

from ..accommodation import is_accommodation_query
from ..discovery import experience_mentioned, off_topic, requested_places, traveller_message
from ..data import as_of, public_text
from ..observability import elapsed, event
from ..provider import interpret_turn, notebook_intent
from ..search import extract_search_constraints, filter_tours
from ..store import published_records
from .constants import ALIASES, COUNT
from .facade import facade_attr
from .parsing import count, parse_date
from .replay import load_context_and_replay, validate_replay_turn
from .state import run_context, visitor_context, working


def _handle_structured_action(message, text, basis, records, tours):
    """Parse structured UI JSON payloads (``REQUEST_QUOTE``, ``SELECT_TOUR``, etc.).

    Returns:
        Tuple of ``(early_return, message, text)``. When ``early_return`` is
        True, ``working`` has already been populated and ``interpret()`` should
        return immediately.
    """
    structured_action = None
    if isinstance(message, str) and message.strip().startswith("{") and message.strip().endswith("}"):
        try:
            structured_action = json.loads(message.strip())
        except Exception:
            structured_action = None

    if structured_action and isinstance(structured_action, dict):
        act_type = structured_action.get("type")
        act_payload = structured_action.get("payload", {})
        if act_type in ("REQUEST_QUOTE", "PRICE_TOUR"):
            raw_tid = act_payload.get("tourId") or act_payload.get("tour")
            tour_id = next((key for key, row in tours.items() if raw_tid in (key, row.get("slug"))), None)
            travel_date = date.fromisoformat(act_payload.get("date") or act_payload.get("travelDate"))
            adults = act_payload.get("adults")
            ages = act_payload.get("childAges", act_payload.get("ages", []))
            if (not tour_id or type(adults) is not int or not 1 <= adults <= 100
                    or not isinstance(ages, list) or len(ages) > 30
                    or any(type(age) is not int or not 0 <= age <= 120 for age in ages)):
                raise ValueError("Invalid tour quotation configuration")
            ctx = {"tour": tour_id, "date": travel_date.isoformat(), "adults": adults, "kids": len(ages), "ages": ages}
            working.get().update(context=ctx, basis=basis, records=records, tours=tours,
                                 action="discover", named=tour_id, select=False, panel_action=None,
                                 explicit_quote=True, prompt=f"Check rates for {tours[tour_id]['title']} on {travel_date}",
                                 events=[{"stage": "interpret", "provider": "local rules", "action": "discover"}])
            party = "family" if ctx.get("kids") else "adult_party" if ctx.get("adults") else "unspecified"
            event(
                "AGENT",
                "intent.classified",
                intent="discover",
                named_tour=tour_id,
                party_type=party,
                matched_rules=[f"structured:{act_type}"],
                entities=ctx,
                preferences={},
                previous_context=json.loads(basis),
                updated_context=ctx,
                duration_ms=0,
            )
            return True, message, text
        elif act_type in ("SELECT_TOUR", "VIEW_TOUR"):
            raw_tid = str(act_payload.get("tourId") or act_payload.get("tour") or "").strip()
            tour_id = next((k for k, v in tours.items() if k == raw_tid or v.get("slug") == raw_tid), raw_tid)
            message = f"@tour {tour_id}"
            text = message.lower()
            tour_title = tours.get(tour_id, {}).get("title", tour_id)
            working.get()["prompt"] = f"Tell me about {tour_title}"
            working.get().setdefault("matched_rules", []).append(f"structured:{act_type}")
        elif act_type == "CONFIRM_CANCELLATION":
            ctx = json.loads(basis)
            target = act_payload.get("targetId") or (ctx.get("pending_cancellation") or {}).get("target_id")
            if target:
                ctx["pending_cancellation"] = {**(ctx.get("pending_cancellation") or {"target_type": "booking"}), "target_id": str(target)}
                working.get()["execute_cancellation"] = dict(ctx["pending_cancellation"])
                ctx.pop("pending_cancellation", None)
                working.get().update(
                    context=ctx, basis=basis, records=records, tours=tours,
                    action="cancel_confirm", named=None, select=False, panel_action=None,
                    events=[{"stage": "interpret", "provider": "local rules", "action": "cancel_confirm"}],
                )
                return True, message, text
        elif act_type == "DECLINE_CANCELLATION":
            ctx = json.loads(basis)
            ctx.pop("pending_cancellation", None)
            working.get().update(
                context=ctx, basis=basis, records=records, tours=tours,
                action="cancel_decline", named=None, select=False, panel_action=None,
                events=[{"stage": "interpret", "provider": "local rules", "action": "cancel_decline"}],
            )
            return True, message, text
    return False, message, text


def _disambiguate_similar_tours(text, tours, named, has_explicit_id):
    """Return matching tour IDs when a natural-language title is ambiguous across multiple published tours."""
    if has_explicit_id or not named or named not in tours:
        return []
    title_l = tours[named]["title"].lower().replace("–", "-")
    stem = re.sub(r"\s+(?:tour|package|stay|trip|holiday|day tour|walking tour)$", "", title_l).strip()
    if len(stem) < 6:
        return []
    # Only disambiguate if the user didn't supply a longer, more specific tour's full title
    # and multiple published tours share this stem.
    siblings = [
        k for k, row in sorted(tours.items())
        if stem in row["title"].lower().replace("–", "-")
    ]
    if len(siblings) <= 1:
        return []
    # If the matched tour's full title is strictly longer than `<stem> tour` (e.g. "Cultural Triangle Sri Lanka Package"),
    # it unambiguously identifies that specific tour.
    if title_l != stem and title_l != f"{stem} tour" and title_l in text.replace("–", "-"):
        return []
    # Exact title-only browsing (e.g. "Cultural Triangle Tour") without a quote/party/date request
    # selects the exact titled tour; quote requests on an ambiguous stem trigger disambiguation.
    is_quote_like = bool(re.search(r"\b(?:quote|price|cost|rate|how much|adults?|kids?|child|children|202\d-\d{2}-\d{2})\b", text))
    if not is_quote_like and text.strip().replace("–", "-") == title_l:
        return []
    # Check if duration in text narrows to a single sibling
    if day_m := re.search(rf"\b({COUNT})[- ]days?\b", text):
        d_req = count(day_m[1])
        by_day = [k for k in siblings if re.search(rf"\b{d_req}\s*days?\b", tours[k].get("duration", "").lower())]
        if len(by_day) == 1:
            return []
    if night_m := re.search(rf"\b({COUNT})[- ]nights?\b", text):
        n_req = count(night_m[1])
        by_night = [k for k in siblings if re.search(rf"\b{n_req}\s*nights?\b", tours[k].get("duration", "").lower())]
        if len(by_night) == 1:
            return []
    return siblings


def _classify_intent(text, ctx, tours):
    """Classify the primary intent ``action`` and optional ``named`` tour ID in strict priority order."""
    named = next((key for key, row in sorted(tours.items(), key=lambda pair: -len(pair[1]["title"]))
                  if row["title"].lower().replace("–", "-") in text.replace("–", "-")), None)
    action = "discover"
    if off_topic(text):
        return "off_topic", None
    if re.search(r"\bnorthern sri lanka\b", text) and re.search(r"\b(?:book|reserve|buy)\b", text):
        action = "draft_tour"
    elif re.search(r"\bmirissa\b", text) and re.search(r"discount|loyalty|40%", text):
        action = "mirissa_discount"
    elif re.search(r"galle fort", text) and re.search(r"cancel|cancellation", text) and re.search(r"36\s*hours?", text):
        action = "galle_cancellation"
    elif re.search(r"ignore .*instructions|profit margin|reveal .*cost|publish .*without|invent .*price|\d+% off", text):
        action = "reject"
    elif (named or ctx.get("tour")) and (day_match := re.search(r"\b(?:what (?:happens|do we do)|show me|tell me about)?\s*(?:on )?day\s+([1-9]\d?)\b", text)):
        active_t = named or ctx.get("tour")
        if active_t in tours and tours[active_t].get("days"):
            target_d = int(day_match.group(1))
            matching_d = next((d for d in tours[active_t]["days"] if d["day"] == target_d), None)
            if matching_d:
                action = "tour_day_detail"
                working.get()["day_detail"] = matching_d
                named = active_t
    elif (named or ctx.get("tour")) and re.search(r"\b(?:full|complete|entire|whole)\b.*?\b(?:itinerary|package|tour|schedule|days|plan)\b|\ball\s+days\b|\bday[- ]by[- ]day\b|\bcomplete\s+itinerary\b", text):
        active_t = named or ctx.get("tour")
        if active_t in tours and tours[active_t].get("days"):
            action = "tour_itinerary"
            named = active_t
    elif (named or ctx.get("tour")) and re.search(r"\b(?:are (?:entrance )?tickets included|entrance tickets included|what(?:'s| is) included|tour inclusions?)\b", text):
        active_t = named or ctx.get("tour")
        if active_t in tours:
            action = "tour_inclusions"
            named = active_t
    elif (is_accom := is_accommodation_query(text))[0]:
        _, dest_match, hotel_match, is_rate, is_alt = is_accom
        if (named or ctx.get("tour")) and not dest_match and re.search(r"\b(?:this tour|this package|which hotels?|what hotels?|included hotels?|hotels? in (?:it|this)|tour hotels?)\b", text):
            action = "tour_hotels"
            named = named or ctx.get("tour")
        else:
            action = "accommodation"
            working.get()["hotel_match"] = hotel_match
            working.get()["dest_match"] = dest_match
            working.get()["is_rate_query"] = is_rate
            working.get()["is_alt_query"] = is_alt
            if hotel_match:
                working.get()["hotel_source"] = hotel_match.source_tour_id
                working.get()["named"] = hotel_match.source_tour_id
    elif re.fullmatch(r"(?:please )?compare (?:them|these|those|my options|the routes|these tours|these journeys|these options)[.!?]?", text) and ctx.get("suggestions"):
        action = "compare"
    elif ctx.get("suggestions") and re.search(r"\b(?:which\s+(?:of\s+)?(?:those|these|them)|do\s+any\s+of\s+(?:those|these|them)|any\s+of\s+(?:those|these))\b", text):
        working.get()["suggestion_pool"] = list(ctx["suggestions"])
        working.get()["explicit_search"] = True
        action = "general"
    elif (ctx.get("suggestions") or ctx.get("last_suggestions")) and (ord_m := re.search(r"\b(?:the\s+)?(first|1st|second|2nd|third|3rd|last)(?:\s+(?:one|tour|option|package|itinerary|course))?\b", text)):
        idx_map = {"first": 0, "1st": 0, "second": 1, "2nd": 1, "third": 2, "3rd": 2, "last": -1}
        idx = idx_map[ord_m.group(1)]
        sugg = ctx.get("suggestions") or []
        if not (-len(sugg) <= idx < len(sugg)):
            sugg = ctx.get("last_suggestions") or sugg
        if -len(sugg) <= idx < len(sugg) and sugg[idx] in tours:
            named = sugg[idx]
            ctx["tour"] = named
            if re.search(r"\b(?:itinerary|days?|schedule|details?|plan|route)\b", text):
                action = "tour_itinerary"
            else:
                action = "discover"
    elif re.search(r"python script|sort a list|write .*code", text):
        action = "off_topic"
    elif re.search(r"\b(?:custom|airport transfer|adam.s peak)\b|design .*journey|across kandy|(?:stay at|change pickup|with extra|different hotel)|sigiriya.*from (?!kandy)", text):
        action = "custom"
    elif re.search(r"vegetarian|vegan|halal|dietary", text):
        action = "dietary"
    elif re.search(r"\b(?:deposit|payment) policy\b|when .*balance", text):
        action = "payment"
    elif ctx.get("pending_cancellation") and re.search(r"\b(?:yes|go ahead|confirm|proceed|cancel it)\b", text) and not re.search(r"\b(?:don'?t|not|policy|refund)\b", text):
        action = "cancel_confirm"
    elif ctx.get("pending_cancellation") and re.search(r"\b(?:don'?t cancel|keep|never mind|not yet|do not cancel)\b", text):
        action = "cancel_decline"
    elif re.search(r"\b(?:how much.*back|money back|what would happen if i cancel(?:led)?|refund eligib)\b", text):
        action = "refund_inquiry"
    elif re.search(r"\brefund\s+policy\b", text):
        action = "cancellation"
    elif re.search(r"\b(?:cancel|cancellation|withdraw|forget this itinerary|changed my mind|can'?t make it)\b", text):
        if re.search(r"\b(?:policy|terms|hours?|refund policy)\b", text) and not re.search(r"\b(?:i want to cancel|cancel this|cancel my|cancel the|withdraw|forget this|changed my mind|can'?t make it)\b", text):
            action = "cancellation"
        else:
            action = "cancel_request"
    elif re.search(r"kids.*free|children.*free", text):
        action = "children"
    elif re.search(r"is yala open|jaffna", text):
        action = "unknown"
    elif "polonnaruwa" in text and not named:
        action = "polonnaruwa"
    return action, named


def _populate_custom_context(message, text, records, ctx):
    """Extract custom itinerary destinations, duration, party count, and date into ``ctx['custom']``."""
    custom = {"request": message.strip(), "destinations": [row["title"] for row in records.values() if row["type"] == "destination"
                              and re.search(r"\b" + re.escape(row["title"].split()[0].lower()) + r"\b", text)]}
    if requested := re.search(rf"\b({COUNT})[- ]days?\b", text):
        custom["days"] = count(requested[1])
    if party := re.search(rf"\b({COUNT})\s+adults?\b|\bfamily of ({COUNT})\b", text):
        custom["party"] = count(party[1] or party[2])
    try:
        departure = parse_date(text)
    except ValueError:
        departure = None
    if departure:
        custom["date"] = departure
    ctx["custom"] = custom


def _extract_date_and_travellers(text, ctx, match, action):
    """Extract departure date, adult count, child count, ages, and infants into ``ctx``.

    Returns:
        Tuple of ``(action, departure)``.
    """
    departure = None
    try:
        departure = parse_date(text)
    except ValueError:
        departure = None
        ctx.pop("date", None)
        action = "invalid_date"
    if not departure and re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", text):
        ctx.pop("date", None)
        action = "invalid_date"
    if not departure and re.search(r"\b(?:change the date|starting|departing|instead on|new date|next (?:week|month|summer))\b", text):
        ctx.pop("date", None)
    if departure:
        ctx["date"] = departure
    elif ctx.get("date"):
        try:
            if date.fromisoformat(ctx["date"]) < as_of():
                ctx.pop("date", None)
        except ValueError:
            ctx.pop("date", None)
    if party := re.search(rf"\b({COUNT})\s+adults?\b", text):
        ctx["adults"] = count(party[1])
    elif re.search(r"\b(?:a\s+)?couple\b", text):
        ctx["adults"] = 2
    elif re.search(r"\bsolo\b|just me", text):
        ctx["adults"] = 1
    if kids := re.search(rf"\b({COUNT})\s+(?:kid|kids|child|children)\b", text):
        ctx["kids"] = count(kids[1])
        ctx.pop("ages", None)
    if ages := re.search(r"\b(?:aged|ages?)\s+(?:is\s+|are\s+)?(\d{1,3}(?:\s*(?:,\s*and\s+|,\s*|\band\s+)\d{1,3})*)", text):
        ctx["ages"] = [int(x) for x in re.findall(r"\d+", ages[1])][:30]
        if ctx.get("kids", -1) < 0:
            ctx["kids"] = len(ctx["ages"])
    if baby := re.search(rf"\b({COUNT})[- ]year[- ]old", text):
        ctx["ages"] = [count(baby[1])]
        ctx.setdefault("kids", 1)
    if infant_match := re.search(rf"\b({COUNT}|an?)\s+infants?\b", text):
        infant_token = infant_match[1]
        infant_cnt = 1 if infant_token in {"a", "an"} else count(infant_token)
        if not kids and not ages and not baby:
            ctx["ages"] = [0] * min(30, infant_cnt)
            ctx["kids"] = len(ctx["ages"])
        elif ages or baby:
            existing_ages = list(ctx.get("ages", []))
            ctx["ages"] = (existing_ages + [0] * infant_cnt)[:30]
            if kids:
                ctx["kids"] = count(kids[1]) + infant_cnt
            else:
                ctx["kids"] = len(ctx["ages"])
        else:
            # Child count was given without child ages; keep kids > len(ages) so Mira asks for child age
            ctx["kids"] = count(kids[1]) + infant_cnt
    if re.search(r"\b(?:other child|and another|or another)\b", text):
        action = "invalid_party"
    if re.search(r"\b(?:child|children|kids?|baby|infant|family)\b", text) and "kids" not in ctx:
        ctx["kids"] = -1
    if re.search(r"\b(?:only adults|no children|without children)\b", text):
        ctx.update(kids=0, ages=[])
    if match:
        ages = [] if match[4] == "-" else [int(x) for x in match[4].split(",")][:31]
        ctx.update(adults=int(match[3]), kids=len(ages), ages=ages)
    return action, departure


def _resolve_tour_and_search(text, ctx, records, tours, action, named, select, departure):
    """Resolve implied tour from quote/search constraints or route to destination/general/custom."""
    is_tour_ref = bool(ctx.get("tour") in tours and re.search(r"\b(?:this|that|the)\s+(?:day\s+)?(?:tour|trip|package)\b", text))
    if action == "discover" and not named and not select and not is_tour_ref and (
        (departure and "adults" in ctx) or re.search(r"\b(?:quote|price|how much|rate|cost)\b", text)
    ):
        quote_sc = extract_search_constraints(text)
        pool = filter_tours(tours, quote_sc) if quote_sc else {}
        if len(pool) == 1:
            named = next(iter(pool))
            ctx["tour"] = named
        else:
            search_pool = pool or tours
            title_hits = [
                k for k, r in search_pool.items()
                if re.search(r"\b" + re.escape(r["title"].lower().split()[0].rstrip("&")) + r"\b", text)
            ]
            if len(title_hits) == 1:
                named = title_hits[0]
                ctx["tour"] = named
            elif len(title_hits) > 1:
                day_hits = [k for k in title_hits if "night" not in tours[k]["duration"].lower()]
                if len(day_hits) == 1:
                    named = day_hits[0]
                    ctx["tour"] = named
    search_constraints = (
        extract_search_constraints(text)
        if (action == "discover" and not named and not select and not is_tour_ref)
        else {}
    )
    in_active_custom_plan = bool((ctx.get("custom") or {}).get("goal") == "plan_itinerary" or ctx.get("proposal"))
    is_explicit_tour_search = bool(re.search(r"\b(?:find|search|show|recommend|existing|published)\b.*\b(?:tours?|packages?|excursions?|trips?|courses?|options?)\b", text))
    is_explicit_plan = bool(re.search(r"\b(?:plan|planning|design|organize|arrange|build|create|custom|customise|customize|tailor|bespoke)\b", text))
    is_planning_phrase = bool(re.search(r"\b(?:plan|planning|design|organize|arrange|build|create|update|make|add|remove|reduce|shorten|extend)\b", text))
    is_discovery_query = bool(
        re.search(r"\b(?:what|which|any|do you have|show me|find|list|recommend|are there|looking for|include|includes|including|cover|covering|visit|visiting)\b", text)
        and re.search(r"\b(?:tours?|packages?|trips?|itinerar(?:y|ies)|courses?|routes?|options?|holidays?|excursions?|both)\b", text)
    )
    places = requested_places(text, records) if (action == "discover" and not named and not select and not is_tour_ref) else []
    if (
        action == "discover"
        and not named
        and not select
        and not is_tour_ref
        and not in_active_custom_plan
        and not is_explicit_plan
        and (len(places) >= 2 or (places and is_discovery_query))
    ):
        ctx.pop("tour", None)
        ctx.pop("proposal", None)
        ctx.pop("custom", None)
        merged_search = dict(search_constraints)
        if places:
            merged_search["places"] = places
        ctx["search"] = merged_search
        if "trip_type" in merged_search:
            ctx["trip_type"] = merged_search["trip_type"]
        ctx["preferences"] = text[:400]
        working.get()["explicit_search"] = True
        action = "general"
    elif search_constraints and re.search(r"\b(?:tour|trip|package|holiday|stay|day|week|beach|cultur|multi)\b", text) and not (
        (in_active_custom_plan and not is_explicit_tour_search)
        or (is_planning_phrase and (working.get().get("trip_id") or places or re.search(r"\b(?:covering|visiting|across|to)\b", text)))
    ):
        # Explicit published-tour search/filter overrides stale selections and proposals
        ctx.pop("tour", None)
        ctx.pop("proposal", None)
        ctx.pop("custom", None)
        ctx["search"] = search_constraints
        if "trip_type" in search_constraints:
            ctx["trip_type"] = search_constraints["trip_type"]
        ctx["preferences"] = text[:400]
        working.get()["explicit_search"] = True
        filtered_pool = filter_tours(tours, search_constraints)
        if len(filtered_pool) == 1 and (departure or re.search(r"\b(?:adults?|quote|price)\b", text)) and not search_constraints.get("theme"):
            ctx["tour"] = next(iter(filtered_pool))
            named = ctx["tour"]
        else:
            action = "general"
    elif action == "discover" and not named and not (departure or re.search(r"\b(?:adults?|kids?|child|children|ages?|solo|quote|price|book)\b", text)):
        ctx.pop("search", None)
        text_words = set(re.findall(r"[a-z]+", text))
        ctx_tour = next((k for k, row in records.items() if row["type"] == "destination"
                         and row["title"].lower().split()[0] in text_words), None)
        if ctx_tour:
            action, named = "destination", ctx_tour
        elif text and not select:
            action = "general"
            ctx["preferences"] = text[:400]
    if action == "discover" and not named and re.search(r"price|how much|quote", text):
        unknown_named = bool(re.search(
            r"\b(?:how much is|price (?:of|for)|quote for)\s+(?:the\s+|a\s+)?(?!(?:this|that|the)\s+(?:tour|trip|quote|package)\b)[a-z]+\s+(?:tour|trip|expedition|package|safari)\b",
            text,
        ))
        has_tour = ctx.get("tour") in tours and not unknown_named
        if unknown_named:
            ctx.pop("tour", None)
        if not has_tour:
            action = "custom"
    return action, named


def _classify_traveller_and_trip_type(text, ctx, tours, action):
    """Populate ``ctx['traveller_type']`` and ``ctx['trip_type']`` from text and active context."""
    if re.search(r"\bfamily\b", text) or ctx.get("kids", 0) > 0:
        ctx["traveller_type"] = "family"
    elif re.search(r"\bgroup\b", text) or ctx.get("adults", 0) > 2:
        ctx["traveller_type"] = "group"
    elif re.search(r"\bcouple\b", text) or ctx.get("adults") == 2:
        ctx["traveller_type"] = "couple" if "couple" in text else "two adults"
    elif ctx.get("adults") == 1:
        ctx["traveller_type"] = "solo"
    if action == "custom":
        ctx["trip_type"] = "custom"
    elif ctx.get("tour") in tours:
        ctx["trip_type"] = "multi-day" if "night" in tours[ctx["tour"]]["duration"].lower() else "day tour"
    elif "trip_type" in (ctx.get("search") or {}):
        ctx["trip_type"] = ctx["search"]["trip_type"]
    elif re.search(r"\bday (trip|tour)\b", text):
        ctx["trip_type"] = "day tour"
    elif re.search(r"(?<!not a )(?<!no )\bmulti[- ]?day\b", text):
        ctx["trip_type"] = "multi-day"


def _handle_notebook_panel_action(text, ctx):
    """Process ``@day`` and ``@depart`` interactive notebook commands."""
    panel_action = "invalid"
    if ctx.get("proposal"):
        if chosen := re.fullmatch(r"@day (\d{1,2})", text):
            day = int(chosen[1]) - 1
            if 0 <= day < len(ctx["proposal"]):
                ctx["selected_day"] = day
                panel_action = "day"
        elif depart := re.fullmatch(r"@depart (\d{4}-\d{2}-\d{2})", text):
            try:
                departure = date.fromisoformat(depart[1])
                if departure < as_of():
                    raise ValueError("past departure")
                ctx.setdefault("custom", {})["date"] = departure.isoformat()
                panel_action = "date"
            except ValueError:
                pass
    action = "proposal_view" if panel_action != "invalid" else "unknown"
    return action, panel_action


def _handle_notebook_planning(message, text, records, tours, ctx, action, named, active_tour_quote_turn, departure, events):
    """Run RAG evidence lookup, optional ``notebook_intent``, and typed state-machine route planning."""
    from ..planner import build_grounded_route
    from .state_machine import TripState, hybrid_extract_operations, reduce_state

    destinations = {k: r["title"] for k, r in records.items() if r["type"] == "destination"}
    previous = ctx.get("proposal", [])
    prev_state = TripState.from_ctx(ctx, records)

    evidence = {}
    if re.search(r"\?|\b(?:what|where|tell me|when|why|can i)\b", text) and not re.search(r"quote|price|cost|deposit|payment", text):
        words = set(re.findall(r"[a-z]{3,}", text)) - {"what", "where", "tell", "when", "about", "the", "can"}
        candidates = []
        for key, row in records.items():
            if key == "P06":
                continue
            for i, block in enumerate(public_text(row["body"]).split("\n\n")):
                block = block.strip()
                hits = len(words & set(re.findall(r"[a-z]{3,}", (row["title"] + " " + block).lower())))
                if hits and block and not block.startswith("#"):
                    candidates.append((hits, f"{key}:{i}", block[:800]))
        evidence = {k: v for _, k, v in sorted(candidates, reverse=True)[:14]}
    intent_fn = facade_attr("notebook_intent", notebook_intent)
    intent = intent_fn(message, previous, destinations, events, evidence)
    if intent and intent.panels is not None:
        working.get()["optional_panels"] = intent.panels
    if intent and intent.operation == "fact" and intent.evidence_key in evidence:
        k = intent.evidence_key
        working.get()["evidence"] = (k.split(":")[0], evidence[k])
        return "sourced_answer"
    elif intent and intent.operation == "unknown" and evidence:
        return "unknown"

    ops, clarification_q = hybrid_extract_operations(
        message, prev_state, destinations, events, interpret_fn=facade_attr("interpret_turn", interpret_turn)
    )
    reduced = reduce_state(prev_state, ops, destinations)
    working.get()["reducer_result"] = reduced
    if clarification_q or reduced.clarification_needed:
        q_text = clarification_q or reduced.clarification_needed
        reduced.state.pending_clarification = {"question": q_text}
        reduced.state.active_goal = "custom_planning"
        reduced.state.sync_to_ctx(ctx, destinations)
        return "clarify_plan"
    if reduced.validation_errors:
        prev_state.pending_clarification = {"question": "; ".join(reduced.validation_errors)}
        prev_state.sync_to_ctx(ctx, destinations)
        return "clarify_plan"

    new_state = reduced.state
    new_state.pending_clarification = None
    if not new_state.requested_destinations and intent and intent.destinations:
        new_state.requested_destinations = [d for d in intent.destinations if d in destinations]
    if not new_state.requested_destinations:
        theme_ids = [key for pattern, key in [("train|nature", "D05"), ("beach|coast|southern", "D08"), ("culture", "D03")] if re.search(pattern, text) and key in destinations]
        if theme_ids:
            new_state.requested_destinations = theme_ids
    if not new_state.duration_days and intent and intent.days:
        new_state.duration_days = intent.days
    if new_state.adults is None and intent and intent.adults:
        new_state.adults = intent.adults

    explicit_plan_verb = bool(re.search(r"\b(?:plan|planning|design|organize|arrange|build|create|custom|customise|customize|tailor|bespoke)\b", text))
    if explicit_plan_verb or action == "custom" or prev_state.active_goal == "custom_planning":
        new_state.active_goal = "custom_planning"

    route = None
    if (
        new_state.active_goal == "custom_planning"
        and not working.get().get("explicit_search")
        and named not in tours
        and not active_tour_quote_turn
    ):
        if new_state.segments:
            route = [s.destination_id for s in new_state.segments for _ in range(s.days)]
            new_state.proposal = route
            new_state.duration_days = len(route)
            new_state.selected_day = min(new_state.selected_day, len(route) - 1)
            new_state.readiness = "ready" if (new_state.adults and new_state.departure_date) else "provisional"
            new_state.sync_to_ctx(ctx, destinations)
            return "custom"
        elif new_state.requested_destinations and new_state.duration_days:
            route = build_grounded_route(new_state.requested_destinations, new_state.duration_days)
            new_state.proposal = route
            new_state.selected_day = min(new_state.selected_day, len(route) - 1)
            new_state.readiness = "ready" if (new_state.adults and new_state.departure_date) else "provisional"
            new_state.sync_to_ctx(ctx, destinations)
            return "custom"
        else:
            new_state.proposal = []
            new_state.readiness = "clarifying"
            new_state.sync_to_ctx(ctx, destinations)
            return "clarify_plan"

    return action


def interpret(state):
    """Node 1: Load visitor/trip context, handle idempotent replays, and classify user intent.

    Parses structured UI actions (``REQUEST_QUOTE``, ``SELECT_TOUR``, ``@trip``,
    ``@tour``, ``@day``, ``@depart``) as well as natural-language queries for
    tours, policies, accommodation, party sizes, dates, and bespoke notebook
    itineraries. Populates ``working`` for downstream nodes.
    """
    message = next((m.content for m in reversed(state.get("messages", [])) if isinstance(m, HumanMessage)), "")
    text = message.strip()[:1200].lower() if isinstance(message, str) else ""
    working.get()["user_text"] = text
    visitor = visitor_context.get()
    run = run_context.get()
    # --- 1. Load visitor or trip-notebook context and check for idempotent replay ---
    saved, replay = load_context_and_replay(visitor, run)
    if replay:
        turn = validate_replay_turn(replay)
        working.get().update(replay=turn)
        return {}
    basis = saved["context"] if saved else "{}"
    prev_context = json.loads(basis)
    ctx = json.loads(basis)
    records = facade_attr("published_records", published_records)()
    tours = {key: row for key, row in records.items() if row["type"] == "tour"}

    # --- 2. Handle structured JSON action payloads from frontend widgets ---
    early_return, message, text = _handle_structured_action(message, text, basis, records, tours)
    if early_return:
        return {}

    # --- 3. Classify primary intent and extract constraints ---
    match = re.fullmatch(r"@trip ([A-Z\d-]+) (\d{4}-\d{2}-\d{2}) (\d{1,3}) (-|\d{1,3}(?:,\d{1,3})*)", message.strip()) if isinstance(message, str) else None
    select = re.fullmatch(r"@tour ([A-Z\d-]+)", message.strip()) if isinstance(message, str) else None
    started = perf_counter()
    action, named = _classify_intent(text, ctx, tours)
    matched_rules = working.get().setdefault("matched_rules", [])
    matched_rules.append(f"intent:{action}")
    if match:
        matched_rules.append("command:@trip")
    if select:
        matched_rules.append("command:@tour")

    if action == "custom":
        _populate_custom_context(message, text, records, ctx)
        matched_rules.append("extract:custom_context")
    dialogue_res = None
    dialogue_events = []
    pending_task = ctx.get("pending_task") or {}
    if not (match or select) and pending_task.get("type") == "quotation" and pending_task.get("tour_id") in tours:
        has_quote_input = bool(
            parse_date(text)
            or re.search(rf"\b({COUNT})\s+(?:adults?|kids?|child(?:ren)?)\b|\b(?:a\s+)?couple\b|\bsolo\b", text)
        )
        is_switching_intent = bool(re.search(r"\b(?:cancel|custom|plan|instead|policy|other\s+tours?|different)\b", text))
        if has_quote_input and not is_switching_intent:
            named = pending_task["tour_id"]
            ctx["tour"] = named
            ctx["focused_entity_type"] = "tour"
            ctx["focused_entity_id"] = named
            action = "discover"
            working.get()["dialogue_quote_resolved"] = True
            matched_rules.append(f"pending_task:quotation:{named}")
    if (
        not (match or select)
        and not working.get().get("dialogue_quote_resolved")
        and ctx.get("tour") in tours
        and not ctx.get("proposal")
        and (dur_only := re.fullmatch(rf"(?:make\s+it\s+|around\s+|about\s+)?({COUNT})[- ]days?[.!?]?", text))
    ):
        from ..search import tour_days
        req_days = count(dur_only.group(1))
        active_t = tours[ctx["tour"]]
        if req_days != tour_days(active_t):
            ctx["pending_task"] = {"type": "duration_choice", "requested_days": req_days, "tour_id": ctx["tour"]}
            action = "clarify_duration_choice"
            working.get()["clarification_question"] = (
                f"{active_t['title']} is a {active_t.get('duration', '')} published package and cannot be shortened to {req_days} days. "
                f"Would you like to see shorter published tours around {req_days} days, or build a custom {req_days}-day itinerary?"
            )
            matched_rules.append(f"pending_task:duration_choice:{req_days}")
    if (
        not (match or select)
        and pending_task.get("type") == "duration_choice"
        and re.search(r"\b(?:add|remove|custom|plan|build|segment|mirissa|ella|kandy|galle)\b", text)
        and not re.search(r"\b(?:published|existing|shorter\s+tours?)\b", text)
    ):
        req_d = pending_task.get("requested_days") or 5
        slug_to_id = {r["path"].rsplit("/", 1)[-1].removesuffix(".md"): k for k, r in records.items() if r["type"] == "destination"}
        places = (ctx.get("search") or {}).get("places") or (ctx.get("discovery") or {}).get("constraints", {}).get("places") or []
        init_dests = [slug_to_id[p] for p in places if p in slug_to_id]
        if not init_dests and any("hill" in p or "mountain" in p for p in ctx.get("original_preferences", [])):
            init_dests = ["D05"]
        if init_dests:
            from .state_machine import ItinerarySegment
            d0 = init_dests[0]
            ctx["custom"] = {
                "goal": "plan_itinerary",
                "days": req_d,
                "destination_ids": [d0],
                "destinations": [records[d0]["title"]],
                "segments": [
                    ItinerarySegment(
                        segment_id=f"seg_{d0}",
                        destination_id=d0,
                        destination_name=records[d0]["title"],
                        days=req_d,
                        allocation_source="inferred",
                    ).model_dump()
                ],
            }
        ctx.pop("pending_task", None)
        ctx.pop("tour", None)
        action = "custom"
        matched_rules.append("pending_task:duration_choice_to_custom")
    if not (match or select) and not working.get().get("dialogue_quote_resolved") and action in {"discover", "general", "accommodation", "destination", "custom", "unknown", "tour_itinerary"}:
        from .state_machine import TripState, resolve_dialogue_turn
        prev_dialogue_state = TripState.from_ctx(ctx, records)
        dialogue_res = resolve_dialogue_turn(
            message if isinstance(message, str) else text,
            prev_dialogue_state,
            records,
            tours,
            empty_filter_result=bool(ctx.get("empty_filter_result")),
            interpret_fn=facade_attr("interpret_turn", interpret_turn) if working.get().get("trip_id") else None,
            events=dialogue_events,
        )
        if dialogue_res.reference_resolution == "ambiguous" and dialogue_res.needs_clarification:
            action = "clarify_reference"
            working.get()["clarification_question"] = dialogue_res.clarification_question
            matched_rules.append("dialogue:clarify_reference")
        elif dialogue_res.speech_act == "filter_recommendations":
            scope_ids = list(
                ctx.get("suggestions")
                or (ctx.get("historical_suggestions") or [[]])[-1]
                or ctx.get("last_suggestions")
                or []
            )
            if scope_ids:
                working.get()["suggestion_pool"] = scope_ids
                working.get()["explicit_search"] = True
                working.get()["discovery_message"] = traveller_message(message[:1200])
                action = "general"
                matched_rules.append("dialogue:scoped_filter")
        elif dialogue_res.speech_act == "compare_products" and (ctx.get("suggestions") or ctx.get("historical_suggestions")):
            if not ctx.get("suggestions") and ctx.get("historical_suggestions"):
                ctx["suggestions"] = list(ctx["historical_suggestions"][-1])
            action = "compare"
            matched_rules.append("dialogue:compare")
        elif dialogue_res.speech_act == "explore_product" and dialogue_res.referenced_entity_type == "tour" and dialogue_res.referenced_entity_id in tours:
            named = dialogue_res.referenced_entity_id
            ctx["tour"] = named
            ctx["focused_entity_type"] = "tour"
            ctx["focused_entity_id"] = named
            action = "tour_itinerary" if dialogue_res.response_strategy == "show_itinerary" else "discover"
            matched_rules.append(f"dialogue:explore:{named}")
        elif dialogue_res.speech_act == "factual_question" and dialogue_res.referenced_entity_type == "tour" and dialogue_res.referenced_entity_id in tours:
            named = dialogue_res.referenced_entity_id
            ctx["tour"] = named
            ctx["focused_entity_type"] = "tour"
            ctx["focused_entity_id"] = named
            if "day_detail" in dialogue_res.requested_facts and tours[named].get("days"):
                ord_days = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3, "fourth": 4, "4th": 4, "fifth": 5, "5th": 5}
                target_d = None
                if dm := re.search(r"\bday\s+(\d+)\b", text):
                    target_d = int(dm.group(1))
                elif om := re.search(r"\b(first|1st|second|2nd|third|3rd|fourth|4th|fifth|5th)\s+day\b", text):
                    target_d = ord_days[om.group(1)]
                matching_d = next((d for d in tours[named]["days"] if d["day"] == target_d), None) if target_d else None
                if matching_d:
                    action = "tour_day_detail"
                    working.get()["day_detail"] = matching_d
                else:
                    action = "product_qa"
                    working.get()["requested_facts"] = dialogue_res.requested_facts
            else:
                action = "product_qa"
                working.get()["requested_facts"] = dialogue_res.requested_facts
            matched_rules.append(f"dialogue:product_qa:{named}")
        elif dialogue_res.speech_act == "factual_question" and dialogue_res.retrieval_scope == "custom_plan":
            # Read-only destination question during custom planning: do not mutate plan
            dest_hit = next((k for k, r in records.items() if r.get("type") == "destination" and r["title"].lower() in text), None)
            if dest_hit:
                action, named = "destination", dest_hit
                working.get()["readonly_custom_question"] = True
                matched_rules.append(f"dialogue:readonly_dest:{dest_hit}")
        elif dialogue_res.speech_act == "request_quote" and dialogue_res.referenced_entity_type == "tour" and dialogue_res.referenced_entity_id in tours:
            named = dialogue_res.referenced_entity_id
            ctx["tour"] = named
            ctx["focused_entity_type"] = "tour"
            ctx["focused_entity_id"] = named
            action = "discover"
            working.get()["dialogue_quote_resolved"] = True
            matched_rules.append(f"dialogue:quote:{named}")
    departure = None
    if action in {"cancel_request", "cancel_confirm", "cancel_decline", "refund_inquiry"}:
        from ..cancellation import evaluate_cancellation, find_owned_bookings
        from ..catalog import PublicQuote
        from ..store import db as _db
        uid = working.get().get("user_id")
        actor_id = uid or visitor
        with _db() as conn:
            owned_bookings = [b for b in find_owned_bookings(conn, visitor, uid) if b.get("status", "confirmed") != "cancelled"]
        working.get()["owned_bookings"] = owned_bookings
        pending = ctx.get("pending_cancellation") or {}

        def _bind_pending_booking(b_row: dict) -> dict:
            pq = PublicQuote.model_validate_json(b_row["public"])
            ev = evaluate_cancellation(tours.get(pq.source), pq, b_row)
            return {
                "target_type": "booking",
                "target_id": b_row["quote"],
                "booking_reference": b_row["id"],
                "version": b_row.get("version", 0),
                "actor_id": actor_id,
                "policy_version": ev.policy_version,
                "refund_amount": str(ev.refund_amount),
            }

        if action == "cancel_confirm" and pending:
            if pending.get("target_type") == "booking":
                matched_b = next((b for b in owned_bookings if b["quote"] == pending.get("target_id")), None)
                if matched_b:
                    rebound = _bind_pending_booking(matched_b)
                    still_valid = (
                        pending.get("actor_id") in {actor_id, visitor}
                        and pending.get("booking_reference") == rebound["booking_reference"]
                        and pending.get("version") == rebound["version"]
                        and pending.get("policy_version") == rebound["policy_version"]
                        and pending.get("refund_amount") == rebound["refund_amount"]
                    )
                    if still_valid:
                        working.get()["execute_cancellation"] = dict(pending)
                        ctx.pop("pending_cancellation", None)
                    else:
                        ctx["pending_cancellation"] = rebound
                        action = "cancel_preview"
                else:
                    ctx.pop("pending_cancellation", None)
                    action = "cancel_booking"
            else:
                working.get()["execute_cancellation"] = dict(pending)
                ctx.pop("pending_cancellation", None)
        elif action == "cancel_decline":
            ctx.pop("pending_cancellation", None)
        elif action == "cancel_request":
            # Check if user is selecting from pending choices
            if pending.get("choices"):
                chosen = next(
                    (c for c in pending["choices"] if c["booking_reference"].lower() in text or c["tour_id"].lower() in text or c["tour_title"].lower() in text),
                    None,
                )
                matched_b = next((b for b in owned_bookings if chosen and b["quote"] == chosen["quote_id"]), None)
                if matched_b:
                    ctx["pending_cancellation"] = _bind_pending_booking(matched_b)
                    action = "cancel_preview"
                else:
                    action = "cancel_clarify_target"
            elif len(owned_bookings) > 1:
                direct_matches = []
                for b in owned_bookings:
                    pq = PublicQuote.model_validate_json(b["public"])
                    t_rec = tours.get(pq.source) or {}
                    dests = [d.replace("-", " ") for d in t_rec.get("destinations", [])]
                    if (
                        b["id"].lower() in text
                        or pq.source.lower() in text
                        or pq.title.lower() in text
                        or any(re.search(r"\b" + re.escape(d) + r"\b", text) for d in dests)
                    ):
                        direct_matches.append(b)
                if len(direct_matches) == 1:
                    ctx["pending_cancellation"] = _bind_pending_booking(direct_matches[0])
                    action = "cancel_preview"
                else:
                    choices = []
                    for b in (direct_matches or owned_bookings)[:5]:
                        pq = PublicQuote.model_validate_json(b["public"])
                        choices.append({
                            "quote_id": b["quote"],
                            "booking_reference": b["id"],
                            "tour_id": pq.source,
                            "tour_title": pq.title,
                            "travel_date": pq.date.isoformat(),
                            "version": b.get("version", 0),
                        })
                    ctx["pending_cancellation"] = {"choices": choices}
                    working.get()["cancel_choices"] = choices
                    action = "cancel_clarify_target"
            elif len(owned_bookings) == 1:
                ctx["pending_cancellation"] = _bind_pending_booking(owned_bookings[0])
                action = "cancel_preview"
            elif ctx.get("proposal") or (ctx.get("custom") or {}).get("goal") == "plan_itinerary":
                ctx["pending_cancellation"] = {
                    "target_type": "plan",
                    "target_id": working.get().get("trip_id") or "current_plan",
                    "actor_id": actor_id,
                }
                action = "cancel_preview"
            else:
                action = "cancel_booking"
    if action in {"discover", "cancellation"}:
        has_explicit_id = bool(match or select or re.search(r"\bt\d{2}\b", text))
        if match or select:
            named = (match or select)[1]
            if named not in tours:
                action = "unknown"
        named = named or (
            None
            if re.search(r"\b(?:plan|planning|design|organize|arrange)\b", text)
            else next((k for k, pattern in ALIASES.items() if k in tours and re.search(pattern, text)), None)
        )
        ambiguous = (
            _disambiguate_similar_tours(text, tours, named, has_explicit_id)
            if action == "discover" and not working.get().get("dialogue_quote_resolved")
            else []
        )
        if ambiguous:
            named = None
            ctx.pop("tour", None)
            action, departure = _extract_date_and_travellers(text, ctx, match, action)
            action = "disambiguate_tour"
            working.get()["ambiguous_tours"] = ambiguous
            matched_rules.append(f"disambiguate:{','.join(ambiguous)}")
        elif named in tours:
            matched_rules.append(f"tour_match:{named}")
        if named in tours and action == "discover":
            if ctx.get("tour") and named != ctx.get("tour"):
                ctx.pop("date", None)
                # A newly named package with an explicit adult-only party is a new brief.
                new_adult_party = re.search(rf"\bfor (?:{COUNT}) adults?\b", text)
                mentions_children = re.search(r"\b(?:family|kids?|child(?:ren)?|infants?|bab(?:y|ies)|ages?|aged|year.old)\b", text)
                if new_adult_party and not mentions_children:
                    ctx.update(kids=0, ages=[])
            ctx["tour"] = named
        if action == "discover":
            action, departure = _extract_date_and_travellers(text, ctx, match, action)
            if departure:
                matched_rules.append("extract:date")
            if not working.get().get("dialogue_quote_resolved"):
                action, named = _resolve_tour_and_search(text, ctx, records, tours, action, named, select, departure)
            if ctx.get("search"):
                matched_rules.append("extract:search_constraints")
            if ctx.get("adults", 1) not in range(1, 101) or any(not 0 <= age <= 120 for age in ctx.get("ages", [])):
                action = "invalid_party"
            if action == "discover" and (ctx.get("kids", 0) > 30 or len(ctx.get("ages", [])) > 30):
                action = "custom"
    # Preserve quote, itinerary and explicit notebook operations before entering discovery.
    # Party mentions are common in discovery. Only keep the quote path when the
    # turn supplies quote fields or refers to an active package without new interests.
    experience = action in {"discover", "accommodation"} and not (match or select or departure or working.get().get("dialogue_quote_resolved")) and experience_mentioned(text, tours)
    party_update = bool(re.search(rf"\b(?:{COUNT})\s+(?:adults?|kids?|child(?:ren)?)\b|\b(?:a\s+)?couple\b|\b(?:age[ds]?|quote|price)\b", text))
    if action == "discover" and experience and not party_update and (
        not named or re.search(r"\b(?:no|avoid|without|exclude)\b", text)
    ):
        named = None
        action = "general"
    if action == "accommodation" and experience and not any(working.get().get(k) for k in
            ("hotel_match", "dest_match", "is_rate_query", "is_alt_query")):
        action = "general"
    if action == "destination" and requested_places(text, records) and not re.match(
        r"(?:what (?:is|are)|where (?:is|are)|tell me about)\b", text
    ):
        place = records[named]["title"].lower().split()[0]
        if experience_mentioned(text.replace(place, ""), tours):
            action, named = "general", None
    has_discovery_place = bool((ctx.get("discovery") or {}).get("constraints", {}).get("places") or (ctx.get("search") or {}).get("places"))
    is_followup_refinement = bool(
        has_discovery_place
        and not working.get().get("dialogue_quote_resolved")
        and (ctx.get("pending_task") or {}).get("type") != "quotation"
        and (
            re.search(rf"\b({COUNT})[- ]days?\b|\bfortnight\b|\bweek\b", text)
            or departure
            or re.search(r"\b(?:me and my|wife|husband|partner|two of us|alone|myself|adults?|kids?|children)\b", text)
        )
    )
    in_planning = bool(ctx.get("custom", {}).get("goal") == "plan_itinerary" or ctx.get("proposal") or is_followup_refinement)
    explicit_tour_ref = bool(match or select or re.search(r"\bt\d{2}\b", text) or re.search(r"\b(?:quote|price|cost|rate|how much|book)\b", text))
    if in_planning and action == "accommodation" and not working.get().get("hotel_match") and not working.get().get("is_rate_query"):
        action = "custom"
    if in_planning and not explicit_tour_ref and action == "discover" and named in tours:
        # While actively building a custom plan, interest mentions like "whale watching"
        # must update the plan rather than silently switching to a published tour (e.g. T05).
        full_title_hit = tours[named]["title"].lower().replace("–", "-") in text.replace("–", "-")
        if not full_title_hit:
            named = None
            ctx.pop("tour", None)
    notebook_request = in_planning and action in {"general", "custom", "destination", "discover"} and not working.get().get("explicit_search") and not explicit_tour_ref
    notebook_request = notebook_request or action in {"destination", "custom"} or bool(
        re.search(r"\b(plan|planning|design|organize|arrange|another|change|remove|extend|what is)\b", text)
        or (re.search(r"\b(?:want to visit|like to visit)\b", text) and requested_places(text, records))
        or (re.search(rf"\b({COUNT})[- ]days?\b", text) and not working.get().get("explicit_search")
            and not re.search(r"\b(only|tour|holiday|excursion)\b", text)))
    if action == "custom" and (ctx.get("discovery") or {}).get("constraints", {}).get("places") and not (ctx.get("custom") or {}).get("destination_ids"):
        slug_to_id = {r["path"].rsplit("/", 1)[-1].removesuffix(".md"): k for k, r in records.items() if r["type"] == "destination"}
        carried = [slug_to_id[s] for s in ctx["discovery"]["constraints"]["places"] if s in slug_to_id]
        if carried:
            ctx.setdefault("custom", {}).update(
                goal="plan_itinerary",
                destination_ids=carried,
                destinations=[records[d]["title"] for d in carried],
            )
    if action == "general" and not notebook_request:
        working.get()["discovery_message"] = traveller_message(message[:1200])
    if action not in {"general", "custom", "product_qa", "tour_day_detail", "clarify_reference"} and not is_followup_refinement and not working.get().get("dialogue_quote_resolved"):
        ctx.pop("discovery", None)
    _classify_traveller_and_trip_type(text, ctx, tours, action)

    # --- 4. Handle notebook panel actions and bespoke route planning ---
    events = list(dialogue_events)
    panel_action = None
    if working.get().get("trip_id") and text.startswith("@") and not (match or select):
        action, panel_action = _handle_notebook_panel_action(text, ctx)
        matched_rules.append(f"notebook_panel:{panel_action}")
    active_tour_quote_turn = bool(
        ctx.get("tour") in tours
        and re.search(r"\b(?:quote|price|cost|rate|rates|adults?|couple|solo|kids?|child|children|ages?|infants?|202\d-\d{2}-\d{2})\b", text)
        and not re.search(r"\b(?:custom|design|instead|different|plan a)\b", text)
    )
    if (
        working.get().get("trip_id")
        and not working.get().get("discovery_message")
        and not working.get().get("readonly_custom_question")
        and not (match or select or panel_action or named in tours or active_tour_quote_turn)
        and action in {"general", "custom", "destination", "discover"}
    ):
        action = _handle_notebook_planning(message, text, records, tours, ctx, action, named, active_tour_quote_turn, departure, events)
        matched_rules.append(f"notebook_planning:{action}")
    if action == "general":
        working.get()["discovery_message"] = traveller_message(message[:1200])
    if (select or match or (action == "discover" and named in tours)) and not working.get().get("readonly_custom_question"):
        # Keep the itinerary in turn history. Future edits target the published trip.
        for field in ("proposal", "custom", "selected_day"):
            ctx.pop(field, None)
    if (named or ctx.get("tour")) in tours and action in {"discover", "tour_itinerary", "tour_day_detail", "tour_inclusions", "tour_hotels", "product_qa"}:
        ctx["focused_entity_type"] = "tour"
        ctx["focused_entity_id"] = named or ctx.get("tour")
    if action == "discover" and ctx.get("tour") in tours:
        if ctx.get("date") and "adults" in ctx:
            if (ctx.get("pending_task") or {}).get("type") == "quotation":
                ctx.pop("pending_task", None)
        else:
            ctx["pending_task"] = {"type": "quotation", "tour_id": ctx["tour"]}
    if action == "general" and text and not ctx.get("original_preferences"):
        prefs = [w for w in ("hill country", "mountains", "southern beaches", "southern coast", "beaches", "wildlife", "cultural", "tea") if w in text]
        if prefs:
            ctx["original_preferences"] = prefs
    working.get().update(context=ctx, basis=basis, records=records, tours=tours, action=action, named=named,
                         select=bool(select), panel_action=panel_action, events=[*events, {"stage": "interpret", "provider": "local rules",
                         "action": action, "ms": round((perf_counter() - started) * 1000)}])
    party = "family" if ctx.get("kids") else "adult_party" if ctx.get("adults") else "unspecified"
    entities = {k: ctx[k] for k in ("tour", "date", "adults", "kids", "ages", "search", "custom") if k in ctx}
    preferences = {k: ctx[k] for k in ("traveller_type", "trip_type") if k in ctx}
    event(
        "AGENT",
        "intent.classified",
        intent=action,
        named_tour=named,
        party_type=party,
        matched_rules=matched_rules,
        entities=entities,
        preferences=preferences,
        previous_context=prev_context.get("discovery", {}) if action == "general" else prev_context,
        updated_context=preferences if action == "general" else ctx,
        duration_ms=elapsed(started),
    )
    return {}
