"""Canonical shared state and ContextVar definitions for Mira's LangGraph workflow.

All ContextVar objects have exactly one canonical definition here and are
re-exported by ``mira.agent`` so ``mira.main`` and workflow nodes share the
exact same ContextVar instances.
"""
from contextvars import ContextVar
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

visitor_context = ContextVar("visitor", default=None)
run_context = ContextVar("run", default=None)

# Only the validated turn is emitted as graph state. The per-run working data stays server-side.
working = ContextVar("working", default=None)


class GraphState(TypedDict, total=False):
    """Public LangGraph state emitted to AG-UI (surface, messages, and validated turn)."""

    surface: list[dict]
    messages: Annotated[list, add_messages]
    turn: dict
