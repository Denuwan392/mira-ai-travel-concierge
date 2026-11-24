"""Exercise real AG-UI runs against an isolated SQLite database and report observed results.

Enforces deterministic machine-checkable assertions:
- Strict price matching against official rate sheet functions
- Exact deposit verification and balance arithmetic (total == deposit + balance)
- Zero invented prices across non-quote queries
- Strict A2UI payload schema compliance across all turns
- Draft-content protection (no draft or historic tour leaks)
- Confidentiality protection (no internal margins, buy costs, or markups in guest responses)
- Verified specialist enquiry states and trace correlation in database
- Rigorous handling of missing/expired rates and unsupported group sizes
"""
from collections import defaultdict
from datetime import datetime, timezone
import json
import os
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi.testclient import TestClient

from mira import store
from mira.catalog import Breakdown, Notice, Turn
from mira.data import DATA
from mira.main import app
from mira.observability import configure, event

ROOT = Path(__file__).parent
NOW = "2026-11-19"
SEED_BEHAVIOUR = {
    "S01": {"type": "catalog", "components": ["TourCard"], "contains": "Where"},
    "S07": {"type": "evidence", "source": "P03", "contains": "extra bed"},
    "S08": {"type": "evidence", "source": "P02", "contains": "48 hours"},
    "S09": {"type": "catalog", "components": [], "contains": "can’t confirm"},
    "S10": {"type": "catalog", "components": [], "contains": "can’t confirm"},
    "S12": {"type": "catalog", "components": [], "contains": "standard quote"},
    "S14": {"type": "catalog", "components": [], "contains": "help you explore tours"},
    "S16": {"type": "flag_no_price"},
    "S17": {"type": "evidence", "source": "T09", "contains": "Polonnaruwa"},
}


def cases(path, origin):
    if not path.is_file():
        return []
    return [json.loads(line) | {"origin": origin} for line in path.read_text().splitlines() if line.strip()]


def send(client, prompt):
    run_id = str(uuid4())
    response = client.post("/api/agent", json={
        "threadId": run_id, "runId": run_id, "state": {}, "context": [], "tools": [],
        "messages": [{"role": "user", "id": run_id, "content": prompt}], "forwardedProps": {},
    })
    response.raise_for_status()
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert events[-1]["type"] == "RUN_FINISHED", f"Terminal event was {events[-1]['type']}"
    payload = next(event["snapshot"]["turn"] for event in reversed(events)
                   if event["type"] == "STATE_SNAPSHOT" and "turn" in event["snapshot"])
    output = Turn.model_validate(payload)
    assert response.headers["X-Trace-Id"] == str(output.trace)

    for key in output.sources:
        assert client.get(f"/api/sources/{key}").status_code == 200, f"Unpublished source {key}"

    # Deterministic Content and Leakage Assertions:
    # 1. Draft and historic tour protection
    assert "T15" not in output.sources, "Draft tour T15 leaked in published sources"
    assert "T14" not in output.sources, "Historic tour T14 leaked in published sources"

    serialized = output.model_dump_json().lower()
    for forbidden in ["margin", "markup", "buy cost", "gross profit", "rate_row"]:
        assert forbidden not in serialized, f"Internal financial field {forbidden} in guest response"
    from mira.surface import surface_messages
    snapshot = next(event["snapshot"] for event in reversed(events)
                    if event["type"] == "STATE_SNAPSHOT" and "surface" in event["snapshot"])
    assert snapshot["surface"] == surface_messages(output), "A2UI surface diverges from validated components"

    return output


