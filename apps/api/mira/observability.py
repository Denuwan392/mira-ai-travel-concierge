"""Operational logging. Event names and fields are selected by the application."""
import json
import logging
import os
import sys
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
COLORS = {"API": 36, "WEB": 32, "NEXT": 34, "AGENT": 35, "LLM": 33,
          "RAG": 36, "PRICING": 32, "TRACE": 35, "ERROR": 31}


class Formatter(logging.Formatter):
    def __init__(self, style="pretty", color=False):
        super().__init__()
        self.style = style
        self.color = color

    def format(self, record):
        fields = getattr(record, "mira_fields", {})
        component = getattr(record, "mira_component", "API")
        # Framework/provider messages sometimes contain URLs, headers or response bodies.
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
            # Frame positions are useful without values, source lines or the exception message.
            fields = {**fields, "exception_type": exception.__name__, "frames": [
                f"{Path(frame.filename).name}:{frame.lineno} in {frame.name}"
                for frame in traceback.extract_tb(tb, limit=-12)
            ]}
        context = record.mira_context if hasattr(record, "mira_context") else correlation()
        timestamp = datetime.fromtimestamp(record.created, timezone.utc)
        if self.style == "json":
            return json.dumps({"timestamp": timestamp.isoformat(timespec="milliseconds"),
                               "level": record.levelname, "component": component,
                               "event": message, **fields, **context}, ensure_ascii=True)
        label = f"[{component}]"
        if self.color:
            label = f"\033[{COLORS[component]}m{label}\033[0m"
        details = " ".join(f"{k}={json.dumps(v, ensure_ascii=True)}" for k, v in (fields | context).items())
        return f"{timestamp.astimezone():%H:%M:%S} {record.levelname:<7} {label} {message}" + (f" | {details}" if details else "")


def configure():
    mode = os.getenv("LOG_FORMAT", "pretty").lower()
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(Formatter(mode, (sys.stderr.isatty() or os.getenv("MIRA_DEV_COLOR") == "1")
                                   and "NO_COLOR" not in os.environ))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
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
