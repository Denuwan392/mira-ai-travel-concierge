"""Select grounded passages and construct semantically validated itineraries from published content.

Ensures custom or extended trip days cite real destination guides or linked
published tours, excludes raw accommodation/entrance/package metadata from
daily activities, and validates destination coverage, exclusions, and
arrival/departure ordering before surfacing a ``JourneyPlan``.
"""
import re
from pathlib import Path

from .data import public_text

_METADATA_LINE = re.compile(
    r"^(?:\*{0,2}(?:accommodation|meals?|entrance\s+tickets?(?:\s+included)?|included\s+visits?|duration|start|category|highlights?)\s*:|\d+\.\s+\w+\s*[–-])",
    re.I,
)
_OVERVIEW_LINE = re.compile(
    r"^(?:the ancient kingdoms in a week|for first-time visitors who want to see|"
    r"(?:eleven|seven|fourteen|six|five|eight|ten|two|three)\s+days?\s+of\b|"
    r"sun,\s*sand\s+and\s+sea\b|our grand tour:|new for the \d{4}|enquire for prices)",
    re.I,
)
_ROUTE_OR_STAY_LINE = re.compile(
    r"\(\d+\s+nights?\)|or similar\b|\b\d+\s+nights?\s+at\b|\bbreakfast\s+and\s+dinner\b",
    re.I,
)
_DEPARTURE_LOGISTICS = re.compile(
    r"\b(?:drop[- ]off at the airport|airport drop[- ]off|transfer to (?:the )?airport|departure transfer|fly home)\b",
    re.I,
)


def _is_clean_activity(text: str) -> bool:
    """Return True if ``text`` is a genuine activity description rather than metadata, route summary, or hotel stay."""
    s = text.strip()
    if not s or len(s) < 15:
        return False
    if s.startswith(("#", "**", "* ")):
        return False
    if _METADATA_LINE.match(s) or _OVERVIEW_LINE.match(s) or _ROUTE_OR_STAY_LINE.search(s):
        return False
    return True


def get_grounded_day_experience(
    records,
    destination_id,
    used,
    *,
    allow_departure: bool = False,
    day_num: int | None = None,
    interests: list[str] | None = None,
    excluded_interests: list[str] | None = None,
):
    """Pick an unused, source-grounded activity passage for a destination stop.

    Filters out accommodation/meal/entrance-ticket metadata, package overviews,
    excluded interests, and (unless ``allow_departure`` is True) airport drop-off logistics.
    """
    destination = records[destination_id]
    name = destination["title"]
    slug = Path(destination["path"]).stem
    candidates = []
    excl = [e.lower() for e in (excluded_interests or [])]
    prefs = [i.lower() for i in (interests or [])]

    def _allowed(p: str) -> bool:
        pl = p.lower()
        for e in excl:
            if e in pl or any(w in pl for w in e.split() if len(w) > 3):
                return False
        return True

    # 1. Gather clean paragraphs from the destination guide itself.
    for paragraph in public_text(destination["body"]).split("\n\n"):
        clean_p = paragraph.strip()
        if _is_clean_activity(clean_p) and _allowed(clean_p) and (allow_departure or not _DEPARTURE_LOGISTICS.search(clean_p)):
            candidates.append((clean_p, destination_id))

    # 2. Gather clean activity lines from parsed tour days and body lines.
    for tour in records.values():
        if tour["type"] != "tour" or slug not in tour["destinations"]:
            continue
        for day_obj in tour.get("days", []):
            desc = public_text(day_obj.get("description", "")).strip()
            if not desc or not re.search(r"\b" + re.escape(name) + r"\b", f"{day_obj.get('title', '')} {desc}", re.I):
                continue
            if not _is_clean_activity(desc) or not _allowed(desc):
                continue
            if not allow_departure and _DEPARTURE_LOGISTICS.search(desc):
                continue
            if all(previous != desc for previous, _ in candidates):
                candidates.append((desc, tour["id"]))
        for line in public_text(tour["body"]).splitlines():
            if line.startswith("#") or not re.search(r"\b" + re.escape(name) + r"\b", line, re.I):
                continue
            passage = line.removeprefix("- ").strip()
            if not _is_clean_activity(passage) or not _allowed(passage):
                continue
            if not allow_departure and _DEPARTURE_LOGISTICS.search(passage):
                continue
            if all(previous != passage for previous, _ in candidates):
                candidates.append((passage, tour["id"]))

    # Prioritize candidates matching active user interests
    if prefs:
        candidates.sort(key=lambda pair: -sum(1 for i in prefs if i in pair[0].lower()))

    # 3. Return the first candidate not already used in the current plan.
    for passage, source in candidates:
        if passage not in used:
            return passage, source

    # 4. If all specific activities are used, provide clearly labeled leisure time grounded in the destination.
    label = f"Day {day_num}: " if day_num else ""
    leisure = (
        f"{label}Leisure time in {name} — unhurried day at your own pace "
        "(specific activities to be confirmed by a travel specialist)."
    )
    if leisure not in used:
        return leisure, destination_id
    return f"{label}Open leisure day in {name} (specialist to tailor optional local excursions).", destination_id


def build_grounded_route(destination_ids: list[str], total_days: int) -> list[str]:
    """Distribute ``total_days`` across ``destination_ids`` in coherent sequential blocks."""
    if not destination_ids or total_days < 1:
        return []
    n = min(30, total_days)
    return [destination_ids[min(len(destination_ids) - 1, i * len(destination_ids) // n)] for i in range(n)]


def validate_itinerary(
    days: list,
    expected_days: int,
    requested_dest_ids: list[str],
    records: dict,
    excluded_terms: set[str] | None = None,
) -> tuple[bool, str | None]:
    """Validate semantic and business rules for a constructed ``JourneyPlan``.

    Checks:
    - Duration consistency (``len(days) == expected_days``).
    - Every requested destination appears in the itinerary.
    - No excluded terms appear in day names or passages.
    - Every ``source`` and ``evidence`` ID exists in ``records``.
    - No metadata lines or premature airport drop-off before the final day.
    - Passages are non-empty and not duplicated verbatim.
    """
    if not days or len(days) != expected_days:
        return False, "duration_mismatch"

    present_sources = {d.source for d in days}
    if any(dest_id not in present_sources for dest_id in requested_dest_ids):
        return False, "missing_requested_destination"

    seen_passages: set[str] = set()
    excl = {t.lower() for t in (excluded_terms or set())}
    for idx, d in enumerate(days):
        if d.source not in records:
            return False, "invalid_destination_source"
        if d.evidence and d.evidence not in records:
            return False, "invalid_evidence_source"
        if not d.passage or _METADATA_LINE.match(d.passage.strip()):
            return False, "metadata_in_activity"
        if d.passage in seen_passages:
            return False, "repeated_activity"
        seen_passages.add(d.passage)
        if idx < len(days) - 1 and _DEPARTURE_LOGISTICS.search(d.passage):
            return False, "premature_departure_logistics"
        if excl:
            haystack = f"{d.name} {d.passage}".lower()
            if any(term in haystack for term in excl):
                return False, "excluded_destination_or_activity"

    return True, None
