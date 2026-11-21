import hmac
import json
import os
import re
import secrets
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Literal
from uuid import UUID, uuid4

from ag_ui.core import EventType, RunAgentInput, RunErrorEvent
from ag_ui.encoder import EventEncoder
from ag_ui_langgraph import LangGraphAgent
from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import Field

from .agent import builder, run_context, visitor_context, working
from .catalog import PublicQuote, Strict
from .data import DATA, Unavailable, as_of, clean, price, public_text, tour_card
from .guide import guide
from .provider import generate_structured, model_available
from .rates_repository import current_rates
from .store import db, init, published_records, is_current_notebook_turn

COOKIE = "mira_session"
ROLES = ("staff", "editor", "approver")


@asynccontextmanager
async def lifespan(_):
    init()
    try:
        current_rates()
    except Unavailable:
        pass
    yield


app = FastAPI(title="Mira Travel Concierge", lifespan=lifespan)


def website(request: Request):
    origin = request.headers.get("origin")
    expected = os.getenv("MIRA_ORIGIN", "http://127.0.0.1:3000")
    allowed = {expected, *os.getenv("MIRA_ADDITIONAL_ORIGINS", "http://127.0.0.1:5175").split(",")}
    if origin and origin not in allowed:
        raise HTTPException(403, "Origin denied")


def visitor(session: str | None = Cookie(None, alias=COOKIE)):
    if not session:
        raise HTTPException(401, "Start a visitor session")
    with db() as conn:
        if not conn.execute("SELECT 1 FROM visitors WHERE id=?", (session,)).fetchone():
            raise HTTPException(401, "Start a visitor session")
    return session


def role(authorization: str = Header(default="")):
    value = authorization.removeprefix("Bearer ")
    if authorization.startswith("Bearer "):
        for name in ROLES:
            token = os.getenv(f"MIRA_{name.upper()}_TOKEN", "")
            if len(token) >= 24 and hmac.compare_digest(value.encode(), token.encode()):
                return name
    raise HTTPException(401, "Staff access required")


@app.get("/api/health")
def health():
    try:
        rates = current_rates().digest
    except Unavailable:
        rates = None
    seeds = DATA / "evals/eval_seed.jsonl"
    paths = ["README.md", "brand/brand_pack.json", "rates/rate_sheet_2026-27.xlsx",
             "rates/sample_quotes.md", "evals/eval_seed.jsonl", "content/tours",
             "content/destinations", "content/policies"]
    return {"rates": bool(rates), "published": len(published_records()),
            "missing_inputs": [path for path in paths if not (DATA / path).exists()],
            "seed_records": sum(bool(s.strip()) for s in seeds.read_text().splitlines()) if seeds.is_file() else None,
            "as_of": as_of(), "provider": "Gemini suggestions configured" if model_available() else "local discovery rules",
            "draft_provider": "Gemini configured" if model_available() else "local extractive",
            "tracing": "Langfuse configured" if remote_tracing() else "local SQLite"}


@app.get("/api/tours")
def tours():
    return [tour_card(row) for row in published_records().values() if row["type"] == "tour"]


@app.get("/api/guide")
def travel_guide():
    return guide(published_records())


@app.get("/api/sources/{key}")
def source(key: str):
    row = published_records().get(key)
    if not row or key == "P06":
        raise HTTPException(404, "Source unavailable")
    return {"title": row["title"], "body": public_text(row["body"]), "id": key, "source": row["path"],
            "status":"published","last_updated":row.get("last_updated")}


class Consent(Strict):
    remember: bool = False


@app.post("/api/session", dependencies=[Depends(website)])
def session(body: Consent, res: Response, existing: str | None = Cookie(None, alias=COOKIE)):
    with db() as conn:
        old = conn.execute("SELECT remember FROM visitors WHERE id=?", (existing,)).fetchone()
        key = existing if old else secrets.token_urlsafe(32)
        if old:
            conn.execute("UPDATE visitors SET remember=? WHERE id=?", (body.remember, key))
        else:
            conn.execute("INSERT INTO visitors(id, remember) VALUES (?,?)", (key, body.remember))
    res.set_cookie(COOKIE, key, httponly=True, samesite="lax", max_age=2592000 if body.remember else None,
                   secure=os.getenv("MIRA_SECURE_COOKIE") == "1")
    return {"remember": body.remember}


