import asyncio
import json
import logging
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import turn
from mira import main, store
from mira.observability import Formatter, RequestLogging, configure, event, request_id

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
        with socket.create_connection(listener.getsockname(), timeout=2):
            accepted, _ = listener.accept()
            accepted.close()


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
