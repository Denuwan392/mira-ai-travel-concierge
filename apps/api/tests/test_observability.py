import asyncio
import json
import logging
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import headers, quotes, turn
from mira import main, store
from mira.observability import ConsoleHandler, Formatter, RequestLogging, configure, event, request_id, shorten_id

ROOT = Path(__file__).resolve().parents[3]


def formatted(records):
    formatter = Formatter("json", color=True)
    return [json.loads(formatter.format(record)) for record in records]


def test_configuration_and_redaction(monkeypatch, capsys):
    original = logging.getLogger()
    handlers, level = original.handlers[:], original.level
    prefixes = ("uvicorn", "uvicorn.error", "uvicorn.access", "httpx", "httpx2", "httpcore", "google_genai", "opentelemetry", "langfuse", "alembic")
    loggers = [(logger, logger.handlers[:], logger.level, logger.propagate)
               for logger in map(logging.getLogger, prefixes)]
    monkeypatch.setenv("LOG_FORMAT", "json")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("MIRA_DEV_COLOR", "1")
    try:
        configure()
        configure()
        event("PRICING", "pricing.started", level=logging.DEBUG)
        try:
            raise ValueError("traveller@example.test Bearer secret 876-LKR private")
        except ValueError:
            logging.getLogger("google_genai").exception("Request content: %s", "private prompt")
        lines = capsys.readouterr().err.splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["level"] == "DEBUG"
        detail = json.loads(lines[1])
        assert detail["exception_type"] == "ValueError"
        assert any("test_configuration_and_redaction" in frame for frame in detail["frames"])
        assert not any(value in "\n".join(lines) for value in ("traveller@", "Bearer", "876-LKR", "private", "\x1b"))
    finally:
        original.handlers[:] = handlers
        original.setLevel(level)
        for logger, old_handlers, old_level, old_propagate in loggers:
            logger.handlers[:] = old_handlers
            logger.setLevel(old_level)
            logger.propagate = old_propagate


def test_request_rejects_unsuitable_ids_and_redacts_http_exception(caplog):
    service = FastAPI()
    service.add_middleware(RequestLogging)

    @service.get("/fail/{identifier}")
    def fail(identifier: str):
        raise RuntimeError(identifier)

    supplied = "test@example.test"
    response = TestClient(service).get("/fail/private-notes?token=secret", headers={"X-Request-Id": supplied})
    assert response.status_code == 500
    identifier = response.headers["X-Request-Id"]
    assert str(UUID(identifier)) == identifier
    payload = formatted(caplog.records)
    assert [item["event"] for item in payload] == ["http.exception", "http.request"]
    assert all(item["route"] == "/fail/{identifier}" for item in payload)
    assert not any(secret in str(payload) for secret in [supplied, "private-notes", "token=secret"])


def test_parallel_requests_keep_context_through_await():
    async def check():
        service = FastAPI()
        service.add_middleware(RequestLogging)
        both = asyncio.Event()
        observed = []

        @service.get("/check")
        async def inspect():
            observed.append(request_id.get())
            if len(observed) == 2:
                both.set()
            await asyncio.wait_for(both.wait(), 2)
            return {"current": request_id.get()}

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=service), base_url="http://test") as client:
            identifiers = [str(uuid4()), str(uuid4())]
            replies = await asyncio.gather(*(client.get("/check", headers={"X-Request-Id": item}) for item in identifiers))
            assert [reply.json()["current"] for reply in replies] == identifiers
            assert [reply.headers["X-Request-Id"] for reply in replies] == identifiers
            assert request_id.get() is None

    asyncio.run(check())


