import asyncio
import hmac
import logging
import json
import os
import re
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from functools import lru_cache
from time import perf_counter
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
from .auth import (
    AUTH_COOKIE,
    LoginInput,
    PasswordChangeInput,
    ProfileUpdateInput,
    RegisterInput,
    UserProfile,
    UserRoleUpdateInput,
    audit_log,
    bootstrap_admin,
    check_brute_force,
    clear_auth_cookie,
    clear_failed_login,
    create_user_session,
    get_current_user,
    get_current_user_optional,
    hash_password,
    record_failed_login,
    require_role,
    set_auth_cookie,
    verify_password,
)
from .catalog import PublicQuote, Strict
from .data import DATA, Unavailable, as_of, clean, price, public_text, tour_card
from .guide import guide
from .observability import RequestLogging, elapsed, event as log_event, is_sensitive_key, request_id, sanitize_value, trace_id
from .provider import generate_structured, model_available
from .rates_repository import current_rates
from . import store
from .store import db, init, published_records, is_current_notebook_turn

COOKIE = "mira_session"
ROLES = ("staff", "editor", "approver")


@asynccontextmanager
async def lifespan(_):
    init()
    bootstrap_admin()
    try:
        current_rates()
    except Unavailable:
        log_event("PRICING", "rates.unavailable", level=logging.WARNING)
    yield


app = FastAPI(title="Mira Travel Concierge", lifespan=lifespan)
app.add_middleware(RequestLogging)


def website(request: Request):
    origin = request.headers.get("origin")
    expected = os.getenv("MIRA_ORIGIN", "http://127.0.0.1:3000")
    allowed = {expected, *os.getenv("MIRA_ADDITIONAL_ORIGINS", "http://127.0.0.1:5175").split(",")}
    if origin and origin not in allowed:
        raise HTTPException(403, "Origin denied")


def visitor(session: str | None = Cookie(None, alias=COOKIE), user: UserProfile | None = Depends(get_current_user_optional)):
    if not session:
        raise HTTPException(401, "Start a visitor session")
    with db() as conn:
        owner = conn.execute("SELECT user_id FROM visitors WHERE id=?", (session,)).fetchone()
        if not owner or (owner["user_id"] and (not user or user.id != owner["user_id"])):
            raise HTTPException(401, "Start a visitor session")
    return session


def role(
    authorization: str = Header(default=""),
    auth_token: str | None = Cookie(None, alias=AUTH_COOKIE),
):
    # 1. Check HttpOnly cookie for authenticated staff/approver/admin
    if auth_token:
        with db() as conn:
            row = conn.execute(
                """SELECT u.id, u.role, u.status, s.revoked, s.expires_at
                   FROM user_sessions s
                   JOIN users u ON u.id = s.user_id
                   WHERE s.id = ?""",
                (auth_token,),
            ).fetchone()
            if row and row["revoked"] == 0:
                try:
                    expires_dt = datetime.fromisoformat(row["expires_at"])
                    if expires_dt >= datetime.now(timezone.utc):
                        if row["status"] != "active":
                            raise HTTPException(403, "Account is deactivated.")
                        if row["role"] in ("admin", "approver", "staff"):
                            return row["role"]
                        else:
                            raise HTTPException(403, "Staff access required")
                except HTTPException:
                    raise
                except Exception:
                    pass

    # 2. Check Bearer token (for legacy staff tokens)
    value = authorization.removeprefix("Bearer ")
    if authorization.startswith("Bearer "):
        for name in ("admin", "approver", "editor", "staff"):
            token = os.getenv(f"MIRA_{name.upper()}_TOKEN", "")
            if len(token) >= 24 and hmac.compare_digest(value.encode(), token.encode()):
                return name
    raise HTTPException(401, "Staff access required")


_BUILD_REVISION = os.getenv("MIRA_BUILD_REV", "rc-2026-11-25")


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
    return {"rates": bool(rates), "published": len(published_records()), "revision": _BUILD_REVISION,
            "missing_inputs": [path for path in paths if not (DATA / path).exists()],
            "seed_records": sum(bool(s.strip()) for s in seeds.read_text().splitlines()) if seeds.is_file() else None,
            "as_of": as_of(), "provider": "Gemini suggestions configured" if model_available() else "local discovery rules",
            "draft_provider": "Gemini configured" if model_available() else "local extractive",
            "tracing": "Langfuse configured" if remote_tracing() else "local SQLite",
            "database": store.DB.name}


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
def session(body: Consent, res: Response, existing: str | None = Cookie(None, alias=COOKIE), auth_user: UserProfile | None = Depends(get_current_user_optional)):
    with db() as conn:
        old = conn.execute("SELECT remember,user_id FROM visitors WHERE id=?", (existing,)).fetchone()
        if old and old["user_id"] and (not auth_user or auth_user.id != old["user_id"]):
            old = None
        key = existing if old else secrets.token_urlsafe(32)
        uid = auth_user.id if auth_user else None
        if old:
            conn.execute("UPDATE visitors SET remember=?, user_id=COALESCE(user_id, ?) WHERE id=?", (body.remember, uid, key))
        else:
            conn.execute("INSERT INTO visitors(id, remember, user_id) VALUES (?,?,?)", (key, body.remember, uid))
    res.set_cookie(COOKIE, key, httponly=True, samesite="lax", max_age=2592000 if body.remember else None,
                   secure=os.getenv("MIRA_SECURE_COOKIE") == "1")
    return {"remember": body.remember}


@app.get("/api/session")
def session_status(key: str = Depends(visitor), auth_user: UserProfile | None = Depends(get_current_user_optional)):
    with db() as conn:
        row = conn.execute("SELECT remember,context,user_id FROM visitors WHERE id=?", (key,)).fetchone()
        if not row:
            raise HTTPException(401, "Start a visitor session")
        if row["user_id"] and auth_user and row["user_id"] != auth_user.id:
            raise HTTPException(403, "Access to another user's session is prohibited")
    context = json.loads(row["context"])
    if auth_user and auth_user.preferences:
        for k, v in auth_user.preferences.items():
            if k not in context:
                context[k] = v
    return {"remember": bool(row["remember"]), "context": context}


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
def create_trip(key: str = Depends(visitor), auth_user: UserProfile | None = Depends(get_current_user_optional)):
    trip_id = str(uuid4())
    with db() as conn:
        conn.execute("INSERT INTO trips(id,visitor) VALUES (?,?)", (trip_id,key))
        if auth_user:
            conn.execute("UPDATE visitors SET user_id=? WHERE id=?", (auth_user.id, key))
    return {"id": trip_id}


@app.get("/api/trips")
def trips(key: str = Depends(visitor), auth_user: UserProfile | None = Depends(get_current_user_optional)):
    with db() as conn:
        if auth_user:
            return [dict(r) for r in conn.execute(
                """SELECT id,title,updated FROM trips 
                   WHERE (visitor=? OR visitor IN (SELECT id FROM visitors WHERE user_id=?)) AND revision>0 
                   ORDER BY updated DESC,rowid DESC""", (key, auth_user.id))]
        else:
            return [dict(r) for r in conn.execute(
                "SELECT id,title,updated FROM trips WHERE visitor=? AND revision>0 ORDER BY updated DESC,rowid DESC", (key,))]