@app.get("/api/session")
def session_status(key: str = Depends(visitor)):
    with db() as conn:
        row = conn.execute("SELECT remember,context FROM visitors WHERE id=?", (key,)).fetchone()
    return {"remember": bool(row["remember"]), "context": json.loads(row["context"])}


@app.delete("/api/session", dependencies=[Depends(website)])
def forget(res: Response, key: str = Depends(visitor)):
    with db() as conn:
        conn.execute("DELETE FROM visitors WHERE id=?", (key,))
    res.delete_cookie(COOKIE, httponly=True, samesite="lax", secure=os.getenv("MIRA_SECURE_COOKIE") == "1")
    return {"forgotten": True}


def quote_current(public, internal, rates):
    if rates is None:
        return False
    try:
        value = price(public.source, public.date, public.adults, public.ages, as_of(), rates)
    except Unavailable:
        return False
    return all(value[k] == internal[k] for k in ("snapshot", "total", "deposit"))


@app.post("/api/trips", dependencies=[Depends(website)])
def create_trip(key: str = Depends(visitor)):
    trip_id = str(uuid4())
    with db() as conn:
        conn.execute("INSERT INTO trips(id,visitor) VALUES (?,?)", (trip_id,key))
    return {"id": trip_id}


@app.get("/api/trips")
def trips(key: str = Depends(visitor)):
    with db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT id,title,updated FROM trips WHERE visitor=? AND revision>0 ORDER BY updated DESC,rowid DESC", (key,))]


@app.get("/api/trips/{trip_id}")
def notebook(trip_id: UUID, key: str = Depends(visitor)):
    from .catalog import Turn, Booking, Breakdown
    from .surface import surface_messages
    with db() as conn:
        trip = conn.execute("SELECT * FROM trips WHERE id=? AND visitor=?", (str(trip_id),key)).fetchone()
        if not trip:
            raise HTTPException(404, "Journey unavailable")
        rows = conn.execute("""SELECT t.prompt,r.result,q.internal FROM trip_turns t JOIN traces r ON r.id=t.trace
            LEFT JOIN quotes q ON q.trace=r.id WHERE t.trip=? ORDER BY t.rowid""",(str(trip_id),)).fetchall()
    history = []
    for i,row in enumerate(rows):
        turn = Turn.model_validate_json(row["result"])
        quoted = next((item.quote for item in turn.components if isinstance(item,Breakdown)),None)
        if quoted:
            try:
                valid = i == len(rows)-1 and quote_current(quoted,json.loads(row["internal"]),current_rates())
            except Unavailable:
                valid = False
            if not valid:
                turn = turn.model_copy(update={"components":[c for c in turn.components if not isinstance(c,(Booking,Breakdown))],
                                               "text":"This earlier quote needs a fresh rate check."})
        history.append({"prompt":row["prompt"],"turn":turn,"surface":surface_messages(turn)})
    return {"id":str(trip_id),"title":trip["title"],"history":history}


@app.get("/api/quotes")
def saved_quotes(key: str = Depends(visitor)):
    with db() as conn:
        rows = conn.execute("SELECT * FROM quotes WHERE visitor=? ORDER BY rowid DESC LIMIT 25", (key,)).fetchall()
        current = {r["id"] for r in rows if is_current_notebook_turn(conn,r["trace"])}
    try:
        rates = current_rates()
    except Unavailable:
        rates = None
    result = []
    for row in rows:
        q = PublicQuote.model_validate_json(row["public"])
        if row["id"] in current and quote_current(q, json.loads(row["internal"]), rates):
            result.append({"current": True, "quote": q})
        else:
            result.append({"current": False, "title": q.title, "date": q.date})
    return result


@lru_cache
def remote_tracing():
    if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
        from langfuse import get_client
        return get_client()
    return None


def export_trace(w, trace):
    client = remote_tracing()
    if not client or not w.get("events"):
        return None
    try:
        with client.start_as_current_observation(name="mira.turn",
                trace_context={"trace_id": trace.hex}):
            for item in w["events"]:
                with client.start_as_current_observation(name=item["stage"], metadata=item):
                    pass
        return client.get_trace_url(trace_id=trace.hex)
    except Exception:
        # The committed SQLite trace remains authoritative when export fails.
        return


