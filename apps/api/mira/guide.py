"""Traveler-facing map destinations and day sections from published tour records."""
import re
from pathlib import Path

from .data import public_text, tour_card


def guide(records):
    destinations = {
        Path(row["path"]).stem: {"id": row["id"], "name": row["title"]}
        for row in records.values() if row["type"] == "destination"
    }
    tours = []
    for row in records.values():
        if row["type"] != "tour":
            continue
        sections = re.split(r"^#{2,6}\s+([^\n]+)\n", public_text(row["body"]), flags=re.M)
        days = []
        for heading, content in zip(sections[1::2], sections[2::2]):
            match = re.match(r"Day\s+(\d+)\b\s*[:–-]?\s*(.*)", heading, re.I)
            if match and content.strip():
                days.append({"number": int(match[1]), "title": match[2] or heading,
                             "body": content.strip().replace("**", "")})
        tours.append({**tour_card(row), "places": [slug for slug in row["destinations"] if slug in destinations],
                      "days": days})
    return {"places": destinations, "tours": tours}