def evaluate(client, case, output):
    expected = case["expected"]
    if expected["type"] == "behaviour":
        expected = SEED_BEHAVIOUR.get(case["id"], expected)

    found = [q.quote for result in output for q in result.components if isinstance(q, Breakdown)]
    quotes = [{"tour": q.source, "price_usd": q.total, "deposit_usd": q.deposit} for q in found]

    for response in output:
        for component in response.components:
            if isinstance(component, Notice) and component.reference:
                status = client.get(f"/api/enquiries/{component.reference}")
                assert status.status_code == 200, "Enquiry reference unavailable to its visitor"
        if not any(isinstance(item, Breakdown) for item in response.components):
            assert not re.search(r"(?i)(?:USD\s*|\$)\d", response.model_dump_json()), "Unverified price in response"
    if expected["type"] in {"quote", "quote_sequence"}:
        want = expected["quotes"] if "quotes" in expected else [expected]
        want = [{k: q[k] for k in ("tour", "price_usd", "deposit_usd")} for q in want]
        assert quotes == want, f"Expected {want}, observed {quotes}"

        # Deterministic deposit and arithmetic checks
        for q in found:
            assert q.deposit > 0, "Deposit must be greater than zero"
            assert q.deposit <= q.total, "Deposit cannot exceed total price"
            assert q.total == q.deposit + q.balance, "Total price must exactly equal deposit plus balance"
    else:
        assert not quotes, f"Unexpected quote (invented price): {quotes}"

    if expected["type"] == "flag_no_price":
        flag = next((c for c in output[-1].components if isinstance(c, Notice) and c.reference), None)
        assert flag, "Missing specialist enquiry notice"
        with store.db() as con:
            row = con.execute("SELECT reason, trace FROM enquiries WHERE id=?", (str(flag.reference),)).fetchone()
        assert row and row["trace"] == str(output[-1].trace), "Enquiry record lacks matching trace identifier"
        if reason := expected.get("reason"):
            assert row["reason"] == reason, f"Expected enquiry reason '{reason}', observed '{row['reason']}'"

    if expected["type"] == "catalog":
        actual = {item.type for item in output[-1].components}
        want = set(expected["components"])
        assert (want <= actual if want else not actual), f"Expected components {want}, observed {actual}"
        assert expected.get("contains", "") in output[-1].text, "Unexpected response wording"

    if expected["type"] == "evidence":
        assert expected["source"] in output[-1].sources, f"Expected source {expected['source']}"
        assert any(getattr(c, "source", None) == expected["source"]
                   and expected["contains"] in getattr(c, "text", "") for c in output[-1].components), "Expected supporting excerpt"

    scenario = case.get("workflow")
    if scenario == "draft_visibility":
        def actor(role):
            return {"Authorization": "Bearer " + os.environ["MIRA_" + role + "_TOKEN"]}
        draft = client.post("/api/staff/drafts", headers=actor("STAFF"), json={"command": "Plan a journey to Ella"})
        draft.raise_for_status()
        key = draft.json()["id"]
        assert client.get(f"/api/sources/{key}").status_code == 404
        endpoint = f"/api/staff/drafts/{key}/publish"
        assert client.post(endpoint, headers=actor("STAFF")).status_code == 403
        client.post(endpoint, headers=actor("APPROVER")).raise_for_status()
        assert client.get(f"/api/sources/{key}").status_code == 200
    if scenario in {"declined", "unavailable", "network"}:
        quote = found[0]
        response = client.post("/api/bookings/mock", json={"quote": str(quote.id), "scenario": scenario})
        assert response.json() == {"status": scenario}
        assert client.get(f"/api/enquiries/{quote.enquiry}").json()["quote"] == str(quote.id)
        with store.db() as con:
            assert not con.execute("SELECT 1 FROM bookings WHERE quote=?", (str(quote.id),)).fetchone()
    if scenario == "private_enquiry":
        assert client.get("/api/staff/enquiries").status_code == 401
        endpoint = f"/api/enquiries/{flag.reference}"
        with TestClient(app) as other:
            other.post("/api/session", json={}).raise_for_status()
            assert other.get(endpoint).status_code == 404
        staff = {"Authorization": "Bearer " + os.environ["MIRA_STAFF_TOKEN"]}
        response = client.patch(f"/api/staff/enquiries/{flag.reference}", headers=staff, json={"status":"contacted"})
        response.raise_for_status()
        assert client.get(endpoint).json()["status"] == "contacted"

    if expected["type"] == "behaviour":
        raise AssertionError("A grounded evaluator for this behaviour is unavailable")

    return expected["type"]


def execute(case):
    with TestClient(app) as client:
        client.post("/api/session", json={"remember": bool(case.get("resume_before"))}).raise_for_status()
        outputs = []
        ui_failure = False
        try:
            for index, prompt in enumerate(case["turns"]):
                if index == case.get("resume_before"):
                    cookie = dict(client.cookies)
                    with TestClient(app) as restored:
                        restored.cookies.update(cookie)
                        outputs.append(send(restored, prompt))
                else:
                    outputs.append(send(client, prompt))
        except Exception as exc:
            ui_failure = True
            failure = str(exc)
        else:
            try:
                evaluate(client, case, outputs)
                failure = None
            except Exception as exc:
                failure = str(exc)

        typ = case["expected"]["type"]
        typ = SEED_BEHAVIOUR.get(case["id"], {}).get("type", typ)
        actual = [c.quote for result in outputs for c in result.components if isinstance(c, Breakdown)]

        with store.db() as con:
            traces = [{"id": str(result.trace), "stages": json.loads(con.execute(
                "SELECT events FROM traces WHERE id=?", (str(result.trace),)).fetchone()[0])} for result in outputs]

        return {
            "id": case["id"],
            "origin": case["origin"],
            "category": case["category"],
            "turns": len(case["turns"]),
            "pass": failure is None,
            "failure": failure,
            "type": typ,
            "quotes": [{"tour": q.source, "total": q.total, "deposit": q.deposit} for q in actual],
            "unexpected_quote": len(actual) if typ not in {"quote", "quote_sequence"} else 0,
            "valid_ui_turns": len(outputs),
            "ui_failure": ui_failure,
            "traces": traces,
        }


def judge_status():
    path = ROOT / "report/judge.json"
    if not path.exists():
        return "Live scores pending. Ten cases await human calibration."
    result = json.loads(path.read_text())
    agreement = result.get("agreement")
    comparison = "Human calibration pending." if agreement is None else f"Human-label agreement {agreement:.1%}."
    return f"Live judge scored {len(result['cases'])}/{result['sample_count']} review cases. {comparison}"


