"""Helper to resolve attributes through the ``mira.agent`` facade for monkeypatch compatibility."""
import sys


def facade_attr(name: str, default):
    """Return ``getattr(mira.agent, name, default)`` if ``mira.agent`` is loaded."""
    mod = sys.modules.get("mira.agent")
    return getattr(mod, name, default) if mod is not None else default
