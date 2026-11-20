"""Compose a v0.9 A2UI surface exclusively from an already validated traveller turn."""
from .catalog import Turn

CATALOG = "urn:ceylon-compass:mira:1"
SURFACE = "journey"


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
    return [
        {"version": "v0.9", "createSurface": {"surfaceId": SURFACE, "catalogId": CATALOG}},
        {"version": "v0.9", "updateComponents": {"surfaceId": SURFACE, "components": [root, *nodes]}},
    ]