def test_agent_logs_link_to_local_trace_and_export_failure_is_safe(app_client, monkeypatch, caplog):
    def unavailable():
        raise OSError("token=private-example")

    monkeypatch.setattr(main, "remote_tracing", unavailable)
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "fake")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "fake")
    identifier = str(uuid4())
    app_client.headers["X-Request-Id"] = identifier
    with caplog.at_level(logging.INFO, logger="mira"):
        result = turn(app_client, "Sigiriya day trip for two adults on 10 January 2027")
    with store.db() as conn:
        stages = json.loads(conn.execute("SELECT events FROM traces WHERE id=?", (str(result.trace),)).fetchone()[0])
        quote = conn.execute("SELECT id FROM quotes WHERE trace=?", (str(result.trace),)).fetchone()
    assert quote
    assert next(stage for stage in stages if stage["stage"] == "persistence")["request_id"] == identifier
    events = formatted(caplog.records)
    assert {"workflow.started", "intent.classified", "retrieval.completed", "pricing.completed",
            "turn.persisted", "trace.export_failed", "http.request"} <= {event["event"] for event in events}
    assert all(value["request_id"] == identifier and value["trace_id"] == str(result.trace) for value in events)
    assert not any("private-example" in str(value) or "cost_lkr" in value for value in events)


def test_dev_checks_occupied_port_without_disturbing_owner():
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind(("127.0.0.1", 0))
        except PermissionError:
            import pytest
            pytest.skip("local socket binding is disabled by the test sandbox")
        listener.listen()
        code = '''
import sys
sys.path.insert(0, "scripts")
import dev
dev.SERVICES = (("WEB", int(sys.argv[1]), ".", ()),)
dev.configure()
raise SystemExit(0 if dev.ports_free() else 1)
'''
        result = subprocess.run([sys.executable, "-c", code, str(listener.getsockname()[1])],
                                cwd=ROOT, capture_output=True, text=True, timeout=8)
        assert result.returncode == 1
        assert "port.unavailable" in result.stderr and "lsof" in result.stderr
        try:
            with socket.create_connection(listener.getsockname(), timeout=2):
                accepted, _ = listener.accept()
                accepted.close()
        except PermissionError:
            pass


def test_dev_ctrl_c_and_child_failure(tmp_path):
    child = '''
import pathlib, signal, sys, time
p = pathlib.Path(sys.argv[1])
def stop(*_):
    p.with_suffix(".stopped").touch()
    sys.exit(0)
signal.signal(signal.SIGTERM, stop)
p.touch()
while True:
    time.sleep(0.02)
'''
    code = '''
import sys
sys.path.insert(0, "scripts")
from dev import supervise
raise SystemExit(supervise((("WEB", 0, ".", (sys.executable, "-c", sys.argv[1], sys.argv[2])),)))
'''
    from time import monotonic, sleep

    marker = tmp_path / "ready"
    worker = subprocess.Popen([sys.executable, "-c", code, child, str(marker)], cwd=ROOT)
    try:
        deadline = monotonic() + 5
        while not marker.exists() and worker.poll() is None and monotonic() < deadline:
            sleep(0.02)
        assert marker.exists()
        worker.send_signal(signal.SIGINT)
        assert worker.wait(timeout=8) == 130
        assert marker.with_suffix(".stopped").exists()
    finally:
        if worker.poll() is None:
            worker.terminate()
            worker.wait(timeout=8)
    result = subprocess.run([sys.executable, "-c", code, "raise SystemExit(7)", str(marker)],
                            cwd=ROOT, env=os.environ, timeout=8)
    assert result.returncode == 7


def make_record(component, event_name, fields=None, context=None, level=logging.INFO, exc_info=None):
    record = logging.LogRecord("mira." + component.lower(), level, "test.py", 10, event_name, (), exc_info)
    record.mira_component = component
    record.mira_fields = fields or {}
    record.mira_context = context or {}
    return record


