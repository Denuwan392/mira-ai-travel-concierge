import asyncio
import json
import logging
import re
from contextvars import ContextVar
from datetime import date
from functools import wraps
from pathlib import Path
from time import perf_counter
from uuid import UUID, uuid4
from typing import Annotated, TypedDict

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from .catalog import Breakdown, Booking, Card, DayStop, Proposal, RouteMap, Departure, SourcePanel, Excerpt, Notice, Picker, PublicQuote, Turn
from .accommodation import is_accommodation_query
from .data import Unavailable, as_of, price, public_text, tour_card
from .observability import elapsed, event, request_id
from .planner import get_grounded_day_experience
from .provider import rank, notebook_intent
from .rates_repository import current_rates
from .search import extract_search_constraints, filter_tours, rank_filtered_tours
from .surface import surface_messages
from .store import db, encode, published_records, is_current_notebook_turn

visitor_context = ContextVar("visitor", default=None)
run_context = ContextVar("run", default=None)
MONTHS = "January February March April May June July August September October November December".split()
ALIASES = {
    "T01": r"sigiriya.*(?:day (?:trip|tour)|from kandy)|minneriya.*day",
    "T05": r"whale|dolphin",
    "T09": r"cultural triangle(?! tour\b)|ancient cities",
    "T11": r"mirissa.*(?:beach|stay)|beach.*mirissa",
    "T04": r"galle fort.*(?:walk|tour)",
}
WORDS = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split()
COUNT = r"\d{1,3}|" + "|".join(WORDS[1:])


def count(word):
    return int(word) if word.isdigit() else WORDS.index(word)


