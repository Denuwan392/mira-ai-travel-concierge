"""Compose a v0.9 A2UI surface exclusively from an already validated traveller turn.

Translates the backend's ``Turn`` component list into A2UI ``createSurface`` and
``updateComponents`` protocol messages consumed by the frontend renderer.
"""
from .catalog import Turn

CATALOG = "urn:ceylon-compass:mira:1"
SURFACE = "journey"


def surface_messages(turn: Turn) -> list[dict]:
    """Build A2UI v0.9 surface creation and component tree messages for a turn.

    When a turn contains ``TourCard`` items without detail/transactional widgets
    (``TravellerPicker``, ``PriceBreakdown``, ``BookingForm``), it is treated as
    a discovery view and collapses individual cards into a ``JourneyResults``
    list node.

    Args:
        turn: Validated ``catalog.Turn`` payload for the current assistant turn.

    Returns:
        Two-element list containing the ``createSurface`` and
        ``updateComponents`` A2UI v0.9 protocol dictionaries.
    """
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
    return [
        {"version": "v0.9", "createSurface": {"surfaceId": SURFACE, "catalogId": CATALOG}},
        {"version": "v0.9", "updateComponents": {"surfaceId": SURFACE, "components": [root, *nodes]}},
    ]
