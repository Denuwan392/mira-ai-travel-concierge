"""Operational logging. Event names and fields are selected by the application."""
import atexit
import json
import logging
import os
import sys
import threading
import traceback
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import UUID, uuid4

from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse

request_id = ContextVar("request_id", default=None)
trace_id = ContextVar("trace_id", default=None)

# Restrained ANSI color palette
COLORS = {
    "API": 36,       # cyan
    "AGENT": 35,     # purple
    "RAG": 36,       # teal
    "PRICING": 33,   # yellow
    "UI": 32,        # green
    "TRACE": 35,     # magenta
    "ERROR": 31,     # red
    "WARNING": 33,   # amber
    "NEXT": 34,      # blue
    "WEB": 34,       # blue
    "LLM": 33,       # yellow
}

STAGE_COLORS = {
    "INTENT": 35,    # purple (AGENT)
    "RAG": 36,       # teal (RAG)
    "PRICE": 33,     # yellow (PRICING)
    "GROUND": 36,    # teal (RAG)
    "UI": 32,        # green (UI)
    "TRACE": 35,     # magenta (TRACE)
    "DONE": 32,      # green
    "FAILED": 31,    # red
    "ERROR": 31,     # red
}

STATUS_NAMES = {
    200: "200 OK",
    201: "201 Created",
    204: "204 No Content",
    304: "304 Not Modified",
    400: "400 Bad Request",
    401: "401 Unauthorized",
    403: "403 Forbidden",
    404: "404 Not Found",
    409: "409 Conflict",
    422: "422 Unprocessable",
    500: "500 Error",
    502: "502 Bad Gateway",
    503: "503 Unavailable",
}

INTENT_TITLES = {
    "discover": "Day tour",
    "custom": "Custom itinerary",
    "compare": "Compare tours",
    "cancellation": "Cancellation policy",
    "payment": "Payment policy",
    "children": "Child policy",
    "dietary": "Dietary requirements",
    "polonnaruwa": "Polonnaruwa tour",
    "destination": "Destination enquiry",
    "general": "Tour recommendations",
}

WORKFLOW_EVENTS = {
    "workflow.started",
    "intent.classified",
    "retrieval.completed",
    "pricing.started",
    "pricing.completed",
    "grounding.completed",
    "ui.validated",
    "turn.persisted",
    "turn.replayed",
    "trace.queued",
    "trace.export_failed",
    "workflow.run_error",
    "workflow.node_failed",
    "turn.persistence_failed",
    "workflow.finished",
}


SENSITIVE_KEY_SUBSTRINGS = ("token", "secret", "password", "bearer", "auth", "cost_lkr", "private", "credential")


def is_sensitive_key(key: str) -> bool:
    k = key.lower()
    return any(sub in k for sub in SENSITIVE_KEY_SUBSTRINGS)


def sanitize_value(val):
    if isinstance(val, str):
        if "@" in val:
            import re
            val = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[REDACTED_EMAIL]", val)
        if "Bearer " in val:
            import re
            val = re.sub(r"Bearer\s+\S+", "Bearer [REDACTED]", val)
    return val


def shorten_id(val: str | None, debug: bool = False) -> str:
    if not val:
        return ""
    s = str(val)
    if debug:
        return s
    clean = s.replace("-", "")
    if len(clean) >= 32:
        return f"{s[:8]}…"
    return s


def colorize(text: str, code: int | str, enabled: bool) -> str:
    if not enabled:
        return text
    return f"\033[{code}m{text}\033[0m"


def truncate(text: str, max_len: int = 120) -> str:
    if len(text) <= max_len:
        return text
    return f"{text[:max_len - 1]}…"


