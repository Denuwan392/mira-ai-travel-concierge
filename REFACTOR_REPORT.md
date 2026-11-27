# Refactor Report — Mira LangGraph Workflow Modularization

## 1. Original Architecture

Previously, Mira's entire LangGraph conversational travel-agent workflow lived in a single monolithic file, [apps/api/mira/agent.py](file:///Users/denuwanwijesinghe/Documents/BSc.%20Artficial%20Intellligence/Competition/intern_assignment/apps/api/mira/agent.py) (~1,188 lines after documentation). It combined:

- Shared `ContextVar` definitions (`visitor_context`, `run_context`, `working`) and `GraphState`
- Regex constants (`MONTHS`, `ALIASES`, `WORDS`, `COUNT`) and parsing helpers (`count`, `parse_date`, `section`)
- All 5 LangGraph nodes (`interpret`, `retrieve`, `quote_node`, `compose`, `save`)
- Context loading, idempotent replay validation, and optimistic concurrency persistence (`persist`)
- Enquiry deduplication (`matching_enquiry`, `quote_enquiry`)
- Conditional edge routing (`quote_route`) and node error logging (`log_node_errors`)
- Graph compilation (`builder`, `graph`)

All external callers (`mira.main`) and test monkeypatches (`test_workflows.py`, `test_tour_relevance_regression.py`, `test_notebooks.py`, `test_family_planning_workflow.py`, `test_enquiry_and_context_regression.py`) imported symbols directly from `mira.agent`.

---

## 2. Updated Architecture

