"""Structured tour itinerary parsing for Ceylon Compass Holidays.

Parses rich multi-day markdown tour documents into typed Pydantic models,
preserving daily titles, descriptions, meal inclusions, accommodations,
ticket inclusions, and exclusions with strict source provenance.
"""
import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base Pydantic model forbidding extra/unexpected fields."""

    model_config = ConfigDict(extra="forbid")


class DaySchedule(StrictModel):
    """Structured schedule and inclusions for a single day of a tour."""

    day: int = Field(ge=1, le=30)
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=2000)
    meals: str | None = None
    accommodation: str | None = None
    entrance_tickets: str | None = None
    other_inclusions: str | None = None
    optional_activities: str | None = None
    source: str = Field(pattern=r"^[A-Z][A-Z0-9-]{1,60}$")


class TourItinerary(StrictModel):
    """Complete parsed tour document including metadata, daily stops, and inclusions."""

    id: str = Field(pattern=r"^[A-Z][A-Z0-9-]{1,60}$")
    title: str = Field(min_length=1, max_length=500)
    status: Literal["published", "draft"]
    category: str = ""
    duration: str = ""
    start: str = ""
    destinations: list[str] = Field(default_factory=list)
    hotels: list[str] = Field(default_factory=list)
    teaser_price: str | None = None
    last_updated: str = ""
    summary: str = ""
    days: list[DaySchedule] = Field(default_factory=list)
    inclusions: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    source: str = Field(pattern=r"^[A-Z][A-Z0-9-]{1,60}$")


def parse_day_section(day_num: int, header_line: str, body_text: str, source_id: str) -> DaySchedule:
    """Parse a single day section markdown into a DaySchedule model."""
    # Header format: "Day X: Title" or "Day X - Title"
    title_match = re.search(r"Day\s+\d+\s*[:\-]\s*(.*)", header_line, re.I)
    title = title_match.group(1).strip() if title_match else header_line.strip()

    # Extract field bullets:
    # - **Meals:** ...
    # - **Accommodation:** ...
    # - **Entrance tickets included:** ...
    # - **Other inclusions:** ...
    # - **Optional activities:** ...
    meals = None
    accommodation = None
    entrance_tickets = None
    other_inclusions = None
    optional_activities = None

    desc_lines = []
    for line in body_text.splitlines():
        trimmed = line.strip()
        if re.match(r"^-\s*\*\*Meals:\*\*", trimmed, re.I):
            meals = re.sub(r"^-\s*\*\*Meals:\*\*\s*", "", trimmed, flags=re.I).strip()
        elif re.match(r"^-\s*\*\*Accommodation:\*\*", trimmed, re.I):
            accommodation = re.sub(r"^-\s*\*\*Accommodation:\*\*\s*", "", trimmed, flags=re.I).strip()
        elif re.match(r"^-\s*\*\*Entrance tickets included:\*\*", trimmed, re.I):
            entrance_tickets = re.sub(r"^-\s*\*\*Entrance tickets included:\*\*\s*", "", trimmed, flags=re.I).strip()
        elif re.match(r"^-\s*\*\*Other inclusions:\*\*", trimmed, re.I):
            other_inclusions = re.sub(r"^-\s*\*\*Other inclusions:\*\*\s*", "", trimmed, flags=re.I).strip()
        elif re.match(r"^-\s*\*\*Optional activities:\*\*", trimmed, re.I):
            optional_activities = re.sub(r"^-\s*\*\*Optional activities:\*\*\s*", "", trimmed, flags=re.I).strip()
        elif trimmed and not trimmed.startswith("#"):
            if not trimmed.startswith("- **"):
                desc_lines.append(trimmed)

    description = " ".join(desc_lines).strip()
    if not description:
        description = title

    return DaySchedule(
        day=day_num,
        title=title,
        description=description,
        meals=meals,
        accommodation=accommodation,
        entrance_tickets=entrance_tickets,
        other_inclusions=other_inclusions,
        optional_activities=optional_activities,
        source=source_id,
    )


def parse_tour_markdown(meta: dict, body: str) -> TourItinerary:
    """Parse a full tour markdown document into a TourItinerary model."""
    tour_id = meta.get("id", "")
    title = meta.get("title", "")
    status = meta.get("status", "draft")
    category = meta.get("category", "")
    duration = meta.get("duration", "")
    start = meta.get("start", "")
    destinations = meta.get("destinations", [])
    hotels = meta.get("hotels", [])
    teaser_price = meta.get("teaser_price")
    last_updated = str(meta.get("last_updated", ""))

    # Summary is the intro paragraph under the H1
    intro_match = re.search(r"^#\s+[^\n]+\n+([^\n#]+)", body, re.M)
    summary = intro_match.group(1).strip() if intro_match else ""

    # Parse Days: "### Day 1: ..." to next "### Day" or "##"
    day_matches = list(re.finditer(r"^###\s+Day\s+(\d+)\s*[:\-]\s*([^\n]+)", body, re.M))
    days: list[DaySchedule] = []

    for i, m in enumerate(day_matches):
        day_num = int(m.group(1))
        header_title = m.group(2).strip()
        start_idx = m.end()
        end_idx = day_matches[i + 1].start() if i + 1 < len(day_matches) else None
        
        # If last day, cut before "## Inclusions" or "##"
        if end_idx is None:
            next_h2 = re.search(r"^##\s+", body[start_idx:], re.M)
            end_idx = start_idx + next_h2.start() if next_h2 else len(body)

        day_text = body[start_idx:end_idx].strip()
        days.append(parse_day_section(day_num, f"Day {day_num}: {header_title}", day_text, tour_id))

    # Parse Inclusions & Exclusions
    inclusions = []
    if inc_match := re.search(r"^##\s+Inclusions\s*\n([\s\S]*?)(?=^##|\Z)", body, re.M):
        for line in inc_match.group(1).splitlines():
            line = line.strip().removeprefix("-").strip()
            if line:
                inclusions.append(line)

    exclusions = []
    if exc_match := re.search(r"^##\s+Exclusions\s*\n([\s\S]*?)(?=^##|\Z)", body, re.M):
        for line in exc_match.group(1).splitlines():
            line = line.strip().removeprefix("-").strip()
            if line:
                exclusions.append(line)

    return TourItinerary(
        id=tour_id,
        title=title,
        status=status,
        category=category,
        duration=duration,
        start=start,
        destinations=destinations,
        hotels=hotels,
        teaser_price=teaser_price,
        last_updated=last_updated,
        summary=summary,
        days=days,
        inclusions=inclusions,
        exclusions=exclusions,
        source=tour_id,
    )