class Formatter(logging.Formatter):
    def __init__(self, style="pretty", color=False, debug=False):
        super().__init__()
        self.style = style
        self.color = color if style != "json" else False
        self.debug = debug

    def format(self, record):
        fields = getattr(record, "mira_fields", {})
        component = getattr(record, "mira_component", "API")
        if not hasattr(record, "mira_fields"):
            lifecycle = {
                "Application startup complete.": "application.started",
                "Application shutdown complete.": "server.stopped",
                "Waiting for application startup.": "server.starting",
                "Shutting down": "server.stopping",
            }
            message = lifecycle.get(record.msg, "framework.diagnostic") if isinstance(record.msg, str) else "framework.diagnostic"
            fields = {"logger": record.name}
            if (record.name == "uvicorn.error" and message == "framework.diagnostic"
                    and isinstance(record.msg, str) and record.msg.startswith("Uvicorn running on ")
                    and isinstance(record.args, tuple) and record.args and isinstance(record.args[-1], int)):
                message = "server.ready"
                fields = {"port": record.args[-1]}
        else:
            message = record.msg

        if record.exc_info and record.exc_info[0]:
            exception, _, tb = record.exc_info
            fields = {**fields, "exception_type": exception.__name__, "frames": [
                f"{Path(frame.filename).name}:{frame.lineno} in {frame.name}"
                for frame in traceback.extract_tb(tb, limit=-12)
            ]}

        context = record.mira_context if hasattr(record, "mira_context") else correlation()
        timestamp = datetime.fromtimestamp(record.created, timezone.utc)

        if self.style == "json":
            return json.dumps({
                "timestamp": timestamp.isoformat(timespec="milliseconds"),
                "level": record.levelname,
                "component": component,
                "event": message,
                **fields,
                **context
            }, ensure_ascii=True)

        return self.format_pretty_record(record, component, message, fields, context, timestamp)

    def format_pretty_record(self, record, component, message, fields, context, timestamp):
        time_str = f"{timestamp.astimezone():%H:%M:%S}"
        raw_label = f"[{component}]"
        label_str = f"{raw_label:<8}"
        if self.color:
            color_code = COLORS.get(component, 37)
            label_display = f"\033[{color_code}m{label_str}\033[0m"
        else:
            label_display = label_str

        # 1. Compact HTTP access log
        if component == "API" and message == "http.request":
            method = fields.get("method", "HTTP")
            route = fields.get("route", "")
            status = fields.get("status")
            duration_ms = fields.get("duration_ms")
            status_text = STATUS_NAMES.get(status, f"{status}") if status else "no status"
            dur_text = f" · {duration_ms}ms" if duration_ms is not None else ""

            if self.color and status:
                if status >= 500:
                    status_colored = f"\033[31m{status_text}\033[0m"
                elif status >= 400:
                    status_colored = f"\033[33m{status_text}\033[0m"
                else:
                    status_colored = f"\033[32m{status_text}\033[0m"
            else:
                status_colored = status_text

            line = f"{time_str}  {label_display} {method} {route} · {status_colored}{dur_text}"
            return truncate(line)

        # 2. Compact Frontend request log
        if component in {"NEXT", "WEB"} and message == "frontend.request":
            method = fields.get("method", "HTTP")
            status = fields.get("status")
            duration_ms = fields.get("duration_ms")
            path = fields.get("path")
            status_text = STATUS_NAMES.get(status, f"{status}") if status else "no status"
            dur_text = f" · {duration_ms}ms" if duration_ms is not None else ""
            path_text = f" {path}" if path else ""
            line = f"{time_str}  {label_display} {method}{path_text} · {status_text}{dur_text}"
            return truncate(line)

        # 3. Startup & Lifecycle logs
        if message == "server.ready":
            port = fields.get("port", 8000)
            return f"{time_str}  {label_display} Ready on http://127.0.0.1:{port}"
        if message == "service.started":
            port = fields.get("port")
            port_text = f" · port {port}" if port else ""
            return f"{time_str}  {label_display} Service started{port_text}"
        if message == "application.started":
            return f"{time_str}  {label_display} Application startup complete"
        if message == "server.starting":
            return f"{time_str}  {label_display} Server starting"
        if message == "server.stopped":
            return f"{time_str}  {label_display} Server stopped"
        if message == "server.stopping":
            return f"{time_str}  {label_display} Server stopping"
        if message == "port.unavailable":
            port = fields.get("port")
            remedy = fields.get("remedy", "")
            rem_str = f" ({remedy})" if remedy else ""
            err_label = f"[{'ERROR':<7}]"
            if self.color:
                err_label = f"\033[1;31m{err_label}\033[0m"
            return f"{time_str}  {err_label} {label_display} port.unavailable · Port {port} unavailable{rem_str}"

        # 4. Warnings and Errors
        if record.levelno >= logging.ERROR:
            err_label = f"[{'ERROR':<7}]"
            if self.color:
                err_label = f"\033[1;31m{err_label}\033[0m"
            exc_part = f" · {fields.get('exception_type')}" if fields.get("exception_type") else ""
            msg_line = f"{time_str}  {err_label} {label_display} {message}{exc_part}"
            if self.debug and record.exc_info and record.exc_info[0]:
                stack = "".join(traceback.format_exception(*record.exc_info)).rstrip()
                return f"{msg_line}\n{stack}"
            frames = fields.get("frames", [])
            if frames:
                frame_line = f"\n          at {frames[-1]}"
                return truncate(msg_line) + frame_line
            return truncate(msg_line)

        if record.levelno == logging.WARNING:
            warn_label = f"[{'WARN':<7}]"
            if self.color:
                warn_label = f"\033[33m{warn_label}\033[0m"
            return truncate(f"{time_str}  {warn_label} {label_display} {message}")

        # 5. DEBUG mode or General INFO
        if self.debug:
            details_dict = {**fields, **context}
            details = " ".join(f"{k}={json.dumps(v, ensure_ascii=True)}" for k, v in details_dict.items())
            return f"{time_str}  {record.levelname:<7} {label_display} {message}" + (f" | {details}" if details else "")

        # Default INFO formatting: clean, no repeated IDs, shortened UUIDs if in fields, redacted sensitive data
        safe_fields = {}
        for k, v in fields.items():
            if k in ("logger",) or is_sensitive_key(k):
                continue
            if isinstance(v, str) and len(v) >= 32:
                v = shorten_id(v, debug=False)
            safe_fields[k] = sanitize_value(v)
        details = " · ".join(f"{k}: {v}" for k, v in safe_fields.items() if v is not None and v != "")
        line = f"{time_str}  {label_display} {message}" + (f" · {details}" if details else "")
        return truncate(line)

    def format_workflow(self, records: list[logging.LogRecord]) -> str:
        if not records:
            return ""

        indent = "          "
        dim = "90"
        pipe = colorize("│", dim, self.color)
        top_branch = colorize("┌─", dim, self.color)
        mid_branch = colorize("├─", dim, self.color)
        end_branch = colorize("└─", dim, self.color)

        title = None
        trace_val = None
        for r in records:
            ctx = getattr(r, "mira_context", {})
            if "trace_id" in ctx and not trace_val:
                trace_val = ctx["trace_id"]
            fields = getattr(r, "mira_fields", {})
            if fields.get("notebook"):
                title = "Journey notebook"
            elif not title and fields.get("intent"):
                intent_raw = fields.get("intent")
                title = INTENT_TITLES.get(intent_raw, intent_raw.replace("_", " ").capitalize() if intent_raw else None)
        if not title:
            title = "Travel Assistant"

        lines = [f"\n{indent}{top_branch} MIRA AGENT · {title}", f"{indent}{pipe}"]

        for r in records:
            msg = r.msg
            fields = getattr(r, "mira_fields", {})
            if msg == "intent.classified":
                intent_val = fields.get("intent", "")
                party_val = fields.get("party_type", "")
                intent_name = INTENT_TITLES.get(intent_val, intent_val.replace("_", " ").capitalize())
                party_name = party_val.replace("_", " ") if party_val else ""
                text = f"{intent_name} · {party_name}" if party_name else intent_name
                tag = colorize(f"{'INTENT':<8}", STAGE_COLORS["INTENT"], self.color)
                lines.append(f"{indent}{mid_branch} {tag} {truncate(text)}")

            elif msg == "retrieval.completed":
                sources = fields.get("sources", [])
                docs = fields.get("documents", len(sources))
                src_str = " · ".join(sources) if sources else "none"
                doc_str = f"{docs} document" if docs == 1 else f"{docs} documents"
                text = f"Retrieved {src_str} · {doc_str}"
                tag = colorize(f"{'RAG':<8}", STAGE_COLORS["RAG"], self.color)
                lines.append(f"{indent}{mid_branch} {tag} {truncate(text)}")

            elif msg == "pricing.completed":
                tour_id = fields.get("tour_id", "")
                status = fields.get("rate_status", "")
                rule = fields.get("rule")
                dur = fields.get("duration_ms")
                dur_str = f" · {dur}ms" if dur is not None else ""
                if status == "verified":
                    text = f"Verified quote · {tour_id}{dur_str}"
                else:
                    rule_str = f" ({rule})" if rule else ""
                    text = f"Quote {status} · {tour_id}{rule_str}{dur_str}"
                tag = colorize(f"{'PRICE':<8}", STAGE_COLORS["PRICE"], self.color)
                lines.append(f"{indent}{mid_branch} {tag} {truncate(text)}")

            elif msg == "grounding.completed":
                sources = fields.get("sources", [])
                src_str = " · ".join(sources) if sources else "none"
                text = f"Sources attached · {src_str}"
                tag = colorize(f"{'GROUND':<8}", STAGE_COLORS["GROUND"], self.color)
                lines.append(f"{indent}{mid_branch} {tag} {truncate(text)}")

            elif msg == "ui.validated":
                comps = fields.get("components", 0)
                comp_str = f"{comps} component validated" if comps == 1 else f"{comps} components validated"
                tag = colorize(f"{'UI':<8}", STAGE_COLORS["UI"], self.color)
                lines.append(f"{indent}{mid_branch} {tag} {comp_str}")

            elif msg == "turn.persisted":
                qid = fields.get("quote_id")
                enquiry = fields.get("enquiry", False)
                parts = []
                if qid:
                    parts.append("Quote saved")
                if enquiry:
                    parts.append("enquiry created")
                if not parts:
                    parts.append("Turn saved")
                text = " · ".join(parts)
                tag = colorize(f"{'TRACE':<8}", STAGE_COLORS["TRACE"], self.color)
                lines.append(f"{indent}{mid_branch} {tag} {truncate(text)}")

            elif msg == "turn.replayed":
                tag = colorize(f"{'TRACE':<8}", STAGE_COLORS["TRACE"], self.color)
                lines.append(f"{indent}{mid_branch} {tag} Turn replayed from cache")

            elif msg == "trace.export_failed":
                tag = colorize(f"{'TRACE':<8}", STAGE_COLORS["TRACE"], self.color)
                lines.append(f"{indent}{mid_branch} {tag} Remote export failed (safe)")

            elif r.levelno >= logging.ERROR and msg in {"workflow.run_error", "workflow.node_failed", "turn.persistence_failed"}:
                node = fields.get("node")
                text = f"Error: {msg}" + (f" in {node}" if node else "")
                tag = colorize(f"{'ERROR':<8}", STAGE_COLORS["ERROR"], self.color)
                lines.append(f"{indent}{mid_branch} {tag} {truncate(text)}")

        lines.append(f"{indent}{pipe}")

        finish_record = next((r for r in reversed(records) if r.msg == "workflow.finished"), None)
        outcome = finish_record.mira_fields.get("outcome", "completed") if finish_record and hasattr(finish_record, "mira_fields") else "completed"
        dur = finish_record.mira_fields.get("duration_ms") if finish_record and hasattr(finish_record, "mira_fields") else None

        dur_str = f"{dur}ms" if dur is not None else ""
        trace_str = shorten_id(trace_val, debug=self.debug)
        trace_part = f"trace: {trace_str}" if trace_str else ""
        info = " · ".join(p for p in (dur_str, trace_part) if p)

        if outcome == "completed":
            tag = colorize(f"{'DONE':<8}", STAGE_COLORS["DONE"], self.color)
        elif outcome == "failed":
            tag = colorize(f"{'FAILED':<8}", STAGE_COLORS["FAILED"], self.color)
        else:
            tag = colorize(f"{outcome.upper():<8}", STAGE_COLORS.get(outcome.upper(), 33), self.color)

        lines.append(f"{indent}{end_branch} {tag} {info}\n")
        return "\n".join(lines)