The workflow has been modularized into an internal package, `apps/api/mira/agent_workflow/`, while [apps/api/mira/agent.py](file:///Users/denuwanwijesinghe/Documents/BSc.%20Artficial%20Intellligence/Competition/intern_assignment/apps/api/mira/agent.py) is retained as a thin, 50-line backward-compatible facade.

```text
apps/api/mira/
├── agent.py                        # Backward-compatible public facade
└── agent_workflow/
    ├── __init__.py                 # Package marker
    ├── state.py                    # Canonical ContextVars (visitor_context, run_context, working) & GraphState
    ├── constants.py                # MONTHS, ALIASES, WORDS, COUNT
    ├── facade.py                   # facade_attr() for monkeypatch-safe resolution via mira.agent
    ├── parsing.py                  # count(), parse_date(), section()
    ├── logging_utils.py            # log_node_errors()
    ├── routing.py                  # quote_route()
    ├── replay.py                   # load_context_and_replay(), validate_replay_turn()
    ├── enquiry.py                  # matching_enquiry(), quote_enquiry()
    ├── interpret.py                # interpret() + 8 focused internal helpers
    ├── retrieve.py                 # retrieve()
    ├── quote.py                    # quote_node()
    ├── compose.py                  # compose() + 7 focused internal handlers
    ├── persistence.py              # persist(), save()
    └── graph.py                    # StateGraph builder & compiled graph
```

---

## 3. Module Responsibility Map

| Module | Responsibility |
|---|---|
| `mira/agent.py` | Backward-compatible facade re-exporting all public symbols, ContextVars, nodes, and monkeypatchable bindings. |
| `mira/agent_workflow/state.py` | Single canonical definition of `visitor_context`, `run_context`, `working`, and `GraphState`. |
| `mira/agent_workflow/constants.py` | Static regex patterns and word/month lookup tables (`MONTHS`, `ALIASES`, `WORDS`, `COUNT`). |
| `mira/agent_workflow/facade.py` | `facade_attr(name, default)` helper resolving monkeypatched attributes (`published_records`, `rank`, `notebook_intent`) on `mira.agent`. |
| `mira/agent_workflow/parsing.py` | Pure parsing utilities (`count`, `parse_date`, `section`). |
| `mira/agent_workflow/logging_utils.py` | `log_node_errors` decorator for node-level exception logging. |
| `mira/agent_workflow/routing.py` | `quote_route` conditional edge deciding `quote` vs `compose`. |
| `mira/agent_workflow/replay.py` | `load_context_and_replay` and `validate_replay_turn` for idempotent replay and stale quote invalidation. |
| `mira/agent_workflow/enquiry.py` | `matching_enquiry` and `quote_enquiry` for enquiry deduplication and `ENQ-YYYY-...` reference assignment. |
| `mira/agent_workflow/interpret.py` | `interpret` node decomposed into `_handle_structured_action`, `_classify_intent`, `_populate_custom_context`, `_extract_date_and_travellers`, `_resolve_tour_and_search`, `_classify_traveller_and_trip_type`, `_handle_notebook_panel_action`, and `_handle_notebook_planning`. |
| `mira/agent_workflow/retrieve.py` | `retrieve` node selecting grounded policies, destinations, or filtered/ranked tours. |
| `mira/agent_workflow/quote.py` | `quote_node` computing live USD quotes via `data.price()` and capturing unavailability reasons. |
| `mira/agent_workflow/compose.py` | `compose` node decomposed into `_build_row_components`, `_compose_verified_quote`, `_compose_unavailable_quote`, `_compose_custom_handoff`, `_compose_draft_handoff`, `_compose_accommodation_response`, `_compose_discovery_or_clarification`, `_apply_custom_proposal_panels`, and `_apply_notebook_source_panels`. |
| `mira/agent_workflow/persistence.py` | `persist` (SQLite `BEGIN IMMEDIATE` + optimistic concurrency check) and async `save` node. |
| `mira/agent_workflow/graph.py` | LangGraph `StateGraph` wiring (`START -> interpret -> retrieve -> [quote ->] compose -> save -> END`). |

---

## 4. Original-to-New Function Mapping

| Original (`mira/agent.py`) | New Canonical Location |
|---|---|
| `visitor_context`, `run_context`, `working`, `GraphState` | `mira.agent_workflow.state` |
| `MONTHS`, `ALIASES`, `WORDS`, `COUNT` | `mira.agent_workflow.constants` |
| `count`, `parse_date`, `section` | `mira.agent_workflow.parsing` |
| `log_node_errors` | `mira.agent_workflow.logging_utils` |
| `quote_route` | `mira.agent_workflow.routing` |
| `matching_enquiry`, `quote_enquiry` | `mira.agent_workflow.enquiry` |
| `interpret` (context/replay parts) | `mira.agent_workflow.replay.{load_context_and_replay,validate_replay_turn}` |
| `interpret` (intent & planning) | `mira.agent_workflow.interpret.interpret` + `_handle_*` / `_classify_*` / `_extract_*` / `_resolve_*` |
| `retrieve` | `mira.agent_workflow.retrieve.retrieve` |
| `quote_node` | `mira.agent_workflow.quote.quote_node` |
| `compose` | `mira.agent_workflow.compose.compose` + `_build_*` / `_compose_*` / `_apply_*` |
| `persist`, `save` | `mira.agent_workflow.persistence.{persist,save}` |
| `builder`, `graph` | `mira.agent_workflow.graph.{builder,graph}` |

---

## 5. Dependency Changes

- **No new external dependencies** were added.
- **No changes to `mira.main` imports**: `from .agent import builder, run_context, visitor_context, working` continues to resolve identically.
- Internal module dependency graph inside `mira.agent_workflow` is strictly acyclic:
  `constants` / `state` / `facade` -> `parsing` / `logging_utils` / `enquiry` / `replay` -> `routing` / `interpret` / `retrieve` / `quote` / `compose` / `persistence` -> `graph` -> `mira.agent`.

---

## 6. Backward Compatibility Strategy

1. **Facade at `apps/api/mira/agent.py`**: Re-exports every symbol listed in `__all__` (`builder`, `graph`, `interpret`, `retrieve`, `quote_node`, `compose`, `save`, `persist`, `parse_date`, `visitor_context`, `run_context`, `working`, etc.).
2. **Canonical ContextVars**: `visitor_context`, `run_context`, and `working` are instantiated once in `mira.agent_workflow.state` and imported by reference everywhere, verified by `test_characterization_contextvar_identity_and_graph_nodes`.
3. **Monkeypatch Compatibility**: Existing tests patch `agent.published_records`, `agent.rank`, and `agent.notebook_intent`. `interpret.py` and `retrieve.py` resolve those three callables through `facade_attr()` so monkeypatching `mira.agent` intercepts calls inside the submodules without creating circular imports.

---

## 7. Before-and-After Line Counts

| File | Before | After |
|---|---:|---:|
| `apps/api/mira/agent.py` | 1,188 | 50 |
| `apps/api/mira/agent_workflow/__init__.py` | — | 1 |
| `apps/api/mira/agent_workflow/compose.py` | — | 444 |
| `apps/api/mira/agent_workflow/constants.py` | — | 12 |
| `apps/api/mira/agent_workflow/enquiry.py` | — | 41 |
| `apps/api/mira/agent_workflow/facade.py` | — | 8 |
| `apps/api/mira/agent_workflow/graph.py` | — | 24 |
| `apps/api/mira/agent_workflow/interpret.py` | — | 507 |
| `apps/api/mira/agent_workflow/logging_utils.py` | — | 18 |
| `apps/api/mira/agent_workflow/parsing.py` | — | 37 |
| `apps/api/mira/agent_workflow/persistence.py` | — | 120 |
| `apps/api/mira/agent_workflow/quote.py` | — | 43 |
| `apps/api/mira/agent_workflow/replay.py` | — | 54 |
| `apps/api/mira/agent_workflow/retrieve.py` | — | 67 |
| `apps/api/mira/agent_workflow/routing.py` | — | 12 |
| `apps/api/mira/agent_workflow/state.py` | — | 24 |
| **Total** | **1,188** | **1,462** |

---

## 8. Before-and-After Test and Evaluation Results

| Suite | Command | Before | After |
|---|---|---|---|
| Backend pytest (existing + characterization) | `PYTHONPATH=apps/api:apps/api/.deps ./.venv/bin/python3 -m pytest apps/api/tests -q` | 222 passed (plus 5 new characterization tests = 227 passed) | **227 passed** in 19.33s |
| Bytecode compilation | `PYTHONPATH=apps/api:apps/api/.deps ./.venv/bin/python3 -m compileall -q apps/api/mira evals` | Exit 0 | **Exit 0** |
| Evaluation suite | `PYTHONPATH=apps/api:apps/api/.deps ./.venv/bin/python3 evals/runner.py` | 53/54 passed (98.1%), 63/63 turns validated | **53/54 passed (98.1%)**, 63/63 turns validated |
| Normalized `evals/report/report.json` diff | Normalized comparison excluding `generated_at`, `ms`, `duration_ms`, UUIDs, and `ENQ-...` refs | Baseline | **100% identical** (only `generated_at` differed) |

---

## 9. Known Pre-Existing Failures

- **`evals/runner.py` case `P03`** (pre-existing): Expected `[{'tour': 'T09', 'price_usd': 2680, 'deposit_usd': 670}]`, observed `[{'tour': 'T09', 'price_usd': 2965, 'deposit_usd': 742}]`. This is the documented Q-1043 discrepancy where `sample_quotes.md` omitted child extra-bed costs (`64,000 LKR`), whereas the authoritative rate workbook includes them (also proven in `apps/api/tests/test_pricing.py::test_q1043_comprehensive_financial_breakdown_audit`). Left untouched per non-negotiable constraints.

---

## 10. Unresolved Regression Risks

- **Direct monkeypatching of submodule-internal functions**: External tests patching `mira.agent.published_records`, `mira.agent.rank`, or `mira.agent.notebook_intent` are covered via `facade_attr()`. Future tests that patch other symbols on `mira.agent` (e.g., `mira.agent.price`) would only intercept calls if those symbols are also routed through `facade_attr()`.
- **Shared mutable `working` dict**: Helper functions in `interpret.py` and `compose.py` mutate `ctx` and `working.get()` in place in the exact original order; reordering helper calls without reviewing `ctx`/`working` mutations could alter state transitions.

---

## 11. AI-Assisted Changes

This modularization, characterization test suite ([apps/api/tests/test_agent_refactor_characterization.py](file:///Users/denuwanwijesinghe/Documents/BSc.%20Artficial%20Intellligence/Competition/intern_assignment/apps/api/tests/test_agent_refactor_characterization.py)), and `REFACTOR_REPORT.md` were generated and verified with AI assistance, with all behavioral invariants validated against the pre-refactor test suite and normalized evaluation report.