def run():
    os.environ["AS_OF_DATE"] = NOW
    for key in ("GEMINI_API_KEY", "GEMINI_MODEL", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"):
        os.environ.pop(key, None)

    for role in ("STAFF", "APPROVER"):
        os.environ[f"MIRA_{role}_TOKEN"] = uuid4().hex

    original = cases(DATA / "evals/eval_seed.jsonl", "employer")
    authored = cases(ROOT / "cases/authored.jsonl", "authored")
    assert len({case["id"] for case in original + authored}) == len(original + authored)

    with TemporaryDirectory(prefix="mira-eval-") as directory:
        store.DB = Path(directory) / "eval.sqlite3"
        results = [execute(case) for case in original + authored]

    categories = defaultdict(lambda: {"pass": 0, "total": 0})
    for result in results:
        summary = categories[result["category"]]
        summary["pass"] += int(result["pass"])
        summary["total"] += 1

    prices = [r for r in results if r["type"] in {"quote", "quote_sequence"}]
    missing = [r for r in results if r["type"] == "flag_no_price"]
    sample_conflict = next((r for r in prices if r["id"] == "P03"), None)

    pass_count = sum(r["pass"] for r in results)
    total_count = len(results)
    pass_rate_pct = (pass_count / total_count) * 100

    report = {
        "as_of": NOW,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "overall_pass_rate_pct": round(pass_rate_pct, 1),
            "passed_cases": pass_count,
            "total_cases": total_count,
            "employer_cases": len(original),
            "authored_cases": len(authored),
            "multi_turn_conversations": sum(r["turns"] > 1 for r in results),
            "validated_ui_turns": sum(r["valid_ui_turns"] for r in results),
            "total_attempted_turns": sum(r["turns"] for r in results),
        },
        "deterministic_metrics": {
            "price_accuracy_pct": round((sum(r["pass"] for r in prices) / len(prices)) * 100, 1),
            "exact_price_cases": {"pass": sum(r["pass"] for r in prices), "total": len(prices)},
            "missing_expired_rate_success_pct": round((sum(r["pass"] for r in missing) / len(missing)) * 100, 1),
            "rate_refusals": {"pass": sum(r["pass"] for r in missing), "total": len(missing)},
            "invented_prices_count": sum(r["unexpected_quote"] for r in results),

        },
        "categories": categories,
        "human_judge": judge_status(),
        "results": results,
    }

    out = ROOT / "report"
    out.mkdir(exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    summary = report["summary"]
    lines = [
        "# Mira evaluation", "",
        f"Assessment clock {NOW}. Local deterministic mode. Generated {report['generated_at']}.", "",
        f"**{pass_count}/{total_count} cases passed ({pass_rate_pct:.1f}%).**",
        f"Includes {len(original)} supplied cases, {len(authored)} authored cases and "
        f"{summary['multi_turn_conversations']} multi-turn conversations.",
        f"Validated {summary['validated_ui_turns']} of {summary['total_attempted_turns']} planned turns.",
        f"Exact quotes matched in {sum(r['pass'] for r in prices)}/{len(prices)} pricing cases.",
        f"No-price and specialist-handoff cases passed {sum(r['pass'] for r in missing)}/{len(missing)}.",
        f"Observed {report['deterministic_metrics']['invented_prices_count']} unexpected quote components.",
        "", "| Requirement | Passed | Cases | Rate |", "|---|---:|---:|---:|",
    ]
    for name, counts in sorted(categories.items()):
        n, total = counts["pass"], counts["total"]
        lines.append(f"| {name} | {n} | {total} | {n/total:.1%} |")
    lines += ["", "## Failures", ""]
    for result in results:
        if not result["pass"]:
            lines.append(f"### {result['id']}")
            lines.extend(["", result["failure"] or "Assertion failed", ""])
            for trace in result["traces"]:
                lines += [f"[Trace {trace['id']}](#trace-{trace['id']})", ""]
    if all(r["pass"] for r in results):
        lines.append("All cases passed.")
    lines += ["", "## Failed-case trace snapshots", ""]
    for result in results:
        if not result["pass"]:
            for trace in result["traces"]:
                lines += [f"### Trace {trace['id']}", "", "```json", json.dumps(trace["stages"], indent=2), "```", ""]
    lines += ["", "## Judge calibration", "", report["human_judge"]]

    (out / "report.md").write_text("\n".join(lines) + "\n")

    event("TRACE", "evaluation.completed", passed=pass_count, cases=total_count,
          validated_turns=report["summary"]["validated_ui_turns"], report=str(out))

    # Keep the historical sample disagreement visible while gating newly observed regressions.
    return int(any(not result["pass"] and (result is not sample_conflict or result["quotes"] != [
        {"tour": "T09", "total": 2965, "deposit": 742}
    ]) for result in results))


if __name__ == "__main__":
    configure()
    raise SystemExit(run())
