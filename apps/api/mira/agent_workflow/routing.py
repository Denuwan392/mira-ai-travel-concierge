"""Conditional edge routing functions for Mira's LangGraph workflow."""
import logging

from ..observability import event
from .state import working


def post_interpret_route(_):
    """Conditional edge after ``interpret``: skip to ``save`` on replay, else ``retrieve``."""
    w = working.get()
    has_replay = "replay" in w
    target = "save" if has_replay else "retrieve"
    event(
        "AGENT",
        "routing.selected",
        level=logging.INFO,
        edge=f"interpret -> {target}",
        conditions={"has_replay": has_replay},
        reason="idempotent replay detected" if has_replay else "fresh turn requires retrieval",
    )
    return target


def quote_route(_):
    """Conditional edge: route to ``quote`` only when tour, date, adults, and all child ages are known."""
    w = working.get()
    ctx = w["context"]
    conditions = {
        "action_is_discover": w["action"] == "discover",
        "not_select": not w["select"],
        "tour_in_catalogue": ctx.get("tour") in w["tours"],
        "has_date": bool(ctx.get("date")),
        "has_adults": "adults" in ctx,
        "child_ages_complete": ctx.get("kids", 0) == len(ctx.get("ages", [])),
    }
    if all(conditions.values()):
        target = "quote"
        reason = "all required quote inputs present"
    else:
        target = "compose"
        missing = [k for k, v in conditions.items() if not v]
        reason = f"skipping quote ({', '.join(missing)})"
    event(
        "AGENT",
        "routing.selected",
        level=logging.INFO,
        edge=f"retrieve -> {target}",
        conditions=conditions,
        reason=reason,
    )
    return target