@app.get("/api/trips/{trip_id}")
def notebook(trip_id: UUID, key: str = Depends(visitor), auth_user: UserProfile | None = Depends(get_current_user_optional)):
    from .catalog import Turn, Booking, Breakdown
    from .surface import surface_messages
    with db() as conn:
        if auth_user:
            trip = conn.execute(
                """SELECT * FROM trips 
                   WHERE id=? AND (visitor=? OR visitor IN (SELECT id FROM visitors WHERE user_id=?))""",
                (str(trip_id), key, auth_user.id),
            ).fetchone()
        else:
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
def saved_quotes(key: str = Depends(visitor), auth_user: UserProfile | None = Depends(get_current_user_optional)):
    with db() as conn:
        if auth_user:
            rows = conn.execute(
                """SELECT * FROM quotes 
                   WHERE visitor=? OR visitor IN (SELECT id FROM visitors WHERE user_id=?)
                   ORDER BY rowid DESC LIMIT 25""",
                (key, auth_user.id),
            ).fetchall()
        else:
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
    if not w.get("events"):
        return None
    try:
        client = remote_tracing()
        if not client:
            return None
        req_id = request_id.get()
        meta = {"request_id": req_id} if req_id else {}
        with client.start_as_current_observation(name="mira.turn",
                trace_context={"trace_id": trace.hex}, metadata=meta):
            for item in w["events"]:
                clean_item = {k: sanitize_value(v) for k, v in item.items() if not is_sensitive_key(k)}
                with client.start_as_current_observation(name=item.get("stage", "stage"), metadata=clean_item):
                    pass
        if hasattr(client, "flush"):
            client.flush()
        log_event("TRACE", "trace.queued", destination="langfuse")
    except Exception:
        log_event("TRACE", "trace.export_failed", level=logging.WARNING, exception=True)
    return None


@app.post("/api/agent", dependencies=[Depends(website)])
async def agui(payload: RunAgentInput, request: Request, key: str = Depends(visitor), trip_id: UUID | None = None,
               auth_user: UserProfile | None = Depends(get_current_user_optional)):
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
        if trip_id:
            if auth_user:
                trip_found = conn.execute(
                    """SELECT 1 FROM trips 
                       WHERE id=? AND (visitor=? OR visitor IN (SELECT id FROM visitors WHERE user_id=?))""",
                    (str(trip_id), key, auth_user.id),
                ).fetchone()
            else:
                trip_found = conn.execute("SELECT 1 FROM trips WHERE id=? AND visitor=?", (str(trip_id), key)).fetchone()
            if not trip_found:
                raise HTTPException(404, "Journey unavailable")
        prior = conn.execute("SELECT t.trip FROM traces r LEFT JOIN trip_turns t ON t.trace=r.id WHERE r.visitor=? AND r.run=?", (key,run)).fetchone()
        if prior and prior["trip"] != (str(trip_id) if trip_id else None):
            raise HTTPException(409, "Turn belongs to a different journey")
        existing = conn.execute("SELECT id FROM traces WHERE visitor=? AND run=?", (key, run)).fetchone()
        if existing:
            trace = UUID(existing["id"])

    async def stream():
        start = perf_counter()
        outcome = "interrupted"
        tokens = [(visitor_context, visitor_context.set(key)), (run_context, run_context.set(run)),
                  (trace_id, trace_id.set(str(trace))),
                  (working, working.set({"trace": trace, "trip_id": str(trip_id) if trip_id else None, "prompt": user.content}))]
        log_event("AGENT", "workflow.started", notebook=trip_id is not None)
        try:
            async for event in adapter.run(safe):
                if event.type == EventType.RUN_ERROR:
                    outcome = "failed"
                    log_event("ERROR", "workflow.run_error", level=logging.ERROR)
                    event = RunErrorEvent(type=EventType.RUN_ERROR, message="Mira couldn’t finish. Please retry.")
                if event.type == EventType.RUN_FINISHED:
                    if outcome != "failed":
                        outcome = "completed"
                        if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
                            await asyncio.to_thread(export_trace, working.get(), trace)
                yield encoder.encode(event)
        finally:
            if outcome != "completed":
                stages = [*working.get().get("events", []), {"stage":"stream", "outcome":outcome, "ms":elapsed(start)}]
                try:
                    with db() as conn:
                        conn.execute("INSERT OR IGNORE INTO failed_traces(id,events) VALUES(?,?)",
                                     (str(trace), json.dumps(stages)))
                    if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
                        await asyncio.to_thread(export_trace, {"events": stages}, trace)
                except Exception:
                    log_event("ERROR", "trace.persistence_failed", level=logging.ERROR)
            log_event("AGENT", "workflow.finished", outcome=outcome, duration_ms=elapsed(start))
            for var, token in reversed(tokens):
                var.reset(token)

    return StreamingResponse(stream(), media_type=encoder.get_content_type(), headers={"X-Trace-Id": str(trace)})


class Book(Strict):
    quote: UUID
    scenario: Literal["success", "declined", "unavailable", "network", "expired"] = "success"


@app.post("/api/bookings/mock", dependencies=[Depends(website)])
def booking(body: Book, key: str = Depends(visitor), auth_user: UserProfile | None = Depends(get_current_user_optional)):
    try:
        rates = current_rates()
    except Unavailable:
        rates = None
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        quote = conn.execute(
            """SELECT * FROM quotes 
               WHERE id=? AND (visitor=? OR visitor IN (SELECT id FROM visitors WHERE user_id=?))""",
            (str(body.quote), key, auth_user.id if auth_user else ""),
        ).fetchone()
        if not quote:
            raise HTTPException(404, "Quote unavailable")
        previous = conn.execute("SELECT id FROM bookings WHERE quote=?", (str(body.quote),)).fetchone()
        if previous and body.scenario == "success":
            return {"status": "success", "reference": previous["id"]}
        current = quote_current(PublicQuote.model_validate_json(quote["public"]), json.loads(quote["internal"]), rates)
        current = current and is_current_notebook_turn(conn, quote["trace"])
        result = body.scenario if (current or body.scenario == "expired") else "expired"
        events = json.loads(conn.execute("SELECT events FROM traces WHERE id=?", (quote["trace"],)).fetchone()[0])
        conn.execute("UPDATE traces SET events=? WHERE id=?", (json.dumps(
            [*events[-49:], {"stage": "mock_booking", "outcome": result}]), quote["trace"]))
        if result != "success":
            resp = {"status": result}
            if previous:
                resp["confirmed_reference"] = previous["id"]
            return resp
        reference = str(uuid4())
        conn.execute("INSERT INTO bookings(quote,id) VALUES (?,?)", (str(body.quote), reference))
        return {"status": "success", "reference": reference}


# ==============================================================================
# AUTHENTICATION & TRAVELLER PROFILE ENDPOINTS
# ==============================================================================

