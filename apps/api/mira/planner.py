"""Select passages for proposed stops from the published guide and linked tours."""
import re
from pathlib import Path

from .data import public_text


def get_grounded_day_experience(records, destination_id, used):
    destination = records[destination_id]
    name = destination["title"]
    slug = Path(destination["path"]).stem
    candidates = []
    for paragraph in public_text(destination["body"]).split("\n\n"):
        if paragraph.strip() and not paragraph.startswith(("#", "**")):
            candidates.append((paragraph.strip(), destination_id))
    for tour in records.values():
        if tour["type"] != "tour" or slug not in tour["destinations"]:
            continue
        for line in public_text(tour["body"]).splitlines():
            if line.startswith("#") or not re.search(r"\b" + re.escape(name) + r"\b", line, re.I):
                continue
            passage = line.removeprefix("- ").strip()
            if passage and all(previous != passage for previous, _ in candidates):
                candidates.append((passage, tour["id"]))
    for passage, source in candidates:
        if passage not in used:
            return passage, source
    return "A specialist will confirm activities for this additional day.", destination_id
