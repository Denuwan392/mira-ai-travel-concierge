import json
from uuid import uuid4

from fastapi.testclient import TestClient
from mira.main import app


def send(client, trip, message, run=None):
    run = run or str(uuid4())
    response = client.post("/api/agent",params={"trip_id":trip},json={
        "threadId":trip,"runId":run,"messages":[{"id":run,"role":"user","content":message}],
        "state":{},"tools":[],"context":[],"forwardedProps":{}})
    response.raise_for_status()
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert events[-1]["type"]=="RUN_FINISHED"
    return next(e["snapshot"]["turn"] for e in reversed(events) if e["type"]=="STATE_SNAPSHOT" and "turn" in e["snapshot"])


def test_owned_persistent_trip_edits_and_replay(app_client):
    trip = app_client.post("/api/trips").json()["id"]
    send(app_client,trip,"We have six days for nature, trains and beaches")
    run = str(uuid4())
    edit = send(app_client,trip,"Add another day in Ella",run)
    assert send(app_client,trip,"Add another day in Ella",run)==edit
    plan = next(c for c in edit["components"] if c["type"]=="JourneyPlan")
    assert len(plan["days"])==7 and any(d["name"]=="Ella" for d in plan["days"])
    history = app_client.get(f"/api/trips/{trip}").json()["history"]
    assert len(history)==2 and history[-1]["surface"][0]["version"]=="v0.9"
    assert app_client.get("/api/trips").json()[0]["id"]==trip
    with TestClient(app) as other:
        other.post("/api/session",json={})
        assert other.get("/api/trips").json()==[]
        assert other.get(f"/api/trips/{trip}").status_code==404


def test_quote_obsolete_after_custom_edit(app_client):
    trip = app_client.post("/api/trips").json()["id"]
    output = send(app_client,trip,"Sigiriya day trip for two adults on 10 January 2027")
    quote = next(c["quote"] for c in output["components"] if c["type"]=="PriceBreakdown")
    assert quote["total"]==315
    send(app_client,trip,"Design a custom journey in Ella")
    assert app_client.get("/api/quotes").json()[0]["current"] is False
    assert app_client.post("/api/bookings/mock",json={"quote":quote["id"]}).json()["status"]=="expired"
    previous = app_client.get(f"/api/trips/{trip}").json()["history"][0]["turn"]
    assert not any(c["type"]=="PriceBreakdown" for c in previous["components"])


def test_day_and_date_actions_persist_in_staff_request(app_client):
    import json
    from conftest import headers
    trip = app_client.post("/api/trips").json()["id"]
    send(app_client,trip,"Six days of nature, trains and beaches")
    selected = send(app_client,trip,"@day 3")
    assert next(c for c in selected["components"] if c["type"]=="InteractiveMap")["selected"]==2
    send(app_client,trip,"@depart 2027-02-11")
    rows = app_client.get("/api/staff/enquiries",headers=headers("staff")).json()
    assert len(rows)==1 and json.loads(rows[0]["trip"])["date"]=="2027-02-11"
    rejected = send(app_client,trip,"@day 99")
    assert not any(c["type"]=="PriceBreakdown" for c in rejected["components"])


def test_grounded_model_selects_only_a_published_passage(app_client,monkeypatch):
    from mira import agent
    from mira.provider import NotebookIntent
    def choose(prompt, previous, destinations, events, evidence):
        key = next(k for k,text in evidence.items() if "Nine Arches Bridge" in text)
        return NotebookIntent(operation="fact",evidence_key=key)
    monkeypatch.setattr(agent,"notebook_intent",choose)
    trip = app_client.post("/api/trips").json()["id"]
    result = send(app_client,trip,"What is the Nine Arches Bridge near Ella?")
    panel = next(c for c in result["components"] if c["type"]=="PolicySnippet")
    assert panel["source"] in result["sources"] and "Nine Arches Bridge" in panel["text"]
    assert panel["text"] in app_client.get("/api/sources/"+panel["source"]).json()["body"]