@app.post("/api/auth/register", dependencies=[Depends(website)])
def register(
    body: RegisterInput,
    response: Response,
    request: Request,
    existing_visitor: str | None = Cookie(None, alias=COOKIE),
):
    email = body.email.strip().lower()
    with db() as conn:
        existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            raise HTTPException(400, "An account with this email already exists.")

        user_id = str(uuid4())
        hashed = hash_password(body.password)
        conn.execute(
            """INSERT INTO users(id, email, password_hash, full_name, role, status, phone, preferences)
               VALUES (?, ?, ?, ?, 'traveller', 'active', ?, ?)""",
            (user_id, email, hashed, body.full_name.strip(), body.phone.strip(), json.dumps(body.preferences)),
        )

        ip = request.client.host if request.client else ""
        ua = request.headers.get("user-agent", "")
        token, _ = create_user_session(conn, user_id, existing_visitor, remember=True, ip=ip, ua=ua)
        audit_log(conn, user_id, "register", user_id)

    set_auth_cookie(response, token, remember=True)
    return UserProfile(
        id=user_id,
        email=email,
        full_name=body.full_name.strip(),
        role="traveller",
        status="active",
        phone=body.phone.strip(),
        preferences=body.preferences,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@app.post("/api/auth/login", dependencies=[Depends(website)])
def login(
    body: LoginInput,
    response: Response,
    request: Request,
    existing_visitor: str | None = Cookie(None, alias=COOKIE),
):
    email = body.email.strip().lower()
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")

    with db() as conn:
        check_brute_force(conn, email)
        if ip:
            check_brute_force(conn, ip)

        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if not user or not verify_password(body.password, user["password_hash"]):
            record_failed_login(conn, email)
            if ip:
                record_failed_login(conn, ip)
            audit_log(conn, email, "login_failed", "auth", outcome="denied")
            raise HTTPException(401, "Invalid email or password.")

        if user["status"] != "active":
            raise HTTPException(403, "Account is deactivated.")

        clear_failed_login(conn, email)
        if ip:
            clear_failed_login(conn, ip)

        token, _ = create_user_session(conn, user["id"], existing_visitor, remember=body.remember, ip=ip, ua=ua)
        audit_log(conn, user["id"], "login", user["id"])

    set_auth_cookie(response, token, remember=body.remember)
    prefs = json.loads(user["preferences"]) if user["preferences"] else {}
    return UserProfile(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
        status=user["status"],
        phone=user["phone"] or "",
        preferences=prefs,
        created_at=user["created_at"],
    )


@app.post("/api/auth/logout", dependencies=[Depends(website)])
def logout(
    response: Response,
    auth_token: str | None = Cookie(None, alias=AUTH_COOKIE),
    current_user: UserProfile = Depends(get_current_user),
):
    if auth_token:
        with db() as conn:
            conn.execute("UPDATE user_sessions SET revoked=1 WHERE id=?", (auth_token,))
            audit_log(conn, current_user.id, "logout", current_user.id)
    clear_auth_cookie(response)
    response.delete_cookie(COOKIE, path="/")
    return {"logged_out": True}


@app.get("/api/auth/me")
def me(current_user: UserProfile = Depends(get_current_user)):
    return current_user


@app.patch("/api/auth/profile", dependencies=[Depends(website)])
def update_profile(
    body: ProfileUpdateInput,
    current_user: UserProfile = Depends(get_current_user),
):
    with db() as conn:
        updates = []
        params = []
        full_name = current_user.full_name
        phone = current_user.phone
        preferences = current_user.preferences

        if body.full_name is not None:
            full_name = body.full_name.strip()
            updates.append("full_name=?")
            params.append(full_name)
        if body.phone is not None:
            phone = body.phone.strip()
            updates.append("phone=?")
            params.append(phone)
        if body.preferences is not None:
            preferences = body.preferences
            updates.append("preferences=?")
            params.append(json.dumps(preferences))

        if updates:
            updates.append("updated_at=CURRENT_TIMESTAMP")
            params.append(current_user.id)
            conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id=?", params)
            audit_log(conn, current_user.id, "profile_update", current_user.id)

    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        full_name=full_name,
        role=current_user.role,
        status=current_user.status,
        phone=phone,
        preferences=preferences,
        created_at=current_user.created_at,
    )


