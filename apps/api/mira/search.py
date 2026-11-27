"""Deterministic tour constraint extraction, filtering, and ranking."""
import re

WORDS = (
    "zero one two three four five six seven eight nine ten eleven twelve "
    "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty"
).split()
COUNT = r"\d{1,3}|" + "|".join(WORDS[1:])


def parse_count(word: str) -> int:
    """Convert a digit string or English number word (1..20) to an integer."""
    return int(word) if word.isdigit() else WORDS.index(word)


def tour_days(tour: dict) -> int:
    """Infer total tour duration in days from ``duration`` text or parsed ``days``."""
    duration = (tour.get("duration") or "").lower()
    if "half day" in duration:
        return 1
    if match := re.search(r"(\d+)\s*days?", duration):
        return int(match.group(1))
    if match := re.search(r"(\d+)\s*nights?", duration):
        return int(match.group(1)) + 1
    return len(tour.get("days", [])) or 1


def is_day_tour(tour: dict) -> bool:
    """Return True if the tour is a single-day or half-day excursion."""
    duration = (tour.get("duration") or "").lower()
    category = (tour.get("category") or "").lower()
    if "night" in duration:
        return False
    return category in {"day tour", "city tour"} or "day" in duration


def is_multi_day_tour(tour: dict) -> bool:
    """Return True if the tour spans multiple days or overnight stays."""
    duration = (tour.get("duration") or "").lower()
    category = (tour.get("category") or "").lower()
    return "night" in duration or category in {
        "round trip",
        "short stay",
        "beach stay",
        "special interest",
    }


def extract_search_constraints(text: str) -> dict:
    """Extract explicit trip-type, duration, departure, and theme constraints from user text."""
    constraints: dict = {}
    negated_multiday = bool(re.search(r"\b(?:not\s+(?:a\s+)?|no\s+)multi[- ]?day\b", text))
    day_tour_hit = bool(
        negated_multiday
        or re.search(
            r"(?<!multi-)(?<!multi )\bday\s+(?:trip|tour|excursion)s?\b"
            r"|\b(?:one|1)[- ]day\b"
            r"|\bonly\s+(?:have\s+)?(?:one|1)\s+day\b"
            r"|\bhalf[- ]day\b"
            r"|\bcity\s+tours?\b"
            r"|\bshort\s+trip\b",
            text,
        )
    )

    days = None
    if re.search(r"\b(?:two|2)[- ]weeks?\b|\bfortnight\b", text):
        days = 14
    elif re.search(r"\b(?:one|1)[- ]week\b", text):
        days = 7
    elif day_match := re.search(rf"\b({COUNT})[- ]days?\b", text):
        days = parse_count(day_match.group(1))
    elif night_match := re.search(rf"\b({COUNT})[- ]nights?\b", text):
        days = parse_count(night_match.group(1)) + 1

    multi_day_hit = False
    if not day_tour_hit:
        if re.search(r"\bmulti[- ]?days?\b", text):
            multi_day_hit = True
        elif days is not None and days >= 2:
            multi_day_hit = True

    if day_tour_hit:
        constraints["trip_type"] = "day tour"
        if days is None:
            days = 1
    elif multi_day_hit:
        constraints["trip_type"] = "multi-day"

    if days is not None:
        constraints["days"] = days

    if dep_match := re.search(
        r"\b(?:from|departing(?:\s+from)?|starting\s+(?:from|in))\s+"
        r"(kandy|colombo|galle|mirissa|negombo|ella|sigiriya|nuwara\s+eliya|jaffna|airport|cmb)\b",
        text,
    ):
        constraints["departure"] = dep_match.group(1).strip()

    if re.search(r"\b(?:beach(?:es)?|coast(?:al)?|whale|dolphin)\b", text):
        constraints["theme"] = "beach"
    elif re.search(r"\b(?:cultur(?:e|al)|heritage|ancient|temple|triangle)\b", text):
        constraints["theme"] = "cultural"
    elif re.search(r"\b(?:wildlife|safari|elephant|leopard)\b", text):
        constraints["theme"] = "wildlife"
    elif re.search(
        r"\b(?:train|scenic|scener(?:y|ies)|tea|hill(?:s|\s+country)?|mountains?|highlands?|"
        r"cool(?:\s+weather)?|misty?|peaceful|tranquil|waterfall(?:s)?)\b",
        text,
    ):
        constraints["theme"] = "scenic"

    return constraints