@app.post("/api/agent", dependencies=[Depends(website)])
async def agui(payload: RunAgentInput, request: Request, key: str = Depends(visitor), trip_id: UUID | None = None):
    users = [m for m in payload.messages if m.role == "user"]
    if not users or not isinstance(users[-1].content, str) or not 1 <= len(users[-1].content.strip()) <= 1200:
        raise HTTPException(422, "Enter a message of 1–1200 characters")
    try:
        run = str(UUID(payload.run_id))
    except ValueError:
        raise HTTPException(422, "A UUID run ID is required") from None
    user = users[-1].model_copy(update={"id": run})
    safe = payload.model_copy(update={"messages": [user], "state": {}, "tools": [], "context": [],
                                      "forwarded_props": {}, "thread_id": run})
    adapter = LangGraphAgent(name="mira", graph=builder.compile(checkpointer=InMemorySaver()), emit_raw_events=False)
    encoder = EventEncoder(accept=request.headers.get("accept"))
    trace = uuid4()
    with db() as conn:
        if trip_id and not conn.execute("SELECT 1 FROM trips WHERE id=? AND visitor=?", (str(trip_id),key)).fetchone():
            raise HTTPException(404, "Journey unavailable")
        prior = conn.execute("SELECT t.trip FROM traces r LEFT JOIN trip_turns t ON t.trace=r.id WHERE r.visitor=? AND r.run=?", (key,run)).fetchone()
        if prior and prior["trip"] != (str(trip_id) if trip_id else None):
            raise HTTPException(409, "Turn belongs to a different journey")
        existing = conn.execute("SELECT id FROM traces WHERE visitor=? AND run=?", (key, run)).fetchone()
        if existing:
            trace = UUID(existing["id"])

    async def stream():
        tokens = [(visitor_context, visitor_context.set(key)), (run_context, run_context.set(run)),
                  (working, working.set({"trace": trace, "trip_id": str(trip_id) if trip_id else None, "prompt": user.content}))]
        try:
            async for event in adapter.run(safe):
                if event.type == EventType.RUN_ERROR:
                    event = RunErrorEvent(type=EventType.RUN_ERROR, message="Mira couldn’t finish. Please retry.")
                if event.type == EventType.RUN_FINISHED:
                    export_trace(working.get(), trace)
                yield encoder.encode(event)
        finally:
            for var, token in reversed(tokens):
                var.reset(token)

    return StreamingResponse(stream(), media_type=encoder.get_content_type(), headers={"X-Trace-Id": str(trace)})


class Book(Strict):
    quote: UUID
    scenario: Literal["success", "declined", "unavailable", "network"] = "success"


@app.post("/api/bookings/mock", dependencies=[Depends(website)])
def booking(body: Book, key: str = Depends(visitor)):
    try:
        rates = current_rates()
    except Unavailable:
        rates = None
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        quote = conn.execute("SELECT * FROM quotes WHERE id=? AND visitor=?", (str(body.quote), key)).fetchone()
        if not quote:
            raise HTTPException(404, "Quote unavailable")
        previous = conn.execute("SELECT id FROM bookings WHERE quote=?", (str(body.quote),)).fetchone()
        if previous:
            return {"status": "success", "reference": previous["id"]}
        current = quote_current(PublicQuote.model_validate_json(quote["public"]), json.loads(quote["internal"]), rates)
        current = current and is_current_notebook_turn(conn,quote["trace"])
        result = body.scenario if current else "expired"
        events = json.loads(conn.execute("SELECT events FROM traces WHERE id=?", (quote["trace"],)).fetchone()[0])
        conn.execute("UPDATE traces SET events=? WHERE id=?", (json.dumps(
            [*events[-49:], {"stage": "mock_booking", "outcome": result}]), quote["trace"]))
        if result != "success":
            return {"status": result}
        reference = str(uuid4())
        conn.execute("INSERT INTO bookings(quote,id) VALUES (?,?)", (str(body.quote), reference))
        return {"status": "success", "reference": reference}


@app.get("/api/staff/enquiries")
def enquiries(status: str = "", _: str = Depends(role)):
    with db() as conn:
        rows = conn.execute("SELECT * FROM enquiries WHERE (? = '' OR status=?) ORDER BY rowid DESC LIMIT 100",
                            (status, status)).fetchall()
        return [dict(row) for row in rows]