@app.post("/api/auth/password", dependencies=[Depends(website)])
def change_password(
    body: PasswordChangeInput,
    current_user: UserProfile = Depends(get_current_user),
    auth_token: str | None = Cookie(None, alias=AUTH_COOKIE),
):
    with db() as conn:
        user = conn.execute("SELECT password_hash FROM users WHERE id=?", (current_user.id,)).fetchone()
        if not user or not verify_password(body.current_password, user["password_hash"]):
            raise HTTPException(400, "Current password does not match.")

        hashed = hash_password(body.new_password)
        conn.execute("UPDATE users SET password_hash=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (hashed, current_user.id))
        if auth_token:
            conn.execute("UPDATE user_sessions SET revoked=1 WHERE user_id=? AND id != ?", (current_user.id, auth_token))
        audit_log(conn, current_user.id, "password_change", current_user.id)

    return {"success": True}


_REASON_LABELS = {
    "verified_quote": "Verified quote saved",
    "tour_rate": "Tour rate requires specialist confirmation",
    "hotel_rate_missing_or_ambiguous": "Hotel seasonal rate requires specialist confirmation",
    "missing_amount": "Rate sheet amount requires specialist confirmation",
    "date_or_fx_expired": "Travel date or FX window outside automated rate sheet",
    "custom_or_unsupported": "Custom itinerary requires specialist confirmation",
    "conflicting_tour_scope": "Published tour scope requires specialist confirmation",
    "draft_tour_unsupported": "Draft package requires custom specialist proposal",
    "accommodation_confirmation": "Standalone hotel rate requires specialist confirmation",
    "group_size": "Group size exceeds automated vehicle tariff",
    "not_published": "Unpublished tour requires specialist confirmation",
}


def _utc_iso(ts: str | None) -> str | None:
    if not ts:
        return None
    s = str(ts).strip()
    if "T" in s and (s.endswith("Z") or "+" in s):
        return s
    return s.replace(" ", "T") + "Z"


def _enrich_enquiry(conn, row, records: dict, include_traveller: bool = False) -> dict:
    data = dict(row)
    trip_raw = data.get("trip") or "{}"
    try:
        trip_data = json.loads(trip_raw) if isinstance(trip_raw, str) else (trip_raw or {})
    except (ValueError, TypeError):
        trip_data = {}
    if not isinstance(trip_data, dict):
        trip_data = {}

    tour_id = trip_data.get("tour")
    tour_name = (
        records[tour_id]["title"]
        if tour_id and tour_id in records
        else ("Custom journey" if data.get("reason") == "custom_or_unsupported" else "General Sri Lanka enquiry")
    )
    adults = trip_data.get("adults") or trip_data.get("party")
    ages = trip_data.get("ages") or []
    kids = trip_data.get("kids")
    children_count = kids if isinstance(kids, int) and kids >= 0 else len(ages)

    reason = data.get("reason") or ""
    human_reason = _REASON_LABELS.get(reason, reason.replace("_", " ").capitalize() if reason else "Specialist review")
    if reason == "verified_quote":
        category = "Verified Quote"
    elif reason == "custom_or_unsupported":
        category = "Custom Itinerary"
    elif tour_id:
        category = "Rate Confirmation"
    else:
        category = "Published Tour Enquiry"

    quoted_total_usd = None
    quoted_deposit_usd = None
    mock_booking_status = None
    mock_booking_reference = None
    if data.get("quote"):
        q_row = conn.execute("SELECT public FROM quotes WHERE id=?", (data["quote"],)).fetchone()
        if q_row:
            try:
                pq = json.loads(q_row["public"])
                quoted_total_usd = pq.get("total")
                quoted_deposit_usd = pq.get("deposit")
            except (ValueError, TypeError):
                pass
        b_row = conn.execute("SELECT id, created FROM bookings WHERE quote=?", (data["quote"],)).fetchone()
        if b_row:
            mock_booking_status = "confirmed"
            mock_booking_reference = b_row["id"]

    trip_row = conn.execute("SELECT trip FROM trip_turns WHERE trace=?", (data.get("trace"),)).fetchone()
    note_row = conn.execute("SELECT MAX(created) AS last_note FROM notes WHERE enquiry=?", (data["id"],)).fetchone()
    candidates = [t for t in (data.get("updated_at"), data.get("created"), note_row["last_note"] if note_row else None) if t]
    last_activity = max(candidates) if candidates else data.get("created")

    ref = data.get("reference") or f"ENQ-{(data.get('created') or '2026')[:4]}-{data['id'].replace('-', '')[:8].upper()}"

    enriched = {
        **data,
        "reference": ref,
        "created": _utc_iso(data.get("created")),
        "updated_at": _utc_iso(data.get("updated_at") or data.get("created")),
        "last_activity_at": _utc_iso(last_activity),
        "follow_up_date": data.get("follow_up_date"),
        "trip_id": trip_row["trip"] if trip_row else None,
        "tour_id": tour_id,
        "tour_name": tour_name,
        "travel_date": trip_data.get("date"),
        "adults": adults,
        "children_count": children_count,
        "child_ages": ages,
        "enquiry_category": category,
        "human_reason": human_reason,
        "quotation_status": "verified" if data.get("quote") else "specialist_required",
        "quoted_total_usd": quoted_total_usd,
        "quoted_deposit_usd": quoted_deposit_usd,
        "mock_booking_status": mock_booking_status,
        "mock_booking_reference": mock_booking_reference,
        "special_requests": data.get("contact_notes") or trip_data.get("notes") or "",
        "is_contactable": bool((data.get("contact_email") or "").strip()),
    }

    if include_traveller:
        u_row = conn.execute(
            """SELECT u.full_name, u.email, u.phone
               FROM traces t
               JOIN visitors v ON v.id = t.visitor
               LEFT JOIN users u ON u.id = v.user_id
               WHERE t.id = ?""",
            (data.get("trace"),),
        ).fetchone()
        c_name = (data.get("contact_name") or "").strip()
        c_email = (data.get("contact_email") or "").strip()
        c_phone = (data.get("contact_phone") or "").strip()
        if c_email:
            enriched["traveller_type"] = "Contact request" if not (u_row and u_row["email"]) else "Registered traveller"
            enriched["traveller_name"] = c_name or (u_row["full_name"] if u_row else "") or "Customer"
            enriched["traveller_email"] = c_email
            enriched["traveller_phone"] = c_phone or (u_row["phone"] if u_row else "") or ""
            enriched["is_contactable"] = True
        elif u_row and u_row["email"]:
            enriched["traveller_type"] = "Registered traveller"
            enriched["traveller_name"] = u_row["full_name"]
            enriched["traveller_email"] = u_row["email"]
            enriched["traveller_phone"] = u_row["phone"] or ""
            enriched["is_contactable"] = True
        else:
            enriched["traveller_type"] = "Guest traveller"
            enriched["traveller_name"] = c_name or "Guest traveller"
            enriched["traveller_email"] = "Contact details not provided"
            enriched["traveller_phone"] = c_phone
            enriched["is_contactable"] = False

    return enriched


@app.get("/api/traveller/overview")
def traveller_overview(
    key: str = Depends(visitor),
    current_user: UserProfile = Depends(get_current_user),
):
    records = published_records()
    with db() as conn:
        total_quotes = conn.execute(
            """SELECT COUNT(*) FROM quotes q
               WHERE q.visitor=? OR q.visitor IN (SELECT id FROM visitors WHERE user_id=?)""",
            (key, current_user.id),
        ).fetchone()[0]

        total_enquiries = conn.execute(
            """SELECT COUNT(*) FROM enquiries e
               JOIN traces t ON t.id = e.trace
               WHERE t.visitor=? OR t.visitor IN (SELECT id FROM visitors WHERE user_id=?)""",
            (key, current_user.id),
        ).fetchone()[0]

        active_enquiries = conn.execute(
            """SELECT COUNT(*) FROM enquiries e
               JOIN traces t ON t.id = e.trace
               WHERE (t.visitor=? OR t.visitor IN (SELECT id FROM visitors WHERE user_id=?))
                 AND e.status NOT IN ('booked', 'closed', 'closed_lost', 'unqualified')""",
            (key, current_user.id),
        ).fetchone()[0]

        total_trips = conn.execute(
            """SELECT COUNT(*) FROM trips
               WHERE (visitor=? OR visitor IN (SELECT id FROM visitors WHERE user_id=?)) AND revision > 0""",
            (key, current_user.id),
        ).fetchone()[0]

        quotes_rows = conn.execute(
            """SELECT q.* FROM quotes q
               WHERE q.visitor=? OR q.visitor IN (SELECT id FROM visitors WHERE user_id=?)
               ORDER BY q.rowid DESC LIMIT 10""",
            (key, current_user.id),
        ).fetchall()

        enquiries_rows = conn.execute(
            """SELECT e.*
               FROM enquiries e
               JOIN traces t ON t.id = e.trace
               WHERE t.visitor=? OR t.visitor IN (SELECT id FROM visitors WHERE user_id=?)
               ORDER BY e.rowid DESC LIMIT 20""",
            (key, current_user.id),
        ).fetchall()

        trips_rows = conn.execute(
            """SELECT id, title, context, updated FROM trips
               WHERE (visitor=? OR visitor IN (SELECT id FROM visitors WHERE user_id=?)) AND revision > 0
               ORDER BY updated DESC LIMIT 10""",
            (key, current_user.id),
        ).fetchall()

        enriched_enquiries = [_enrich_enquiry(conn, r, records, include_traveller=False) for r in enquiries_rows]

        enriched_trips = []
        for r in trips_rows:
            try:
                tctx = json.loads(r["context"] or "{}")
            except (ValueError, TypeError):
                tctx = {}
            tid = tctx.get("tour")
            tname = records[tid]["title"] if tid and tid in records else (r["title"] or "Sri Lanka Journey")
            enriched_trips.append({
                "id": r["id"],
                "title": r["title"],
                "tour": tid,
                "tour_name": tname,
                "date": tctx.get("date"),
                "adults": tctx.get("adults"),
                "updated": _utc_iso(r["updated"]),
            })

        quote_ids = [r["id"] for r in quotes_rows]
        booking_map = {}
        trip_map = {}
        if quote_ids:
            placeholders = ",".join("?" for _ in quote_ids)
            for br in conn.execute(f"SELECT quote, id FROM bookings WHERE quote IN ({placeholders})", quote_ids).fetchall():
                booking_map[br["quote"]] = br["id"]
            for tr in conn.execute(
                f"SELECT q.id AS qid, tt.trip FROM quotes q JOIN trip_turns tt ON tt.trace = q.trace WHERE q.id IN ({placeholders})",
                quote_ids,
            ).fetchall():
                trip_map[tr["qid"]] = tr["trip"]

    try:
        rates = current_rates()
    except Unavailable:
        rates = None

    last_quote = None
    recent_quotes = []
    for idx, q_row in enumerate(quotes_rows):
        pq = PublicQuote.model_validate_json(q_row["public"])
        is_cur = quote_current(pq, json.loads(q_row["internal"]), rates)
        entry = {
            "id": str(pq.id),
            "title": pq.title,
            "date": pq.date,
            "total": pq.total,
            "deposit": pq.deposit,
            "adults": pq.adults,
            "ages": pq.ages,
            "children": len(pq.ages),
            "current": is_cur,
            "trip_id": trip_map.get(str(pq.id)),
            "mock_booking_reference": booking_map.get(str(pq.id)),
            "created": _utc_iso(q_row["created"]),
        }
        recent_quotes.append(entry)
        if idx == 0:
            last_quote = entry

    return {
        "user": current_user,
        "last_quote": last_quote,
        "quotes": recent_quotes,
        "total_quotes": total_quotes,
        "total_enquiries": total_enquiries,
        "active_enquiries": active_enquiries,
        "total_trips": total_trips,
        "enquiries": enriched_enquiries,
        "trips": enriched_trips,
    }


@app.get("/api/traveller/quotes")
def traveller_quotes(
    key: str = Depends(visitor),
    current_user: UserProfile = Depends(get_current_user),
):
    with db() as conn:
        rows = conn.execute(
            """SELECT * FROM quotes 
               WHERE visitor=? OR visitor IN (SELECT id FROM visitors WHERE user_id=?)
               ORDER BY rowid DESC LIMIT 50""",
            (key, current_user.id),
        ).fetchall()
        current = {r["id"] for r in rows if is_current_notebook_turn(conn, r["trace"])}
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
            result.append({"current": False, "title": q.title, "date": q.date, "total": q.total, "deposit": q.deposit})
    return result


@app.get("/api/traveller/enquiries")
def traveller_enquiries(
    key: str = Depends(visitor),
    current_user: UserProfile = Depends(get_current_user),
):
    records = published_records()
    with db() as conn:
        enquiries_rows = conn.execute(
            """SELECT e.*
               FROM enquiries e
               JOIN traces t ON t.id = e.trace
               WHERE t.visitor=? OR t.visitor IN (SELECT id FROM visitors WHERE user_id=?)
               ORDER BY e.rowid DESC LIMIT 50""",
            (key, current_user.id),
        ).fetchall()
        return [_enrich_enquiry(conn, r, records, include_traveller=False) for r in enquiries_rows]


# ==============================================================================
# STAFF DASHBOARD & ENQUIRY MANAGEMENT
# ==============================================================================

class ContactEnquiryInput(Strict):
    enquiry_id: str | None = None
    quote_id: str | None = None
    trip_id: str | None = None
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    phone: str = Field(default="", max_length=40)
    tour_id: str | None = None
    tour_title: str = Field(default="", max_length=200)
    date: str = Field(default="", max_length=40)
    adults: int = Field(default=2, ge=1, le=50)
    child_ages: list[int] = Field(default_factory=list)
    notes: str = Field(default="", max_length=1000)


@app.post("/api/enquiries/contact", dependencies=[Depends(website)])
def submit_contact_enquiry(
    body: ContactEnquiryInput,
    key: str = Depends(visitor),
    auth_user: UserProfile | None = Depends(get_current_user_optional),
):
    email_clean = body.email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email_clean):
        raise HTTPException(422, "Please provide a valid email address")
    name_clean = clean(body.name)
    phone_clean = clean(body.phone)
    notes_clean = clean(body.notes)
    user_id = auth_user.id if auth_user else ""

    with db() as conn:
        target_row = None
        if body.enquiry_id:
            target_row = conn.execute(
                """SELECT e.id, e.reference, e.status FROM enquiries e
                   JOIN traces t ON t.id = e.trace
                   WHERE (e.id = ? OR e.reference = ?)
                     AND (t.visitor = ? OR t.visitor IN (SELECT id FROM visitors WHERE user_id = ?))""",
                (body.enquiry_id, body.enquiry_id, key, user_id),
            ).fetchone()
        if not target_row and body.quote_id:
            target_row = conn.execute(
                """SELECT e.id, e.reference, e.status FROM enquiries e
                   JOIN traces t ON t.id = e.trace
                   WHERE e.quote = ?
                     AND (t.visitor = ? OR t.visitor IN (SELECT id FROM visitors WHERE user_id = ?))""",
                (body.quote_id, key, user_id),
            ).fetchone()

        if target_row:
            enq_id = target_row["id"]
            enq_ref = target_row["reference"] or f"ENQ-{as_of().year}-{enq_id.replace('-', '')[:8].upper()}"
            conn.execute(
                """UPDATE enquiries
                   SET contact_name = ?,
                       contact_email = ?,
                       contact_phone = ?,
                       contact_notes = ?,
                       is_contactable = 1,
                       enquiry_type = 'contact_request',
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (name_clean, email_clean, phone_clean, notes_clean, enq_id),
            )
            return {
                "id": enq_id,
                "reference": enq_ref,
                "status": target_row["status"],
                "is_contactable": True,
            }

        # Create a clean new enquiry with a non-PII trace
        enq_id = str(uuid4())
        trace_uuid = str(uuid4())
        run_uuid = str(uuid4())
        enq_ref = f"ENQ-{as_of().year}-{enq_id.replace('-', '')[:8].upper()}"
        trip_payload = {
            "tour": body.tour_id,
            "tour_title": body.tour_title,
            "date": body.date,
            "adults": body.adults,
            "kids": len(body.child_ages),
            "ages": body.child_ages,
        }
        trace_events = [{"stage": "contact_request", "tour": body.tour_id or "custom"}]
        conn.execute(
            "INSERT INTO traces(id, visitor, run, events, result) VALUES (?,?,?,?,?)",
            (trace_uuid, key, run_uuid, json.dumps(trace_events), json.dumps({"trace": trace_uuid})),
        )
        reason = "verified_quote" if body.quote_id else ("custom_or_unsupported" if not body.tour_id else "specialist_contact")
        conn.execute(
            """INSERT INTO enquiries(
                   id, reference, trace, quote, trip, reason, status,
                   contact_name, contact_email, contact_phone, contact_notes,
                   is_contactable, enquiry_type, updated_at
               ) VALUES (?,?,?,?,?,?,'new',?,?,?,?,1,'contact_request',CURRENT_TIMESTAMP)""",
            (
                enq_id,
                enq_ref,
                trace_uuid,
                body.quote_id,
                json.dumps(trip_payload),
                reason,
                name_clean,
                email_clean,
                phone_clean,
                notes_clean,
            ),
        )
        if body.trip_id:
            trip_row = conn.execute("SELECT id FROM trips WHERE id=? AND visitor=?", (body.trip_id, key)).fetchone()
            if trip_row:
                conn.execute(
                    "INSERT INTO trip_turns(trip, trace, prompt) VALUES (?,?,?)",
                    (body.trip_id, trace_uuid, "Submitted specialist enquiry form"),
                )
        return {
            "id": enq_id,
            "reference": enq_ref,
            "status": "new",
            "is_contactable": True,
        }


@app.get("/api/enquiries/{reference}")
def visitor_enquiry(
    reference: str,
    key: str = Depends(visitor),
    auth_user: UserProfile | None = Depends(get_current_user_optional),
):
    records = published_records()
    user_id = auth_user.id if auth_user else ""
    with db() as conn:
        row = conn.execute(
            """SELECT e.* FROM enquiries e
               JOIN traces t ON t.id=e.trace
               WHERE (e.id=? OR e.reference=?)
                 AND (t.visitor=? OR t.visitor IN (SELECT id FROM visitors WHERE user_id=?))""",
            (reference, reference, key, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Enquiry unavailable in this session")
        enriched = _enrich_enquiry(conn, row, records, include_traveller=False)
    return {
        "id": enriched["id"],
        "reference": enriched["reference"],
        "status": enriched["status"],
        "quote": enriched["quote"],
        "created": enriched["created"],
        "updated_at": enriched["updated_at"],
        "tour_id": enriched["tour_id"],
        "tour_name": enriched["tour_name"],
        "travel_date": enriched["travel_date"],
        "adults": enriched["adults"],
        "children_count": enriched["children_count"],
        "human_reason": enriched["human_reason"],
        "quoted_total_usd": enriched["quoted_total_usd"],
        "quoted_deposit_usd": enriched["quoted_deposit_usd"],
    }


@app.get("/api/staff/traces/{trace}")
def staff_trace(trace: UUID, _: str = Depends(role)):
    with db() as conn:
        row = conn.execute("""SELECT events FROM traces WHERE id=? UNION ALL
            SELECT events FROM failed_traces WHERE id=? LIMIT 1""", (str(trace), str(trace))).fetchone()
    if not row:
        raise HTTPException(404, "Trace unavailable")
    return {"id": trace, "events": json.loads(row["events"])}


@app.get("/api/staff/evaluation")
def evaluation(_: str = Depends(role)):
    from pathlib import Path
    path = Path(os.getenv("MIRA_EVAL_REPORT", "evals/report/report.json"))
    if not path.is_file():
        raise HTTPException(404, "Run the evaluation suite to generate a report")
    return json.loads(path.read_text())


@app.get("/api/staff/dashboard/overview")
def dashboard_overview(_: str = Depends(role)):
    with db() as conn:
        total_enquiries = conn.execute("SELECT COUNT(*) FROM enquiries").fetchone()[0]
        open_enquiries = conn.execute(
            "SELECT COUNT(*) FROM enquiries WHERE status NOT IN ('booked', 'closed', 'closed_lost', 'unqualified')"
        ).fetchone()[0]
        pending_followups = conn.execute(
            "SELECT COUNT(*) FROM enquiries WHERE status IN ('new', 'in_review', 'waiting', 'waiting_customer')"
        ).fetchone()[0]
        contactable_enquiries = conn.execute(
            """SELECT COUNT(*) FROM enquiries e
               JOIN traces t ON t.id = e.trace
               LEFT JOIN visitors v ON v.id = t.visitor
               WHERE (e.is_contactable = 1 OR e.contact_email != '' OR v.user_id IS NOT NULL)
                 AND e.status NOT IN ('booked', 'closed', 'closed_lost', 'unqualified')"""
        ).fetchone()[0]
        unassigned_enquiries = conn.execute(
            """SELECT COUNT(*) FROM enquiries
               WHERE (assigned_to IS NULL OR assigned_to = '')
                 AND status NOT IN ('booked', 'closed', 'closed_lost', 'unqualified')"""
        ).fetchone()[0]
        missing_rate_enquiries = conn.execute(
            """SELECT COUNT(*) FROM enquiries
               WHERE quote IS NULL
                 AND status NOT IN ('booked', 'closed', 'closed_lost', 'unqualified')"""
        ).fetchone()[0]
        quotes_requiring_confirmation = conn.execute(
            "SELECT COUNT(*) FROM enquiries WHERE reason='verified_quote' AND status='new'"
        ).fetchone()[0]
        pending_content_approvals = conn.execute(
            "SELECT COUNT(*) FROM drafts WHERE status IN ('draft', 'revision_requested')"
        ).fetchone()[0]
        recent_activity = [
            dict(r) | {"created": _utc_iso(r["created"])}
            for r in conn.execute("SELECT * FROM audit ORDER BY id DESC LIMIT 10").fetchall()
        ]
        return {
            "total_enquiries": total_enquiries,
            "open_enquiries": open_enquiries,
            "pending_followups": pending_followups,
            "contactable_enquiries": contactable_enquiries,
            "unassigned_enquiries": unassigned_enquiries,
            "missing_rate_enquiries": missing_rate_enquiries,
            "quotes_requiring_confirmation": quotes_requiring_confirmation,
            "pending_content_approvals": pending_content_approvals,
            "recent_activity": recent_activity,
        }


@app.get("/api/staff/enquiries")
def enquiries(
    response: Response,
    status: str = "",
    search: str = "",
    assigned_to: str = "",
    contactable: str = "",
    sort: str = "newest",
    limit: int = 50,
    offset: int = 0,
    _: str = Depends(role),
):
    records = published_records()
    safe_limit = max(1, min(limit, 200))
    safe_offset = max(0, offset)
    order_clause = {
        "oldest": "e.rowid ASC",
        "updated": "COALESCE(e.updated_at, e.created) DESC, e.rowid DESC",
        "status": "e.status ASC, e.rowid DESC",
        "follow_up": "CASE WHEN e.follow_up_date IS NULL OR e.follow_up_date='' THEN 1 ELSE 0 END, e.follow_up_date ASC, e.rowid DESC",
    }.get(sort, "e.rowid DESC")
    with db() as conn:
        base_from = """FROM enquiries e
            JOIN traces t ON t.id = e.trace
            LEFT JOIN visitors v ON v.id = t.visitor
            LEFT JOIN users u ON u.id = v.user_id
            WHERE 1=1"""
        params: list = []
        if status.strip():
            base_from += " AND e.status = ?"
            params.append(status.strip())
        if assigned_to.strip():
            if assigned_to.strip() == "__unassigned__":
                base_from += " AND (e.assigned_to IS NULL OR e.assigned_to = '')"
            else:
                base_from += " AND e.assigned_to = ?"
                params.append(assigned_to.strip())
        if contactable.strip() == "1":
            base_from += " AND (e.is_contactable = 1 OR e.contact_email != '' OR v.user_id IS NOT NULL)"
        elif contactable.strip() == "0":
            base_from += " AND e.is_contactable = 0 AND (e.contact_email IS NULL OR e.contact_email = '') AND v.user_id IS NULL"
        if search.strip():
            s = f"%{search.strip()}%"
            base_from += (
                " AND (e.id LIKE ? OR e.reference LIKE ? OR e.trip LIKE ? OR e.reason LIKE ? "
                "OR e.contact_name LIKE ? OR e.contact_email LIKE ? OR u.full_name LIKE ? OR u.email LIKE ?)"
            )
            params.extend([s, s, s, s, s, s, s, s])

        total_count = conn.execute(f"SELECT COUNT(*) {base_from}", params).fetchone()[0]
        response.headers["X-Total-Count"] = str(total_count)

        rows = conn.execute(
            f"SELECT e.* {base_from} ORDER BY {order_clause} LIMIT ? OFFSET ?",
            [*params, safe_limit, safe_offset],
        ).fetchall()
        return [_enrich_enquiry(conn, row, records, include_traveller=True) for row in rows]


@app.get("/api/staff/enquiries/{key}")
def enquiry(key: str, _: str = Depends(role)):
    key_str = key.strip()
    records = published_records()
    with db() as conn:
        row = conn.execute("SELECT * FROM enquiries WHERE id=? OR reference=?", (key_str, key_str)).fetchone()
        if not row:
            raise HTTPException(404, "Enquiry unavailable")
        enq_id = row["id"]
        trace = conn.execute("SELECT events FROM traces WHERE id=?", (row["trace"],)).fetchone()
        finance = conn.execute("SELECT internal FROM quotes WHERE id=?", (row["quote"],)).fetchone()
        notes = conn.execute("SELECT actor,body,created FROM notes WHERE enquiry=? ORDER BY id", (enq_id,))
        enriched = _enrich_enquiry(conn, row, records, include_traveller=True)

        quote_history = []
        trip_id = enriched.get("trip_id")
        tour_id = enriched.get("tour_id")
        if trip_id:
            q_rows = conn.execute(
                """SELECT q.id, q.public, q.internal, q.created
                   FROM quotes q
                   JOIN trip_turns tt ON tt.trace = q.trace
                   WHERE tt.trip = ?
                   ORDER BY q.rowid DESC LIMIT 20""",
                (trip_id,),
            ).fetchall()
        elif row["quote"]:
            q_rows = conn.execute(
                "SELECT id, public, internal, created FROM quotes WHERE id=?",
                (row["quote"],),
            ).fetchall()
        else:
            q_rows = []
        for qr in q_rows:
            try:
                pq = json.loads(qr["public"])
                iq = json.loads(qr["internal"])
            except (ValueError, TypeError):
                continue
            if tour_id and pq.get("source") != tour_id:
                continue
            quote_history.append({
                "id": qr["id"],
                "tour_id": pq.get("source"),
                "date": pq.get("date"),
                "adults": pq.get("adults"),
                "ages": pq.get("ages") or [],
                "total": pq.get("total"),
                "deposit": pq.get("deposit"),
                "cost_lkr": iq.get("cost_lkr"),
                "gross_profit_pct": iq.get("gross_profit_pct"),
                "created": _utc_iso(qr["created"]),
                "is_latest": qr["id"] == row["quote"],
            })

        return enriched | {
            "events": json.loads(trace["events"]) if trace else [],
            "notes": [dict(n) | {"created": _utc_iso(n["created"])} for n in notes],
            "finance": json.loads(finance["internal"]) if finance else None,
            "quote_history": quote_history,
        }


class FollowUp(Strict):
    status: Literal[
        "new",
        "in_review",
        "contacted",
        "waiting",
        "waiting_customer",
        "quoted",
        "booked",
        "closed",
        "closed_lost",
        "unqualified",
    ]
    note: str = Field(max_length=500, default="")
    assigned_to: str | None = None
    follow_up_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$|^$")


_TERMINAL_ENQUIRY_STATUSES = {"booked", "closed", "closed_lost", "unqualified"}


@app.patch("/api/staff/enquiries/{key}", dependencies=[Depends(website)])
def follow_up(key: str, body: FollowUp, actor: str = Depends(role)):
    key_str = key.strip()
    if re.search(r"@|(?:\d[ .-]*){7}", body.note):
        raise HTTPException(422, "Use a note without personal details")
    with db() as conn:
        existing = conn.execute("SELECT id, status, quote FROM enquiries WHERE id=? OR reference=?", (key_str, key_str)).fetchone()
        if not existing:
            raise HTTPException(404, "Enquiry unavailable")
        enq_id = existing["id"]
        current_status = existing["status"]
        if body.status == "booked":
            has_booking = bool(
                existing["quote"]
                and conn.execute("SELECT 1 FROM bookings WHERE quote=?", (existing["quote"],)).fetchone()
            )
            if not existing["quote"] and not has_booking:
                raise HTTPException(422, "Cannot mark enquiry as booked without a verified quote or booking reference")
        if current_status in _TERMINAL_ENQUIRY_STATUSES and body.status != current_status:
            if body.status not in _TERMINAL_ENQUIRY_STATUSES and body.status != "in_review":
                raise HTTPException(
                    422,
                    f"Closed or booked enquiries must be reopened to 'in_review' before transitioning to '{body.status}'",
                )

        assigned_name = ""
        if body.assigned_to:
            assignee = conn.execute("SELECT full_name FROM users WHERE id=?", (body.assigned_to,)).fetchone()
            if assignee:
                assigned_name = assignee["full_name"]
            else:
                raise HTTPException(404, "Assigned staff member not found")

        updates = ["status=?", "updated_at=CURRENT_TIMESTAMP"]
        params: list = [body.status]
        if body.assigned_to is not None:
            updates.extend(["assigned_to=?", "assigned_name=?"])
            params.extend([body.assigned_to or None, assigned_name])
        if body.follow_up_date is not None:
            updates.append("follow_up_date=?")
            params.append(body.follow_up_date or None)
        params.append(enq_id)
        updated = conn.execute(f"UPDATE enquiries SET {', '.join(updates)} WHERE id=?", params).rowcount
        if not updated:
            raise HTTPException(404, "Enquiry unavailable")
        if body.note.strip():
            conn.execute("INSERT INTO notes(enquiry,actor,body) VALUES (?,?,?)", (enq_id, actor, clean(body.note)))
        conn.execute(
            "INSERT INTO audit(actor,action,target) VALUES (?,?,?)",
            (actor, f"follow_up:{current_status}->{body.status}", enq_id),
        )
    res = {"status": body.status}
    if body.assigned_to is not None:
        res["assigned_to"] = body.assigned_to
        res["assigned_name"] = assigned_name
    if body.follow_up_date is not None:
        res["follow_up_date"] = body.follow_up_date or None
    return res


@app.get("/api/staff/users/assignable")
def assignable_staff(_: str = Depends(role)):
    with db() as conn:
        rows = conn.execute(
            "SELECT id, full_name, email, role FROM users WHERE role IN ('staff', 'approver', 'admin') AND status='active' ORDER BY full_name"
        ).fetchall()
        return [dict(r) for r in rows]


# ==============================================================================
# CONTENT DRAFT & HUMAN APPROVAL WORKFLOW
# ==============================================================================

class DraftCommand(Strict):
    command: str = Field(min_length=5, max_length=300)


class DraftText(Strict):
    title: str = Field(min_length=4, max_length=100)
    body: str = Field(min_length=20, max_length=2000)


@app.post("/api/staff/drafts", dependencies=[Depends(website)])
def generate(body: DraftCommand, actor: str = Depends(role)):
    if actor not in {"staff", "editor", "approver", "admin"}:
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
        conn.execute("INSERT INTO drafts(id,title,body,source,author,status) VALUES (?,?,?,?,?,'draft')",
                     (key, draft.title, draft.body, row["id"], actor))
        conn.execute("INSERT INTO audit(actor,action,target) VALUES (?,?,?)", (actor, mode, key))
    return {"id": key, "mode": mode}


@app.get("/api/staff/drafts")
def drafts(actor: str = Depends(role)):
    if actor not in {"staff", "editor", "approver", "admin"}:
        raise HTTPException(403, "Editor access required")
    with db() as conn:
        return [
            dict(r)
            | {
                "created": _utc_iso(r["created"]),
                "published": _utc_iso(r["published"]),
                "reviewed_at": _utc_iso(r["reviewed_at"]) if "reviewed_at" in r.keys() else None,
            }
            for r in conn.execute("SELECT * FROM drafts ORDER BY rowid DESC LIMIT 100")
        ]


class DraftReviewInput(Strict):
    action: Literal["approve", "request_revision", "reject"]
    notes: str = Field(default="", max_length=1000)


@app.post("/api/staff/drafts/{key}/review", dependencies=[Depends(website)])
def review_draft(key: str, body: DraftReviewInput, actor: str = Depends(role)):
    if actor != "approver":
        raise HTTPException(403, "Approver access required")
    status_map = {
        "approve": "approved",
        "request_revision": "revision_requested",
        "reject": "rejected",
    }
    target_status = status_map[body.action]
    with db() as conn:
        updated = conn.execute(
            """UPDATE drafts 
               SET status=?, reviewer=?, review_notes=?, reviewed_at=CURRENT_TIMESTAMP 
               WHERE id=? AND status != 'published'""",
            (target_status, actor, body.notes, key),
        )
        if not updated.rowcount:
            raise HTTPException(409, "Draft unavailable or already published")
        conn.execute("INSERT INTO audit(actor,action,target) VALUES (?,?,?)", (actor, f"review_{body.action}", key))
    return {"status": target_status, "id": key}


@app.post("/api/staff/drafts/{key}/publish", dependencies=[Depends(website)])
def publish(key: str, actor: str = Depends(role)):
    if actor != "approver":
        raise HTTPException(403, "Approver access required")
    with db() as conn:
        updated = conn.execute(
            "UPDATE drafts SET status='published', published=CURRENT_TIMESTAMP WHERE id=? AND status IN ('draft', 'approved')",
            (key,),
        )
        if not updated.rowcount:
            raise HTTPException(409, "Draft unavailable or already published")
        conn.execute("INSERT INTO audit(actor,action,target) VALUES (?,?,?)", (actor, "publish", key))
    return {"status": "published"}


@app.get("/api/staff/audit")
def audit(_: str = Depends(role)):
    with db() as conn:
        return [dict(row) | {"created": _utc_iso(row["created"])} for row in conn.execute("SELECT * FROM audit ORDER BY id DESC LIMIT 100")]


@app.get("/api/staff/me")
def staff_identity(actor: str = Depends(role), current_user: UserProfile | None = Depends(get_current_user_optional)):
    if current_user:
        return {
            "role": current_user.role,
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
        }
    return {"role": actor}


# ==============================================================================
# ADMIN USER MANAGEMENT & AUDIT
# ==============================================================================

@app.get("/api/admin/users")
def list_users(search: str = "", role_filter: str = "", status_filter: str = "", actor: str = Depends(role)):
    if actor != "admin":
        raise HTTPException(403, "Admin access required")
    with db() as conn:
        query = "SELECT id, email, full_name, role, status, phone, preferences, created_at, updated_at FROM users WHERE 1=1"
        params = []
        if search.strip():
            s = f"%{search.strip()}%"
            query += " AND (email LIKE ? OR full_name LIKE ?)"
            params.extend([s, s])
        if role_filter.strip():
            query += " AND role = ?"
            params.append(role_filter.strip())
        if status_filter.strip():
            query += " AND status = ?"
            params.append(status_filter.strip())
        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["preferences"] = json.loads(d["preferences"]) if d.get("preferences") else {}
            d["created_at"] = _utc_iso(d.get("created_at"))
            d["updated_at"] = _utc_iso(d.get("updated_at"))
            result.append(d)
        return result


class AdminUserUpdate(Strict):
    role: Literal["guest", "traveller", "staff", "approver", "admin"] | None = None
    status: Literal["active", "deactivated"] | None = None


@app.patch("/api/admin/users/{user_id}", dependencies=[Depends(website)])
def update_user(
    user_id: UUID,
    body: AdminUserUpdate,
    actor: str = Depends(role),
    current_user: UserProfile | None = Depends(get_current_user_optional),
):
    if actor != "admin":
        raise HTTPException(403, "Admin access required")
    uid_str = str(user_id)
    if current_user and current_user.id == uid_str:
        if body.status == "deactivated":
            raise HTTPException(400, "Cannot deactivate your own admin account")
        if body.role and body.role != "admin":
            raise HTTPException(400, "Cannot demote your own admin account")

    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id=?", (uid_str,)).fetchone()
        if not user:
            raise HTTPException(404, "User not found")

        updates = []
        params = []
        if body.role:
            updates.append("role=?")
            params.append(body.role)
        if body.status:
            updates.append("status=?")
            params.append(body.status)
        if not updates:
            raise HTTPException(422, "No updates supplied")

        updates.append("updated_at=CURRENT_TIMESTAMP")
        params.append(uid_str)
        conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id=?", params)

        if body.status == "deactivated":
            conn.execute("UPDATE user_sessions SET revoked=1 WHERE user_id=?", (uid_str,))

        conn.execute(
            "INSERT INTO audit(actor,action,target) VALUES (?,?,?)",
            (actor, f"admin_update_user:role={body.role}:status={body.status}", uid_str),
        )
    return {"id": uid_str, "updated": True}


@app.get("/api/admin/audit")
def admin_audit(actor: str = Depends(role)):
    if actor != "admin":
        raise HTTPException(403, "Admin access required")
    with db() as conn:
        return [dict(row) | {"created": _utc_iso(row["created"])} for row in conn.execute("SELECT * FROM audit ORDER BY id DESC LIMIT 100")]


# ==============================================================================
# READ-ONLY STAFF PRICING PREVIEW (NO DB WRITES)
# ==============================================================================

_PREVIEW_REASON_MESSAGES = {
    "hotel_rate_missing_or_ambiguous": "Contracted hotel rates for one or more nights on the selected dates are missing or have overlapping supplier revisions in the rate sheet.",
    "missing_amount": "A required room/occupancy rate amount (such as single-room occupancy) is missing in the rate sheet for this configuration.",
    "unconfirmed_hotel_rate": "One or more hotel nights have an unconfirmed supplier currency or contract note.",
    "tour_rate": "No automated package rate row exists for this tour in the workbook.",
    "not_published": "Tour is not a published tour.",
    "conflicting_tour_scope": "Tour scope requires specialist manual pricing.",
    "date_or_fx_expired": "Travel date is in the past or outside the contracted FX/rate validity window.",
    "season_rate": "No contracted season rate covers the selected travel dates.",
    "transport_rate": "No transport tier matches the total traveller group size.",
    "group_size": "Requested party size exceeds the configured maximum group size.",
    "hotel_schedule": "Tour hotel schedule does not match the configured duration.",
    "rate_import_invalid": "Rate workbook could not be validated.",
}


from datetime import date as _Date


class PricingPreviewInput(Strict):
    tour_id: str = Field(min_length=1, max_length=64)
    date: _Date
    adults: int = Field(ge=1, le=100)
    child_ages: list[int] = Field(default_factory=list, max_length=30)
    infants: int = Field(default=0, ge=0, le=30)


@app.post("/api/staff/pricing/preview", dependencies=[Depends(website)])
def staff_pricing_preview(body: PricingPreviewInput, _: str = Depends(role)):
    if any(not 0 <= a <= 120 for a in body.child_ages):
        raise HTTPException(422, "Child ages must be between 0 and 120.")
    if len(body.child_ages) + body.infants > 30:
        raise HTTPException(422, "Total children and infants cannot exceed 30.")

    combined_ages = [*body.child_ages, *([0] * body.infants)]
    records = published_records()
    resolved_tour_id = next(
        (k for k, v in records.items() if v.get("type") == "tour" and (k == body.tour_id or v.get("slug") == body.tour_id)),
        body.tour_id,
    )
    tour_title = records.get(resolved_tour_id, {}).get("title", resolved_tour_id)
    today = as_of()
    evaluated_config = {
        "tour_id": resolved_tour_id,
        "tour_title": tour_title,
        "date": body.date.isoformat(),
        "adults": body.adults,
        "child_ages": list(body.child_ages),
        "infants": body.infants,
        "as_of": today.isoformat(),
    }

    try:
        rates = current_rates()
    except Unavailable as exc:
        return {
            "preview_only": True,
            "outcome": "PRICING_SERVICE_ERROR",
            "rate_digest": None,
            "evaluated_config": evaluated_config,
            "currency": "USD",
            "total_usd": None,
            "deposit_usd": None,
            "balance_usd": None,
            "snapshot": None,
            "reason_code": str(exc),
            "reason": _PREVIEW_REASON_MESSAGES.get(str(exc), f"Rate sheet unavailable ({exc})."),
            "finance": None,
        }

    try:
        result = price(resolved_tour_id, body.date, body.adults, combined_ages, today, rates=rates)
    except Unavailable as exc:
        code = str(exc)
        return {
            "preview_only": True,
            "outcome": "PRICE_UNAVAILABLE",
            "rate_digest": rates.digest,
            "evaluated_config": evaluated_config,
            "currency": "USD",
            "total_usd": None,
            "deposit_usd": None,
            "balance_usd": None,
            "snapshot": None,
            "reason_code": code,
            "reason": _PREVIEW_REASON_MESSAGES.get(code, f"Automated pricing unavailable ({code})."),
            "finance": None,
        }

    return {
        "preview_only": True,
        "outcome": "PRICE_VERIFIED",
        "rate_digest": rates.digest,
        "evaluated_config": evaluated_config,
        "currency": "USD",
        "total_usd": result["total"],
        "deposit_usd": result["deposit"],
        "balance_usd": result["balance"],
        "snapshot": result["snapshot"],
        "reason_code": None,
        "reason": None,
        "finance": {
            "cost_lkr": result["cost_lkr"],
            "gross_profit_pct": result["gross_profit_pct"],
            "breakdown": result["breakdown"],
        },
    }