def _matches_theme(tour: dict, theme: str) -> bool:
    """Check whether a tour's title, category, destinations, or intro match ``theme``."""
    haystack = " ".join(
        [
            tour.get("title", ""),
            tour.get("category", ""),
            " ".join(tour.get("destinations", [])),
            tour.get("body", "")[:600],
        ]
    ).lower()
    if theme == "beach":
        return tour.get("category", "").lower() == "beach stay" or bool(
            re.search(r"\b(?:beach|mirissa|whale|dolphin)\b", haystack)
        )
    if theme == "cultural":
        return bool(
            re.search(
                r"\b(?:cultural|culture|heritage|ancient|anuradhapura|polonnaruwa|sigiriya|kandy|dambulla|temple)\b",
                haystack,
            )
        )
    if theme == "wildlife":
        return bool(
            re.search(
                r"\b(?:wildlife|safari|yala|udawalawe|minneriya|elephant|leopard|whale|dolphin)\b",
                haystack,
            )
        )
    if theme == "scenic":
        full_haystack = " ".join(
            [
                tour.get("title", ""),
                tour.get("category", ""),
                " ".join(tour.get("destinations", [])),
                tour.get("body", "")[:1800],
            ]
        ).lower()
        return bool(
            re.search(
                r"\b(?:train|scenic|scener(?:y|ies)|tea|ella|nuwara[- ]eliya|hill(?:s|\s+country)?|"
                r"mountains?|highlands?|misty?|cool|waterfall(?:s)?|panoram(?:a|ic)|countryside)\b",
                full_haystack,
            )
        )
    return True


def _matches_departure(tour: dict, departure: str, trip_type: str | None) -> bool:
    """Match requested departure city against ``tour['start']``, including Colombo/airport aliases."""
    start = (tour.get("start") or "").lower()
    if departure in start:
        return True
    if departure == "colombo" and trip_type != "day tour":
        return "airport" in start or "cmb" in start or "negombo" in start
    if departure == "mirissa" and "south" in start:
        return True
    return False


def filter_tours(tours: dict, constraints: dict) -> dict:
    """Deterministically filter published tours to those satisfying explicit constraints."""
    trip_type = constraints.get("trip_type")
    departure = constraints.get("departure")
    theme = constraints.get("theme")

    pool = {k: t for k, t in tours.items() if t.get("type") == "tour"}
    if trip_type == "day tour":
        pool = {k: t for k, t in pool.items() if is_day_tour(t)}
    elif trip_type == "multi-day":
        # Exclude T06 (conflicting_tour_scope) from primary multi-day recommendations
        pool = {k: t for k, t in pool.items() if is_multi_day_tour(t) and k != "T06"}

    if departure:
        pool = {k: t for k, t in pool.items() if _matches_departure(t, departure, trip_type)}

    if theme:
        themed = {k: t for k, t in pool.items() if _matches_theme(t, theme)}
        if themed:
            pool = themed

    return pool


