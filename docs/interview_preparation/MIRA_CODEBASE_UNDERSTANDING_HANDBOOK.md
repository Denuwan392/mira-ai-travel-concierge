# Mira · Developer codebase and live demo defense

Evidence edition · 26 November 2026 · HEAD 75d40b8 matches the local origin/main reference. Initially clean worktree. No submission receipt or submission tag establishes the exact delivered revision.

## Contents

- [Part 0 · Emergency preparation](#part-0)
- [Part 1 · One traveller turn](#part-1)
- [Part 2 · Navigate by responsibility](#part-2)
- [Part 3 · File atlas](#part-3)
- [Part 4 · Read the functions in execution context](#part-4)
- [Part 5 · Follow nine workflows](#part-5)
- [Part 6 · Graph, prompts and state](#part-6)
- [Part 7 · Work a quote by hand](#part-7)
- [Part 8 · Ground an answer](#part-8)
- [Part 9 · From a validated turn to pixels](#part-9)
- [Part 10 · Persistence and access](#part-10)
- [Part 11 · Evidence, evaluation and traces](#part-11)
- [Part 12 · Live coding practice](#part-12)
- [Part 13 · Oral examination](#part-13)
- [Part 14 · Debug during the demo](#part-14)
- [Part 15 · 20-minute presentation and 10-minute defense](#part-15)
- [Part 16 · Assignment traceability](#part-16)
- [Part 17 · Second-screen lookup](#part-17)

<a id="part-0"></a>

## Part 0 · Emergency preparation

Friday 27 November 2026, 11:30–12:00 Asia/Colombo. Learn the quick-booker first. At the end of rehearsal you should be able to predict USD 315, point to the multiplication that pays for a child’s bed, then find the enquiry by its reference.

**30 minutes** — 8 min on the graph and HTTP entry, 12 min on T01 and Q-1043, 5 min on the failed trace, 5 min saying the handoff aloud.

**One hour** — add 15 min on the workspace hook and component contract, 10 min on a family conversation, 5 min on the approval gate.

**Two hours** — add one timed 20-minute demo, 20 min on exercises 1–5 and 20 min answering questions with the editor closed. Reopen the file whenever an answer depends on a condition.

**Four hours** — add a second rehearsal with unexpected dates, a staff session in another browser, a mock decline and retry, then practise the remaining edits and replay your weakest explanation.

**Keep open** — workspace on port 5175, a separate staff login, the archived report, the tariff function and its tests. Use synthetic traveller details. Keep the assessment clock at 2026-11-19. A browser refresh retains a notebook only while its caller can still access it.

**First commands** — `make dev`, `curl -fsS http://127.0.0.1:8000/api/health`, `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests/test_pricing.py`. Run `make eval` in a rehearsal copy because it rewrites the report. Never reset the live demo database to troubleshoot a price.

### Ranked editor tabs

1. **P0** `apps/api/mira/data.py:226–324` · `calculate`. Where a money decision becomes binding. Start at the two room counts and work outward.
2. **P0** `apps/api/mira/agent_workflow/routing.py:5–12` (facade `agent.py`) · `quote_route`. The interview hinges on knowing when Mira has enough information to quote.
3. **P0** `apps/api/mira/main.py:449–525` · `agui`. The trust boundary between the browser, graph, staff and database.
4. **P0** `apps/ceylon-compass/workspace/useConversation.js:49–79` · `send`. Tracks the active notebook, retry identity and consent in the demonstrated workspace.
5. **P0** `apps/ceylon-compass/src/lib/live/service.ts:42–68` · `run`. The shared AG-UI transport. Use it to distinguish a stream error from an invalid snapshot.
6. **P0** `apps/ceylon-compass/workspace/Workspace.jsx:3034` · `PriceBreakdownPanel`. The canonical demo screen. Its quote compatibility checks can hide a price after a party edit.
7. **P0** `apps/api/mira/catalog.py:98–157` · `PublicQuote`, `Turn`. The public financial contract and the discriminated component union.
8. **P0** `apps/api/mira/rates_repository.py:16–43` · `current_rates`. Binds the quote to exact workbook bytes.
9. **P1** `apps/api/mira/store.py:82–98` · `published_records`. Explains migrations, persistence and immediate visibility of published drafts.
10. **P1** `apps/api/mira/surface.py:12–43` · `surface_messages`. Transforms typed components into an ordered A2UI layout.
11. **P1** `apps/ceylon-compass/src/lib/live/surface.ts:54–89` · `readSurface`. Checks layout references before React can use them.
12. **P1** `apps/api/mira/provider.py:81–118` · `rank`. Limits Gemini to structured choices and records fallback.
13. **P1** `evals/runner.py:168–213` · `execute`. Replays real HTTP turns and exposes the precise failed assertion.
14. **P1** `apps/api/tests/test_pricing.py:13–63` · `test_exact_quote`. Independent expected totals, age limits and workbook discrepancies.
15. **P1** `apps/api/mira/auth.py:286–382` · `get_current_user_optional`. Binds account identity to an active session.
16. **P1** `apps/api/mira/search.py:159–180` · `filter_tours`. Constrains the candidate set before model ranking.
17. **P1** `apps/api/mira/observability.py:99–114` · `sanitize_value`. Determines what may leave the server in trace metadata.
18. **P1** `apps/ceylon-compass/src/components/staff/StaffConsole.tsx:207` · `StaffConsole`. The reviewer can follow a quote into the private operational console.
19. **P1** `evals/judge.py:223–369` · `judge`. Separates automated judgements from agreement with human labels.
20. **P1** `apps/api/mira/planner.py:12–51` · `get_grounded_day_experience`. Connects each custom day to destination evidence.

<a id="part-1"></a>

## Part 1 · Build My Mental Model of the System

### Conceptual Overview

A traveller types a message in the browser. Mira’s backend runs a **5-node LangGraph workflow** that separates **AI-assisted classification/ranking** (optional Gemini) from **deterministic business logic** (published Markdown retrieval, Excel rate-sheet pricing, strict Pydantic/Zod UI validation, and atomic SQLite persistence).

```text
[Traveller Browser :5175]
   │  POST /api/agent?trip_id=... (AG-UI SSE, HttpOnly mira_session cookie)
   ▼
[FastAPI Boundary: main.py:agui] ──► [LangGraph 5-Node Pipeline]
                                         1. interpret  (rules + optional Gemini NotebookIntent)
                                         2. retrieve   (published_records + filter_tours + optional Gemini rank)
                                         3. quote_route (deterministic Python guard)
                                         4. quote_node (deterministic data.calculate + rate_snapshots)
                                         5. compose    (Turn + A2UI v0.9 surface_messages)
                                         6. save       (SQLite BEGIN IMMEDIATE + Langfuse export)
   │  SSE STATE_SNAPSHOT { turn, surface } + X-Trace-Id
   ▼
[Frontend Zod Gate: entry() + readSurface()] ──► [Workspace.jsx / PriceBreakdownPanel]
```

### Layer-by-Layer Separation of Concerns

| Concern | Where It Lives | Controlled By | Works Without Gemini? |
| :--- | :--- | :--- | :---: |
| **Control Flow** | `agent_workflow/graph.py:builder` (`START → interpret → retrieve → quote_route → quote/compose → save → END`) | **Deterministic Python** | Yes |
| **AI-Controlled Decisions** | `provider.py:rank` (top 3 tour IDs) & `provider.py:notebook_intent` (operation, destinations, optional panels) | **Gemini Structured Output** (strictly validated against known IDs) | Falls back to `search.py:rank_filtered_tours` & regex rules |
| **Pricing & Deposits** | `data.py:calculate`, `rates_repository.py:current_rates` | **Deterministic Python + Excel SHA-256** | Yes (100% deterministic) |
| **Content Grounding** | `data.py:content`, `store.py:published_records`, `planner.py:get_grounded_day_experience` | **Deterministic Markdown + DB published drafts** | Yes |
| **UI Validation** | Backend `catalog.py:Turn` (Pydantic v2) + Frontend `catalog.ts:Turn` & `surface.ts:readSurface` (Zod) | **Strict Schema Contracts** | Yes |
| **Persistent Data** | SQLite (`.mira/demo.sqlite3` or `.mira/mira.sqlite3`) via `store.py` | **SQLite WAL + Alembic** | Yes |
| **Temporary Run State** | `working = ContextVar("working")` in `agent_workflow/state.py` | **Per-request Python ContextVar** (discarded after turn) | Yes |
| **Security Boundaries** | `main.py:website` (Origin), `visitor` (cookie), `role` (staff/approver/admin), `PublicQuote` allowlist | **FastAPI Dependencies & Pydantic** | Yes |

### System Startup Sequence (`make dev`)

1. `make dev` runs `./scripts/dev.sh`.
2. `dev.sh` loads `.env` (preserving CLI overrides like `MIRA_DB`), sets `AS_OF_DATE=2026-11-19`, `PYTHONPATH=$PWD/apps/api`, checks ports (`scripts/dev.py --check-ports`), runs `./scripts/setup.sh`, builds the standalone workspace (`npm --prefix apps/ceylon-compass run workspace:build`), and launches `scripts/dev.py`.
3. `scripts/dev.py` supervises three processes:
   - **FastAPI Backend (`:8000`)** — runs `store.init()` (Alembic migrations to `head`), exposes `/api/health`, `/api/agent`, `/api/trips`, `/api/staff/*`, `/api/auth/*`.
   - **Next.js Editorial App (`:3000`)** — serves marketing pages and proxies `/api/*` to `:8000` and `/workspace/*` to `:5175`.
   - **Ceylon Compass Vite App (`:5175`)** — serves the canonical demo workspace at `http://127.0.0.1:5175/workspace/index.html` and `/staff`.

<a id="part-2"></a>

## Part 2 · Directory-Level Understanding

```text
intern_assignment/
├── apps/
│   ├── api/mira/                     # [Backend & AI Layer] FastAPI, LangGraph, pricing, auth, DB
│   │   ├── migrations/versions/      # [Data Layer] 6 Alembic migrations (0001_catalogue .. 0006_enquiry_contact_fields)
│   │   ├── data.py                   # [P0] Markdown loader, public_text sanitizer, deterministic pricing engine
│   │   ├── agent.py                  # [P0] Backward-compatible 50-line facade re-exporting agent_workflow.*
│   │   ├── agent_workflow/           # [P0] Modularized LangGraph workflow package (15 focused modules)
│   │   │   ├── graph.py, state.py, routing.py, facade.py
│   │   │   ├── interpret.py, retrieve.py, quote.py, enquiry.py, compose.py, persistence.py, replay.py
│   │   │   └── parsing.py, constants.py, logging_utils.py, __init__.py
│   │   ├── main.py                   # [P0] FastAPI routes, AG-UI SSE endpoint, RBAC, booking, staff endpoints
│   │   ├── catalog.py                # [P0] Strict Pydantic v2 Turn & component union (PublicQuote allowlist)
│   │   ├── rates_repository.py       # [P0] SHA-256 rate_snapshots cache for Excel workbook
│   │   ├── store.py                  # [P1] SQLite WAL connection, Alembic init, published_records overlay
│   │   ├── provider.py               # [P1] Gemini structured-output wrapper with fallback & token tracking
│   │   ├── surface.py                # [P1] Translates validated Turn into A2UI v0.9 surface messages
│   │   ├── auth.py                   # [P1] Argon2id hashing, user_sessions, RBAC require_role
│   │   ├── search.py                 # [P1] Deterministic constraint extraction, filter_tours, rank_filtered_tours
│   │   ├── observability.py          # [P1] Structured logging + PII/secret sanitizer (sanitize_value)
│   │   ├── planner.py                # [P1] Source-grounded multi-day itinerary builder
│   │   ├── accommodation.py          # [P2] Hotel-specific question grounding helper
│   │   ├── guide.py                  # [P2] Public travel-guide/catalogue serializer
│   │   └── itinerary_parser.py       # [P2] Parses tour Markdown day headings & inclusions
│   ├── api/tests/                    # [Testing Layer] 222 pytest unit & HTTP integration tests
│   ├── ceylon-compass/
│   │   ├── workspace/                # [P0 Frontend] Canonical standalone demo UI (Workspace.jsx, useConversation.js)
│   │   └── src/
│   │       ├── lib/live/             # [P0/P1 Frontend] AG-UI HttpAgent (service.ts), Zod Turn (catalog.ts), A2UI check (surface.ts)
│   │       └── components/staff/     # [P1 Frontend] StaffConsole.tsx (enquiries, drafts, traces, evals)
│   └── web/                          # [Frontend / MCP] Next.js editorial app + stdio MCP server (mcp/server.mjs)
├── GenAI-Intern-Take-Home-Assignment/
│   └── ceylon-compass-dataset/       # [Read-Only Dataset] Tours, destinations, policies, rate_sheet_2026-27.xlsx, eval_seed.jsonl
├── evals/                            # [Evaluation Layer] runner.py, judge.py, cases/, report/report.md, report/mcp_smoke.json
├── scripts/                          # [Infra Layer] dev.sh, dev.py, setup.sh, init_demo_db.py, reset_demo.py, test-mcp.sh
└── docs/                             # [Documentation] Architecture, system audits, interview_preparation/
```

### Repository Navigation Index

| If I need to change or inspect... | Where should I look? |
| :--- | :--- |
| AI response behavior & routing | `apps/api/mira/agent_workflow/` (`interpret.py`, `retrieve.py`, `routing.py`, `compose.py`) |
| LLM model, timeout, or structured schema | `apps/api/mira/provider.py` (`generate_structured`, `rank`, `notebook_intent`) & `.env` |
| Quote margin, deposit, FX, or child pricing | `apps/api/mira/data.py` (`calculate`) & `rate_sheet_2026-27.xlsx` (`Settings` tab) |
| Missing/expired rate behavior | `apps/api/mira/data.py` (`calculate`) & `apps/api/mira/agent_workflow/` (`quote.py`, `compose.py`) |
| Tour filtering & deterministic ranking | `apps/api/mira/search.py` (`extract_search_constraints`, `filter_tours`, `rank_filtered_tours`) |
| Custom multi-day itinerary grounding | `apps/api/mira/planner.py` (`get_grounded_day_experience`) |
| Public vs internal quote fields | `apps/api/mira/catalog.py` (`PublicQuote`) & `apps/api/mira/agent_workflow/quote.py` (`quote_node`) |
| UI component rendering (canonical demo) | `apps/ceylon-compass/workspace/Workspace.jsx` (`PriceBreakdownPanel`, `TravellerPickerPanel`) |
| Frontend stream & Zod validation | `apps/ceylon-compass/src/lib/live/service.ts` (`run`) & `surface.ts` (`readSurface`) |
| Session memory & notebook persistence | `apps/ceylon-compass/workspace/useConversation.js` (`send`) & `apps/api/mira/agent_workflow/persistence.py` (`persist`) |
| Staff permissions & approver publish gate | `apps/api/mira/main.py` (`role`, `publish`) & `apps/api/mira/auth.py` (`require_role`) |
| Tracing & PII redaction | `apps/api/mira/observability.py` (`sanitize_value`) & `apps/api/mira/main.py` (`export_trace`) |
| Evaluation runner & metrics | `evals/runner.py` (`execute`, `run`), `evals/judge.py`, `evals/report/report.md` |
| Database schema & migrations | `apps/api/mira/store.py` & `apps/api/mira/migrations/versions/0001..0006` |

<a id="part-3"></a>

## Part 3 · File atlas

### 1. apps/api/mira/data.py

**P0** · Where a money decision becomes binding. Start at the two room counts and work outward. Start at `apps/api/mira/data.py:170–242` · `calculate`.

Related definitions: `parse_rates`, `number`, `one`, `as_of`, `round_up`, `price`, `calculate`, `content`, `published`, `public_text`

Imports to recognize: `import hashlib`, `import os`, `import re`, `pathlib`, `xml.etree.ElementTree`, `zipfile`, `dataclasses`. Inspect alongside `apps/web/tests/live-pricing.spec.ts`.

### 2. apps/api/mira/agent.py & apps/api/mira/agent_workflow/

**P0** · `agent.py` is now a 50-line backward-compatible facade re-exporting all workflow symbols from `apps/api/mira/agent_workflow/`. Start at `apps/api/mira/agent_workflow/routing.py:5–12` · `quote_route` and `apps/api/mira/agent_workflow/graph.py:13–24` · `builder`.

Related definitions: `interpret` (`interpret.py`), `retrieve` (`retrieve.py`), `quote_route` (`routing.py`), `quote_node` (`quote.py`), `quote_enquiry` & `matching_enquiry` (`enquiry.py`), `compose` (`compose.py`), `persist` & `save` (`persistence.py`), `load_context_and_replay` (`replay.py`), `facade_attr` (`facade.py`).

Imports to recognize: `langgraph.graph`, `contextvars`, `asyncio`, `langchain_core.messages`. Inspect alongside `apps/api/mira/main.py`.

### 3. apps/api/mira/main.py

**P0** · The trust boundary between the browser, graph, staff and database. Start at `apps/api/mira/main.py:417–491` · `agui`.

Related definitions: `agui`, `visitor`, `website`, `role`, `session`, `notebook`, `quote_current`, `booking`, `generate`, `review_draft`, `publish`, `follow_up`, `export_trace`

Imports to recognize: `import asyncio`, `import hmac`, `import logging`, `import json`, `import os`, `import re`, `import secrets`.

### 4. apps/ceylon-compass/workspace/useConversation.js

**P0** · Tracks the active notebook, retry identity and consent in the demonstrated workspace. Start at `apps/ceylon-compass/workspace/useConversation.js:49` · `send`.


Imports to recognize: `import { useEffect, useRef, useState } from "react";`, `import { api, entry, run, session } from "@/lib/live/service";`. Inspect alongside `apps/api/tests/test_acceptance_scenarios.py`.

### 5. apps/ceylon-compass/src/lib/live/service.ts

**P0** · The shared AG-UI transport. Use it to distinguish a stream error from an invalid snapshot. Start at `apps/ceylon-compass/src/lib/live/service.ts:42` · `run`.


Imports to recognize: `import { reportFailure } from "../error-capture";`, `import { Turn } from "./catalog";`, `import { readSurface } from "./surface";`. Inspect alongside `apps/api/tests/conftest.py`.

### 6. apps/ceylon-compass/workspace/Workspace.jsx

**P0** · The canonical demo screen. Its quote compatibility checks can hide a price after a party edit. Start at `apps/ceylon-compass/workspace/Workspace.jsx:3034` · `PriceBreakdownPanel`.


Imports to recognize: `import React, { useState, useEffect, useLayoutEffect, useRef, useCallback, createContext, useContext } from "r`, `import { createRoot } from "react-dom/client";`, `import { useConversation } from "./useConversation";`.

### 7. apps/api/mira/catalog.py

**P0** · The public financial contract and the discriminated component union. Start at `apps/api/mira/catalog.py:71–84` · `PublicQuote`.


Imports to recognize: `typing`, `uuid`, `datetime`, `pydantic`. Inspect alongside `apps/api/mira/agent.py`.

### 8. apps/api/mira/rates_repository.py

**P0** · Binds the quote to exact workbook bytes. Start at `apps/api/mira/rates_repository.py:11–26` · `current_rates`.

Related definitions: `current_rates`

Imports to recognize: `hashlib`, `xml.etree.ElementTree`, `zipfile`, `.`, `.data`, `.store`. Inspect alongside `apps/api/mira/agent.py`.

### 9. apps/api/mira/store.py

**P1** · Explains migrations, persistence and immediate visibility of published drafts. Start at `apps/api/mira/store.py:61–71` · `published_records`.

Related definitions: `db`, `init`, `published_records`, `is_current_notebook_turn`

Imports to recognize: `import json`, `import os`, `import sqlite3`, `contextlib`, `pathlib`. Inspect alongside `apps/api/tests/test_enquiry_identity_lifecycle.py`.

### 10. apps/api/mira/surface.py

**P1** · Transforms typed components into an ordered A2UI layout. Start at `apps/api/mira/surface.py:8–25` · `surface_messages`.

Related definitions: `surface_messages`

Imports to recognize: `.catalog`. Inspect alongside `apps/api/mira/agent.py`.

### 11. apps/ceylon-compass/src/lib/live/surface.ts

**P1** · Checks layout references before React can use them. Start at `apps/ceylon-compass/src/lib/live/surface.ts:54` · `readSurface`.


Imports to recognize: `import { z } from "zod/v4";`, `import type { Turn } from "./catalog";`. Inspect alongside `apps/ceylon-compass/src/lib/live/service.ts`.

### 12. apps/api/mira/provider.py

**P1** · Limits Gemini to structured choices and records fallback. Start at `apps/api/mira/provider.py:61–97` · `rank`.

Related definitions: `model_available`, `generate_structured`, `rank`, `notebook_intent`

Imports to recognize: `import logging`, `import os`, `time`, `typing`, `pydantic`, `.observability`. Inspect alongside `apps/api/tests/test_agent_live.py`.

### 13. evals/runner.py

**P1** · Replays real HTTP turns and exposes the precise failed assertion. Start at `evals/runner.py:168–213` · `execute`.

Related definitions: `execute`, `run`

Imports to recognize: `collections`, `datetime`, `import json`, `import os`, `import re`, `pathlib`, `tempfile`. Inspect alongside `apps/api/tests/test_accommodation_intent.py`.

### 14. apps/api/tests/test_pricing.py

**P1** · Independent expected totals, age limits and workbook discrepancies. Start at `apps/api/tests/test_pricing.py:21–23` · `test_exact_quote`.


Imports to recognize: `dataclasses`, `datetime`, `decimal`, `import pytest`, `mira.data`, `conftest`.

### 15. apps/api/mira/auth.py

**P1** · Binds account identity to an active session. Start at `apps/api/mira/auth.py:262–340` · `get_current_user_optional`.


Imports to recognize: `import base64`, `import json`, `import logging`, `import os`, `import re`, `import secrets`, `datetime`. Inspect alongside `apps/api/mira/main.py`.

### 16. apps/api/mira/search.py

**P1** · Constrains the candidate set before model ranking. Start at `apps/api/mira/search.py:153–174` · `filter_tours`.


Imports to recognize: `import re`. Inspect alongside `apps/api/mira/agent.py`.

### 17. apps/api/mira/observability.py

**P1** · Determines what may leave the server in trace metadata. Start at `apps/api/mira/observability.py:104–112` · `sanitize_value`.


Imports to recognize: `import atexit`, `import json`, `import logging`, `import os`, `import sys`, `import threading`, `import traceback`. Inspect alongside `apps/api/mira/main.py`.

### 18. apps/ceylon-compass/src/components/staff/StaffConsole.tsx

**P1** · The reviewer can follow a quote into the private operational console. Start at `apps/ceylon-compass/src/components/staff/StaffConsole.tsx:207` · `StaffConsole`.


Imports to recognize: `import { useCallback, useEffect, useRef, useState, type CSSProperties, type FormEvent } from "react";`, `import { api } from "@/lib/live/service";`, `import { Search, Shield, X, Check, AlertCircle, Clock, FileText, Users, Activity } from "lucide-react";`. Inspect alongside `apps/ceylon-compass/src/test/staff-layout.test.tsx`.

### 19. evals/judge.py

**P1** · Separates automated judgements from agreement with human labels. Start at `evals/judge.py:223–369` · `judge`.


Imports to recognize: `import argparse`, `import hashlib`, `collections`, `datetime`, `import json`, `import os`, `pathlib`. Inspect alongside `evals/runner.py`.

### 20. apps/api/mira/planner.py

**P1** · Connects each custom day to destination evidence. Start at `apps/api/mira/planner.py:8–28` · `get_grounded_day_experience`.


Imports to recognize: `import re`, `pathlib`, `.data`. Inspect alongside `apps/api/mira/agent.py`.

<a id="part-4"></a>

## Part 4 · Read the functions in execution context

### parse_rates — Where do spreadsheet row numbers come from?

`apps/api/mira/data.py:127–141` · `parse_rates`. The importer reads cached Excel cell values, enumerates each sheet from its actual first data row and keeps the row number alongside its cells. It extracts the FX end date separately.

Source excerpt, lines 127–140.

```python
def parse_rates(raw):
    from io import BytesIO
    book = load_workbook(BytesIO(raw), read_only=True, data_only=True)
    try:
        def rows(tab, first):
            return tuple((i, row) for i, row in enumerate(
                book[tab].iter_rows(min_row=first, values_only=True), first) if row[0] is not None)

        settings = rows("Settings", 2)
        fx_line = one((row for _, row in settings if row[0] == "FX rate (LKR per 1 USD)"), "fx")
        expiry = datetime.strptime(fx_line[2].removeprefix("Fixed for quoting until "), "%d %b %Y").date()
        return Rates(hashlib.sha256(raw).hexdigest(), settings, expiry, rows("Seasons", 2),
                     rows("Tours", 2), rows("Hotels", 4), rows("Transport", 2), book.epoch)
    finally:
```

A missing settings label cannot safely default to an exchange rate.

### number — Why reject a cell containing 28,000?

`apps/api/mira/data.py:83–95` · `number`. Only a recognized LKR string or numeric cell can become Decimal. A bare formatted string is ambiguous. A Boolean is also rejected even though Python treats it as an integer subtype.

Source excerpt, lines 83–95.

```python
def number(value):
    if isinstance(value, bool):
        raise Unavailable("invalid_amount")
    if isinstance(value, str):
        if not re.fullmatch(r"LKR (?:[1-9]\d{0,2}(?:,\d{3})+|\d+)(?:\.\d+)?", value):
            raise Unavailable("invalid_amount")
        value = Decimal(value[4:].replace(",", ""))
    if not isinstance(value, (int, float, Decimal)):
        raise Unavailable("missing_amount")
    amount = Decimal(str(value))
    if not amount.is_finite() or amount < 0:
        raise Unavailable("invalid_amount")
    return amount
```

LKR 28,000 passes. A nonfinite float fails before the arithmetic.

### one — What if two hotels match a night?

`apps/api/mira/data.py:144–148` · `one`. Materializing the candidate rows allows an exact cardinality check. Both zero and two matches raise the caller’s reason code.

Source excerpt, lines 144–148.

```python
def one(matches, code):
    rows = list(matches)
    if len(rows) != 1:
        raise Unavailable(code)
    return rows[0]
```

Choosing the first matching row would conceal overlapping contracts.

### as_of — How can November tests still run in December?

`apps/api/mira/data.py:151–154` · `as_of`. AS_OF_DATE supplies an ISO date. Without it, the function consults the Colombo clock. Tests use a fixed assessment date.

Source excerpt, lines 151–154.

```python
def as_of():
    from zoneinfo import ZoneInfo
    value = os.getenv("AS_OF_DATE")
    return date.fromisoformat(value) if value else datetime.now(ZoneInfo("Asia/Colombo")).date()
```

A clock change can alter deposit eligibility and quote validity.

### round_up — Why does 315.001 become 320?

`apps/api/mira/data.py:157–158` · `round_up`. Divide by five, take the mathematical ceiling and multiply by five. An exact multiple stays unchanged.

Source excerpt, lines 157–158.

```python
def round_up(value, step):
    return int((value / step).to_integral_value(rounding=ROUND_CEILING) * step)
```

Deposit rounding uses the same function with a step of one.

### price — How does corrupted workbook input surface?

`apps/api/mira/data.py:161–167` · `price`. The wrapper preserves known Unavailable reasons. It translates expected parsing and arithmetic errors into rate_import_invalid.

Source excerpt, lines 161–167.

```python
def price(tour, start, adults, ages, today, rates=None):
    try:
        return calculate(tour, start, adults, ages, today, rates or load_rates())
    except Unavailable:
        raise
    except (OSError, BadZipFile, ParseError, AttributeError, TypeError, KeyError, IndexError, ValueError, ArithmeticError) as exc:
        raise Unavailable("rate_import_invalid") from exc
```

The quote node treats an explicit quote with that import error specially.

### calculate — Who pays for an extra bed?

`apps/api/mira/data.py:170–242` · `calculate`. Every child aged 2–11 adds one bed on every contracted night. The loop checks the hotel ID and inclusive dates, then counts doubles, singles and beds.

Source excerpt, lines 216–242.

```python
            raise Unavailable("unconfirmed_hotel_rate")
        for count, amount in zip((adults // 2, adults % 2, children), rate[5:8]):
            if count:
                lodging += count * number(amount) * multiplier
        used_hotels.append(hotel_row)
    costs = {
        "guide": number(guide) * days, "transport": number(vehicle[3]) * days,
        "entrances": number(adult_fee) * adults + (number(child_fee) * children if children else 0),
        "meals": number(meals) * (adults + Decimal(children) / 2) * days,
        "hotels": lodging,
    }
    cost = sum(costs.values())
    margin = number(settings["Margin – day tours" if kind == "Day tour" else "Margin – multi-day tours"])
    deposit_fraction = number(settings["Deposit – multi-day tours"])
    step = number(settings["Round booking total up to next (USD)"])
    if cost <= 0 or fx <= 0 or not 0 <= margin < 1 or not 0 < deposit_fraction <= 1 or step != 5:
        raise Unavailable("invalid_settings")
    sell = round_up(cost / (fx * (1 - margin)), step)
    due = number(settings["Full payment if starting within (days)"])
    deposit = sell if kind == "Day tour" or (start - today).days <= due else round_up(sell * deposit_fraction, 1)
    return {
        "total": sell, "deposit": deposit, "balance": sell - deposit,
        "cost_lkr": str(cost), "gross_profit_pct": str(100 * (1 - cost / fx / sell)),
        "breakdown": {key: str(value) for key, value in costs.items()},
        "snapshot": rates.digest, "tour_row": rate_row, "transport_row": vehicle_row,
        "hotel_rows": used_hotels,
    }
```

An infant adds to the private party limit while contributing zero seats and beds.

### content — When do edited Markdown files become visible?

`apps/api/mira/data.py:38–65` · `content`. The cached loader parses YAML headers and builds structured days for tours. Malformed records are skipped and duplicate IDs excluded.

Source excerpt, lines 38–51.

```python
def content():
    records = {}
    duplicates = set()
    for path in sorted(DATA.glob("content/*/*.md")):
        try:
            _, header, body = path.read_text().split("---", 2)
            meta = yaml.safe_load(header)
            key = meta["id"]
            if key in records:
                duplicates.add(key)
            rec = {
                **{k: meta[k] for k in ("id", "type", "title", "status")},
                "last_updated": str(meta.get("last_updated","")),
                "category": meta.get("category", ""), "duration": meta.get("duration", ""),
```

Restart the process after changing a source file to invalidate the in-memory cache.

### published — Why can a seemingly valid tour be unavailable?

`apps/api/mira/data.py:68–70` · `published`. Publication status and the historic ID exclusion filter the catalogue before pricing.

Source excerpt, lines 68–70.

```python
def published():
    return {k: r for k, r in content().items()
            if r["status"] == "published" and k not in HISTORIC}
```

A studio concept still needs a supported workbook tour before a quote can exist.

### public_text — How do you keep a marketing price out of a card?

`apps/api/mira/data.py:28–34` · `public_text`. The sanitizer removes comments and filters lines containing financial terms, currencies or URLs. Specific stale claims have explicit replacements.

Source excerpt, lines 28–34.

```python
def public_text(value: str) -> str:
    value = re.sub(r"<!--.*?(?:-->|$)", "", value, flags=re.S)
    value = value.replace(" (where blue whales can be seen all year round)", "")
    value = value.replace("Free cancellation up to 24 hours before the tour.", "See the current cancellation policy for refund terms.")
    value = value.replace("**Family offer: kids under 12 stay free!**", "See the current children and infants policy for child rates.")
    return "\n".join(clean(line) for line in value.splitlines()
                     if not re.search(r"[$€£]|\b(?:USD|LKR|GP|margin|discount)\b|https?://", line, re.I))
```

Filtering is deliberately conservative and may remove legitimate prose on the same line.

### interpret — Where does context come from on the next message?

`apps/api/mira/agent_workflow/interpret.py:424` (`interpret`, backed by `_handle_structured_action`, `_classify_intent`, `_extract_date_and_travellers`, `_resolve_tour_and_search`, `_handle_notebook_planning`, and `replay.py:load_context_and_replay`) · `interpret`. The node finds the latest human message, normalizes it and reads visitor or notebook context. It also looks for an earlier result with the same visitor and run.

Source excerpt, lines 81–99.

```python
def interpret(state):
    message = next((m.content for m in reversed(state.get("messages", [])) if isinstance(m, HumanMessage)), "")
    text = message.strip()[:1200].lower() if isinstance(message, str) else ""
    working.get()["user_text"] = text
    visitor = visitor_context.get()
    run = run_context.get()
    with db() as conn:
        saved = conn.execute("SELECT context FROM visitors WHERE id = ?", (visitor,)).fetchone()
        if trip_id := working.get().get("trip_id"):
            saved = conn.execute("""
                SELECT context, revision FROM trips
                WHERE id=? AND (visitor=? OR visitor IN (
                    SELECT v2.id FROM visitors v1 JOIN visitors v2 ON v1.user_id = v2.user_id WHERE v1.id=? AND v1.user_id IS NOT NULL
                ))
            """, (trip_id, visitor, visitor)).fetchone()
            if not saved:
                raise ValueError("Journey unavailable")
            working.get()["revision"] = saved["revision"]
        replay = conn.execute("SELECT result FROM traces WHERE visitor = ? AND run = ?", (visitor, run)).fetchone()
```

For a notebook it records the revision so a later conflicting write can be detected.

### retrieve — How does a vegetarian query retrieve evidence?

`apps/api/mira/agent_workflow/retrieve.py:12–67` · `retrieve`. The dietary action maps to P04. The node takes published rows for the chosen IDs and records those source IDs in the retrieval stage.

Source excerpt, lines 550–565.

```python
        ids += [key for key, tour in w["tours"].items() if place in tour["destinations"]][:3]
    if action in {"custom", "general"}:
        search = ctx.get("search") if action == "general" else None
        if search:
            filtered = filter_tours(w["tours"], search)
            if not filtered:
                ids = []
                w["no_matching_tours"] = True
            else:
                det_ids = rank_filtered_tours(filtered, search)
                llm_trip = {**search, **{k: ctx[k] for k in ("adults", "kids") if k in ctx}}
                ranked = rank(filtered, llm_trip, w["events"])
                ids = [tid for tid in (ranked or []) if tid in filtered] or det_ids
        else:
            trip = ctx.get("custom", {}) if action == "custom" else {}
            destinations = {name.split()[0].lower() for name in trip.get("destinations", [])}
```

A general tour query takes a different branch and filters the candidate tours first.

### quote_route — Why did Mira ask my child’s age?

`apps/api/mira/agent_workflow/routing.py:5–12` · `quote_route`. Discovery reaches quote only with a supported tour, date, adult count and matching lengths for the stated children and ages. A selection action alone bypasses pricing.

Source excerpt, lines 583–589.

```python
def quote_route(_):
    w = working.get()
    ctx = w["context"]
    if (w["action"] == "discover" and not w["select"] and ctx.get("tour") in w["tours"]
            and ctx.get("date") and "adults" in ctx and ctx.get("kids", 0) == len(ctx.get("ages", []))):
        return "quote"
    return "compose"
```

Two children with one age proceeds to compose for clarification.

### quote_node — Which quote fields can reach the traveller?

`apps/api/mira/agent_workflow/quote.py:15–43` · `quote_node`. The node retains the full value in private working data and explicitly copies total, deposit and balance into PublicQuote with identity and party fields.

Source excerpt, lines 625–638.

```python
def quote_node(_):
    w = working.get()
    ctx = w["context"]
    before = perf_counter()
    event("PRICING", "pricing.started", level=logging.DEBUG, tour_id=ctx["tour"])
    rates = None
    try:
        rates = current_rates()
        value = price(ctx["tour"], date.fromisoformat(ctx["date"]), ctx["adults"], ctx.get("ages", []), as_of(), rates)
        w["internal"] = value
        quote_enquiry(w, "verified_quote")
        w["quote"] = PublicQuote(enquiry=w["enquiry"], enquiry_reference=w["enquiry_reference"],
            id=uuid4(), source=ctx["tour"], title=w["tours"][ctx["tour"]]["title"],
            date=ctx["date"], adults=ctx["adults"], ages=ctx.get("ages", []),
```

Adding cost to the internal result alone does not add it to the public contract.

### quote_enquiry — Where does the visible enquiry reference originate?

`apps/api/mira/agent_workflow/enquiry.py:35–41` · `quote_enquiry`. The helper reuses a matching enquiry or creates a UUID and formats a year-prefixed reference. Persist later writes it transactionally.

Source excerpt, lines 617–622.

```python
def quote_enquiry(w, reason):
    previous = matching_enquiry(w, reason)
    identifier = UUID(previous["id"]) if previous else uuid4()
    reference = previous["reference"] if previous else None
    w["enquiry"] = identifier
    w["enquiry_reference"] = reference or f"ENQ-{as_of().year}-{identifier.hex[:8].upper()}"
```

A selected trip and an explicit quote can have different reuse criteria.

### matching_enquiry — Why can recalculation reuse an enquiry?

`apps/api/mira/agent_workflow/enquiry.py:9–32` · `matching_enquiry`. Candidates belong to the same trip and reason and exclude terminal or booked cases. For explicit quotes it compares tour, date, adults and ages.

Source excerpt, lines 592–605.

```python
def matching_enquiry(w, reason):
    if not w.get("trip_id"):
        return None
    with db() as conn:
        candidates = conn.execute(
            """SELECT e.id, e.reference, e.trip FROM enquiries e JOIN trip_turns t ON t.trace=e.trace
               WHERE t.trip=? AND e.reason=?
                 AND e.status NOT IN ('booked','closed','closed_lost','unqualified')
                 AND (e.quote IS NULL OR e.quote NOT IN (SELECT quote FROM bookings))
               ORDER BY t.rowid DESC""",
            (w["trip_id"], reason),
        ).fetchall()

    keys = ("tour", "date", "adults", "ages") if w.get("explicit_quote") else ("tour",)
```

Comparing only the tour for explicit quotes could associate different parties.

### compose — Who chooses whether to show a price or handoff?

`apps/api/mira/agent_workflow/compose.py:325` (`compose`, backed by `_compose_verified_quote`, `_compose_unavailable_quote`, `_compose_custom_handoff`, `_compose_discovery_or_clarification`, etc.) · `compose`. The node branches on server-side action and working values. It builds catalogue components and attaches evidence, then constructs the turn.

Source excerpt, lines 1007–1021.

```python
            if isinstance(item,Excerpt) and item.type=="DestinationHighlight":
                components[i]=SourcePanel(**(item.model_dump()|{"type":"DestinationCard"}))
    if any(e["stage"].startswith("gemini") and e.get("outcome") in {"fallback","unavailable","unconfigured"} for e in w["events"]):
        text += " Limited service: I’m using the published catalogue."
    sources = list(dict.fromkeys(sources))[:6]
    if "optional_panels" in w:
        optional = {"InteractiveMap", "DateSelector", "ComparisonPanel", "ActivityCard", "StayCard"}
        components = [item for item in components if item.type not in optional or item.type in w["optional_panels"]]
    components = components[:12]
    w["turn"] = Turn(trace=trace, text=text, sources=sources, components=components)
    duration = elapsed(started)
    w["events"].append({"stage": "validated_ui", "components": [c.type for c in components], "ms": duration})
    event("RAG", "grounding.completed", sources=sources, documents=len(sources))
    event("AGENT", "ui.validated", components=len(components), duration_ms=duration)
    return {}
```

A specialist notice conveys an unavailable price without giving the traveller a numeric estimate.

### persist — How does Mira avoid writing twice after a retry?

`apps/api/mira/agent_workflow/persistence.py:18–108` · `persist`. A write transaction checks the visitor/run pair before inserting. It writes trace, quote, enquiry and notebook changes together and checks the original basis.

Source excerpt, lines 1035–1057.

```python
            stage["request_id"] = identifier
        w["events"].append(stage)
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            previous = conn.execute("SELECT result FROM traces WHERE visitor=? AND run=?", (visitor, run)).fetchone()
            if previous:
                turn = Turn.model_validate_json(previous["result"])
            else:
                active = conn.execute("SELECT context FROM visitors WHERE id=?", (visitor,)).fetchone()
                trip_id = w.get("trip_id")
                if trip_id:
                    active = conn.execute("SELECT context FROM trips WHERE id=? AND visitor=? AND revision=?",
                                          (trip_id,visitor,w["revision"])).fetchone()
                if not active or active["context"] != w["basis"]:
                    raise ValueError("Session changed during this turn")
                conn.execute("INSERT INTO traces(id, visitor, run, events, result) VALUES(?,?,?,?,?)",
                             (str(turn.trace), visitor, run, encode(w["events"]), turn.model_dump_json()))
                q = w.get("quote")
                if q:
                    conn.execute("INSERT INTO quotes(id, visitor, trace, public, internal) VALUES(?,?,?,?,?)",
                                 (str(q.id), visitor, str(turn.trace), q.model_dump_json(), encode(w["internal"])))
                if trip_id and w.get("panel_action") == "date":
                    conn.execute("""UPDATE enquiries SET trip=? WHERE id=(
```

Changing context during the run can raise a conflict instead of overwriting newer data.

### save — Why move persistence to a worker thread?

`apps/api/mira/agent_workflow/persistence.py:111–120` · `save`. SQLite operations are synchronous. asyncio.to_thread runs persist without blocking the event loop, then the node dispatches a text event.

Source excerpt, lines 1111–1119.

```python
async def save(_):
    try:
        result = await asyncio.to_thread(persist)
    except Exception:
        event("ERROR", "turn.persistence_failed", level=logging.ERROR, exception=True)
        raise
    message = result["messages"][0]
    await adispatch_custom_event("manually_emit_message", {"message_id": message.id, "message": message.content})
    return result
```

Only after persistence succeeds can the node return the validated snapshot.

### agui — Can a browser choose its own pricing tools?

`apps/api/mira/main.py:417–491` · `agui`. The API builds a safe request using the latest user message and clears client state, tools, context and forwarded properties. A fresh graph adapter streams server-selected events.

Source excerpt, lines 417–430.

```python
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
```

The durable notebook identity is permission-checked separately from the transient thread ID.

### visitor — How is a traveller linked to an account?

`apps/api/mira/main.py:90–97` · `visitor`. The cookie identifies a visitor record. If the row has an owner, the request must carry the matching authenticated user.

Source excerpt, lines 90–97.

```python
def visitor(session: str | None = Cookie(None, alias=COOKIE), user: UserProfile | None = Depends(get_current_user_optional)):
    if not session:
        raise HTTPException(401, "Start a visitor session")
    with db() as conn:
        owner = conn.execute("SELECT user_id FROM visitors WHERE id=?", (session,)).fetchone()
        if not owner or (owner["user_id"] and (not user or user.id != owner["user_id"])):
            raise HTTPException(401, "Start a visitor session")
    return session
```

A trip ID alone cannot authorize access.

### website — What does the origin check enforce?

`apps/api/mira/main.py:82–87` · `website`. A supplied Origin must match the configured website or additional origins. This protects browser writes alongside cookies and endpoint permissions.

Source excerpt, lines 82–87.

```python
def website(request: Request):
    origin = request.headers.get("origin")
    expected = os.getenv("MIRA_ORIGIN", "http://127.0.0.1:3000")
    allowed = {expected, *os.getenv("MIRA_ADDITIONAL_ORIGINS", "http://127.0.0.1:5175").split(",")}
    if origin and origin not in allowed:
        raise HTTPException(403, "Origin denied")
```

Origin may be absent on non-browser clients, so this check is insufficient for staff authorization.

### role — Where is staff access enforced?

`apps/api/mira/main.py:100–136` · `role`. FastAPI resolves a dependency that checks session expiry, role and account status. A legacy bearer-token path compares configured tokens in constant time.

Source excerpt, lines 100–113.

```python
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
```

A traveller who navigates to the staff page still needs server authorization.

### session — What persists when remember is selected?

`apps/api/mira/main.py:185–198` · `session`. The server writes the preference and issues an HttpOnly Lax visitor cookie with a longer max age. A session cookie is used otherwise.

Source excerpt, lines 185–198.

```python
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
```

The notebook ID in sessionStorage is only a locator.

### notebook — What rebuilds conversation history?

`apps/api/mira/main.py:259–288` · `notebook`. The API reads an authorized trip and its saved turns, allowing the browser to reconstruct a validated entry for each historical prompt.

Source excerpt, lines 259–269.

```python
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
```

The page must handle an inaccessible or stale notebook ID.

### quote_current — Why recheck a saved price?

`apps/api/mira/main.py:225–232` · `quote_current`. The service evaluates the saved public inputs against current rates and clock, then compares the saved financial result and snapshot.

Source excerpt, lines 225–232.

```python
def quote_current(public, internal, rates):
    if rates is None:
        return False
    try:
        value = price(public.source, public.date, public.adults, public.ages, as_of(), rates)
    except Unavailable:
        return False
    return all(value[k] == internal[k] for k in ("snapshot", "total", "deposit"))
```

An old receipt may remain stored while becoming unsuitable for booking.

### booking — What happens if a successful payment is retried?

`apps/api/mira/main.py:500–530` · `booking`. The mock endpoint checks ownership and a prior booking inside a transaction. A repeated success returns the existing reference.

Source excerpt, lines 500–513.

```python
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
```

A decline records an outcome. It does not insert a successful booking.

### generate — What is drafted without Gemini?

`apps/api/mira/main.py:1486–1512` · `generate`. The handler selects a published destination and builds a short concept from sanitized evidence. If configured, Gemini may replace that draft with schema-validated copy.

Source excerpt, lines 1486–1499.

```python
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
```

The new database row starts in draft status in either mode.

### review_draft — What are the review choices?

`apps/api/mira/main.py:1537–1556` · `review_draft`. An approver can approve, request revision or reject. The update records reviewer, notes and timestamp and writes an audit event.

Source excerpt, lines 1537–1550.

```python
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
```

A published draft cannot be reviewed again through this route.

### publish — Must there be a separate approved row first?

`apps/api/mira/main.py:1560–1571` · `publish`. An approver may publish directly from draft or approved. The predicate on actor is distinct from the predicate on status.

Source excerpt, lines 1560–1571.

```python
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
```

If the policy requires two separate steps, tighten the SQL status condition and change the workflow tests.

### follow_up — Who updates an enquiry after handoff?

`apps/api/mira/main.py:1404–1460` · `follow_up`. The private PATCH handler accepts structured follow-up data after role and origin checks. Staff can record notes and status independently of traveller chat.

Source excerpt, lines 1404–1415.

```python
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
```

Use the staff workflow test before changing accepted transitions.

### export_trace — What leaves the machine when tracing is enabled?

`apps/api/mira/main.py:335–413` · `export_trace`. The exporter builds one root observation and child observations for stages. Generation metadata can include model and token counts; sanitization filters selected fields.

Source excerpt, lines 367–387.

```python
            propagate_attributes(
                trace_name="mira-concierge-turn",
                session_id=session_id,
                user_id=user_id,
                version=_BUILD_REVISION,
                environment=os.getenv("MIRA_ENV", "development"),
                tags=tags,
            )
            if propagate_attributes is not None
            else nullcontext()
        )
        with prop_ctx:
            with client.start_as_current_observation(
                name="mira.turn",
                as_type="agent",
                trace_context={"trace_id": trace.hex},
                input=trace_input,
                output=trace_output,
                metadata=meta,
            ):
                for item in w["events"]:
```

Email and bearer redaction cannot guarantee removal of names and phone numbers in arbitrary prose.

### model_available — Does configuration prove Gemini is healthy?

`apps/api/mira/provider.py:15–16` · `model_available`. The check requires a key and model name. It performs no network health check.

Source excerpt, lines 15–16.

```python
def model_available():
    return bool(os.getenv("GEMINI_API_KEY") and os.getenv("GEMINI_MODEL"))
```

An expired key can still satisfy the predicate.

### generate_structured — How do you reject a malformed model response?

`apps/api/mira/provider.py:19–58` · `generate_structured`. The provider supplies a JSON schema and parses the text through Pydantic. Calls have an 18-second HTTP timeout, limited retries and 900 output tokens.

Source excerpt, lines 30–38.

```python
        model_name = os.environ["GEMINI_MODEL"]
        with genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options=HttpOptions(timeout=18000, retry_options=HttpRetryOptions(attempts=2,initial_delay=0.25,max_delay=1,http_status_codes=[429,503]))) as client:
            result = client.models.generate_content(
                model=model_name,
                contents=instructions,
                config=GenerateContentConfig(response_mime_type="application/json", response_json_schema=schema.model_json_schema(),
                                             max_output_tokens=900),
            )
```

The caller chooses how to recover from a validation or transport exception.

### rank — What if the model suggests an unknown tour?

`apps/api/mira/provider.py:61–97` · `rank`. The function deduplicates proposed IDs and verifies each one belongs to the candidate set. Invalid suggestions yield None.

Source excerpt, lines 61–74.

```python
def rank(tours, trip, events):
    """Suggest published cards using structured trip details, excluding raw chat and financial inputs."""
    if not model_available() or not tours:
        return None
    started = perf_counter()
    outcome: Literal["ok", "fallback"] = "fallback"
    llm_meta: dict = {}
    try:
        candidates = {
            k: {
                "title": t["title"],
                "destinations": t["destinations"],
                "category": t["category"],
                "duration": t.get("duration", ""),
```

Retrieve can use deterministic ordering when the provider returns None.

### notebook_intent — Can the model control arbitrary panels?

`apps/api/mira/provider.py:108–139` · `notebook_intent`. The provider returns a typed NotebookIntent from constrained instructions and evidence. Allowed panel names are enumerated.

Source excerpt, lines 108–119.

```python
def notebook_intent(prompt, previous, destinations, events, evidence=None):
    """Gemini returns identifiers and preferences only. Content and prices stay server-owned."""
    if not model_available():
        events.append({"stage":"gemini_intent","outcome":"unconfigured"})
        event("LLM", "gemini.unconfigured", level=logging.DEBUG)
        return None
    import json
    started = perf_counter()
    outcome = "unavailable"
    llm_meta: dict = {}
    try:
        result = generate_structured(NotebookIntent,
```

Graph composition still controls the traveller-facing turn.

### db — Who commits database writes?

`apps/api/mira/store.py:17–27` · `db`. The context manager enables foreign keys, yields the SQLite connection inside its transaction context and closes it on exit.

Source excerpt, lines 17–27.

```python
def db():
    _guard_dev_db()
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()
```

An exception leaving that context rolls back pending changes.

### init — How do migrations run at startup?

`apps/api/mira/store.py:30–48` · `init`. A SQLAlchemy connection sets WAL and begins a write transaction. Alembic upgrades to head, then the transaction commits.

Source excerpt, lines 30–43.

```python
def init():
    _guard_dev_db()
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import URL, create_engine

    DB.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(URL.create("sqlite", database=str(DB)),connect_args={"timeout":10})
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA journal_mode=WAL")
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            config = Config()
            config.set_main_option("script_location", str(Path(__file__).with_name("migrations")))
```

Use a separate MIRA_DB for rehearsals so a migration operates on practice data.

### published_records — How soon is a published concept searchable?

`apps/api/mira/store.py:61–71` · `published_records`. Each call starts from published source records and merges database drafts whose status equals published.

Source excerpt, lines 61–71.

```python
def published_records():
    from .data import published
    original = published()
    with db() as conn:
        for row in conn.execute("SELECT * FROM drafts WHERE status = 'published'"):
            original[row["id"]] = {
                "id": row["id"], "title": row["title"], "body": row["body"],
                "type": "tour", "category": "Custom journey", "duration": "", "start": "",
                "destinations": [], "status": "published", "path": "Content studio",
            }
    return original
```

Draft creation alone cannot expose a concept through this read path.

### is_current_notebook_turn — Why can a later notebook turn invalidate checkout?

`apps/api/mira/store.py:51–54` · `is_current_notebook_turn`. The function finds the most recent turn for the same trip. A different latest trace makes the check false.

Source excerpt, lines 51–54.

```python
def is_current_notebook_turn(conn, trace):
    latest = conn.execute("""SELECT trace FROM trip_turns WHERE trip=(
        SELECT trip FROM trip_turns WHERE trace=?) ORDER BY rowid DESC LIMIT 1""", (trace,)).fetchone()
    return latest is None or latest["trace"] == trace
```

Legacy quotes outside a notebook can have no matching turn.

### current_rates — What is actually stored in the rates database?

`apps/api/mira/rates_repository.py:11–26` · `current_rates`. The repository hashes workbook bytes and looks up the matching SQLite blob. It parses the bytes and inserts previously unseen snapshots.

Source excerpt, lines 11–24.

```python
def current_rates():
    try:
        workbook = data.WORKBOOK.read_bytes()
        checksum = sha256(workbook).hexdigest()
        with db() as conn:
            stored = conn.execute("SELECT workbook FROM rate_snapshots WHERE digest=?", (checksum,)).fetchone()
        if stored:
            return data.parse_rates(stored["workbook"])
        rates = data.parse_rates(workbook)
        with db() as conn:
            conn.execute("INSERT OR IGNORE INTO rate_snapshots(digest, workbook) VALUES (?,?)", (checksum, workbook))
        return rates
    except Unavailable:
        raise
```

This is a versioned workbook store. Individual tariff rows are selected in Python.

### surface_messages — Why are tour cards sometimes grouped?

`apps/api/mira/surface.py:8–25` · `surface_messages`. For discovery the adapter groups tour cards into JourneyResults. A picker, price or booking component changes that layout decision.

Source excerpt, lines 8–21.

```python
def surface_messages(turn: Turn) -> list[dict]:
    nodes = []
    cards = [item for item in turn.components if item.type == "TourCard"]
    # A selection, quote or handoff owns its detail view. Discovery owns its list.
    discovery = bool(cards) and not any(
        item.type in {"TravellerPicker", "PriceBreakdown", "BookingForm"} for item in turn.components
    )
    for index, item in enumerate(turn.components):
        if discovery and item.type == "TourCard":
            continue
        nodes.append({"id": f"item-{index}", "component": item.type, "index": index})
    if discovery:
        nodes.append({"id": "results", "component": "JourneyResults"})
    root = {"id": "root", "component": "JourneyColumn", "children": [node["id"] for node in nodes]}
```

Each ordinary node references a turn component by index.

### execute — How is one evaluation case scored?

`evals/runner.py:168–213` · `execute`. A TestClient session sends the case turns, optionally restoring cookies. evaluate checks all outputs; exceptions become recorded failure text. Trace IDs are resolved to stage records.

Source excerpt, lines 168–185.

```python
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
```

A case with two valid turns may still fail its final price assertion.

### run — Why can evaluation exit successfully with a failure?

`evals/runner.py:226–326` · `run`. The final gate recognizes the single historical sample conflict only when its observed quote matches the audited value.

Source excerpt, lines 226–240.

```python
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
```

Read the report counters as well as the process exit code.

### Trace the canonical browser path with the editor open

**Inputs and identity.** The hook’s value defaults to the controlled input state. displayText is optional display copy for a machine-generated action. trim removes whitespace. ready prevents sending before a notebook exists. active.current blocks a second concurrent turn. A new prompt gets a fresh UUID; after a failed turn the same prompt retains the pending UUID. Example: clicking retry after receiving a response late can request the existing persisted result.



```javascript
    const prompt = value.trim();
    if (!ready || !prompt || active.current) return;
    const controller = new AbortController();
    active.current = controller;
    if (pending.current?.prompt !== prompt) pending.current = { prompt, id: crypto.randomUUID() };
    setBusy(true);
    setError("");
    const timeout = setTimeout(() => controller.abort(), 65000);
    try {
      const item = await run(trip.current, prompt, pending.current.id, controller, () => {});
      if (displayText) item.displayPrompt = displayText;
      setItems((prior) => [...prior, item]);
      pending.current = null;
      setInput("");
    } catch {
      setInput(prompt);
      setError("Mira couldn’t finish this request. Retry to recover your turn.");
      const state = await fetch("/api/session", { cache: "no-store" }).catch(() => null);
```

The user sees busy state while awaiting the stream. The controller aborts after 65 seconds. setItems uses the previous state updater so an asynchronous completion appends to the current history. Clearing pending only on success preserves retry semantics. The catch branch distinguishes a lost visitor session from a recoverable network problem. The finally block always clears the timer and busy state.

**From events to a typed entry.** In service.ts the callback receives provider-independent AG-UI state. It parses the turn first, then validates the layout against that parsed turn. An asynchronous run without a final entry throws. Compare the same code in the alternate /plan route, where text progress is rendered.


```typescript
  const turn = Turn.parse(raw);
  return { prompt, turn, surface: readSurface(surface, turn) };
}
export async function run(
  id: string,
  prompt: string,
  runId: string,
  signal: AbortController,
  progress: (s: string) => void,
) {
  const { HttpAgent } = await import("@ag-ui/client");
  const agent = new HttpAgent({
    url: "/api/agent?trip_id=" + encodeURIComponent(id),
    threadId: id,
    initialMessages: [{ id: runId, role: "user", content: prompt }],
  });
  let result: Entry | undefined;
  await agent.runAgent(
    { runId, abortController: signal },
    {
      onTextMessageContentEvent: ({ textMessageBuffer }) => progress(textMessageBuffer),
      onStateChanged: ({ state }) => {
        if (state?.["turn"] && state["surface"])
          result = entry(prompt, state["turn"], state["surface"]);
      },
    },
  );
  if (!result) throw Error("Mira couldn’t finish this turn. Retry to recover it.");
```

**Inputs to the tariff.** quote_node supplies tour (published ID from context), start (ISO text converted to date), adults (explicit integer), ages (list, empty by default), today (assessment clock) and rates (validated snapshot). Direct tests can omit rates on price, which falls back to load_rates. The public result stores date and party as well as totals so checkout can run the same calculation later.

| Lines in data.py | Operation | Q-1043 intermediate or failure |
|---|---|---|
| 171–178 | Validate publication and party; count headcount before reclassifying ages. | travellers=4, adults=2, children=2, size=4. |
| 179–185 | Build a settings lookup. A duplicate key reduces its length and invalidates it. Compare start and today to FX expiry. | Four fits the private limit. |
| 186–196 | Resolve the workbook ID, unpack its unique row, compare scope/title and check the last day. | T09, seven days, six nights. A title mismatch stops here. |
| 197–205 | Check exactly one season on each day, select a unique seat tier and require one hotel ID per night. | Van for four; six hotel schedule entries. |
| 206–220 | For offset zero through five, match the specific hotel/night. zip pairs room counts with double, single and extra-bed tariffs. | Counts (1,0,2). The unused single tariff is never multiplied. |
| 221–227 | Build the LKR breakdown and sum it. | 667,000. A missing used amount raises Unavailable. |
| 228–235 | Read margin, deposit, rounding step and due window. Check valid settings and round at each specified stage. | 2,965 sale; 742 deposit. |
| 236–242 | Return integer guest totals and stringified internal Decimal amounts plus row references/digest. | quote_node projects the public fields. persist saves both objects. |

**What to change live.** To adjust a room rule, edit the occupancy tuple at line 217 in a practice copy. An odd-adult test and an infant test detect unintended changes. To alter the deposit percentage, keep the due-window branch and change the copied Settings cell. To diagnose a missing hotel rate, inspect the date and exact cardinality of the matches at lines 211–213 before proposing any change.

<a id="part-5"></a>

## Part 5 · Follow nine workflows

### A. Quick booker

“Sigiriya day trip for two adults on 10 January 2027” resolves to T01. Two adults, zero child ages and an ISO date open the quote branch. Public total and deposit both equal 315. Persist inserts a linked quote and enquiry; the workspace displays the price and booking action.

Execution order (P01 / S02)

```text
send
  → run
  → agui
  → interpret
  → retrieve
  → quote_route
  → quote_node
  → calculate
  → compose
  → save
  → entry
```



### B. Multi-day family

Start with “Plan a family holiday”. The broad-family test expects a duration and child-age question and zero enquiries. Supply six days, nature, scenic trains, beaches, two adults and a seven-year-old. The full request test expects six sourced days. A supported T09 request with fixed dates can subsequently enter pricing.

Execution order (S03 / test_family_planning_workflow.py)

```text
send
  → interpret
  → notebook_intent (when enabled)
  → retrieve
  → compose
  → persist
```



### C. Custom itinerary

A bespoke route across Kandy and Ella lacks a single workbook product. Destination overlap can suggest related tours. A complete proposal gets an enquiry reference and a specialist handoff. A minor day edit should preserve the enquiry count.

Execution order (D03 / W04)

```text
interpret
  → retrieve
  → compose
  → quote_enquiry or enquiry allocation
  → persist
  → enquiries
```



### D. Expired or missing contract

T01 on 1 November 2027 exceeds FX expiry. T07 with an uncovered hotel night fails a different uniqueness check. Inspect the stored reason and EnquiryNotice. No PublicQuote is constructed. Explicit requests with rate_import_invalid propagate the error; distinguish provider/parse failure from absent tariff data.

Execution order (P05 / P06 / S05)

```text
quote_route
  → current_rates
  → price
  → Unavailable
  → quote_node
  → compose
  → persist
```



### E. Returning visitor

With consent the cookie outlives a browser session. The hook first uses the tab’s stored notebook ID and can fetch the latest trip for a remembered visitor. A missing trip gives a fresh notebook; unauthorized access fails. History and quote validity are reconstructed server-side. A personalized spoken greeting on every entry is unverified.

Execution order (M05 / test_consent_resume_forget)

```text
session
  → useConversation effect
  → trips or notebook
  → entry
  → setItems
```



### F. Staff follows up

A verified quote sets the reason verified_quote. Staff filter the private list and open the reference, record a note and update status. Staff API calls use role checks. Contactability depends on available contact/account data; a private anonymous enquiry alone is insufficient to call a customer.

Execution order (W04 / test_staff_enquiry_workflow.py)

```text
persist
  → enquiries
  → enquiry
  → follow_up
  → notes/status
  → staff detail
```



### G. Studio publishes

Submit an Ella journey concept. The template or model uses published evidence. The insert creates a draft with an author. Approval and publication write audit events. Only the approver can publish, including directly from draft. Published concepts still have no automatically generated rates.

Execution order (W05 / test_draft_visibility_and_authorization)

```text
generate
  → drafts
  → review_draft or publish
  → published_records
  → retrieve
```



### H. Mock payment

Send a quote UUID and scenario declined. The endpoint appends a mock_booking trace stage and returns status declined. The UI offers retry or a fresh quote. Success inserts one booking; a repeat success returns the existing reference. No real payment processor participates.

Execution order (W01–W03)

```text
handleMockBooking
  → booking
  → quote_current
  → is_current_notebook_turn
  → bookings
  → panel
```



### I. Off-topic or unsafe instruction

For “Please write a Python script to find anagrams”, an off_topic rule routes away from quoting. Other guarded requests include demands for pricing secrets or unsupported discounts. The deterministic tariff and public schema limit consequences even when phrase matching misses an unfamiliar request.

Execution order (X01–X04 / S12 / S14)

```text
agui
  → interpret
  → retrieve
  → quote_route
  → compose
  → save
```

Illustrative AG-UI message fields from the test client (run and message IDs must be UUIDs).

```json
{"role":"user","id":"00000000-0000-4000-8000-000000000001",
 "content":"Sigiriya day trip for two adults on 10 January 2027"}
```

<a id="part-6"></a>

## Part 6 · Graph, prompts and state

The graph has five named nodes. There is no open-ended loop asking a model which tool to execute. Routing is explicit Python. This makes interview debugging possible: inspect the action, then the route guard, then the selected node. The design rationale is inferred from those boundaries.


```python
class GraphState(TypedDict, total=False):
    surface: list[dict]
    messages: Annotated[list, add_messages]
    turn: dict


# Only the validated turn is emitted as graph state. The per-run working data stays server-side.
working = ContextVar("working", default=None)
```



```text
START → interpret ─ replay → save → END
            └ fresh → retrieve → quote_route
                                  ├ ready → quote_node → compose → save
                                  └ incomplete or other → compose → save
```

messages uses an add_messages reducer (combines updates by message identity). turn is the validated traveller response. surface holds layout commands. The ContextVar working is private per run, with context, records, action, rows, quote, internal and events populated by different steps. SQLite persists trip context between runs. An InMemorySaver attached to a fresh adapter cannot itself explain returning-visitor memory.

For “A Sigiriya day trip”, context can hold tour=T01 without date or adults. A later dated party completes the guard. Changing child age can change paid seat class, entrances, meals and occupancy. For a replay the graph may proceed directly to save after checking price validity.

provider.rank supplies structured trip constraints and a bounded published candidate description. Suggestions accepts at most three IDs. notebook_intent has a separate schema for planning and panel choice. Draft generation has its own instructions in main.generate. Changing GEMINI_MODEL selects a compatible Gemini model. A different provider requires an adapter with the same schema validation, error handling and telemetry. Bounded prompts, selective model calls and cached parsed workbook data already reduce work. Further latency tuning should begin by comparing observed stage milliseconds.

<a id="part-7"></a>

## Part 7 · Work a quote by hand

Open the original workbook READ ME, Settings, Seasons, Tours, Hotels and Transport sheets alongside data.calculate. The database stores the workbook blob by SHA-256. parse_rates preserves the sheet row numbers and Excel epoch. Numeric Excel dates and textual dates normalize through day(). The active tour must exist exactly once, match its published title, have consistent scope and a sane day/night count. T13 maps to T-13. T06 is blocked for scope conflict.

**Dry run — Q-1043.** Start 12 April 2027, assessment 19 November 2026, T09, two adults, ages [7,10]. All four count for the private limit and van selection. Seven travel days require exactly one season each. Six nights begin on the start date. For each night, match exactly one hotel rate by ID and inclusive validity, convert the specifically marked USD contract to LKR if needed, then sum double rooms, single rooms and extra beds.

| Component | Calculation | LKR |
|---|---|---:|
| Guide | 7 × 9,500 | 66,500 |
| Van | 7 × 26,000 | 182,000 |
| Entrances | 2 × 38,000 + 2 × 19,000 | 114,000 |
| Meals | (2 + 2/2) × 4,500 × 7 | 94,500 |
| Double rooms | 2 × (20,000 + 28,000 + 25,000) | 146,000 |
| Extra beds | 2 children × 2 nights × (4,500 + 6,000 + 5,500) | 64,000 |
| Total | All six components | 667,000 |

USD cost = 667,000 / 300. With 25% gross margin, cost must equal 75% of selling price. Divide by .75 to obtain 2,964.444…, then round upward to USD 2,965. A 25% markup would multiply cost by 1.25 and yield only a 20% gross margin before rounding. Realized GP is 100 × (1 − 667,000 / 300 / 2,965). Deposit is ceiling(2,965 × .25) = 742. Balance = 2,223. The email’s USD 2,680 / 670 follows exactly if the 64,000 is omitted. P03 checks the email; S03 agrees with the workbook. Keep both in the evidence.

An infant counts toward 20 travellers but has no seat, meal, bed or entrance cost. Ages 2 and 11 are inclusive, 12 joins adults; at least one supplied adult is required. Odd adult occupancy uses the single room tariff. Day tours and departures within 30 days are paid in full. A tour ending after FX expiry fails even when its first day is valid.

**Where to edit in a practice copy.** Settings holds FX, margins, deposit, maximum size, due window and rounding step. Code additionally requires step == 5. Transport brackets are inclusive. To change seasons review Seasons plus nightly hotel validity; adjusting one alone can leave a gap. Child meals and age classification are code in calculate. Missing-rate wording is in compose. For a date simulation set AS_OF_DATE and restart. Stored quotes retain historical public/internal JSON; a changed workbook digest can invalidate checkout even when a rounded total happens to match. Replay test_exact_quote, test_group_boundaries, test_age_boundaries, test_full_payment_boundary, test_refuses and test_stale_quote_replayed_without_money.

<a id="part-8"></a>

## Part 8 · Ground an answer

Try “Do you have vegetarian meals?” (G01). interpret recognizes dietary; retrieve maps dietary to [P04]. The retrieved record has id, type, title, status, body and relative path. compose selects evidence from the policy and returns response text and source IDs. The deterministic policy path does not need to send a prompt to Gemini. Open the linked P04 excerpt during rehearsal and compare the response to its wording.

General recommendations first apply extract_search_constraints / filter_tours. A model may rerank eligible published tours; rank rejects unknown IDs and falls back. For a destination, retrieve adds up to three tours whose destination list contains its slug. Several matches are therefore expected. An empty filtered pool sets no_matching_tours. Unknown questions can receive a specialist response. Phrase-based routing has limited paraphrase coverage. There is no embedding ingestion or vector index in this path.

Source files load through data.content’s cache; restart after editing a practice copy. Database drafts are merged on each published_records call. Policy corrections in public_text override conflicting marketing text. Excluding source lines containing currency reduces leak risk but loses legitimate context. RAG here means selecting source material for the response; a model is optional.

**Observed offline turn.** Sending G01 through FastAPI TestClient against a fresh SQLite database produced text “Here’s what our published travel information says.”, sources ["P04"] and one PolicySnippet component. The dietary answer lives in the component, so checking only the chat text misses the evidence. Open content/policies/faq.md in the supplied dataset: the dietary paragraph says vegetarian, vegan and halal meals are available on request. No model prompt or vector query was necessary for this turn.

<a id="part-9"></a>

## Part 9 · From a validated turn to pixels

workspace/useConversation.js uses state for visible items, ready/busy/error and consent. Refs hold the active controller, trip ID and pending run UUID across renders. The mount effect establishes a session and retrieves history. Cleanup aborts the pending request. send disables concurrent turns and preserves the UUID on a retry. Its progress callback is empty in the canonical workspace. The alternate /plan view uses setStream for incremental text.

service.run creates an HttpAgent. It forwards the notebook as a query parameter, yields text progress and accepts an entry only when turn and surface exist. entry parses the TypeScript catalogue using Zod. readSurface checks operation order, catalog and surface IDs, unique node IDs, indexes, matching types and complete coverage. A rejected snapshot leaves the hook in its recoverable error path.

Example layout node for a PriceBreakdown at index zero:

```json
{"id":"item-0","component":"PriceBreakdown","index":0}
```

The monetary props belong to turn.components[0].quote. The layout references the data by index. Workspace.jsx reconciles the latest components against the selected party and active tour; PriceBreakdownPanel renders totals. UIComponentRenderer handles other allowed display types. In the alternate route LiveCanvas switches directly on c.type. Traveller actions feed a new command into the conversation or call a scoped REST endpoint. No model-generated script runs in the browser.

For a component addition, first add a typed variant and discriminator to catalog.py, then update the TypeScript turn union, surface kind list, validated layout and actual workspace renderer. Emit it from compose only for the intended branch. Check both discovery and quote views plus invalid index/type combinations. Use the brand palette and spacing from workspace/style.css for canonical display changes.

**Source of the financial fields**

```python
class PublicQuote(Strict):
    enquiry: UUID | None = None
    enquiry_reference: str | None = None
    id: UUID
    source: Source
    title: Text
    date: CalendarDate
    adults: int
    ages: list[int]
    validity: Literal["recheck_before_booking"] = "recheck_before_booking"
    currency: Literal["USD"] = "USD"
    total: Annotated[int, Field(gt=0)]
    deposit: Annotated[int, Field(gt=0)]
    balance: Annotated[int, Field(ge=0)]
```

Registering a field such as a tariff label requires agreement between PublicQuote, the constructor in quote_node, the Zod quote schema and the React panel. Make the field optional with a sensible display fallback if old saved JSON can lack it. A label-only change needs none of those schema migrations. Workspace.jsx has both a direct quote view and the conversation panel; choose the view the reviewer is using.

<a id="part-10"></a>

## Part 10 · Database, Sessions & Security

### Entity-Relationship Overview (SQLite + WAL + 6 Alembic Migrations)

```text
users ──────────< user_sessions       (Argon2id auth, HttpOnly mira_auth cookie, 24h / 30d)
  │
  └─────────────< visitors            (mira_session cookie, remember flag, visitor context)
                    │
                    ├──< trips ──────< trip_turns >── traces (run-ID idempotency, stage events, Turn JSON)
                    │                                   │
                    └──< traces ─────── quotes ─────────┼── bookings (mock payment, 1:1 with quote)
                                          │             │
                                          └─────────────┴── enquiries ──< notes (private staff notes)

rate_snapshots (SHA-256 workbook BLOB) ◄── quote.internal.snapshot
drafts (id, status: draft|approved|published, author, reviewer)
audit  (append-only via SQLite BEFORE UPDATE/DELETE RAISE ABORT triggers)
failed_traces (id, events)
```

### Security & Access Control Matrix

| Boundary | Enforcement Mechanism | Code Location |
| :--- | :--- | :--- |
| **CSRF / Origin** | Rejects mutating requests from disallowed `Origin` headers | `main.py:96-102` (`website`) |
| **Visitor Isolation** | Requires `mira_session` cookie; if linked to `user_id`, verifies `user.id == owner["user_id"]` | `main.py:105-113` (`visitor`) |
| **Staff / RBAC** | Validates `mira_auth` session cookie (or dev-only `MIRA_*_TOKEN`); checks `status == 'active'` and role | `main.py:116-153` (`role`), `auth.py:376-382` |
| **Approver-Only Publish** | Strictly `actor == "approver"` (even `admin` and `staff` get `403`); allows `draft` or `approved` → `published` | `main.py:1630-1642` (`publish`) |
| **Financial Privacy** | `PublicQuote` Pydantic allowlist strips `cost_lkr`, `gross_profit_pct`, `breakdown`, `hotel_rows` | `catalog.py:98-114`, `agent_workflow/quote.py:27-31` |
| **Trace Redaction** | `sanitize_value` masks emails & `Bearer` tokens; `is_sensitive_key` blocks `cost_lkr`, `token`, `secret`, `password` | `observability.py:96-114` |

> [!WARNING]
> **Honest Limitations:** (1) `sanitize_value` masks email addresses and `Bearer` tokens, not arbitrary names or phone numbers in free-text prompts. (2) Trip prompts are stored locally for notebook replay. (3) Never open `.env` or use real customer data during a screen share; always use separate browser profiles for Traveller vs Staff.

<a id="part-11"></a>

## Part 11 · Evaluation, Testing and Tracing

### Verified Test & Evaluation Evidence (Current Checkout)

| Suite | Command | Verified Result | Notes |
| :--- | :--- | :---: | :--- |
| **Backend Unit & Integration** | `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests` | **222 passed** (26.0s) | Uses isolated temp SQLite (`_guard_dev_db` blocks `.mira/mira.sqlite3`). |
| **Frontend Component & Integration** | `npm --prefix apps/ceylon-compass test` | **73 passed** (9 files, 4.2s) | Covers `LiveCanvas`, `MarkdownContent`, `SourceDisclosure`, `auth-ui`, `staff-layout`, `workspace-preferred`. |
| **Deterministic Eval Suite** | `evals/report/report.md` (clock `2026-11-19`, offline) | **53/54 (98.1%)** | `23/24` exact quotes (`P03` = workbook `$2,965` vs email `$2,680`), `11/11` handoffs, `63/63` valid UI turns, `0` unexpected quotes. |
| **LLM-as-Judge** | `evals/judge.py` / `evals/report/judge.json` | **10/10 scored** | Human-label calibration is still `null` (pending independent human labels). |
| **Standalone MCP Smoke** | `evals/report/mcp_smoke.json` (25 Nov 2026) | **10/10 passed** | Separate stdio MCP server (`apps/web/mcp/server.mjs`) verified for tools, quotes, expired FX, and session isolation. |

### Real Trace Walkthrough (`f108d88e-1e5b-4f04-9e07-1132cf764094`, Archived P03)

`runner.py:execute` replays HTTP turns against an isolated DB, disables cloud keys, and records every stage in `traces.events`:


```json
[
  {
    "stage": "interpret",
    "provider": "local rules",
    "action": "discover",
    "ms": 0
  },
  {
    "stage": "retrieval",
    "sources": [
      "T09"
    ],
    "ms": 0
  },
  {
    "stage": "pricing",
    "outcome": "verified",
    "snapshot": "a16dd63ffb7ed2324e9d709f4b35e1bb3f0d5c2123b765903bce039f5fefdfe2",
    "rate_digest": "a16dd63ffb7ed2324e9d709f4b35e1bb3f0d5c2123b765903bce039f5fefdfe2",
    "ms": 1
  },
  {
    "stage": "validated_ui",
    "components": [
      "PriceBreakdown",
      "TourCard",
      "ItineraryDay",
      "BookingForm"
    ],
    "ms": 0
  },
  {
    "stage": "persistence",
    "enquiry": true,
    "request_id": "d95ad806-fea8-42c8-9c2f-e6bf486f6c28",
    "ms": 1
  }
]
```


**Genuine fix.** docs/BEFORE_AFTER.md records M02 previously returned 365 twice because “age is 12” did not match. The corrected extraction accepts the intervening verb. The authored case now checks 365 then 410. The historical temporary DB no longer exists. Another reproducible importer regression is test_lkr_string_regression: converting recognized text directly to Decimal restores the 28,000 room rate.

Fresh local checks on this checkout passed 43 pricing tests, plus 23 workflow, family and staff tests. The AG-UI library emitted deprecation warnings during those workflow tests. No live provider or remote tracing call was made.

**Independent replay on 26 November.** Copied evals/ to a temporary directory and ran its runner.py with PYTHONPATH=apps/api against this checkout. The runner created its own temporary SQLite database. The new report reproduced 53/54, 23/24 exact quotes, 11/11 handoffs, 63/63 valid turns and zero unexpected quotes. The archived report and dataset were preserved. The runner also translates some starter behaviour descriptions into explicit assertions through SEED_BEHAVIOUR; inspect that mapping when asked who defined “passes”.

<a id="part-12"></a>

## Part 12 · Live coding practice

Practise in an isolated copy. From the repository root, run the following in one terminal. The archive contains tracked files at HEAD. It excludes private settings, your active database and uncommitted work. Setup dependencies there before starting. For the first five exercises: run the baseline, predict the boundary result on paper, apply just the replacement, run the named test, and inspect the difference. A changed business requirement can legitimately make an old expectation fail. Add a new independent expectation before updating the old one.


```sh
practice=$(mktemp -d)
git archive HEAD | tar -x -C "$practice"
cd "$practice"
./scripts/setup.sh
```



### 1. Change the multi-day gross margin

**High likelihood · moderate edit.** `apps/api/mira/data.py:170–242` · `calculate`

Locate the current expression:

```text
margin = number(settings["Margin – day tours" if kind == "Day tour" else "Margin – multi-day tours"])
```

Practice replacement:

```text
margin = number(settings["Margin – day tours" if kind == "Day tour" else "Margin – multi-day tours"])
```

Keep the production expression. In the practice workbook Settings row Margin – multi-day tours replace 0.25 with 0.30. The same cost now occupies 70% of sale. Q-1043 becomes ceil-to-five(667000 / 210) = 3180; deposit 795. Restore the practice cell to undo.

**Verify** — `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests/test_pricing.py -k exact_quote`. Predict that T01 is unchanged; old multi-day expectations should fail. Never patch a sample total.

**Undo** — reverse only the practice edit and rerun the same check. Keep fixture and contract changes together.

### 2. Collect 30% upfront

**High likelihood · moderate edit.** `apps/api/mira/data.py:170–242` · `calculate`

Locate the current expression:

```text
deposit_fraction = number(settings["Deposit – multi-day tours"])
```

Practice replacement:

```text
deposit_fraction = number(settings["Deposit – multi-day tours"])
```

Change only the practice Settings cell Deposit – multi-day tours from 0.25 to 0.30. Q-1043 becomes 890 due on 2965. The day-tour and near-departure branches still collect the whole amount.

**Verify** — `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests/test_pricing.py -k "exact_quote or full_payment_boundary"`. Compare the deposit, balance and unchanged total. Reset the practice cell.

**Undo** — reverse only the practice edit and rerun the same check. Keep fixture and contract changes together.

### 3. Raise child meals to 75%

**High likelihood · moderate edit.** `apps/api/mira/data.py:170–242` · `calculate`

Locate the current expression:

```text
Decimal(children) / 2
```

Practice replacement:

```text
Decimal(children) * Decimal("0.75")
```

Only the meal fraction changes. For two children over seven days add 0.5 × 4500 × 7 = 15750 LKR. Q-1043 cost becomes 682750. Keep seats, beds and admissions unchanged.

**Verify** — `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests/test_pricing.py -k "child or q1043"`. Check each breakdown field. Also run the infant test to ensure zero remains zero.

**Undo** — reverse only the practice edit and rerun the same check. Keep fixture and contract changes together.

### 4. Clarify a missing-rate response

**High likelihood · moderate edit.** `apps/api/mira/agent_workflow/compose.py:78–124` · `_compose_unavailable_quote` (via `compose`)

Locate the current expression:

```text
A travel specialist will confirm the exact rate for you.
```

Practice replacement:

```text
A specialist will check the tariff for your travel dates.
```

Replace only the sentence in the branch shown. Keep the enquiry creation, outcome and absence of financial components.

**Verify** — `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests/test_workflows.py`. Rehearse P05 plus an uncovered hotel night. Check which branch actually uses the revised sentence.

**Undo** — reverse only the practice edit and rerun the same check. Keep fixture and contract changes together.

### 5. Require separate approval before publishing

**High likelihood · moderate edit.** `apps/api/mira/main.py:1560–1571` · `publish`

Locate the current expression:

```text
status IN ('draft', 'approved')
```

Practice replacement:

```text
status = 'approved'
```

Narrow the SQL predicate. An approver attempting direct publication receives 409; after review action approve the update succeeds. The existing direct-publication test may need a review step.

**Verify** — `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests/test_workflows.py -k draft`. Try staff, approver-before-review, approver-after-review. Confirm only the last makes the concept retrievable.

**Undo** — reverse only the practice edit and rerun the same check. Keep fixture and contract changes together.

### 6. Switch the configured model

**High likelihood · small edit.** `apps/api/mira/provider.py:19–58` · `generate_structured`

Locate the current expression:

```text
model_name = os.environ["GEMINI_MODEL"]
```

Practice replacement:

```text
model_name = os.environ["GEMINI_MODEL"]
```

Set GEMINI_MODEL to the alternate Gemini model ID supplied by the reviewer in the practice process. Restart after changing configuration. Confirm availability separately; invalid IDs exercise the fallback.

**Verify** — `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests/test_workflows.py -k provider`. The offline test proves fallback only. Successful model selection requires a credentialed run and a generation observation.

**Undo** — reverse only the practice edit and rerun the same check. Keep fixture and contract changes together.

### 7. Prefer closest duration in suggestions

**Medium likelihood · small edit.** `apps/api/mira/provider.py:61–97` · `rank`

Locate the current expression:

```text
Return their IDs only.
```

Practice replacement:

```text
Prefer the closest duration among eligible tours. Return their IDs only.
```

Adjust the ranking instruction inside the string. The ID allowlist still runs after generation.

**Verify** — `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests/test_tour_relevance_regression.py`. Compare two eligible tours; exact ordering with a live provider is unverified.

**Undo** — reverse only the practice edit and rerun the same check. Keep fixture and contract changes together.

### 8. Recognize plant-based meal questions

**Medium likelihood · small edit.** `apps/api/mira/agent_workflow/interpret.py:66–132, 424` · `_classify_intent` / `interpret`

Locate the current expression:

```text
vegetarian|vegan|halal|dietary
```

Practice replacement:

```text
vegetarian|vegan|halal|dietary|plant-based
```

Add a dietary alias. A matching request follows P04 retrieval.

**Verify** — `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests/test_workflows.py`. Send “Are plant-based meals available?” and inspect source P04. Check that pricing still works.

**Undo** — reverse only the practice edit and rerun the same check. Keep fixture and contract changes together.

### 9. Add a stable evaluation paraphrase

**Medium likelihood · small edit.** `evals/cases/authored.jsonl`

Locate the current expression:

```text
{"id":"P01","category":"pricing","turns":["Sigiriya day trip for two adults on 10 January 2027"],"expected":{"type":"quote","tour":"T01","price_usd":315,"deposit_usd":315}}
```

Practice replacement:

```text
{"id": "P17", "category": "pricing", "turns": ["Sigiriya day trip for 2 adults on 10 January 2027"], "expected": {"type": "quote", "tour": "T01", "price_usd": 315, "deposit_usd": 315}}
```

Keep P01. Append the new JSON line with its own ID and identical expected tariff. The case count increases by one.

**Verify** — `make eval`. Inspect the new case and the historical P03 failure separately.

**Undo** — reverse only the practice edit and rerun the same check. Keep fixture and contract changes together.

### 10. Relabel the canonical quote panel

**Medium likelihood · small edit.** `apps/ceylon-compass/workspace/Workspace.jsx:3034` · `PriceBreakdownPanel`

Locate the current expression:

```text
>Deposit required</span>
```

Practice replacement:

```text
>Due on confirmation</span>
```

Only this display label changes. Quote arithmetic and the alternate React route have separate ownership.

**Verify** — `make workspace-browser`. Rebuild workspace assets. Compare the canonical panel before and after.

**Undo** — reverse only the practice edit and rerun the same check. Keep fixture and contract changes together.

### 11. Tighten the maximum source count

**Medium likelihood · small edit.** `apps/api/mira/catalog.py:115–120` · `Turn`

Locate the current expression:

```text
sources: list[Source] = Field(max_length=6)
```

Practice replacement:

```text
sources: list[Source] = Field(max_length=5)
```

Narrow backend validation. Mirror the corresponding Zod maximum and verify that existing plan turns with six sources can still be read or migrated.

**Verify** — `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests/test_family_planning_workflow.py`. Test a turn with 5 and 6 sources plus saved history before accepting the policy.

**Undo** — reverse only the practice edit and rerun the same check. Keep fixture and contract changes together.

### 12. Show fewer destination matches

**Medium likelihood · small edit.** `apps/api/mira/agent_workflow/retrieve.py:12–67` · `retrieve`

Locate the current expression:

```text
if place in tour["destinations"]][:3]
```

Practice replacement:

```text
if place in tour["destinations"]][:2]
```

Limit extra destination tours to two; keep the destination row itself.

**Verify** — `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests/test_tour_relevance_regression.py`. Ask about Ella. Count related cards and confirm each matches the place.

**Undo** — reverse only the practice edit and rerun the same check. Keep fixture and contract changes together.

### 13. Shorten remembered visitor lifetime

**Medium likelihood · small edit.** `apps/api/mira/main.py:185–198` · `session`

Locate the current expression:

```text
2592000 if body.remember else None
```

Practice replacement:

```text
604800 if body.remember else None
```

Seven days replaces thirty for newly issued remembered visitor cookies. Existing browser cookies keep their previously issued expiry.

**Verify** — `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests/test_workflows.py -k consent`. Inspect Max-Age without displaying cookie values. Check both consent choices.

**Undo** — reverse only the practice edit and rerun the same check. Keep fixture and contract changes together.

### 14. Shorten the client timeout

**Medium likelihood · small edit.** `apps/ceylon-compass/workspace/useConversation.js:49` · `send`

Locate the current expression:

```text
controller.abort(), 65000
```

Practice replacement:

```text
controller.abort(), 45000
```

A slow request aborts sooner. The pending run ID still allows safe retry; too short a deadline increases apparent failures.

**Verify** — `make workspace-browser`. Throttle in a practice browser, retry and check for a single enquiry.

**Undo** — reverse only the practice edit and rerun the same check. Keep fixture and contract changes together.

### 15. Improve fallback trace metadata

**Medium likelihood · small edit.** `apps/api/mira/provider.py:19–58` · `generate_structured`

Locate the current expression:

```text
fields = {"operation": operation}
```

Practice replacement:

```text
fields = {"operation": operation, "provider": "gemini"}
```

Add a constant provider label to the structured event fields. Keep prompts and credentials out of logs.

**Verify** — `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests/test_observability.py`. Inspect metadata with a synthetic turn. The log formatter may select a subset for display.

**Undo** — reverse only the practice edit and rerun the same check. Keep fixture and contract changes together.

<a id="part-13"></a>

## Part 13 · Oral examination

### Pricing, Python and content

#### Where do spreadsheet row numbers come from?

**Spoken answer.** The importer reads cached Excel cell values, enumerates each sheet from its actual first data row and keeps the row number alongside its cells. It extracts the FX end date separately.

**Follow-up — what behavior would you check?** A missing settings label cannot safely default to an exchange rate.

`apps/api/mira/data.py:127–141` · `parse_rates`

### Why reject a cell containing 28,000?

**Spoken answer.** Only a recognized LKR string or numeric cell can become Decimal. A bare formatted string is ambiguous. A Boolean is also rejected even though Python treats it as an integer subtype.

**Follow-up — what behavior would you check?** LKR 28,000 passes. A nonfinite float fails before the arithmetic.

`apps/api/mira/data.py:83–95` · `number`

### What if two hotels match a night?

**Spoken answer.** Materializing the candidate rows allows an exact cardinality check. Both zero and two matches raise the caller’s reason code.

**Follow-up — what behavior would you check?** Choosing the first matching row would conceal overlapping contracts.

`apps/api/mira/data.py:144–148` · `one`

### How can November tests still run in December?

**Spoken answer.** AS_OF_DATE supplies an ISO date. Without it, the function consults the Colombo clock. Tests use a fixed assessment date.

**Follow-up — what behavior would you check?** A clock change can alter deposit eligibility and quote validity.

`apps/api/mira/data.py:151–154` · `as_of`

### Why does 315.001 become 320?

**Spoken answer.** Divide by five, take the mathematical ceiling and multiply by five. An exact multiple stays unchanged.

**Follow-up — what behavior would you check?** Deposit rounding uses the same function with a step of one.

`apps/api/mira/data.py:157–158` · `round_up`

### How does corrupted workbook input surface?

**Spoken answer.** The wrapper preserves known Unavailable reasons. It translates expected parsing and arithmetic errors into rate_import_invalid.

**Follow-up — what behavior would you check?** The quote node treats an explicit quote with that import error specially.

`apps/api/mira/data.py:161–167` · `price`

### Who pays for an extra bed?

**Spoken answer.** Every child aged 2–11 adds one bed on every contracted night. The loop checks the hotel ID and inclusive dates, then counts doubles, singles and beds.

**Follow-up — what behavior would you check?** An infant adds to the private party limit while contributing zero seats and beds.

`apps/api/mira/data.py:170–242` · `calculate`

### When do edited Markdown files become visible?

**Spoken answer.** The cached loader parses YAML headers and builds structured days for tours. Malformed records are skipped and duplicate IDs excluded.

**Follow-up — what behavior would you check?** Restart the process after changing a source file to invalidate the in-memory cache.

`apps/api/mira/data.py:38–65` · `content`

### Why can a seemingly valid tour be unavailable?

**Spoken answer.** Publication status and the historic ID exclusion filter the catalogue before pricing.

**Follow-up — what behavior would you check?** A studio concept still needs a supported workbook tour before a quote can exist.

`apps/api/mira/data.py:68–70` · `published`

### How do you keep a marketing price out of a card?

**Spoken answer.** The sanitizer removes comments and filters lines containing financial terms, currencies or URLs. Specific stale claims have explicit replacements.

**Follow-up — what behavior would you check?** Filtering is deliberately conservative and may remove legitimate prose on the same line.

`apps/api/mira/data.py:28–34` · `public_text`

### Graph orchestration

#### Where does context come from on the next message?

**Spoken answer.** The node finds the latest human message, normalizes it and reads visitor or notebook context. It also looks for an earlier result with the same visitor and run.

**Follow-up — what behavior would you check?** For a notebook it records the revision so a later conflicting write can be detected.

`apps/api/mira/agent_workflow/interpret.py:424` · `interpret`

### How does a vegetarian query retrieve evidence?

**Spoken answer.** The dietary action maps to P04. The node takes published rows for the chosen IDs and records those source IDs in the retrieval stage.

**Follow-up — what behavior would you check?** A general tour query takes a different branch and filters the candidate tours first.

`apps/api/mira/agent_workflow/retrieve.py:12–67` · `retrieve`

### Why did Mira ask my child’s age?

**Spoken answer.** Discovery reaches quote only with a supported tour, date, adult count and matching lengths for the stated children and ages. A selection action alone bypasses pricing.

**Follow-up — what behavior would you check?** Two children with one age proceeds to compose for clarification.

`apps/api/mira/agent_workflow/routing.py:5–12` · `quote_route`

### Which quote fields can reach the traveller?

**Spoken answer.** The node retains the full value in private working data and explicitly copies total, deposit and balance into PublicQuote with identity and party fields.

**Follow-up — what behavior would you check?** Adding cost to the internal result alone does not add it to the public contract.

`apps/api/mira/agent_workflow/quote.py:15–43` · `quote_node`

### Where does the visible enquiry reference originate?

**Spoken answer.** The helper reuses a matching enquiry or creates a UUID and formats a year-prefixed reference. Persist later writes it transactionally.

**Follow-up — what behavior would you check?** A selected trip and an explicit quote can have different reuse criteria.

`apps/api/mira/agent_workflow/enquiry.py:35–41` · `quote_enquiry`

### Why can recalculation reuse an enquiry?

**Spoken answer.** Candidates belong to the same trip and reason and exclude terminal or booked cases. For explicit quotes it compares tour, date, adults and ages.

**Follow-up — what behavior would you check?** Comparing only the tour for explicit quotes could associate different parties.

`apps/api/mira/agent_workflow/enquiry.py:9–32` · `matching_enquiry`

### Who chooses whether to show a price or handoff?

**Spoken answer.** The node branches on server-side action and working values. It builds catalogue components and attaches evidence, then constructs the turn.

**Follow-up — what behavior would you check?** A specialist notice conveys an unavailable price without giving the traveller a numeric estimate.

`apps/api/mira/agent_workflow/compose.py:325` · `compose`

### How does Mira avoid writing twice after a retry?

**Spoken answer.** A write transaction checks the visitor/run pair before inserting. It writes trace, quote, enquiry and notebook changes together and checks the original basis.

**Follow-up — what behavior would you check?** Changing context during the run can raise a conflict instead of overwriting newer data.

`apps/api/mira/agent_workflow/persistence.py:18–108` · `persist`

### Why move persistence to a worker thread?

**Spoken answer.** SQLite operations are synchronous. asyncio.to_thread runs persist without blocking the event loop, then the node dispatches a text event.

**Follow-up — what behavior would you check?** Only after persistence succeeds can the node return the validated snapshot.

`apps/api/mira/agent_workflow/persistence.py:111–120` · `save`

### HTTP, identity and staff operations

#### Can a browser choose its own pricing tools?

**Spoken answer.** The API builds a safe request using the latest user message and clears client state, tools, context and forwarded properties. A fresh graph adapter streams server-selected events.

**Follow-up — what behavior would you check?** The durable notebook identity is permission-checked separately from the transient thread ID.

`apps/api/mira/main.py:417–491` · `agui`

### How is a traveller linked to an account?

**Spoken answer.** The cookie identifies a visitor record. If the row has an owner, the request must carry the matching authenticated user.

**Follow-up — what behavior would you check?** A trip ID alone cannot authorize access.

`apps/api/mira/main.py:90–97` · `visitor`

### What does the origin check enforce?

**Spoken answer.** A supplied Origin must match the configured website or additional origins. This protects browser writes alongside cookies and endpoint permissions.

**Follow-up — what behavior would you check?** Origin may be absent on non-browser clients, so this check is insufficient for staff authorization.

`apps/api/mira/main.py:82–87` · `website`

### Where is staff access enforced?

**Spoken answer.** FastAPI resolves a dependency that checks session expiry, role and account status. A legacy bearer-token path compares configured tokens in constant time.

**Follow-up — what behavior would you check?** A traveller who navigates to the staff page still needs server authorization.

`apps/api/mira/main.py:100–136` · `role`

### What persists when remember is selected?

**Spoken answer.** The server writes the preference and issues an HttpOnly Lax visitor cookie with a longer max age. A session cookie is used otherwise.

**Follow-up — what behavior would you check?** The notebook ID in sessionStorage is only a locator.

`apps/api/mira/main.py:185–198` · `session`

### What rebuilds conversation history?

**Spoken answer.** The API reads an authorized trip and its saved turns, allowing the browser to reconstruct a validated entry for each historical prompt.

**Follow-up — what behavior would you check?** The page must handle an inaccessible or stale notebook ID.

`apps/api/mira/main.py:259–288` · `notebook`

### Why recheck a saved price?

**Spoken answer.** The service evaluates the saved public inputs against current rates and clock, then compares the saved financial result and snapshot.

**Follow-up — what behavior would you check?** An old receipt may remain stored while becoming unsuitable for booking.

`apps/api/mira/main.py:225–232` · `quote_current`

### What happens if a successful payment is retried?

**Spoken answer.** The mock endpoint checks ownership and a prior booking inside a transaction. A repeated success returns the existing reference.

**Follow-up — what behavior would you check?** A decline records an outcome. It does not insert a successful booking.

`apps/api/mira/main.py:500–530` · `booking`

### What is drafted without Gemini?

**Spoken answer.** The handler selects a published destination and builds a short concept from sanitized evidence. If configured, Gemini may replace that draft with schema-validated copy.

**Follow-up — what behavior would you check?** The new database row starts in draft status in either mode.

`apps/api/mira/main.py:1486–1512` · `generate`

### What are the review choices?

**Spoken answer.** An approver can approve, request revision or reject. The update records reviewer, notes and timestamp and writes an audit event.

**Follow-up — what behavior would you check?** A published draft cannot be reviewed again through this route.

`apps/api/mira/main.py:1537–1556` · `review_draft`

### Must there be a separate approved row first?

**Spoken answer.** An approver may publish directly from draft or approved. The predicate on actor is distinct from the predicate on status.

**Follow-up — what behavior would you check?** If the policy requires two separate steps, tighten the SQL status condition and change the workflow tests.

`apps/api/mira/main.py:1560–1571` · `publish`

### Who updates an enquiry after handoff?

**Spoken answer.** The private PATCH handler accepts structured follow-up data after role and origin checks. Staff can record notes and status independently of traveller chat.

**Follow-up — what behavior would you check?** Use the staff workflow test before changing accepted transitions.

`apps/api/mira/main.py:1404–1460` · `follow_up`

### What leaves the machine when tracing is enabled?

**Spoken answer.** The exporter builds one root observation and child observations for stages. Generation metadata can include model and token counts; sanitization filters selected fields.

**Follow-up — what behavior would you check?** Email and bearer redaction cannot guarantee removal of names and phone numbers in arbitrary prose.

`apps/api/mira/main.py:335–413` · `export_trace`

### Model calls and fallback

#### Does configuration prove Gemini is healthy?

**Spoken answer.** The check requires a key and model name. It performs no network health check.

**Follow-up — what behavior would you check?** An expired key can still satisfy the predicate.

`apps/api/mira/provider.py:15–16` · `model_available`

### How do you reject a malformed model response?

**Spoken answer.** The provider supplies a JSON schema and parses the text through Pydantic. Calls have an 18-second HTTP timeout, limited retries and 900 output tokens.

**Follow-up — what behavior would you check?** The caller chooses how to recover from a validation or transport exception.

`apps/api/mira/provider.py:19–58` · `generate_structured`

### What if the model suggests an unknown tour?

**Spoken answer.** The function deduplicates proposed IDs and verifies each one belongs to the candidate set. Invalid suggestions yield None.

**Follow-up — what behavior would you check?** Retrieve can use deterministic ordering when the provider returns None.

`apps/api/mira/provider.py:61–97` · `rank`

### Can the model control arbitrary panels?

**Spoken answer.** The provider returns a typed NotebookIntent from constrained instructions and evidence. Allowed panel names are enumerated.

**Follow-up — what behavior would you check?** Graph composition still controls the traveller-facing turn.

`apps/api/mira/provider.py:108–139` · `notebook_intent`

### Storage and evaluation

#### Who commits database writes?

**Spoken answer.** The context manager enables foreign keys, yields the SQLite connection inside its transaction context and closes it on exit.

**Follow-up — what behavior would you check?** An exception leaving that context rolls back pending changes.

`apps/api/mira/store.py:17–27` · `db`

### How do migrations run at startup?

**Spoken answer.** A SQLAlchemy connection sets WAL and begins a write transaction. Alembic upgrades to head, then the transaction commits.

**Follow-up — what behavior would you check?** Use a separate MIRA_DB for rehearsals so a migration operates on practice data.

`apps/api/mira/store.py:30–48` · `init`

### How soon is a published concept searchable?

**Spoken answer.** Each call starts from published source records and merges database drafts whose status equals published.

**Follow-up — what behavior would you check?** Draft creation alone cannot expose a concept through this read path.

`apps/api/mira/store.py:61–71` · `published_records`

### Why can a later notebook turn invalidate checkout?

**Spoken answer.** The function finds the most recent turn for the same trip. A different latest trace makes the check false.

**Follow-up — what behavior would you check?** Legacy quotes outside a notebook can have no matching turn.

`apps/api/mira/store.py:51–54` · `is_current_notebook_turn`

### What is actually stored in the rates database?

**Spoken answer.** The repository hashes workbook bytes and looks up the matching SQLite blob. It parses the bytes and inserts previously unseen snapshots.

**Follow-up — what behavior would you check?** This is a versioned workbook store. Individual tariff rows are selected in Python.

`apps/api/mira/rates_repository.py:11–26` · `current_rates`

### Why are tour cards sometimes grouped?

**Spoken answer.** For discovery the adapter groups tour cards into JourneyResults. A picker, price or booking component changes that layout decision.

**Follow-up — what behavior would you check?** Each ordinary node references a turn component by index.

`apps/api/mira/surface.py:8–25` · `surface_messages`

### How is one evaluation case scored?

**Spoken answer.** A TestClient session sends the case turns, optionally restoring cookies. evaluate checks all outputs; exceptions become recorded failure text. Trace IDs are resolved to stage records.

**Follow-up — what behavior would you check?** A case with two valid turns may still fail its final price assertion.

`evals/runner.py:168–213` · `execute`

### Why can evaluation exit successfully with a failure?

**Spoken answer.** The final gate recognizes the single historical sample conflict only when its observed quote matches the audited value.

**Follow-up — what behavior would you check?** Read the report counters as well as the process exit code.

`evals/runner.py:226–326` · `run`

### What should happen for “Sigiriya day trip for two adults on 10 January 2027”?

**Spoken answer.** I would expect a verified T01 quote for USD 315 with USD 315 due. I would check the party, date and tariff before interpreting a different result.

**Follow-up — where is the independent expectation?** Case P01 in `evals/cases/authored.jsonl`. Its expected fields are type, tour, price_usd, deposit_usd. Compare them with the observed turn. `apps/api/mira/data.py:170–242` · `calculate`

### What should happen for “Cultural Triangle Sri Lanka Package for 2 adults on 3 May 2027”?

**Spoken answer.** I would expect a verified T09 quote for USD 2125 with USD 532 due. I would check the party, date and tariff before interpreting a different result.

**Follow-up — where is the independent expectation?** Case P02 in `evals/cases/authored.jsonl`. Its expected fields are type, tour, price_usd, deposit_usd. Compare them with the observed turn. `apps/api/mira/data.py:170–242` · `calculate`

### What should happen for “Cultural Triangle Sri Lanka Package for 2 adults and 2 children aged 7 and 10 on 12 April 2027”?

**Spoken answer.** The workbook produces USD 2,965 with USD 742 due. P03 encodes the lower email figure because that example omits child extra beds.

**Follow-up — where is the independent expectation?** Case P03 in `evals/cases/authored.jsonl`. Its expected fields are type, tour, price_usd, deposit_usd. Compare them with the observed turn. `apps/api/mira/data.py:170–242` · `calculate`

### What should happen for “Highlights of Sri Lanka for 2 adults starting 1 December 2026”?

**Spoken answer.** I would expect a verified T08 quote for USD 2505 with USD 2505 due. I would check the party, date and tariff before interpreting a different result.

**Follow-up — where is the independent expectation?** Case P04 in `evals/cases/authored.jsonl`. Its expected fields are type, tour, price_usd, deposit_usd. Compare them with the observed turn. `apps/api/mira/data.py:170–242` · `calculate`

### What should happen for “Sigiriya day trip for 2 adults on 1 November 2027”?

**Spoken answer.** This case expects flag no price. I would inspect the graph action and selected records, then check the actual components against the case assertion.

**Follow-up — where is the independent expectation?** Case P05 in `evals/cases/authored.jsonl`. Its expected fields are type, reason. Compare them with the observed turn. `apps/api/mira/data.py:170–242` · `calculate`

### What should happen for “Kandy Heritage Stay for 2 adults on 11 January 2027”?

**Spoken answer.** This case expects flag no price. I would inspect the graph action and selected records, then check the actual components against the case assertion.

**Follow-up — where is the independent expectation?** Case P06 in `evals/cases/authored.jsonl`. Its expected fields are type, reason. Compare them with the observed turn. `apps/api/mira/data.py:170–242` · `calculate`

### What should happen for “Kandy Heritage Stay for 2 adults starting 14 December 2026”?

**Spoken answer.** I would expect a verified T07 quote for USD 760 with USD 760 due. I would check the party, date and tariff before interpreting a different result.

**Follow-up — where is the independent expectation?** Case P07 in `evals/cases/authored.jsonl`. Its expected fields are type, tour, price_usd, deposit_usd. Compare them with the observed turn. `apps/api/mira/data.py:170–242` · `calculate`

### What should happen for “Kandy Heritage Stay travelling solo starting 1 December 2026”?

**Spoken answer.** I would expect a verified T07 quote for USD 605 with USD 605 due. I would check the party, date and tariff before interpreting a different result.

**Follow-up — where is the independent expectation?** Case P08 in `evals/cases/authored.jsonl`. Its expected fields are type, tour, price_usd, deposit_usd. Compare them with the observed turn. `apps/api/mira/data.py:170–242` · `calculate`

### What should happen for “Sigiriya day trip for 2 adults and one child aged 2 on 10 January 2027”?

**Spoken answer.** I would expect a verified T01 quote for USD 365 with USD 365 due. I would check the party, date and tariff before interpreting a different result.

**Follow-up — where is the independent expectation?** Case P09 in `evals/cases/authored.jsonl`. Its expected fields are type, tour, price_usd, deposit_usd. Compare them with the observed turn. `apps/api/mira/data.py:170–242` · `calculate`

### What should happen for “Sigiriya day trip for 2 adults and one child aged 12 on 10 January 2027”?

**Spoken answer.** I would expect a verified T01 quote for USD 410 with USD 410 due. I would check the party, date and tariff before interpreting a different result.

**Follow-up — where is the independent expectation?** Case P10 in `evals/cases/authored.jsonl`. Its expected fields are type, tour, price_usd, deposit_usd. Compare them with the observed turn. `apps/api/mira/data.py:170–242` · `calculate`

### What should happen for “Sigiriya day trip for 8 adults on 10 January 2027”?

**Spoken answer.** I would expect a verified T01 quote for USD 910 with USD 910 due. I would check the party, date and tariff before interpreting a different result.

**Follow-up — where is the independent expectation?** Case P11 in `evals/cases/authored.jsonl`. Its expected fields are type, tour, price_usd, deposit_usd. Compare them with the observed turn. `apps/api/mira/data.py:170–242` · `calculate`

### What should happen for “Sigiriya day trip for 9 adults on 10 January 2027”?

**Spoken answer.** I would expect a verified T01 quote for USD 1095 with USD 1095 due. I would check the party, date and tariff before interpreting a different result.

**Follow-up — where is the independent expectation?** Case P12 in `evals/cases/authored.jsonl`. Its expected fields are type, tour, price_usd, deposit_usd. Compare them with the observed turn. `apps/api/mira/data.py:170–242` · `calculate`

### What should happen for “Sigiriya day trip for 21 adults on 10 January 2027”?

**Spoken answer.** This case expects flag no price. I would inspect the graph action and selected records, then check the actual components against the case assertion.

**Follow-up — where is the independent expectation?** Case P13 in `evals/cases/authored.jsonl`. Its expected fields are type, reason. Compare them with the observed turn. `apps/api/mira/data.py:170–242` · `calculate`

### What should happen for “Kandy Heritage Stay for 2 adults starting 19 December 2026”?

**Spoken answer.** I would expect a verified T07 quote for USD 780 with USD 780 due. I would check the party, date and tariff before interpreting a different result.

**Follow-up — where is the independent expectation?** Case P14 in `evals/cases/authored.jsonl`. Its expected fields are type, tour, price_usd, deposit_usd. Compare them with the observed turn. `apps/api/mira/data.py:170–242` · `calculate`

### What should happen for “Kandy Heritage Stay for 2 adults starting 20 December 2026”?

**Spoken answer.** I would expect a verified T07 quote for USD 780 with USD 195 due. I would check the party, date and tariff before interpreting a different result.

**Follow-up — where is the independent expectation?** Case P15 in `evals/cases/authored.jsonl`. Its expected fields are type, tour, price_usd, deposit_usd. Compare them with the observed turn. `apps/api/mira/data.py:170–242` · `calculate`

### What should happen for “Train and Day Tour from Kandy to Nuwara Eliya for 2 adults on 10 January 2027”?

**Spoken answer.** This case expects flag no price. I would inspect the graph action and selected records, then check the actual components against the case assertion.

**Follow-up — where is the independent expectation?** Case P16 in `evals/cases/authored.jsonl`. Its expected fields are type, reason. Compare them with the observed turn. `apps/api/mira/data.py:170–242` · `calculate`

<a id="part-14"></a>

## Part 14 · Debug during the demo

**Services fail to start** — Run `.venv/bin/python scripts/dev.py --check-ports` with PYTHONPATH=apps/api. Use `lsof -nP -iTCP:5175 -sTCP:LISTEN` (also 8000 and 3000). Identify the owner before restarting your own supervisor.

**Setup or build failure** — Read the first failing command from make dev. Check `.venv/bin/python --version`, `node --version`, `npm --version`. Run make setup and retry the failed workspace:build in a practice copy.

**API or proxy unavailable** — Compare `curl -fsS http://127.0.0.1:8000/api/health` with the same path on 5175. One success isolates the proxy/origin layer. Check MIRA_API_URL and host spelling, then restart.

**Database cannot initialize** — Check write access to the parent of MIRA_DB and migration errors on the API console. Start a rehearsal using a fresh private path via MIRA_DB. Keep the original DB intact. Verify /api/health and a fresh session.

**Provider timeout, quota, key or schema error** — Look for gemini.failed/fallback and generation outcome; check configured names privately. Use P01 and deterministic retrieval immediately. Restart only after changing process configuration. A completed turn alone cannot prove a live model call.

**Wrong or unavailable price** — Run the pricing test for that tour and inspect snapshot digest, reason, age boundary, FX end, travel end and hotel night. Use the fixed assessment clock. Show the specialist enquiry if no tariff applies.

**Blank canvas or broken stream** — Inspect Network /api/agent, final state and RUN_ERROR. Compare public Turn with surface node types/indexes; readSurface may reject an incomplete layout. Retry the same request once. Rebuild workspace assets after a renderer edit.

**Session expired or staff rejected** — Check HTTP status on /api/session or /api/staff/me. Reopen visitor session or sign in with the correct staff profile. A 403 on publish requires an approver. Avoid account switching in the traveller profile.

**Trace missing** — Read X-Trace-Id and staff trace endpoint for a new synthetic turn. Compare local stages before investigating remote credentials; show the archived P03 stage list if the cloud is unavailable.

**Eval fails or network drops** — Use evals/report/report.md offline. Only the audited P03 value is tolerated by the runner. For another failure locate its ID, input, trace and expected component; rerun its corresponding test in isolation. Acknowledge any unresolved failure.

<a id="part-15"></a>

## Part 15 · 20-minute presentation and 10-minute defense

Before 11:30: run make dev in the demo environment. Check /api/health, a synthetic visitor session, P01, one family plan and one missing-rate handoff. Verify the staff role privately. If using cloud generation, inspect one successful generation observation before promising it in the demo. Open report.md at P03 and keep test_pricing.py at the Q-1043 audit. Rehearse screen sharing at readable zoom with personal tabs, notifications and .env closed. Open the final recording linked in README and verify playback and audio; keep a local authorized backup if available. The recording and live cloud access were not verified during handbook preparation.

**00–01 · Open the workspace** — “Mira helps Ceylon Compass travellers choose a published journey and obtain a tariff-backed quote. I’ll follow one request from the traveller to staff.”

**01–04 · Show the Part 1 and 6 diagrams** — Trace a message through agui, quote_route and persist. Explain which fields can reach React and what runs without Gemini.

**04–07 · Open a fresh conversation** — Type the P01 Sigiriya prompt. Show USD 315 due, the quote ID, the breakdown panel and mock booking. If the page stalls, show test_exact_quote and the archived result.

**07–10 · Start a fresh family notebook** — Type “Plan a family holiday”, then the six-day family prompt in Part 5. Show sourced days, party detail and the enquiry reference. If ranking varies, explain the verified constraints.

**10–12 · Check an unsupported tariff** — Use P05 in a new trip. Look for the specialist message and absence of a numeric quote. Show the FX end guard.

**12–14 · Switch to a separate staff session** — Locate the enquiry by reference, open its reason, add a synthetic note and change follow-up status. If login fails use the workflow test.

**14–16 · Open the local trace and report** — Follow interpret → retrieval → pricing → validated_ui → persistence. Compare P03 with S03 and explain the USD 285 price difference.

**16–18 · Show M02 regression and the price tests** — Explain 365 → 410 as the corrected age crosses 12. Point to the before/after report and new age-boundary expectation.

**18–20 · Invite a traveller request** — Ask for trip, date and party. Predict quote versus handoff before sending. Keep one practice margin edit ready.

**20–30 · Questions and requested code change** — Restate the requested rule, give one positive case and one boundary case, edit the rehearsal copy, run the targeted test and explain the observed delta.

<a id="part-16"></a>

## Part 16 · Assignment traceability

Use the official weighting to budget screen time: working system 35, agent and generated UI 25, evaluation and tracing 25, code quality and demo 15; bonus up to 10. The case counts in Part 11 measure observed behavior, not a predicted assessment score.

| Requirement | Status and evidence | Demonstrate or defend |
|---|---|---|
| 1 Discover | Implemented with rule/model fallback. interpret, retrieve; D01–D03 and family tests. Universal three-question bound unverified. | Start broad; show the first useful component. |
| 2 Remember | Session and notebook restoration implemented. M05 exercises restored cookies. Greeting with last quote on every entry unverified. | Refresh the same notebook and explain consent. |
| 3 UI | Validated catalogue, A2UI layout and AG-UI transport implemented. 63/63 archived valid turns. | Inspect a picker and price card on desktop/mobile. |
| 4 Ground answers | Published rows, policy precedence and source components implemented. 10/10 grounding cases in report. Open-ended language coverage limited. | Ask about diet or cancellation; open the source. |
| 5 Pricing | Deterministic workbook-backed calculation, public/internal split implemented. 23/24 exact evals; workbook/email conflict accounted for. | Recompute Q-1043 and inspect employee-only cost. |
| 6 Absent rates | Fail-closed guards and staff handoff implemented. 11/11 no-price/handoff checks. Import failure can follow a separate error path. | P05, then trace the missing rate. |
| 7 Private enquiries | Implemented in persist, enquiry and follow_up. W04 plus staff integration test. | Open by reference from authorized console. |
| 8 Draft approval | Implemented with Gemini or extractive fallback. Only approver publishes; direct publication from draft allowed. W05. | Show visibility before/after and backend predicate. |

Mock checkout is implemented as simulation. Remote trace export configurable; live delivery unverified here. Judge implemented; independent human calibration missing. MCP smoke evidence is in evals/report/mcp_smoke.json; it is a separate integration from the web graph. Compose configuration is available; container startup was not tested for this guide.

**Deployment and bonus evidence.** compose.yaml builds the API from apps/api/Dockerfile plus the Next and Compass frontends. It binds the frontend ports to loopback. For MCP, apps/web/mcp/server.mjs uses an SDK stdio server, establishes its own backend session and registers search_tours, list_destinations, get_tour_details, get_quote, create_enquiry and get_enquiry_status. Its run helper reaches the same HTTP application. The traveller browser uses HttpAgent instead. Use the archived evals/report/mcp_smoke.json when an external MCP client is unavailable.

<a id="part-17"></a>

## Part 17 · Second-screen lookup

**Demo entry** · http://127.0.0.1:5175/workspace/index.html · staff /staff · backend :8000/api/health. `make dev` starts all three services. `make test` runs frontend and backend. `make eval` also rewrites the archived report; use the rehearsal copy.

**Flow** · useConversation.send → service.run → main.agui → interpret → retrieve → quote_route → quote_node if ready → compose → save/persist → entry/readSurface → Workspace.jsx.

**Remember** · typed state = messages, turn, surface. Private working data = context, action, rows, quote, internal, events. SQLite holds visitors, trips, trip_turns, traces, quotes, enquiries, notes, drafts, audit, bookings and rate_snapshots.

**Money** · one matching tariff per component/date. Adults ≥12; children 2–11; infants free but count toward 20. Cost in LKR / FX / (1 − margin); ceil to USD 5. Deposit full on day trips or ≤30 days, otherwise ceil to USD 1. T01 Jan 10 2027, two adults → 315 / 315. Q-1043 → 667000 LKR → 2965 / 742. Missing rate → no automated amount.

**Evidence** · report 53/54; 23/24 exact; 11/11 handoff; 63/63 valid turns. P03 is the extra-bed discrepancy. M02 is the corrected age parser. Judge agreement pending. Trace ID is the link from quote to stages. A local trace is available offline.

**Security** · PublicQuote allowlist; backend role + approver check; owner check on trips/quotes; cookie rather than client state establishes identity. Sanitization of free text is partial. Mock success returns a stable reference.

**Configuration** · AS_OF_DATE, MIRA_DATA, MIRA_DB, GEMINI_MODEL, GEMINI_API_KEY, MIRA_ORIGIN, MIRA_API_URL, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY. Keep values off screen.

**Targeted test** · `PYTHONPATH=apps/api .venv/bin/python -m pytest -q apps/api/tests/test_pricing.py`. Staff handoff → test_staff_enquiry_workflow.py. Auth and draft visibility → test_workflows.py. Browser rehearsal → make workspace-browser.

**Three questions to answer aloud** · Why did the quote branch open? Which workbook row would make it refuse? Can the current visitor still book this saved quote?

1. **P0** `apps/api/mira/data.py:170–242` · `calculate`. Where a money decision becomes binding. Start at the two room counts and work outward.
2. **P0** `apps/api/mira/agent_workflow/routing.py:5–12` (facade `agent.py`) · `quote_route`. The interview hinges on knowing when Mira has enough information to quote.
3. **P0** `apps/api/mira/main.py:417–491` · `agui`. The trust boundary between the browser, graph, staff and database.
4. **P0** `apps/ceylon-compass/workspace/useConversation.js:49` · `send`. Tracks the active notebook, retry identity and consent in the demonstrated workspace.
5. **P0** `apps/ceylon-compass/src/lib/live/service.ts:42` · `run`. The shared AG-UI transport. Use it to distinguish a stream error from an invalid snapshot.
6. **P0** `apps/ceylon-compass/workspace/Workspace.jsx:3034` · `PriceBreakdownPanel`. The canonical demo screen. Its quote compatibility checks can hide a price after a party edit.
7. **P0** `apps/api/mira/catalog.py:71–84` · `PublicQuote`. The public financial contract and the discriminated component union.
8. **P0** `apps/api/mira/rates_repository.py:11–26` · `current_rates`. Binds the quote to exact workbook bytes.
9. **P1** `apps/api/mira/store.py:61–71` · `published_records`. Explains migrations, persistence and immediate visibility of published drafts.
10. **P1** `apps/api/mira/surface.py:8–25` · `surface_messages`. Transforms typed components into an ordered A2UI layout.
11. **P1** `apps/ceylon-compass/src/lib/live/surface.ts:54` · `readSurface`. Checks layout references before React can use them.
12. **P1** `apps/api/mira/provider.py:61–97` · `rank`. Limits Gemini to structured choices and records fallback.
13. **P1** `evals/runner.py:168–213` · `execute`. Replays real HTTP turns and exposes the precise failed assertion.
14. **P1** `apps/api/tests/test_pricing.py:21–23` · `test_exact_quote`. Independent expected totals, age limits and workbook discrepancies.
15. **P1** `apps/api/mira/auth.py:262–340` · `get_current_user_optional`. Binds account identity to an active session.
16. **P1** `apps/api/mira/search.py:153–174` · `filter_tours`. Constrains the candidate set before model ranking.
17. **P1** `apps/api/mira/observability.py:104–112` · `sanitize_value`. Determines what may leave the server in trace metadata.
18. **P1** `apps/ceylon-compass/src/components/staff/StaffConsole.tsx:207` · `StaffConsole`. The reviewer can follow a quote into the private operational console.
19. **P1** `evals/judge.py:223–369` · `judge`. Separates automated judgements from agreement with human labels.
20. **P1** `apps/api/mira/planner.py:8–28` · `get_grounded_day_experience`. Connects each custom day to destination evidence.
