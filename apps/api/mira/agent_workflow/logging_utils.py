"""Node-level error and timing logging decorator for LangGraph workflow nodes."""
import logging
from functools import wraps
from time import perf_counter

from ..observability import elapsed, event
from .state import working


def log_node_errors(fn):
    """Decorator that records node execution path, duration, and unhandled exceptions."""
    node_name = {"quote_node": "quote"}.get(fn.__name__, fn.__name__)

    @wraps(fn)
    def run(state):
        started = perf_counter()
        w = working.get()
        if isinstance(w, dict):
            w.setdefault("execution_path", []).append(node_name)
        try:
            return fn(state)
        except Exception as exc:
            if isinstance(w, dict):
                w.setdefault("errors", []).append(f"{node_name}: {type(exc).__name__}")
            event("ERROR", "workflow.node_failed", level=logging.ERROR, exception=True, node=node_name)
            raise
        finally:
            if isinstance(w, dict):
                w.setdefault("node_durations", {})[node_name] = elapsed(started)

    return run
