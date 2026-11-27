"""Deterministic date, count, and markdown section parsing helpers."""
import re
from datetime import date

from ..data import public_text, tour_card
from .constants import MONTHS, WORDS


def count(word):
    """Parse a digit string or English number word (1..20) into an integer."""
    return int(word) if word.isdigit() else WORDS.index(word)


def parse_date(text):
    """Extract an ISO ``YYYY-MM-DD`` date from ISO or natural-language day/month/year text."""
    if match := re.search(r"\b\d{4}-\d{2}-\d{2}\b", text):
        return date.fromisoformat(match[0]).isoformat()
    names = "|".join(month[:3] + "(?:" + month[3:] + ")?" if len(month) > 3 else month for month in MONTHS)
    if match := re.search(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({names})\s+(\d{{4}})\b", text, re.I):
        month = next(i + 1 for i, m in enumerate(MONTHS) if m.lower().startswith(match[2].lower()))
        return date(int(match[3]), month, int(match[1])).isoformat()
    if match := re.search(rf"\b({names})\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", text, re.I):
        month = next(i + 1 for i, m in enumerate(MONTHS) if m.lower().startswith(match[1].lower()))
        return date(int(match[3]), month, int(match[2])).isoformat()
    if match := re.search(rf"\b(\d{{4}})\s+({names})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b", text, re.I):
        month = next(i + 1 for i, m in enumerate(MONTHS) if m.lower().startswith(match[2].lower()))
        return date(int(match[1]), month, int(match[3])).isoformat()
    return None


def section(row, heading=None, keyword=None):
    """Extract a sanitized markdown section by heading, keyword lines, or intro summary."""
    body = row["body"]
    if heading:
        match = re.search(rf"^#+ {re.escape(heading)}\s*\n([\s\S]*?)(?=^#|\Z)", body, re.M)
        return public_text(match[1]).strip() if match else ""
    if keyword:
        return "\n".join(public_text(line) for line in body.splitlines()
                         if keyword in line.lower() and not line.startswith("#"))[:500]
    return tour_card(row)["summary"]