def test_pretty_formatting_and_workflow_grouping():
    formatter = Formatter("pretty", color=False)
    tid = "6a3ca43e-7b19-4b1f-9b21-4f1283628172"
    ctx = {"trace_id": tid, "request_id": "b1234567-1111-2222-3333-444455556666"}

    # Test compact HTTP access log formatting
    http_rec = make_record("API", "http.request", {"method": "POST", "route": "/api/agent", "status": 200, "duration_ms": 61}, ctx)
    http_out = formatter.format(http_rec)
    assert "[API]    POST /api/agent · 200 OK · 61ms" in http_out

    # Test startup log formatting
    ready_rec = make_record("API", "server.ready", {"port": 8000})
    ready_out = formatter.format(ready_rec)
    assert "[API]    Ready on http://127.0.0.1:8000" in ready_out

    # Test workflow group formatting
    records = [
        make_record("AGENT", "workflow.started", {"notebook": False}, ctx),
        make_record("AGENT", "intent.classified", {"intent": "discover", "party_type": "adult_party", "duration_ms": 12}, ctx),
        make_record("RAG", "retrieval.completed", {"documents": 1, "sources": ["T01"], "duration_ms": 5}, ctx),
        make_record("PRICING", "pricing.completed", {"tour_id": "T01", "rate_status": "verified", "duration_ms": 7}, ctx),
        make_record("RAG", "grounding.completed", {"documents": 1, "sources": ["T01"]}, ctx),
        make_record("AGENT", "ui.validated", {"components": 4, "duration_ms": 8}, ctx),
        make_record("TRACE", "turn.persisted", {"quote_id": "q1234567-0000-0000-0000-000000000000", "enquiry": True, "duration_ms": 15}, ctx),
        make_record("AGENT", "workflow.finished", {"outcome": "completed", "duration_ms": 37}, ctx),
    ]
    tree = formatter.format_workflow(records)
    assert "┌─ MIRA AGENT · Day tour" in tree
    assert "├─ INTENT   Day tour · adult party" in tree
    assert "├─ RAG      Retrieved T01 · 1 document" in tree
    assert "├─ PRICE    Verified quote · T01 · 7ms" in tree
    assert "├─ GROUND   Sources attached · T01" in tree
    assert "├─ UI       4 components validated" in tree
    assert "├─ TRACE    Quote saved · enquiry created" in tree
    assert "└─ DONE     37ms · trace: 6a3ca43e…" in tree


def test_json_formatting_and_validity():
    formatter = Formatter("json", color=True)
    tid = "6a3ca43e-7b19-4b1f-9b21-4f1283628172"
    ctx = {"trace_id": tid, "request_id": "b1234567-1111-2222-3333-444455556666"}
    rec = make_record("AGENT", "intent.classified", {"intent": "discover", "party_type": "adult_party"}, ctx)
    line = formatter.format(rec)
    assert "\x1b" not in line
    data = json.loads(line)
    assert data["component"] == "AGENT"
    assert data["event"] == "intent.classified"
    assert data["trace_id"] == tid
    assert data["request_id"] == ctx["request_id"]
    assert data["intent"] == "discover"


def test_uuid_shortening_display_only():
    raw_uuid = "6a3ca43e-7b19-4b1f-9b21-4f1283628172"
    assert shorten_id(raw_uuid, debug=False) == "6a3ca43e…"
    assert shorten_id(raw_uuid, debug=True) == raw_uuid
    assert shorten_id("short") == "short"
    assert shorten_id(None) == ""

    # In pretty INFO mode, UUIDs are shortened in workflow output
    ctx = {"trace_id": raw_uuid}
    records = [
        make_record("AGENT", "workflow.started", {}, ctx),
        make_record("AGENT", "workflow.finished", {"outcome": "completed", "duration_ms": 42}, ctx),
    ]
    info_formatter = Formatter("pretty", color=False, debug=False)
    out_info = info_formatter.format_workflow(records)
    assert "trace: 6a3ca43e…" in out_info
    assert raw_uuid not in out_info

    # In pretty DEBUG mode, full trace ID is shown
    debug_formatter = Formatter("pretty", color=False, debug=True)
    out_debug = debug_formatter.format_workflow(records)
    assert f"trace: {raw_uuid}" in out_debug


def test_no_accidental_sensitive_data_exposure():
    formatter = Formatter("pretty", color=False)
    rec = make_record("PRICING", "pricing.completed", {"tour_id": "T01", "rate_status": "verified", "cost_lkr": 50000, "bearer_token": "secret"})
    out = formatter.format(rec)
    assert "secret" not in out