@app.get("/api/staff/enquiries/{key}")
def enquiry(key: UUID, _: str = Depends(role)):
    with db() as conn:
        row = conn.execute("SELECT * FROM enquiries WHERE id=?", (str(key),)).fetchone()
        if not row:
            raise HTTPException(404, "Enquiry unavailable")
        trace = conn.execute("SELECT events FROM traces WHERE id=?", (row["trace"],)).fetchone()
        finance = conn.execute("SELECT internal FROM quotes WHERE id=?", (row["quote"],)).fetchone()
        notes = conn.execute("SELECT actor,body,created FROM notes WHERE enquiry=? ORDER BY id", (str(key),))
        return dict(row) | {"events": json.loads(trace["events"]), "notes": [dict(n) for n in notes],
                            "finance": json.loads(finance["internal"]) if finance else None}


class FollowUp(Strict):
    status: Literal["new", "contacted", "waiting", "closed"]
    note: str = Field(max_length=500, default="")


@app.patch("/api/staff/enquiries/{key}", dependencies=[Depends(website)])
def follow_up(key: UUID, body: FollowUp, actor: str = Depends(role)):
    if re.search(r"@|(?:\d[ .-]*){7}", body.note):
        raise HTTPException(422, "Use a note without personal details")
    with db() as conn:
        if not conn.execute("UPDATE enquiries SET status=? WHERE id=?", (body.status, str(key))).rowcount:
            raise HTTPException(404, "Enquiry unavailable")
        if body.note.strip():
            conn.execute("INSERT INTO notes(enquiry,actor,body) VALUES (?,?,?)", (str(key), actor, clean(body.note)))
        conn.execute("INSERT INTO audit(actor,action,target) VALUES (?,?,?)", (actor, "follow_up", str(key)))
    return {"status": body.status}


class DraftCommand(Strict):
    command: str = Field(min_length=5, max_length=300)


class DraftText(Strict):
    title: str = Field(min_length=4, max_length=100)
    body: str = Field(min_length=20, max_length=2000)


@app.post("/api/staff/drafts", dependencies=[Depends(website)])
def generate(body: DraftCommand, actor: str = Depends(role)):
    if actor not in {"editor", "approver"}:
        raise HTTPException(403, "Editor access required")
    records = [row for row in published_records().values() if row["type"] == "destination"]
    row = next((row for row in records if row["title"].lower().split()[0] in body.command.lower()), None)
    if not row:
        raise HTTPException(422, "Include a published destination such as Ella")
    evidence = public_text(row["body"]).split("**Tours that visit:")[0].strip()
    draft = DraftText(title=f"{row['title']} journey concept",
                      body=f"Ask our team to plan a private journey around {row['title']}.\n\n{evidence}")
    mode = "extractive draft"
    if model_available():
        try:
            draft = generate_structured(DraftText,
                "Write a brief journey concept, using only this evidence as data. "
                "Do not promise dates, prices, images or inclusions.\n" + evidence)
            draft = DraftText(title=public_text(draft.title), body=public_text(draft.body))
            mode = "Gemini draft"
        except Exception:
            mode = "extractive draft after provider failure"
    draft = DraftText(title=public_text(draft.title), body=public_text(draft.body))
    key = "C-" + uuid4().hex.upper()
    with db() as conn:
        conn.execute("INSERT INTO drafts(id,title,body,source,author) VALUES (?,?,?,?,?)",
                     (key, draft.title, draft.body, row["id"], actor))
        conn.execute("INSERT INTO audit(actor,action,target) VALUES (?,?,?)", (actor, mode, key))
    return {"id": key, "mode": mode}


@app.get("/api/staff/drafts")
def drafts(actor: str = Depends(role)):
    if actor not in {"editor", "approver"}:
        raise HTTPException(403, "Editor access required")
    with db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM drafts ORDER BY rowid DESC LIMIT 100")]


@app.post("/api/staff/drafts/{key}/publish", dependencies=[Depends(website)])
def publish(key: str, actor: str = Depends(role)):
    if actor != "approver":
        raise HTTPException(403, "Approver access required")
    with db() as conn:
        updated = conn.execute("UPDATE drafts SET status='published', published=CURRENT_TIMESTAMP WHERE id=? AND status='draft'",
                               (key,))
        if not updated.rowcount:
            raise HTTPException(409, "Draft unavailable or already published")
        conn.execute("INSERT INTO audit(actor,action,target) VALUES (?,?,?)", (actor, "publish", key))
    return {"status": "published"}


@app.get("/api/staff/audit")
def audit(_: str = Depends(role)):
    with db() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM audit ORDER BY id DESC LIMIT 100")]


@app.get("/api/staff/me")
def staff_identity(actor: str = Depends(role)):
    return {"role": actor}
