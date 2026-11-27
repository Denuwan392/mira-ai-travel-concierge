"""Traveler-facing map destinations, tour summaries, and day-by-day sections.

Transforms published markdown records into a structured JSON-ready dictionary
for the frontend guide/explorer UI, stripping internal-only pricing or comments.
"""
import re
from pathlib import Path

from .data import public_text, tour_card


def guide(records):
    """Build the public travel guide payload from published content records.

    Args:
        records: Mapping of record ID -> parsed content dictionary (typically
            from ``store.published_records()``).

    Returns:
        Dict with four keys:
        - ``places``: Map of destination slug -> ``{id, name, description}``.
        - ``tours``: List of tour card dicts enriched with valid ``places`` slugs
          and parsed ``days`` (``{number, title, body}``).
        - ``pages``: List of public policy/FAQ/page metadata (excluding ``P06``,
          which is reserved for internal/non-public use).
        - ``details``: Map of tour ID -> ``{included, excluded}`` sanitized lists.
    """
    # Index published destinations by filename stem (slug) for quick lookup.
    destinations = {
        Path(row["path"]).stem: {"id": row["id"], "name": row["title"], "description": tour_card(row)["summary"]}
        for row in records.values() if row["type"] == "destination"
    }
    tours = []
    for row in records.values():
        if row["type"] != "tour":
            continue
        # Split markdown body on H2-H6 headings so each "Day N" section can be extracted.
        sections = re.split(r"^#{2,6}\s+([^\n]+)\n", public_text(row["body"]), flags=re.M)
        days = []
        for heading, content in zip(sections[1::2], sections[2::2]):
            match = re.match(r"Day\s+(\d+)\b\s*[:–-]?\s*(.*)", heading, re.I)
            if match and content.strip():
                days.append({"number": int(match[1]), "title": match[2] or heading,
                             "body": content.strip().replace("**", "")})
        tours.append({**tour_card(row), "places": [slug for slug in row["destinations"] if slug in destinations],
                      "days": days})
    # P06 is excluded from the public pages list per dataset visibility rules.
    pages = [{"id": row["id"], "title": row["title"], "slug": Path(row["path"]).stem}
             for row in records.values() if row["type"] in {"policy", "faq", "page"} and row["id"] != "P06"]
    details = {row["id"]: {
        "included": public_text("\n".join(row.get("inclusions", []))).splitlines(),
        "excluded": public_text("\n".join(row.get("exclusions", []))).splitlines(),
    } for row in records.values() if row["type"] == "tour"}
    return {"places": destinations, "tours": tours, "pages": pages, "details": details}