class ConsoleHandler(logging.StreamHandler):
    def __init__(self, stream=None, style="pretty", debug=False):
        super().__init__(stream or sys.stderr)
        self.style = style
        self.debug = debug
        self._buffers: dict[str, list[logging.LogRecord]] = {}
        self._lock = threading.Lock()

    def emit(self, record):
        try:
            if self.style == "json" or self.debug:
                msg = self.format(record)
                self.stream.write(msg + self.terminator)
                self.flush()
                return

            context = getattr(record, "mira_context", {})
            trace = context.get("trace_id")
            component = getattr(record, "mira_component", "")
            msg_name = getattr(record, "msg", "")

            is_workflow_msg = (
                trace and (
                    component in {"AGENT", "RAG", "PRICING", "TRACE"} or
                    msg_name in WORKFLOW_EVENTS or
                    (component == "ERROR" and isinstance(msg_name, str) and (msg_name.startswith("workflow.") or msg_name.startswith("turn.")))
                )
            )

            if is_workflow_msg:
                with self._lock:
                    buf = self._buffers.setdefault(trace, [])
                    buf.append(record)

                    if msg_name == "workflow.finished":
                        records = self._buffers.pop(trace, [])
                        output = self.formatter.format_workflow(records)
                        self.stream.write(output + self.terminator)
                        self.flush()
                        return

                    if record.levelno >= logging.ERROR:
                        records = self._buffers.pop(trace, [])
                        output = self.formatter.format_workflow(records)
                        self.stream.write(output + self.terminator)
                        self.flush()
                        return

                    if len(buf) >= 50:
                        records = self._buffers.pop(trace, [])
                        output = self.formatter.format_workflow(records)
                        self.stream.write(output + self.terminator)
                        self.flush()
                        return
                return

            msg = self.format(record)
            self.stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

    def flush_all(self):
        with self._lock:
            for trace, records in list(self._buffers.items()):
                try:
                    output = self.formatter.format_workflow(records)
                    self.stream.write(output + self.terminator)
                except Exception:
                    pass
            self._buffers.clear()
            try:
                self.flush()
            except Exception:
                pass


