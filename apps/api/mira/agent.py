import asyncio
import json
import re
from contextvars import ContextVar
from datetime import date
from time import perf_counter
from uuid import UUID, uuid4
from typing import Annotated, TypedDict

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from .catalog import Breakdown, Booking, Card, Excerpt, Notice, Picker, PublicQuote, Turn
from .data import Unavailable, as_of, price, public_text, tour_card
from .provider import rank
from .rates_repository import current_rates
from .store import db, encode, published_records

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
    messages: Annotated[list, add_messages]
    turn: dict


# Only the validated turn is emitted as graph state. The per-run working data stays server-side.
working = ContextVar("working", default=None)


def interpret(state):
    message = next((m.content for m in reversed(state.get("messages", [])) if isinstance(m, HumanMessage)), "")
    text = message.strip()[:1200].lower() if isinstance(message, str) else ""
    visitor = visitor_context.get()
    run = run_context.get()
    with db() as conn:
        saved = conn.execute("SELECT context FROM visitors WHERE id = ?", (visitor,)).fetchone()
        replay = conn.execute("SELECT result FROM traces WHERE visitor = ? AND run = ?", (visitor, run)).fetchone()
    if replay:
        turn = Turn.model_validate_json(replay["result"])
        old_quote = next((component.quote for component in turn.components if isinstance(component, Breakdown)), None)
        if old_quote:
            try:
                value = price(old_quote.source, old_quote.date, old_quote.adults, old_quote.ages, as_of(), current_rates())
                with db() as conn:
                    stored = conn.execute("SELECT internal FROM quotes WHERE id=?", (str(old_quote.id),)).fetchone()
                snapshot = json.loads(stored["internal"])["snapshot"]
                current = (value["total"], value["deposit"], value["snapshot"]) == (
                    old_quote.total, old_quote.deposit, snapshot)
            except (Unavailable, KeyError, TypeError):
                current = False
            if not current:
                turn = turn.model_copy(update={"text": "This saved quote needs to be refreshed. Check current rates.",
                    "components": [c for c in turn.components if not isinstance(c, (Breakdown, Booking))]})
        working.get().update(replay=turn)
        return {}
    basis = saved["context"] if saved else "{}"
    ctx = json.loads(basis)
    records = published_records()
    tours = {key: row for key, row in records.items() if row["type"] == "tour"}
    named = next((key for key, row in sorted(tours.items(), key=lambda pair: -len(pair[1]["title"]))
                  if row["title"].lower().replace("–", "-") in text.replace("–", "-")), None)
    match = re.fullmatch(r"@trip ([A-Z\d-]+) (\d{4}-\d{2}-\d{2}) (\d{1,3}) (-|[\d,]+)", message.strip()) if isinstance(message, str) else None
    select = re.fullmatch(r"@tour ([A-Z\d-]+)", message.strip()) if isinstance(message, str) else None
    started = perf_counter()
    action = "discover"
    if re.search(r"ignore .*instructions|profit margin|reveal .*cost|publish .*without|invent .*price|\d+% off", text):
        action = "reject"
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
        custom = {"destinations": [row["title"] for row in records.values() if row["type"] == "destination"
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
            ctx["tour"] = named
        if action == "discover":
            try:
                departure = parse_date(text)
            except ValueError:
                departure = None
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
            if ages := re.search(r"\b(?:aged|ages?)\s+(?:is\s+|are\s+)?(\d{1,3}(?:\s*(?:,|and)\s*\d{1,3})*)", text):
                ctx["ages"] = [int(x) for x in re.findall(r"\d+", ages[1])][:30]
                if ctx.get("kids", -1) < 0:
                    ctx["kids"] = len(ctx["ages"])
            if baby := re.search(rf"\b({COUNT})[- ]year[- ]old", text):
                ctx["ages"] = [count(baby[1])]
                ctx.setdefault("kids", 1)
            if re.search(r"\b(?:other child|and another|or another)\b", text):
                action = "invalid_party"
            if re.search(r"\b(?:child|children|kids?|baby|infant|family)\b", text) and "kids" not in ctx:
                ctx["kids"] = -1
            if re.search(r"\b(?:only adults|no children|without children)\b", text):
                ctx.update(kids=0, ages=[])
            if match:
                ages = [] if match[4] == "-" else [int(x) for x in match[4].split(",")][:31]
                ctx.update(adults=int(match[3]), kids=len(ages), ages=ages)
            if action == "discover" and not named and not (departure or re.search(r"\b(?:adults?|kids?|child|children|ages?|solo|quote|price|book)\b", text)):
                ctx_tour = next((k for k, row in records.items() if row["type"] == "destination"
                                 and row["title"].lower().split()[0] in text.split()), None)
                if ctx_tour:
                    action, named = "destination", ctx_tour
                elif text and not select:
                    action = "general"
            if action == "discover" and not named and re.search(r"price|how much|quote", text):
                explicit_followup = bool(re.search(r"update|recheck|that tour|this tour|the quote|^price[? .]*$", text))
                party_reply = bool(re.fullmatch(rf"(?:actually )?(?:there (?:will be|are) )?(?:{COUNT}) adults?[,. ]*(?:can you update the price[? .]*)?", text))
                if not ctx.get("tour") or not (explicit_followup or party_reply):
                    action = "custom"
            if ctx.get("adults", 1) not in range(1, 101) or any(not 0 <= age <= 120 for age in ctx.get("ages", [])):
                action = "invalid_party"
            if action == "discover" and (ctx.get("kids", 0) > 30 or len(ctx.get("ages", [])) > 30):
                action = "custom"
    working.get().update(context=ctx, basis=basis, records=records, tours=tours, action=action, named=named,
                         select=bool(select), events=[{"stage": "interpret", "provider": "local rules",
                         "action": action, "ms": round((perf_counter()-started)*1000)}])
    return {}


def retrieve(_):
    w = working.get()
    records, ctx, action = w["records"], w["context"], w["action"]
    ids = {
        "cancellation": ["P02"], "children": ["P03"], "dietary": ["P04"], "payment": ["P01"],
        "polonnaruwa": ["T09", "T08"],
        "compare": ctx.get("suggestions", [])[:2],
        "destination": [w["named"]], "discover": [ctx.get("tour")],
        "custom": ["T08", "T10", "T12"], "general": ["T01", "T09", "T05"],
    }.get(action, [])
    if action == "destination":
        place = records[w["named"]]["path"].rsplit("/", 1)[-1].removesuffix(".md")
        ids += [key for key, tour in w["tours"].items() if place in tour["destinations"]][:3]
    if action in {"custom", "general"}:
        trip = ctx.get("custom", {}) if action == "custom" else {}
        destinations = {name.split()[0].lower() for name in trip.get("destinations", [])}
        if destinations:
            related = sorted(w["tours"], key=lambda key: -len(destinations.intersection(w["tours"][key]["destinations"])))
            ids = [key for key in related if destinations.intersection(w["tours"][key]["destinations"])][:3] or ids
        ids = rank(w["tours"], trip, w["events"]) or ids
    w["rows"] = [records[key] for key in ids if key in records]
    if action in {"general", "destination", "custom", "compare"}:
        ctx["suggestions"] = [row["id"] for row in w["rows"] if row["type"] == "tour"]
    w["events"].append({"stage": "retrieval", "sources": [r["id"] for r in w["rows"]]})
    return {}


def quote_route(_):
    w = working.get()
    ctx = w["context"]
    if (w["action"] == "discover" and not w["select"] and ctx.get("tour") in w["tours"]
            and ctx.get("date") and "adults" in ctx and ctx.get("kids", 0) == len(ctx.get("ages", []))):
        return "quote"
    return "compose"


def quote_node(_):
    w = working.get()
    ctx = w["context"]
    before = perf_counter()
    try:
        value = price(ctx["tour"], date.fromisoformat(ctx["date"]), ctx["adults"], ctx.get("ages", []), as_of(), current_rates())
        w["internal"] = value
        w["quote"] = PublicQuote(
            id=uuid4(), source=ctx["tour"], title=w["tours"][ctx["tour"]]["title"],
            date=ctx["date"], adults=ctx["adults"], ages=ctx.get("ages", []),
            **{k: value[k] for k in ("total", "deposit", "balance")},
        )
    except (Unavailable, ValueError) as exc:
        w["reason"] = str(exc) if isinstance(exc, Unavailable) else "invalid_travel_details"
    w["events"].append({"stage": "pricing", "outcome": w.get("reason", "verified"),
                        "snapshot": w.get("internal", {}).get("snapshot"),
                        "ms": round((perf_counter()-before)*1000)})
    return {}


def compose(_):
    w = working.get()
    if "replay" in w:
        return {}
    trace = w.get("trace") or uuid4()
    ctx, rows, action = w["context"], w["rows"], w["action"]
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
        elif row["type"] == "tour":
            sources.append(key)
            components.append(Card(**tour_card(row)))
            if action == "discover":
                heading = next(iter(re.findall(r"^#+ ((?:Day 1\b|Highlights\b)[^\n]*)$", row["body"], re.M)), None)
                if heading and (body := section(row, heading)):
                    components.append(Excerpt(type="ItineraryDay", source=key, heading=heading, text=body))
    if w.get("quote"):
        q = w["quote"]
        components.insert(0, Breakdown(quote=q))
        components.append(Booking(quote=q.id))
        text = "I’ve verified the quote for your travel date and group. You can review the deposit and try the demo booking."
    elif w.get("reason") or action == "custom":
        w["reason"] = w.get("reason", "custom_or_unsupported")
        w["enquiry"] = uuid4()
        text = "A travel specialist will confirm the details. I’ve saved a private enquiry for our team."
        components.insert(0, Notice(reference=w["enquiry"], text="Specialist confirmation required"))
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
    elif action in {"cancellation", "children", "dietary", "payment", "polonnaruwa", "destination"} and sources:
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
    else:
        text = "I’m Mira, your Sri Lanka travel companion. Where would you like your journey to begin?"
    w["turn"] = Turn(trace=trace, text=text, sources=sources, components=components)
    w["events"].append({"stage": "validated_ui", "components": [c.type for c in components]})
    return {}


def persist():
    w = working.get()
    if "replay" in w:
        turn = w["replay"]
    else:
        turn = w["turn"]
        visitor, run = visitor_context.get(), run_context.get()
        w["events"].append({"stage": "persistence", "enquiry": bool(w.get("reason") or w.get("quote"))})
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            previous = conn.execute("SELECT result FROM traces WHERE visitor=? AND run=?", (visitor, run)).fetchone()
            if previous:
                turn = Turn.model_validate_json(previous["result"])
            else:
                active = conn.execute("SELECT context FROM visitors WHERE id=?", (visitor,)).fetchone()
                if not active or active["context"] != w["basis"]:
                    raise ValueError("Session changed during this turn")
                conn.execute("INSERT INTO traces(id, visitor, run, events, result) VALUES(?,?,?,?,?)",
                             (str(turn.trace), visitor, run, encode(w["events"]), turn.model_dump_json()))
                q = w.get("quote")
                if q:
                    conn.execute("INSERT INTO quotes(id, visitor, trace, public, internal) VALUES(?,?,?,?,?)",
                                 (str(q.id), visitor, str(turn.trace), q.model_dump_json(), encode(w["internal"])))
                if q or w.get("reason"):
                    conn.execute("INSERT INTO enquiries(id, trace, quote, trip, reason) VALUES(?,?,?,?,?)",
                                 (str(w.get("enquiry") or uuid4()), str(turn.trace), str(q.id) if q else None,
                                  encode(w["context"].get("custom", {}) if w["action"] == "custom" else w["context"]),
                                  w.get("reason", "verified_quote")))
                conn.execute("UPDATE visitors SET context=? WHERE id=?", (encode(w["context"]), visitor))
    return {"turn": turn.model_dump(mode="json"), "messages": [AIMessage(content=turn.text, id=str(turn.trace))]}


async def save(_):
    result = await asyncio.to_thread(persist)
    message = result["messages"][0]
    await adispatch_custom_event("manually_emit_message", {"message_id": message.id, "message": message.content})
    return result


builder = StateGraph(GraphState)
for name, fn in [("interpret", interpret), ("retrieve", retrieve), ("quote", quote_node),
                 ("compose", compose), ("save", save)]:
    builder.add_node(name, fn)
builder.add_edge(START, "interpret")
builder.add_conditional_edges("interpret", lambda _: "save" if "replay" in working.get() else "retrieve",
                              {"save": "save", "retrieve": "retrieve"})
builder.add_conditional_edges("retrieve", quote_route, {"quote": "quote", "compose": "compose"})
builder.add_edge("quote", "compose")
builder.add_edge("compose", "save")
builder.add_edge("save", END)
graph = builder.compile()