def rank_filtered_tours(pool: dict, constraints: dict) -> list[str]:
    """Deterministically rank filtered tours by duration proximity and diversity."""
    if not pool:
        return []
    target_days = constraints.get("days")
    trip_type = constraints.get("trip_type")
    theme = constraints.get("theme")

    def score(tour_id: str) -> tuple:
        t = pool[tour_id]
        d = tour_days(t)
        day_diff = abs(d - target_days) if target_days else 0
        theme_bonus = 0 if (theme and _matches_theme(t, theme)) else 1
        # Prefer diverse flagship day tours when no departure/theme is specified
        default_order = {
            "T01": 0,
            "T03": 1,
            "T05": 2,
            "T02": 3,
            "T04": 4,
            "T09": 0,
            "T16": 1,
            "T08": 2,
            "T11": 0,
            "T12": 1,
            "T10": 2,
            "T07": 3,
            "T13": 4,
        }.get(tour_id, 99)
        if trip_type == "day tour" and not constraints.get("departure") and not theme:
            return (day_diff, default_order, tour_id)
        return (day_diff, theme_bonus, default_order, tour_id)

    return sorted(pool.keys(), key=score)[:3]


_SEMANTIC_SYNONYMS: dict[str, tuple[str, ...]] = {
    "mountain": ("nuwara-eliya", "ella", "kandy", "hill", "highland", "tea", "mist", "train", "scenic", "view"),
    "mountains": ("nuwara-eliya", "ella", "kandy", "hill", "highland", "tea", "mist", "train", "scenic", "view"),
    "scenery": ("scenic", "view", "bridge", "waterfall", "tea", "ella", "nuwara-eliya", "kandy", "train", "lighthouse"),
    "scenic": ("train", "ella", "nuwara-eliya", "tea", "hill", "bridge", "view"),
    "cool": ("nuwara-eliya", "ella", "kandy", "tea", "hill", "highland", "mist"),
    "weather": ("nuwara-eliya", "ella", "hill", "tea", "cool", "mist"),
    "peaceful": ("ella", "nuwara-eliya", "tea", "quiet", "hill", "beach", "mirissa", "heritage"),
    "quiet": ("ella", "nuwara-eliya", "mirissa", "anuradhapura", "tea", "beach"),
    "tea": ("nuwara-eliya", "ella", "kandy", "heritance", "factory", "plantation"),
    "train": ("kandy", "nuwara-eliya", "ella", "scenic", "bridge"),
    "beach": ("mirissa", "hikkaduwa", "galle", "coast", "whale", "dolphin"),
    "wildlife": ("yala", "udawalawe", "minneriya", "safari", "elephant", "leopard", "whale", "dolphin"),
    "culture": ("anuradhapura", "polonnaruwa", "sigiriya", "kandy", "dambulla", "temple", "heritage"),
    "cultural": ("anuradhapura", "polonnaruwa", "sigiriya", "kandy", "dambulla", "temple", "heritage"),
}


def rank_tours_by_preferences(pool: dict, query_text: str, constraints: dict | None = None) -> list[str]:
    """Deterministically rank ``pool`` using token/synonym overlap with descriptions, tags, and constraints."""
    if not pool:
        return []
    tokens = [
        w for w in re.findall(r"[a-z]{3,}", (query_text or "").lower())
        if w not in {"want", "with", "and", "the", "for", "somewhere", "something", "holiday", "trip", "tour", "very", "beautiful"}
    ]
    if not tokens:
        return rank_filtered_tours(pool, constraints or {})

    expanded: set[str] = set(tokens)
    for tok in tokens:
        expanded.update(_SEMANTIC_SYNONYMS.get(tok, ()))

    base_order = {tid: idx for idx, tid in enumerate(rank_filtered_tours(pool, constraints or {}))}

    def score(tour_id: str) -> tuple:
        t = pool[tour_id]
        meta_text = " ".join([t.get("title", ""), t.get("category", ""), " ".join(t.get("destinations", []))]).lower()
        body_text = t.get("body", "").lower()
        meta_hits = sum(2 for kw in expanded if kw in meta_text)
        body_hits = sum(1 for kw in expanded if kw in body_text)
        return (-(meta_hits + body_hits), base_order.get(tour_id, 99), tour_id)

    return sorted(pool.keys(), key=score)[:3]