def configure():
    mode = os.getenv("LOG_FORMAT", "pretty").lower()
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    is_debug = level_name == "DEBUG"
    is_color = (sys.stderr.isatty() or os.getenv("MIRA_DEV_COLOR") == "1") and "NO_COLOR" not in os.environ
    if mode == "json":
        is_color = False

    formatter = Formatter(style=mode, color=is_color, debug=is_debug)
    handler = ConsoleHandler(sys.stderr, style=mode, debug=is_debug)
    handler.setFormatter(formatter)
    atexit.register(handler.flush_all)

    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level_name)

    for name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True

    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    access_logger.propagate = False
    access_logger.setLevel(logging.WARNING)

    for name in ("httpx", "httpx2", "httpcore", "google_genai", "opentelemetry", "langfuse", "alembic"):
        logging.getLogger(name).setLevel(logging.WARNING)


def correlation():
    return {k: v for k, v in {"request_id": request_id.get(), "trace_id": trace_id.get()}.items() if v}


def event(component, name, *, level=logging.INFO, exception=False, **fields):
    logging.getLogger(f"mira.{component.lower()}").log(
        level, name, exc_info=exception, extra={"mira_component": component, "mira_fields": fields, "mira_context": correlation()})


def elapsed(start):
    return round((perf_counter() - start) * 1000)