def parse_date(text):
    if match := re.search(r"\b\d{4}-\d{2}-\d{2}\b", text):
        return date.fromisoformat(match[0]).isoformat()
    names = "|".join(month[:3] + "(?:" + month[3:] + ")?" if len(month) > 3 else month for month in MONTHS)
    if match := re.search(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({names})\s+(\d{{4}})\b", text, re.I):
        month = next(i + 1 for i, m in enumerate(MONTHS) if m.lower().startswith(match[2].lower()))
        return date(int(match[3]), month, int(match[1])).isoformat()
    if match := re.search(rf"\b({names})\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", text, re.I):
        month = next(i + 1 for i, m in enumerate(MONTHS) if m.lower().startswith(match[1].lower()))
        return date(int(match[3]), month, int(match[2])).isoformat()
    return None


def section(row, heading=None, keyword=None):
    body = row["body"]
    if heading:
        match = re.search(rf"^#+ {re.escape(heading)}\s*\n([\s\S]*?)(?=^#|\Z)", body, re.M)
        return public_text(match[1]).strip() if match else ""
    if keyword:
        return "\n".join(public_text(line) for line in body.splitlines()
                         if keyword in line.lower() and not line.startswith("#"))[:500]
    return tour_card(row)["summary"]


class GraphState(TypedDict, total=False):
    surface: list[dict]
    messages: Annotated[list, add_messages]
    turn: dict


# Only the validated turn is emitted as graph state. The per-run working data stays server-side.
working = ContextVar("working", default=None)


def interpret(state):
    message = next((m.content for m in reversed(state.get("messages", [])) if isinstance(m, HumanMessage)), "")
    text = message.strip()[:1200].lower() if isinstance(message, str) else ""
    working.get()["user_text"] = text
    visitor = visitor_context.get()
    run = run_context.get()
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
    if replay:
        turn = Turn.model_validate_json(replay["result"])
        old_quote = next((component.quote for component in turn.components if isinstance(component, Breakdown)), None)
        if old_quote:
            try:
                value = price(old_quote.source, old_quote.date, old_quote.adults, old_quote.ages, as_of(), current_rates())
                with db() as conn:
                    latest = is_current_notebook_turn(conn,str(turn.trace))
                    stored = conn.execute("SELECT internal FROM quotes WHERE id=?", (str(old_quote.id),)).fetchone()
                snapshot = json.loads(stored["internal"])["snapshot"]
                current = latest and (value["total"], value["deposit"], value["snapshot"]) == (
                    old_quote.total, old_quote.deposit, snapshot)
            except (Unavailable, KeyError, TypeError):
                current = False
            if not current:
                turn = turn.model_copy(update={"text": "This saved quote needs to be refreshed. Check current rates.",
                    "components": [c for c in turn.components if not isinstance(c, (Breakdown, Booking))]})
        event("TRACE", "turn.replayed")
        working.get().update(replay=turn)
        return {}
    basis = saved["context"] if saved else "{}"
    ctx = json.loads(basis)
    records = published_records()
    tours = {key: row for key, row in records.items() if row["type"] == "tour"}

    # Handle structured action JSON payloads from UI
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
            return {}
        elif act_type in ("SELECT_TOUR", "VIEW_TOUR"):
            raw_tid = str(act_payload.get("tourId") or act_payload.get("tour") or "").strip()
            tour_id = next((k for k, v in tours.items() if k == raw_tid or v.get("slug") == raw_tid), raw_tid)
            message = f"@tour {tour_id}"
            text = message.lower()
            tour_title = tours.get(tour_id, {}).get("title", tour_id)
            working.get()["prompt"] = f"Tell me about {tour_title}"

    named = next((key for key, row in sorted(tours.items(), key=lambda pair: -len(pair[1]["title"]))
                  if row["title"].lower().replace("–", "-") in text.replace("–", "-")), None)
    match = re.fullmatch(r"@trip ([A-Z\d-]+) (\d{4}-\d{2}-\d{2}) (\d{1,3}) (-|\d{1,3}(?:,\d{1,3})*)", message.strip()) if isinstance(message, str) else None
    select = re.fullmatch(r"@tour ([A-Z\d-]+)", message.strip()) if isinstance(message, str) else None
    started = perf_counter()
    action = "discover"
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
    elif re.fullmatch(r"(?:please )?compare (?:them|these|those|my options|the routes|these tours|these journeys)[.!?]?", text) and ctx.get("suggestions"):
        action = "compare"
    elif re.search(r"python script|sort a list|write .*code", text):
        action = "off_topic"
    elif re.search(r"\b(?:custom|airport transfer|adam.s peak)\b|design .*journey|across kandy|(?:stay at|change pickup|with extra|different hotel)|sigiriya.*from (?!kandy)", text):
        action = "custom"
    elif re.search(r"vegetarian|vegan|halal|dietary", text):
        action = "dietary"
    elif re.search(r"\b(?:deposit|payment) policy\b|when .*balance", text):
        action = "payment"
    elif "cancellation" in text:
        action = "cancellation"
    elif re.search(r"kids.*free|children.*free", text):
        action = "children"
    elif re.search(r"is yala open|jaffna", text):
        action = "unknown"
    elif "polonnaruwa" in text and not named:
        action = "polonnaruwa"
    if action == "custom":
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
    if action in {"discover", "cancellation"}:
        if match or select:
            named = (match or select)[1]
            if named not in tours:
                action = "unknown"
        named = named or next((k for k, pattern in ALIASES.items() if k in tours and re.search(pattern, text)), None)
        if named in tours and action == "discover":
            if named != ctx.get("tour"):
                ctx.pop("date", None)
                # A newly named package with an explicit adult-only party is a new brief.
                new_adult_party = re.search(rf"\bfor (?:{COUNT}) adults?\b", text)
                mentions_children = re.search(r"\b(?:family|kids?|child(?:ren)?|infants?|bab(?:y|ies)|ages?|aged|year.old)\b", text)
                if new_adult_party and not mentions_children:
                    ctx.update(kids=0, ages=[])
            ctx["tour"] = named
        if action == "discover":
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
            if party := re.search(rf"\b({COUNT})\s+adults?\b", text):
                ctx["adults"] = count(party[1])
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
            if search_constraints and re.search(r"\b(?:tour|trip|package|holiday|stay|day|week|beach|cultur|multi)\b", text):
                # Explicit published-tour search/filter overrides stale selections and proposals
                ctx.pop("tour", None)
                ctx.pop("proposal", None)
                ctx.pop("custom", None)
                ctx["search"] = search_constraints
                if "trip_type" in search_constraints:
                    ctx["trip_type"] = search_constraints["trip_type"]
                working.get()["explicit_search"] = True
                filtered_pool = filter_tours(tours, search_constraints)
                if len(filtered_pool) == 1 and ("adults" in ctx or ctx.get("date")):
                    ctx["tour"] = next(iter(filtered_pool))
                    named = ctx["tour"]
                else:
                    action = "general"
            elif action == "discover" and not named and not (departure or re.search(r"\b(?:adults?|kids?|child|children|ages?|solo|quote|price|book)\b", text)):
                ctx.pop("search", None)
                ctx_tour = next((k for k, row in records.items() if row["type"] == "destination"
                                 and row["title"].lower().split()[0] in text.split()), None)
                if ctx_tour:
                    action, named = "destination", ctx_tour
                elif text and not select:
                    action = "general"
            if action == "discover" and not named and re.search(r"price|how much|quote", text):
                unknown_named = bool(re.search(
                    r"\b(?:how much is|price (?:of|for)|quote for)\s+(?:the\s+|a\s+)?(?!(?:this|that|the)\s+(?:tour|trip|quote|package)\b)[a-z]+\s+(?:tour|trip|expedition|package|safari)\b",
                    text,
                ))
                has_tour = ctx.get("tour") in tours and not unknown_named
                has_details = bool(departure or "adults" in text or "kids" in text or "ages" in text or "date" in ctx or "adults" in ctx)
                explicit_followup = bool(re.search(r"update|recheck|that tour|this tour|the tour|the quote|^price[? .]*$", text))
                party_reply = bool(re.fullmatch(rf"(?:actually )?(?:there (?:will be|are) )?(?:{COUNT}) adults?[,. ]*(?:can you update the price[? .]*)?", text))
                if unknown_named:
                    ctx.pop("tour", None)
                if not has_tour:
                    action = "custom"
            if ctx.get("adults", 1) not in range(1, 101) or any(not 0 <= age <= 120 for age in ctx.get("ages", [])):
                action = "invalid_party"
            if action == "discover" and (ctx.get("kids", 0) > 30 or len(ctx.get("ages", [])) > 30):
                action = "custom"
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
    events = []
    panel_action = None
    if working.get().get("trip_id") and text.startswith("@") and not (match or select):
        panel_action = "invalid"
        if ctx.get("proposal"):
            if chosen := re.fullmatch(r"@day (\d{1,2})",text):
                day = int(chosen[1])-1
                if 0 <= day < len(ctx["proposal"]):
                    ctx["selected_day"] = day
                    panel_action = "day"
            elif depart := re.fullmatch(r"@depart (\d{4}-\d{2}-\d{2})",text):
                try:
                    departure = date.fromisoformat(depart[1])
                    if departure < as_of():
                        raise ValueError("past departure")
                    ctx.setdefault("custom",{})["date"] = departure.isoformat()
                    panel_action = "date"
                except ValueError:
                    pass
        action = "proposal_view" if panel_action!="invalid" else "unknown"
    active_tour_quote_turn = bool(
        ctx.get("tour") in tours
        and re.search(r"\b(?:quote|price|cost|rate|rates|adults?|kids?|child|children|ages?|infants?|202\d-\d{2}-\d{2})\b", text)
        and not re.search(r"\b(?:custom|design|instead|different|plan a)\b", text)
    )
    if working.get().get("trip_id") and not (match or select or panel_action or named in tours or active_tour_quote_turn) and action in {"general","custom","destination","discover"}:
        destinations = {k:r["title"] for k,r in records.items() if r["type"]=="destination"}
        previous = ctx.get("proposal", [])
        evidence = {}
        if re.search(r"\?|\b(?:what|where|tell me|when|why|can i)\b",text) and not re.search(r"quote|price|cost|deposit|payment",text):
            words = set(re.findall(r"[a-z]{3,}",text)) - {"what","where","tell","when","about","the","can"}
            candidates = []
            for key,row in records.items():
                if key=="P06":
                    continue
                for i,block in enumerate(public_text(row["body"]).split("\n\n")):
                    block = block.strip()
                    hits = len(words & set(re.findall(r"[a-z]{3,}",(row["title"]+" "+block).lower())))
                    if hits and block and not block.startswith("#"):
                        candidates.append((hits,f"{key}:{i}",block[:800]))
            evidence = {k:v for _,k,v in sorted(candidates,reverse=True)[:14]}
        intent = notebook_intent(message, previous, destinations, events, evidence)
        if intent and intent.panels is not None:
            working.get()["optional_panels"] = intent.panels
        if intent and intent.operation=="fact" and intent.evidence_key in evidence:
            k=intent.evidence_key
            working.get()["evidence"]=(k.split(":")[0],evidence[k])
            action="sourced_answer"
        elif intent and intent.operation=="unknown" and evidence:
            action="unknown"
        extend = re.search(r"(?:add|another|extra|one more).*?day",text) and previous
        reduce = re.search(r"(?:less|fewer|remove|drop|reduce).*?(?:time|day).*?(?:in\s+)?([a-z]+)", text) and previous
        change_days = re.search(r"(?:change|make|adjust).*?(?:to|trip to)\s+([1-9]\d?)[- ]days?", text) and previous
        requested = re.search(rf"\b({COUNT})[- ]days?\b",text)
        ids = [k for k,title in destinations.items() if re.search(r"\b"+re.escape(title.lower())+r"\b",text)]
        plan_request = (
            not working.get().get("explicit_search")
            and requested
            and named not in tours
            and action in {"general", "custom", "destination", "discover"}
        )
        has_duration_or_date = bool(requested or (intent and intent.days) or departure)
        has_scope = bool(
            ids
            or (intent and intent.destinations)
            or re.search(r"train|nature|beach|coast|culture|wildlife|safari|tea|hill", text)
        )
        broad_plan = bool(
            not working.get().get("explicit_search")
            and named not in tours
            and not active_tour_quote_turn
            and not previous
            and (
                (intent and intent.operation == "plan")
                or re.search(r"\b(?:plan|design|organize|arrange)\b.*\b(?:holiday|trip|vacation|journey|itinerary)\b", text)
            )
            and not (has_duration_or_date and has_scope)
            and not requested
        )
        route = None
        if broad_plan:
            ctx.pop("proposal", None)
            action = "clarify_plan"
        elif extend or (intent and intent.operation=="extend" and previous):
            targets = ids or (intent.destinations if intent else []) or previous[-1:]
            target = targets[0]
            idx = max((i for i,k in enumerate(previous) if k==target),default=len(previous)-1)+1
            n = min(intent.days if intent and intent.operation=="extend" and intent.days else 1,30-len(previous))
            route = previous[:idx]+[target]*n+previous[idx:]
        elif reduce:
            matched_title = reduce.group(1).lower()
            matched_id = next((k for k, title in destinations.items() if matched_title in title.lower()), None)
            if matched_id and matched_id in previous and len(previous) > 1:
                idx_to_remove = max(i for i, k in enumerate(previous) if k == matched_id)
                route = previous[:idx_to_remove] + previous[idx_to_remove + 1:]
        elif change_days:
            new_len = min(30, max(1, int(change_days.group(1))))
            if new_len > len(previous):
                last_dest = previous[-1]
                route = previous + [last_dest] * (new_len - len(previous))
            elif new_len < len(previous):
                route = previous[:new_len]
        elif plan_request or (not working.get().get("explicit_search") and intent and intent.operation=="plan" and named not in tours and not active_tour_quote_turn):
            if intent and intent.destinations:
                ids = intent.destinations
            if not ids:
                ids = [key for pattern,key in [("train|nature","D05"),("beach|coast","D08"),("culture","D03")] if re.search(pattern,text) and key in destinations]
            if ids or requested or (intent and intent.days):
                if not ids:
                    ids = list(destinations)[:2]
                n = min(30,max(1,count(requested[1]) if requested else (intent.days if intent and intent.days else len(ids))))
                route = [ids[min(len(ids)-1,i*len(ids)//n)] for i in range(n)]
            else:
                action = "clarify_plan"
        if route:
            ctx["proposal"] = route
            ctx["selected_day"] = min(ctx.get("selected_day",0),len(route)-1)
            ctx.pop("tour",None)
            ctx["custom"] = {**ctx.get("custom",{}),"days":len(route),"destinations":list(dict.fromkeys(destinations[k] for k in route))}
            if intent and intent.adults:
                ctx["custom"]["party"] = intent.adults
            action = "custom"
    if select or match or (action == "discover" and named in tours):
        # Keep the itinerary in turn history. Future edits target the published trip.
        for field in ("proposal", "custom", "selected_day"):
            ctx.pop(field, None)
    working.get().update(context=ctx, basis=basis, records=records, tours=tours, action=action, named=named,
                         select=bool(select), panel_action=panel_action, events=[*events,{"stage": "interpret", "provider": "local rules",
                         "action": action, "ms": round((perf_counter()-started)*1000)}])
    party = "family" if ctx.get("kids") else "adult_party" if ctx.get("adults") else "unspecified"
    event("AGENT", "intent.classified", intent=action, party_type=party, duration_ms=elapsed(started))
    return {}


def retrieve(_):
    started = perf_counter()
    w = working.get()
    records, ctx, action = w["records"], w["context"], w["action"]
    ids = {
        "cancellation": ["P02"], "children": ["P03"], "dietary": ["P04"], "payment": ["P01"],
        "polonnaruwa": ["T09", "T08"],
        "compare": ctx.get("suggestions", [])[:2],
        "destination": [w["named"]], "discover": [ctx.get("tour")],
        "custom": [] if ctx.get("proposal") else ["T08", "T10", "T12"],
        "clarify_plan": ["T01", "T09", "T05"],
        "general": ["T01", "T09", "T05"],
        "tour_itinerary": [w.get("named") or ctx.get("tour")],
        "tour_day_detail": [w.get("named") or ctx.get("tour")],
        "tour_inclusions": [w.get("named") or ctx.get("tour")],
        "accommodation": [w.get("hotel_source") or "P01"],
        "tour_hotels": [w.get("named") or ctx.get("tour")],
        "galle_cancellation": ["P02"],
        "mirissa_discount": ["D08"],
        "draft_tour": [],
    }.get(action, [])
    if action == "destination":
        place = records[w["named"]]["path"].rsplit("/", 1)[-1].removesuffix(".md")
        ids += [key for key, tour in w["tours"].items() if place in tour["destinations"]][:3]
    if action in {"custom", "general"}:
        search = ctx.get("search") if action == "general" else None
        if search:
            filtered = filter_tours(w["tours"], search)
            if not filtered:
                ids = []
                w["no_matching_tours"] = True
            else:
                det_ids = rank_filtered_tours(filtered, search)
                llm_trip = {**search, **{k: ctx[k] for k in ("adults", "kids") if k in ctx}}
                ranked = rank(filtered, llm_trip, w["events"])
                ids = [tid for tid in (ranked or []) if tid in filtered] or det_ids
        else:
            trip = ctx.get("custom", {}) if action == "custom" else {}
            destinations = {name.split()[0].lower() for name in trip.get("destinations", [])}
            if ctx.get("proposal") and action == "custom":
                destinations = {Path(records[key]["path"]).stem for key in ctx["proposal"]}
            if destinations:
                related = sorted(w["tours"], key=lambda key: -len(destinations.intersection(w["tours"][key]["destinations"])))
                ids = [key for key in related if destinations.intersection(w["tours"][key]["destinations"])][:3] or ids
            if not (w.get("trip_id") and ctx.get("proposal")):
                ids = rank(w["tours"], {k:trip[k] for k in ("destinations","days","party") if k in trip}, w["events"]) or ids
    w["rows"] = [records[key] for key in ids if key in records]
    if action in {"general", "destination", "custom", "compare"}:
        ctx["suggestions"] = [row["id"] for row in w["rows"] if row["type"] == "tour"]
    sources = [r["id"] for r in w["rows"]]
    duration = elapsed(started)
    w["events"].append({"stage": "retrieval", "sources": sources, "ms": duration})
    event("RAG", "retrieval.completed", documents=len(sources), sources=sources, duration_ms=duration)
    return {}


def quote_route(_):
    w = working.get()
    ctx = w["context"]
    if (w["action"] == "discover" and not w["select"] and ctx.get("tour") in w["tours"]
            and ctx.get("date") and "adults" in ctx and ctx.get("kids", 0) == len(ctx.get("ages", []))):
        return "quote"
    return "compose"


def matching_enquiry(w, reason):
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
    previous = matching_enquiry(w, reason)
    identifier = UUID(previous["id"]) if previous else uuid4()
    reference = previous["reference"] if previous else None
    w["enquiry"] = identifier
    w["enquiry_reference"] = reference or f"ENQ-{as_of().year}-{identifier.hex[:8].upper()}"


def quote_node(_):
    w = working.get()
    ctx = w["context"]
    before = perf_counter()
    event("PRICING", "pricing.started", level=logging.DEBUG, tour_id=ctx["tour"])
    rates = None
    try:
        rates = current_rates()
        value = price(ctx["tour"], date.fromisoformat(ctx["date"]), ctx["adults"], ctx.get("ages", []), as_of(), rates)
        w["internal"] = value
        quote_enquiry(w, "verified_quote")
        w["quote"] = PublicQuote(enquiry=w["enquiry"], enquiry_reference=w["enquiry_reference"],
            id=uuid4(), source=ctx["tour"], title=w["tours"][ctx["tour"]]["title"],
            date=ctx["date"], adults=ctx["adults"], ages=ctx.get("ages", []),
            **{k: value[k] for k in ("total", "deposit", "balance")},
        )
    except (Unavailable, ValueError) as exc:
        if w.get("explicit_quote") and isinstance(exc, Unavailable) and str(exc) == "rate_import_invalid":
            raise
        w["reason"] = str(exc) if isinstance(exc, Unavailable) else "invalid_travel_details"
    w["events"].append({"stage": "pricing", "outcome": w.get("reason", "verified"),
                        "snapshot": w.get("internal", {}).get("snapshot"), "rate_digest": rates.digest if rates else None,
                        "ms": round((perf_counter()-before)*1000)})
    quote = w.get("quote")
    reason = w.get("reason")
    event("PRICING", "pricing.completed", tour_id=ctx["tour"], rate_status="verified" if quote else "unavailable",
          quote_id=str(quote.id) if quote else None, rule=reason, duration_ms=elapsed(before))
    return {}


def compose(_):
    started = perf_counter()
    w = working.get()
    if "replay" in w:
        return {}
    trace = w.get("trace") or uuid4()
    ctx, rows, action = w["context"], w["rows"], w["action"]
    user_text = w.get("user_text", "")
    components = []
    sources = []
    for row in rows:
        key = row["id"]
        if action in {"cancellation", "children", "dietary", "payment", "polonnaruwa"} or (action == "destination" and row["type"] == "destination"):
            heading = None
            if action == "cancellation" and w["named"] in w["tours"]:
                heading = ("Multi-day tours and stays" if "nights" in w["tours"][w["named"]]["duration"]
                           else "Day and city tours")
            heading = {"dietary": "Can you cater for dietary needs?", "payment": "Payment"}.get(action, heading)
            body = (section(row, heading, "polonnaruwa" if action == "polonnaruwa" else None)
                    if action != "children" and not (action == "cancellation" and not heading)
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
                for d in tour_days:
                    components.append(Excerpt(
                        type="ItineraryDay",
                        source=row["id"],
                        heading=f"Day {d['day']}: {d['title']}",
                        text=f"{d['description']}\n\n• Accommodation: {d.get('accommodation') or 'None'}\n• Meals: {d.get('meals') or 'None'}\n• Included tickets: {d.get('entrance_tickets') or 'None'}"
                    ))
    if w.get("quote"):
        q = w["quote"]
        components.insert(0, Breakdown(quote=q))
        components.append(Booking(quote=q.id))
        text = (
            f"Verified quote: {q.currency} {q.total:,} total (deposit {q.currency} {q.deposit:,}) "
            f"for {q.title} on {q.date}. Private enquiry {q.enquiry_reference} is saved."
        )
    elif w.get("reason"):
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
        elif w.get("explicit_quote"):
            reason_text = {
                "group_size": "The party exceeds the maximum group size in the rate workbook.",
                "transport_rate": "No transport tier matches the selected party size.",
                "date_or_fx_expired": "The selected date is outside the valid pricing window.",
                "season_rate": "No contracted season rate covers the selected travel date.",
                "conflicting_tour_scope": "The tour scope requires manual pricing.",
            }.get(reason_code, f"The workbook could not price this configuration ({reason_code}).")
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
    elif action == "custom":
        w["reason"] = "custom_or_unsupported"
        prior = None
        if w.get("trip_id"):
            with db() as conn:
                candidate = conn.execute("""SELECT e.id, e.trip FROM enquiries e JOIN trip_turns t ON t.trace=e.trace
                    WHERE t.trip=? AND e.reason='custom_or_unsupported'
                      AND e.status NOT IN ('booked','closed','closed_lost','unqualified')
                    ORDER BY t.rowid DESC LIMIT 1""",(w["trip_id"],)).fetchone()
                if candidate:
                    if w.get("panel_action") == "date":
                        prior = candidate
                    else:
                        try:
                            prev_custom = json.loads(candidate["trip"]) if candidate["trip"] else {}
                            curr_custom = ctx.get("custom", {})
                            if (
                                prev_custom.get("destinations") == curr_custom.get("destinations")
                                and prev_custom.get("days") == curr_custom.get("days")
                            ) or prev_custom.get("request") == curr_custom.get("request"):
                                prior = candidate
                        except (ValueError, TypeError):
                            pass
        w["enquiry"] = UUID(prior["id"]) if prior else uuid4()
        enq_ref = f"ENQ-{as_of().year}-{str(w['enquiry']).replace('-', '')[:8].upper()}"
        text = "A travel specialist will confirm the details. I’ve saved a private enquiry for our team."
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
    elif action == "draft_tour":
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
    elif action == "mirissa_discount":
        text = "Mirissa is a scenic crescent beach on the south coast, celebrated for blue-whale watching between November and April. We quote official contracted rates from our rate sheet and do not offer a 40% loyalty discount."
        sources = ["D08"]
        components.append(Excerpt(type="DestinationHighlight", source="D08", heading="Mirissa",
                                  text=public_text(w["records"]["D08"]["body"])))
    elif action == "galle_cancellation":
        text = "Under our master cancellation policy (P02), day and city tours require at least 48 hours notice before departure for a full refund. Cancellations made 36 hours before start fall within the 48-hour window and are non-refundable."
        sources = ["P02"]
        components.append(Excerpt(type="PolicySnippet", source="P02", heading="Day and city tours",
                                  text="Full refund if cancelled at least 48 hours before the tour start. No refund if cancelled less than 48 hours before start."))
    elif action == "tour_day_detail" and w.get("day_detail"):
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
        row = rows[0]
        included = public_text("\n".join(row.get("inclusions", []))).strip()
        text = included or "I can’t confirm the inclusions from the published itinerary. You can request an enquiry."
        sources = [row["id"]]
    elif action == "accommodation":
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
    elif action == "tour_hotels" and rows:
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
        row = rows[0]
        tour_days = row.get("days", [])
        text = f"Here is the complete {len(tour_days)}-day itinerary for {row['title']}. Each day's route, accommodation, and inclusions are shown below."
        sources = [row["id"]]
    elif action == "reject":
        text = "I can help with a standard quote using our published tours and current rates. Which tour are you considering?"
    elif action == "off_topic":
        text = "I’m Mira, your Sri Lanka travel companion. I can help you explore tours or plan a trip."
    elif action == "unknown":
        text = "I can’t confirm that from our published travel information. You can ask me to create a custom enquiry."
    elif action == "compare" and rows:
        text = "Here are the published routes from your last results. Compare the duration, starting point and destinations, then choose a tour to plan."
    elif action == "destination" and len(ctx.get("suggestions", [])) > 1:
        text = f"I found {len(ctx['suggestions'])} published journeys that visit {w['records'][w['named']]['title']}. Would you like to compare their routes or explore one itinerary?"
    elif action == "children" and sources:
        if re.search(r"\b(?:t07|kandy heritage|stay free|kids under 12)\b", user_text) or w.get("named") == "T07":
            text = "Our current master child policy (P03) supersedes any older promotional mentions. Children aged 2 to 11 pay applicable child costs (half-price meals, entrance tickets, and extra bed fees in hotel stays), while infants under 2 travel free."
        else:
            text = "Here’s what our published travel information says."
    elif action in {"cancellation", "dietary", "payment", "polonnaruwa", "destination"} and sources:
        text = "Here’s what our published travel information says."
    elif action == "invalid_party":
        text = "Please enter a valid adult count and give each child’s age."
    elif action == "invalid_date":
        text = "Please enter a valid travel date with the year included."
    elif action == "discover" and rows:
        text = "Here’s a published tour for your journey. What’s your travel date and who’s coming?"
        if ctx.get("date"):
            text = "Who’s coming? Please include the ages of any children."
        elif "adults" in ctx:
            text = "What date would you like to travel?"
        components.append(Picker(tour=ctx["tour"], date=ctx.get("date"),
                                 adults=ctx.get("adults") or 2, ages=ctx.get("ages", [])))
    elif ctx.get("adults") and action == "discover":
        text = "I’ve noted your group. Which tour or part of Sri Lanka would you like to explore?"
    elif w.get("no_matching_tours"):
        search = ctx.get("search") or {}
        if search.get("trip_type") == "day tour" and search.get("departure"):
            text = (
                f"I couldn’t find any published day tours departing from {search['departure'].title()}. "
                "Our published day tours currently depart from Kandy, Colombo, Galle, or Mirissa. "
                "Would you like to explore those or request a custom itinerary?"
            )
        else:
            text = (
                "I couldn’t find any published tours matching those exact criteria. "
                "Would you like to adjust your preferences or request a custom itinerary?"
            )
    elif action == "clarify_plan":
        if ctx.get("traveller_type") == "family":
            text = (
                "I’d love to help plan your Sri Lanka family holiday. To tailor the right route, could you share:\n"
                "1. How many days you’d like to travel (or your preferred dates)?\n"
                "2. How many adults and the ages of any children?\n"
                "3. What your family enjoys most (for example, wildlife safaris, beaches, train rides, or cultural sites)?\n\n"
                "While you decide, these published tours are popular with families: "
                "Sigiriya & Minneriya (fortress + elephant safari), Mirissa Whale Watching (short morning boat trip), "
                "and Cultural Triangle (multi-day heritage loop)."
            )
        else:
            text = (
                "I’d be happy to help plan your Sri Lanka journey. Could you share:\n"
                "1. How many days you’d like to travel (or your preferred dates)?\n"
                "2. Who is travelling (adults and any children's ages)?\n"
                "3. Which destinations or interests appeal most (wildlife, beaches, tea hills, or culture)?"
            )
    elif action == "general" and ctx.get("search") and rows:
        search = ctx["search"]
        trip_type = search.get("trip_type")
        departure = search.get("departure")
        theme = search.get("theme")
        days = search.get("days")
        if trip_type == "day tour":
            if departure:
                text = (
                    f"Here are our published day tours departing from {departure.title()}. "
                    "Which one would you like to explore, and what’s your travel date?"
                )
            else:
                text = (
                    "Here are our published day tours. Which departure location suits you best "
                    "(for example, Kandy, Colombo, Galle, or Mirissa), and what date are you considering?"
                )
        elif trip_type == "multi-day":
            if theme == "cultural" and days:
                text = f"Here are our published multi-day cultural tours around {days} days. Which itinerary would you like to explore?"
            elif days:
                text = f"Here are our published multi-day tours around {days} days. Which itinerary would you like to explore?"
            else:
                text = "Here are our published multi-day tours. Which itinerary would you like to explore?"
        elif theme:
            text = f"Here are our published {theme} tours. Would you like to explore one of these itineraries?"
        else:
            text = "Here are our published tours matching your request. Which itinerary would you like to explore?"
    else:
        text = "I’m Mira, your Sri Lanka travel companion. Where would you like your journey to begin?"
    if w.get("trip_id") and action in {"custom","proposal_view"} and ctx.get("proposal"):
        used_passages = set()
        days = []
        for k in ctx["proposal"]:
            dest_title = w["records"][k]["title"]
            passage, src = get_grounded_day_experience(w["records"], k, used_passages)
            used_passages.add(passage)
            days.append(DayStop(source=k, evidence=src, name=dest_title, passage=passage))
        selected = min(ctx.get("selected_day",0),len(days)-1)
        components[:0] = [Proposal(days=days,selected=selected),RouteMap(days=days,selected=selected),
                          Departure(value=ctx.get("custom",{}).get("date"))]
        sources = list(dict.fromkeys([days[selected].source, *sources, *(d.evidence or d.source for d in days)]))[:6]
        text = f"Your proposed journey now has {len(days)} days. I’ve saved the route for specialist confirmation."
        if action=="proposal_view":
            d = days[selected]
            text = (f"Day {selected+1} takes you to {d.name}." if w["panel_action"]=="day"
                    else f"I’ve updated your proposed departure to {ctx['custom']['date']}. Your route still needs specialist confirmation.")
    if action=="sourced_answer":
        source,passage=w["evidence"]
        sources=[source]
        components=[Excerpt(type="PolicySnippet",source=source,heading=w["records"][source]["title"],text=passage)]
        text="Here is the passage from our published travel library that answers your question."
    if w.get("trip_id") and sources:
        first = sources[0]
        if action=="compare" and len(rows)>1:
            components.insert(0,SourcePanel(type="ComparisonPanel",source=first,heading="Compare journeys",
                text=" · ".join(r["title"]+" ("+r["duration"]+")" for r in rows)))
        if action=="discover" and rows and rows[0]["type"]=="tour":
            record=rows[0]
            for kind,pattern in [("StayCard",r"Accommodation:\*\* ([^\n]+)"),("ActivityCard",r"Entrance tickets included:\*\* ([^\n]+)")]:
                hit=re.search(pattern,public_text(record["body"]))
                if hit and hit[1].strip().lower() not in {"none","n/a"}:
                    components.append(SourcePanel(type=kind,source=first,heading="Published stay" if kind=="StayCard" else "Included visits",text=hit[1]))
        if w.get("quote"):
            components.append(SourcePanel(type="ConfirmationPanel",source=first,heading="Quote saved",text="Your private enquiry is available to the travel team."))
        if not any(getattr(c, "type", None) == "TourCard" and getattr(c, "id", None) == first for c in components):
            components.append(SourcePanel(type="SourceReference",source=first,heading="From the travel library",text=w["records"][first]["title"]))
        for i,item in enumerate(components):
            if isinstance(item,Excerpt) and item.type=="DestinationHighlight":
                components[i]=SourcePanel(**(item.model_dump()|{"type":"DestinationCard"}))
    if any(e["stage"].startswith("gemini") and e.get("outcome") in {"fallback","unavailable","unconfigured"} for e in w["events"]):
        text += " Limited service: I’m using the published catalogue."
    sources = list(dict.fromkeys(sources))[:6]
    if "optional_panels" in w:
        optional = {"InteractiveMap", "DateSelector", "ComparisonPanel", "ActivityCard", "StayCard"}
        components = [item for item in components if item.type not in optional or item.type in w["optional_panels"]]
    components = components[:12]
    w["turn"] = Turn(trace=trace, text=text, sources=sources, components=components)
    duration = elapsed(started)
    w["events"].append({"stage": "validated_ui", "components": [c.type for c in components], "ms": duration})
    event("RAG", "grounding.completed", sources=sources, documents=len(sources))
    event("AGENT", "ui.validated", components=len(components), duration_ms=duration)
    return {}


def persist():
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
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            previous = conn.execute("SELECT result FROM traces WHERE visitor=? AND run=?", (visitor, run)).fetchone()
            if previous:
                turn = Turn.model_validate_json(previous["result"])
            else:
                active = conn.execute("SELECT context FROM visitors WHERE id=?", (visitor,)).fetchone()
                trip_id = w.get("trip_id")
                if trip_id:
                    active = conn.execute("SELECT context FROM trips WHERE id=? AND visitor=? AND revision=?",
                                          (trip_id,visitor,w["revision"])).fetchone()
                if not active or active["context"] != w["basis"]:
                    raise ValueError("Session changed during this turn")
                conn.execute("INSERT INTO traces(id, visitor, run, events, result) VALUES(?,?,?,?,?)",
                             (str(turn.trace), visitor, run, encode(w["events"]), turn.model_dump_json()))
                q = w.get("quote")
                if q:
                    conn.execute("INSERT INTO quotes(id, visitor, trace, public, internal) VALUES(?,?,?,?,?)",
                                 (str(q.id), visitor, str(turn.trace), q.model_dump_json(), encode(w["internal"])))
                if trip_id and w.get("panel_action") == "date":
                    conn.execute("""UPDATE enquiries SET trip=? WHERE id=(
                        SELECT e.id FROM enquiries e JOIN trip_turns t ON t.trace=e.trace
                        WHERE t.trip=? AND e.reason='custom_or_unsupported' ORDER BY t.rowid DESC LIMIT 1)""",
                        (encode(w["context"].get("custom",{})),trip_id))
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
                if trip_id:
                    conn.execute("INSERT INTO trip_turns(trip,trace,prompt) VALUES(?,?,?)",(trip_id,str(turn.trace),w["prompt"]))
                    conn.execute("""UPDATE trips SET context=?,revision=revision+1,updated=CURRENT_TIMESTAMP,
                        title=CASE WHEN revision=0 THEN ? ELSE title END WHERE id=?""",
                        (encode(w["context"]),w["prompt"][:100],trip_id))
                else:
                    conn.execute("UPDATE visitors SET context=? WHERE id=?", (encode(w["context"]), visitor))
                stage["ms"] = elapsed(started)
                conn.execute("UPDATE traces SET events=? WHERE id=?", (encode(w["events"]), str(turn.trace)))
        if not previous:
            event("TRACE", "turn.persisted", quote_id=str(q.id) if q else None, enquiry=enquiry,
                  duration_ms=elapsed(started))
    return {"turn": turn.model_dump(mode="json"), "surface": surface_messages(turn), "messages": [AIMessage(content=turn.text, id=str(turn.trace))]}


async def save(_):
    try:
        result = await asyncio.to_thread(persist)
    except Exception:
        event("ERROR", "turn.persistence_failed", level=logging.ERROR, exception=True)
        raise
    message = result["messages"][0]
    await adispatch_custom_event("manually_emit_message", {"message_id": message.id, "message": message.content})
    return result


def log_node_errors(fn):
    @wraps(fn)
    def run(state):
        try:
            return fn(state)
        except Exception:
            event("ERROR", "workflow.node_failed", level=logging.ERROR, exception=True, node=fn.__name__)
            raise

    return run


builder = StateGraph(GraphState)
for name, fn in [("interpret", interpret), ("retrieve", retrieve), ("quote", quote_node),
                 ("compose", compose), ("save", save)]:
    builder.add_node(name, fn if name == "save" else log_node_errors(fn))
builder.add_edge(START, "interpret")
builder.add_conditional_edges("interpret", lambda _: "save" if "replay" in working.get() else "retrieve",
                              {"save": "save", "retrieve": "retrieve"})
builder.add_conditional_edges("retrieve", quote_route, {"quote": "quote", "compose": "compose"})
builder.add_edge("quote", "compose")
builder.add_edge("compose", "save")
builder.add_edge("save", END)
graph = builder.compile()