def test_concurrent_request_isolation():
    import io
    import threading
    stream = io.StringIO()
    handler = ConsoleHandler(stream=stream, style="pretty", debug=False)
    formatter = Formatter("pretty", color=False, debug=False)
    handler.setFormatter(formatter)

    tid_a = "aaaaaaaa-1111-2222-3333-444455556666"
    tid_b = "bbbbbbbb-1111-2222-3333-444455556666"

    def run_worker(tid, intent_name):
        ctx = {"trace_id": tid}
        handler.emit(make_record("AGENT", "workflow.started", {"intent": intent_name}, ctx))
        time.sleep(0.01)
        handler.emit(make_record("AGENT", "intent.classified", {"intent": intent_name, "party_type": "adult_party"}, ctx))
        time.sleep(0.01)
        handler.emit(make_record("AGENT", "workflow.finished", {"outcome": "completed", "duration_ms": 25}, ctx))

    t1 = threading.Thread(target=run_worker, args=(tid_a, "discover"))
    t2 = threading.Thread(target=run_worker, args=(tid_b, "custom"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    output = stream.getvalue()
    assert "trace: aaaaaaaa…" in output
    assert "trace: bbbbbbbb…" in output
    blocks = [b.strip() for b in output.split("┌─ MIRA AGENT") if b.strip()]
    assert len(blocks) == 2
    assert any("Day tour" in b and "trace: aaaaaaaa…" in b for b in blocks)
    assert any("Custom itinerary" in b and "trace: bbbbbbbb…" in b for b in blocks)


def test_exception_formatting():
    try:
        raise ValueError("simulated test error")
    except ValueError:
        exc_info = sys.exc_info()

    rec = make_record("ERROR", "workflow.node_failed", {"node": "interpret"}, level=logging.ERROR, exc_info=exc_info)
    info_formatter = Formatter("pretty", color=False, debug=False)
    info_out = info_formatter.format(rec)
    assert "[ERROR]  " in info_out
    assert "workflow.node_failed" in info_out
    assert "ValueError" in info_out

    debug_formatter = Formatter("pretty", color=False, debug=True)
    debug_out = debug_formatter.format(rec)
    assert "Traceback (most recent call last):" in debug_out
    assert "ValueError: simulated test error" in debug_out


def test_non_tty_and_no_color_behavior(monkeypatch):
    rec = make_record("API", "http.request", {"method": "GET", "route": "/api/health", "status": 200, "duration_ms": 5})

    monkeypatch.setenv("NO_COLOR", "1")
    formatter_nocolor = Formatter("pretty", color=False)
    assert "\x1b" not in formatter_nocolor.format(rec)

    monkeypatch.delenv("NO_COLOR", raising=False)
    formatter_color = Formatter("pretty", color=True)
    assert "\x1b[" in formatter_color.format(rec)


def test_clean_process_shutdown():
    import io
    stream = io.StringIO()
    handler = ConsoleHandler(stream=stream, style="pretty", debug=False)
    formatter = Formatter("pretty", color=False, debug=False)
    handler.setFormatter(formatter)

    tid = "cccccccc-1111-2222-3333-444455556666"
    ctx = {"trace_id": tid}
    handler.emit(make_record("AGENT", "workflow.started", {}, ctx))
    handler.emit(make_record("AGENT", "intent.classified", {"intent": "discover"}, ctx))
    assert tid in handler._buffers
    assert stream.getvalue() == ""

    handler.flush_all()
    assert tid not in handler._buffers
    assert "trace: cccccccc…" in stream.getvalue()


def test_one_trace_per_traveller_turn_with_child_stages(app_client):
    """Verify that every traveller turn produces a unique SQLite trace with all required stages:
    intent, retrieval, pricing, validated_ui, persistence.
    """
    res1 = turn(app_client, "Sigiriya day trip for two adults on 10 January 2027")
    res2 = turn(app_client, "Actually, can we go on 15 January 2027 instead?")
    assert res1.trace != res2.trace

    with store.db() as conn:
        t1_row = conn.execute("SELECT events FROM traces WHERE id=?", (str(res1.trace),)).fetchone()
        t2_row = conn.execute("SELECT events FROM traces WHERE id=?", (str(res2.trace),)).fetchone()

    assert t1_row and t2_row
    stages1 = [s["stage"] for s in json.loads(t1_row[0])]
    stages2 = [s["stage"] for s in json.loads(t2_row[0])]
    for required in ["interpret", "retrieval", "pricing", "validated_ui", "persistence"]:
        assert required in stages1, f"Missing stage {required} in turn 1"
        assert required in stages2, f"Missing stage {required} in turn 2"


def test_quote_to_trace_bidirectional_linkage_and_staff_inspection(app_client):
    """Verify saved quote references the exact trace that created it, and staff
    can inspect the full linked trace events through /api/staff/enquiries/{id}.
    """
    res = turn(app_client, "Sigiriya day trip for two adults on 10 January 2027")
    [q] = quotes(res)

    with store.db() as conn:
        q_row = conn.execute("SELECT trace FROM quotes WHERE id=?", (str(q.id),)).fetchone()
        assert q_row and q_row["trace"] == str(res.trace)

        e_row = conn.execute("SELECT id, trace FROM enquiries WHERE quote=?", (str(q.id),)).fetchone()
        assert e_row and e_row["trace"] == str(res.trace)

    enquiry_detail = app_client.get(f"/api/staff/enquiries/{e_row['id']}", headers=headers("staff")).json()
    assert enquiry_detail["trace"] == str(res.trace)
    assert any(s["stage"] == "pricing" and s["outcome"] == "verified" for s in enquiry_detail["events"])
    assert enquiry_detail["finance"]["cost_lkr"] == "66000"


def test_failed_price_trace_safely_recorded(app_client):
    """Verify that a pricing refusal (e.g. missing amount) generates a trace
    recording the exact failure reason without exposing internal cost fields to the traveller.
    """
    # T12 for 1 adult requires single room at H04, which is missing in rate sheet
    res = turn(app_client, "Treasures of Sri Lanka for 1 adult on 10 April 2027")
    assert not quotes(res)
    assert any(c.type == "EnquiryNotice" for c in res.components)

    with store.db() as conn:
        t_row = conn.execute("SELECT events FROM traces WHERE id=?", (str(res.trace),)).fetchone()
        e_row = conn.execute("SELECT reason FROM enquiries WHERE trace=?", (str(res.trace),)).fetchone()

    events = json.loads(t_row[0])
    pricing_stage = next(s for s in events if s["stage"] == "pricing")
    assert pricing_stage["outcome"] == "missing_amount"
    assert e_row["reason"] == "missing_amount"


def test_langfuse_mock_export_structure_and_sanitization(app_client, monkeypatch):
    """Verify that Langfuse export builds correlated observation spans with sanitized metadata
    and invokes client.flush().
    """
    spans = []

    class MockObservation:
        def __init__(self, name, metadata=None, trace_context=None, as_type="span", input=None, output=None, **kwargs):
            self.name = name
            self.metadata = metadata
            self.trace_context = trace_context
            self.as_type = as_type
            self.input = input
            self.output = output

        def __enter__(self):
            spans.append({
                "name": self.name,
                "as_type": self.as_type,
                "input": self.input,
                "output": self.output,
                "metadata": self.metadata,
                "trace_context": self.trace_context,
            })
            return self

        def __exit__(self, *args):
            pass

    class MockLangfuse:
        def __init__(self):
            self.flushed = False

        def start_as_current_observation(self, name, metadata=None, trace_context=None, **kwargs):
            return MockObservation(name, metadata=metadata, trace_context=trace_context, **kwargs)

        def flush(self):
            self.flushed = True

    mock_client = MockLangfuse()
    monkeypatch.setattr(main, "remote_tracing", lambda: mock_client)
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-mock")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-mock")

    res = turn(app_client, "Sigiriya day trip for two adults on 10 January 2027")
    assert mock_client.flushed is True
    root_spans = [s for s in spans if s["name"] == "mira.turn"]
    assert len(root_spans) == 1
    assert root_spans[0]["trace_context"]["trace_id"] == res.trace.hex
    assert root_spans[0]["as_type"] == "agent"
    assert root_spans[0]["input"] == {"message": "Sigiriya day trip for two adults on 10 January 2027"}
    assert root_spans[0]["output"]["outcome"] == "completed"

    # Child stages and typed observations
    child_types = {s["name"]: s["as_type"] for s in spans if s["name"] != "mira.turn"}
    assert child_types["interpret"] == "chain"
    assert child_types["retrieval"] == "retriever"
    assert child_types["pricing"] == "tool"
    assert "persistence" in child_types

    # Privacy check: No sensitive substrings in span metadata
    for span in spans:
        meta = span.get("metadata") or {}
        for k, v in meta.items():
            assert "cost_lkr" not in k
            assert "token" not in k
            assert "Bearer" not in str(v)