def valid_id(value):
    try:
        return str(UUID(value)) if value and len(value) == 36 else None
    except ValueError:
        return None


class RequestLogging:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        supplied = next((v.decode("latin1") for k, v in scope["headers"] if k == b"x-request-id"), None)
        identifier = valid_id(supplied) or str(uuid4())
        token = request_id.set(identifier)
        trace_token = trace_id.set(None)
        start, status, completed = perf_counter(), None, False
        response_trace = None
        method = scope["method"]
        method = method if method in {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"} else "OTHER"

        async def observe(message):
            nonlocal status, completed, response_trace
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = MutableHeaders(scope=message)
                headers["x-request-id"] = identifier
                response_trace = valid_id(headers.get("x-trace-id"))
            await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body"):
                completed = True

        def route():
            return getattr(scope.get("route"), "path", "<unmatched>")

        try:
            await self.app(scope, receive, observe)
        except Exception:
            trace_id.set(response_trace)
            event("ERROR", "http.exception", level=logging.ERROR, exception=True, method=method, route=route())
            if status is None:
                await JSONResponse({"detail": "Internal server error"}, status_code=500)(scope, receive, observe)
            else:
                raise
        finally:
            trace_id.set(response_trace)
            event("API", "http.request", method=method, route=route(), status=status,
                  duration_ms=elapsed(start), completed=completed,
                  level=logging.ERROR if status and status >= 500 else logging.INFO)
            trace_id.reset(trace_token)
            request_id.reset(token)
