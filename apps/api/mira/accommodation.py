"""Accommodation and hotel lookup engine for Ceylon Compass Holidays.

Provides structured, source-grounded hotel recommendations from published tours (T01-T16)
and rate sheet (rate_sheet_2026-27.xlsx), separating accommodation intent from tour packages
and protecting internal contract rates.
"""
import re
from typing import NamedTuple, Optional


class HotelInfo(NamedTuple):
    """Lightweight reference pairing a hotel display name with its source tour ID."""

    name: str
    source_tour_id: str


# Search aliases only. User-facing accommodation details come from published records.
HOTEL_REGISTRY = {
    "H07": HotelInfo("Mirissa Bay Villas", "T11"),
    "H03": HotelInfo("Hotel Suisse", "T07"),
    "H02": HotelInfo("Sigiriya Village", "T08"),
    "H04": HotelInfo("Heritance Tea Factory", "T12"),
    "H05": HotelInfo("Heaven Seven", "T08"),
    "H06": HotelInfo("Ella Gap View Lodge", "T12"),
    "H08": HotelInfo("Galle Fort Hotel", "T12"),
    "H09": HotelInfo("Hikka Tranz by Cinnamon", "T08"),
    "H10": HotelInfo("Cinnamon Wild Yala", "T12"),
    "H12": HotelInfo("Anuradhapura Heritage Lodge", "T09"),
    "H01": HotelInfo("Suriya Resort", "T08"),
}

# Alias map for destination matching
DEST_HOTEL_MAP: dict[str, str] = {
    "mirissa": "H07",
    "kandy": "H03",
    "sigiriya": "H02",
    "dambulla": "H02",
    "nuwara eliya": "H04",
    "nuwara-eliya": "H04",
    "ella": "H06",
    "galle": "H08",
    "hikkaduwa": "H09",
    "yala": "H10",
    "udawalawe": "H10",
    "anuradhapura": "H12",
    "colombo": "H01",
    "negombo": "H01",
    "waikkal": "H01",
}


def find_hotel_for_destination(dest_query: str) -> Optional[HotelInfo]:
    """Resolve hotel info by destination keyword or code."""
    query = dest_query.strip().lower()
    for dest_key, hotel_id in DEST_HOTEL_MAP.items():
        if re.search(r"\b" + re.escape(dest_key) + r"\b", query):
            return HOTEL_REGISTRY.get(hotel_id)
    return None


def find_hotel_by_name(name_query: str) -> Optional[HotelInfo]:
    """Resolve hotel info by property name."""
    query = name_query.strip().lower()
    for hotel in HOTEL_REGISTRY.values():
        if hotel.name.lower() in query or query in hotel.name.lower():
            return hotel
    return None


def is_accommodation_query(text: str) -> tuple[bool, Optional[str], Optional[HotelInfo], bool, bool]:
    """Analyze whether query expresses accommodation intent.
    
    Returns:
        is_accom (bool): True if asking for hotels/stay.
        destination (str | None): Destination name if specified.
        hotel (HotelInfo | None): Matched hotel if specified or resolved.
        is_rate_query (bool): True if asking for price/rate/cost.
        is_alternative_query (bool): True if asking for alternative hotel.
    """
    clean_text = text.strip().lower()

    # Accommodation intent trigger patterns
    hotel_kw = bool(re.search(
        r"\b(?:hotel|hotels|resort|resorts|villa|villas|accommodation|accommodations|lodge|lodges|"
        r"where to stay|where can i stay|places? to stay|room rates?|recommend a hotel|suggest a hotel|"
        r"suggest me a hotel|hotel recommendations?|hotel options?|alternative hotels?|hotel rates?|"
        r"which hotels?|what hotels?|hotel stay)\b", clean_text
    ))

    # If the user specifically asks for a tour or package, prioritize tour discovery unless specifically asking for hotel
    if not hotel_kw or (re.search(r"\b(?:beach stay package|tour package|package tour|holiday package|tours? in|trips? in)\b", clean_text)
                        and not re.search(r"\b(?:hotel|hotels|resort|resorts|villa|villas|room rate)\b", clean_text)):
        return False, None, None, False, False

    # Check for specific hotel name first
    hotel_match = find_hotel_by_name(clean_text)

    # Check for destination
    dest_match = None
    for dest_key in DEST_HOTEL_MAP:
        if re.search(r"\b" + re.escape(dest_key) + r"\b", clean_text):
            dest_match = dest_key
            break

    if not hotel_match and dest_match:
        hotel_match = find_hotel_for_destination(dest_match)

    is_rate_query = bool(re.search(r"\b(?:rate|rates|price|prices|cost|how much|per night|book hotel|just the hotel|standalone)\b", clean_text))
    is_alt_query = bool(re.search(r"\b(?:alternative|other hotel|another hotel|different hotel|else to stay)\b", clean_text))

    return True, dest_match, hotel_match, is_rate_query, is_alt_query
