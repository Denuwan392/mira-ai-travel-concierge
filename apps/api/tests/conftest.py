from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from mira import store
from mira.main import app

TODAY = date(2026, 11, 19)


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB", tmp_path / "demo.sqlite3")
    monkeypatch.setenv("AS_OF_DATE", TODAY.isoformat())
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setenv("MIRA_ADMIN_PASSWORD", "Admin#2026!Compass")
    for role in ("STAFF", "EDITOR", "APPROVER"):
        monkeypatch.setenv(f"MIRA_{role}_TOKEN", role.lower() * 8)
    with TestClient(app) as client:
        client.post("/api/session", json={"remember": False}).raise_for_status()
        yield client


def headers(actor):
    return {"Authorization": f"Bearer {actor * 8}"}


def turn(client, content, run=None):
    import json
    from mira.catalog import Turn

    run = run or str(uuid4())
    response = client.post("/api/agent", json={
        "threadId": run, "runId": run, "state": {}, "tools": [], "context": [],
        "messages": [{"role": "user", "id": run, "content": content}], "forwardedProps": {},
    })
    response.raise_for_status()
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert events[-1]["type"] == "RUN_FINISHED", events[-1]
    output = next(event["snapshot"]["turn"] for event in reversed(events)
                  if event["type"] == "STATE_SNAPSHOT" and "turn" in event["snapshot"])
    assert response.headers["X-Trace-Id"] == output["trace"]
    return Turn.model_validate(output)


def quotes(output):
    from mira.catalog import Breakdown
    return [item.quote for item in output.components if isinstance(item, Breakdown)]
