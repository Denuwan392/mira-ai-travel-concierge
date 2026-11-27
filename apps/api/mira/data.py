"""Dataset loader, text sanitizer, and deterministic USD/LKR pricing engine.

Loads markdown content (tours, destinations, policies, FAQs) and the Excel
rate workbook (``rate_sheet_2026-27.xlsx``), enforces strict fail-closed
validation via ``Unavailable`` errors, and computes sell prices, deposits,
and internal margin breakdowns.
"""
import hashlib
import os
import re
from pathlib import Path
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_CEILING
from functools import lru_cache

import yaml
from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel

from .itinerary_parser import parse_tour_markdown, TourItinerary

ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA = Path(os.getenv("MIRA_DATA", ROOT / "GenAI-Intern-Take-Home-Assignment/ceylon-compass-dataset"))
WORKBOOK = DATA / "rates/rate_sheet_2026-27.xlsx"
# T14 is retained in raw content for auditability but excluded from published discovery/pricing.
HISTORIC = {"T14"}


def clean(value: str) -> str:
    """Strip angle brackets and surrounding whitespace from a text value."""
    return re.sub(r"[<>]", "", value).strip()


def public_text(value: str) -> str:
    """Sanitize markdown text for traveller-facing output.

    Removes HTML comments, outdated/unverified inline claims, and any lines
    containing currency symbols, FX/margin keywords, or external URLs.
    """
    value = re.sub(r"<!--.*?(?:-->|$)", "", value, flags=re.S)
    value = value.replace(" (where blue whales can be seen all year round)", "")
    value = value.replace("Free cancellation up to 24 hours before the tour.", "See the current cancellation policy for refund terms.")
    value = value.replace("**Family offer: kids under 12 stay free!**", "See the current children and infants policy for child rates.")
    return "\n".join(clean(line) for line in value.splitlines()
                     if not re.search(r"[$€£]|\b(?:USD|LKR|GP|margin|discount)\b|https?://", line, re.I))


@lru_cache
def content():
    """Load and parse all markdown files under ``DATA/content/*/*.md``.

    Files with duplicate IDs or malformed YAML frontmatter are excluded so
    downstream lookups never encounter ambiguous IDs. Cached per process.
    """
    records = {}
    duplicates = set()
    for path in sorted(DATA.glob("content/*/*.md")):
        try:
            _, header, body = path.read_text().split("---", 2)
            meta = yaml.safe_load(header)
            key = meta["id"]
            if key in records:
                duplicates.add(key)
            rec = {
                **{k: meta[k] for k in ("id", "type", "title", "status")},
                "last_updated": str(meta.get("last_updated","")),
                "category": meta.get("category", ""), "duration": meta.get("duration", ""),
                "start": meta.get("start", ""), "destinations": meta.get("destinations", []),
                "hotels": meta.get("hotels", []) or [],
                "body": body.strip(), "path": str(path.relative_to(DATA)),
            }
            if meta.get("type") == "tour":
                parsed_itinerary = parse_tour_markdown(meta, body)
                rec["itinerary"] = parsed_itinerary
                rec["days"] = [d.model_dump() for d in parsed_itinerary.days]
                rec["inclusions"] = parsed_itinerary.inclusions
                rec["exclusions"] = parsed_itinerary.exclusions
            records[key] = rec
        except (ValueError, KeyError, TypeError, yaml.YAMLError):
            continue
    return {key: row for key, row in records.items() if key not in duplicates}


def published():
    """Return only published records, excluding historic/retired tour IDs."""
    return {k: r for k, r in content().items()
            if r["status"] == "published" and k not in HISTORIC}


def tour_card(row):
    """Build a public summary card dictionary from a content record."""
    intro = next((line for line in row["body"].splitlines() if line and not line.startswith("#")), "")
    return {k: row[k] for k in ("id", "title", "duration", "category", "start")} | {
        "summary": public_text(intro), "source": row["id"]}


class Unavailable(ValueError):
    """Domain error carrying a machine-readable reason code when pricing cannot proceed."""

    pass


def number(value):
    """Parse a non-negative finite ``Decimal`` from numeric cells or ``LKR ...`` strings.

    Raises:
        Unavailable: With ``"missing_amount"`` or ``"invalid_amount"`` on bad input.
    """
    if isinstance(value, bool):
        raise Unavailable("invalid_amount")
    if isinstance(value, str):
        if not re.fullmatch(r"LKR (?:[1-9]\d{0,2}(?:,\d{3})+|\d+)(?:\.\d+)?", value):
            raise Unavailable("invalid_amount")
        value = Decimal(value[4:].replace(",", ""))
    if not isinstance(value, (int, float, Decimal)):
        raise Unavailable("missing_amount")
    amount = Decimal(str(value))
    if not amount.is_finite() or amount < 0:
        raise Unavailable("invalid_amount")
    return amount


def day(value, epoch):
    """Normalize an Excel serial number, ``date``, ``datetime``, or ``DD/MM/YYYY`` string to ``date``."""
    if isinstance(value, datetime):
        return value.date()
    if type(value) is date:
        return value
    if isinstance(value, (float, int)):
        value = from_excel(value, epoch)
        if isinstance(value, datetime):
            return value.date()
    return datetime.strptime(value, "%d/%m/%Y").date()


@dataclass(frozen=True)
class Rates:
    """Immutable snapshot of parsed Excel rate-sheet tabs and metadata."""

    digest: str
    settings: tuple
    fx_end: date
    seasons: tuple
    tours: tuple
    hotels: tuple
    transport: tuple
    epoch: datetime


def load_rates():
    """Read the default rate-sheet workbook from disk and parse it."""
    return parse_rates(WORKBOOK.read_bytes())


@lru_cache(maxsize=3)
def parse_rates(raw):
    """Parse raw ``.xlsx`` bytes into a cached ``Rates`` snapshot.

    Extracts ``Settings``, ``Seasons``, ``Tours``, ``Hotels``, and
    ``Transport`` tabs along with the FX validity expiry date.
    """
    from io import BytesIO
    book = load_workbook(BytesIO(raw), read_only=True, data_only=True)
    try:
        def rows(tab, first):
            return tuple((i, row) for i, row in enumerate(
                book[tab].iter_rows(min_row=first, values_only=True), first) if row[0] is not None)

        settings = rows("Settings", 2)
        fx_line = one((row for _, row in settings if row[0] == "FX rate (LKR per 1 USD)"), "fx")
        expiry = datetime.strptime(fx_line[2].removeprefix("Fixed for quoting until "), "%d %b %Y").date()
        return Rates(hashlib.sha256(raw).hexdigest(), settings, expiry, rows("Seasons", 2),
                     rows("Tours", 2), rows("Hotels", 4), rows("Transport", 2), book.epoch)
    finally:
        book.close()


def one(matches, code):
    """Return the single element in ``matches`` or raise ``Unavailable(code)`` if 0 or >1."""
    rows = list(matches)
    if len(rows) != 1:
        raise Unavailable(code)
    return rows[0]


def as_of():
    """Return the effective pricing date (``AS_OF_DATE`` override or Asia/Colombo today)."""
    from zoneinfo import ZoneInfo
    value = os.getenv("AS_OF_DATE")
    return date.fromisoformat(value) if value else datetime.now(ZoneInfo("Asia/Colombo")).date()


def round_up(value, step):
    """Ceiling-round ``Decimal`` ``value`` up to the nearest multiple of ``step``."""
    return int((value / step).to_integral_value(rounding=ROUND_CEILING) * step)


def price(tour, start, adults, ages, today, rates=None, *, trace_out: dict | None = None):
    """Public pricing entrypoint that normalizes unexpected parsing errors to ``Unavailable``.

    Args:
        tour: Published tour ID (e.g. ``"T01"``).
        start: Departure ``date``.
        adults: Number of adult travellers (>= 1).
        ages: List of additional traveller/child ages (0..120).
        today: Effective booking/quoting ``date``.
        rates: Optional preloaded ``Rates`` snapshot; loads from disk if omitted.
        trace_out: Optional dict populated with non-sensitive pricing trace metadata.

    Returns:
        Pricing dictionary from ``calculate()``.

    Raises:
        Unavailable: On any business-rule violation or malformed workbook data.
    """
    try:
        return calculate(tour, start, adults, ages, today, rates or load_rates(), trace_out=trace_out)
    except Unavailable:
        raise
    except (OSError, BadZipFile, ParseError, AttributeError, TypeError, KeyError, IndexError, ValueError, ArithmeticError) as exc:
        if trace_out is not None:
            trace_out.setdefault("validation_outcomes", {})["rate_import"] = "rate_import_invalid"
        raise Unavailable("rate_import_invalid") from exc


def calculate(tour, start, adults, ages, today, rates, *, trace_out: dict | None = None):
    """Deterministically compute a USD tour quote and internal LKR cost breakdown.

    Enforces all Ceylon Compass business rules:
    1. Tour must be published and not ``T06`` (conflicting scope).
    2. Party ages: 12+ count as adults; 2–11 count as children; <2 are infants
       (counted in ``travellers`` for max group size, but not charged).
    3. Travel dates (including full tour duration) must not precede ``today`` or
       exceed ``rates.fx_end``, and every tour day must match exactly one season.
    4. Title in the rate sheet must match the published markdown title.
    5. Lodging sums double rooms (``adults // 2``), single rooms (``adults % 2``),
       and child beds per night, converting USD Cinnamon contracts via ``fx``.
    6. Sell price = ``round_up(cost / (fx * (1 - margin)), step)`` where
       ``step == 5``. Deposit is 100% for day tours or departures within ``due``
       days; otherwise ``round_up(sell * deposit_fraction, 1)``.
    """
    t_out = trace_out if trace_out is not None else {}
    t_out["inputs"] = {
        "tour": tour,
        "start": start.isoformat() if hasattr(start, "isoformat") else str(start),
        "adults": adults,
        "ages": list(ages) if isinstance(ages, (list, tuple)) else ages,
        "today": today.isoformat() if hasattr(today, "isoformat") else str(today),
    }
    matched_rows = t_out.setdefault("matched_rows", {"tour_row": None, "transport_row": None, "hotel_rows": []})
    rules = t_out.setdefault("business_rules", [])
    validations = t_out.setdefault("validation_outcomes", {})
    stages = t_out.setdefault("calculation_stages", [])

    # --- 1. Validate tour publication status and party composition ---
    if tour not in published() or published()[tour]["type"] != "tour":
        validations["publication"] = "not_published"
        raise Unavailable("not_published")
    validations["publication"] = "ok"
    if type(adults) is not int or adults < 1 or any(type(age) is not int or not 0 <= age <= 120 for age in ages):
        validations["party"] = "unsupported_party"
        raise Unavailable("unsupported_party")
    travellers = adults + len(ages)
    adults += sum(age >= 12 for age in ages)
    children = sum(2 <= age <= 11 for age in ages)
    size = adults + children
    validations["party"] = "ok"
    rules.append("party_ages_12plus_adult_2to11_child_under2_infant")
    stages.append("party_normalized")

    # --- 2. Load settings and validate group size & FX window ---
    settings = {row[0]: row[1] for _, row in rates.settings}
    if len(settings) != len(rates.settings):
        validations["settings"] = "ambiguous_settings"
        raise Unavailable("ambiguous_settings")
    validations["settings"] = "ok"
    if travellers > number(settings["Max group size"]):
        validations["group_size"] = "group_size"
        raise Unavailable("group_size")
    validations["group_size"] = "ok"
    rules.append("max_group_size_includes_infants")
    if start < today or start > rates.fx_end or today > rates.fx_end:
        validations["fx_window"] = "date_or_fx_expired"
        raise Unavailable("date_or_fx_expired")
    validations["fx_window"] = "ok"

    # --- 3. Match tour rate row and cross-check scope, title, and duration ---
    workbook_id = {"T13": "T-13"}.get(tour, tour)
    rate_row, row = one(((i, r) for i, r in rates.tours if r[0] == workbook_id), "tour_rate")
    matched_rows["tour_row"] = rate_row
    validations["tour_row"] = "ok"
    _, title, kind, days, nights, guide, adult_fee, child_fee, meals, hotels, notes = row
    if tour == "T06" or notes or kind not in {"Day tour", "Multi-day"}:
        validations["tour_scope"] = "conflicting_tour_scope"
        raise Unavailable("conflicting_tour_scope")
    validations["tour_scope"] = "ok"
    if re.sub(r"[^\w]", "", title.lower()) != re.sub(r"[^\w]", "", published()[tour]["title"].lower()):
        validations["tour_title"] = "conflicting_tour_title"
        raise Unavailable("conflicting_tour_title")
    validations["tour_title"] = "ok"
    if type(days) is not int or type(nights) is not int or not 0 <= nights < days <= 60:
        validations["duration"] = "invalid_duration"
        raise Unavailable("invalid_duration")
    validations["duration"] = "ok"
    if start + timedelta(days=days - 1) > rates.fx_end:
        validations["fx_window"] = "date_or_fx_expired"
        raise Unavailable("date_or_fx_expired")
    stages.append("tour_matched")

    # --- 4. Verify season coverage and transport tier ---
    for offset in range(days):
        when = start + timedelta(days=offset)
        one((r for _, r in rates.seasons if day(r[1], rates.epoch) <= when <= day(r[2], rates.epoch)),
            "season_rate")
    validations["seasons"] = "ok"
    stages.append("seasons_verified")
    vehicle_row, vehicle = one(((i, r) for i, r in rates.transport if r[1] <= size <= r[2]),
                               "transport_rate")
    matched_rows["transport_row"] = vehicle_row
    validations["transport"] = "ok"
    stages.append("transport_matched")

    # --- 5. Compute nightly hotel lodging costs in LKR ---
    hotel_ids = [] if hotels == "–" else [part.strip() for part in hotels.split(",")]
    if len(hotel_ids) != nights:
        validations["hotel_schedule"] = "hotel_schedule"
        raise Unavailable("hotel_schedule")
    validations["hotel_schedule"] = "ok"
    fx = number(settings["FX rate (LKR per 1 USD)"])
    lodging = Decimal(0)
    used_hotels = []
    for offset, hotel in enumerate(hotel_ids):
        night = start + timedelta(days=offset)
        hotel_row, rate = one(((i, r) for i, r in rates.hotels if r[0] == hotel
                              and day(r[3], rates.epoch) <= night <= day(r[4], rates.epoch)),
                              "hotel_rate_missing_or_ambiguous")
        multiplier = fx if rate[8] == "USD (Cinnamon contract)" else Decimal(1)
        if rate[8] and rate[8] != "USD (Cinnamon contract)":
            validations["hotel_rates"] = "unconfirmed_hotel_rate"
            raise Unavailable("unconfirmed_hotel_rate")
        for count, amount in zip((adults // 2, adults % 2, children), rate[5:8]):
            if count:
                lodging += count * number(amount) * multiplier
        used_hotels.append(hotel_row)
    matched_rows["hotel_rows"] = used_hotels
    validations["hotel_rates"] = "ok"
    rules.append("lodging_double_single_child_bed_fx")
    stages.append("hotels_computed")

    # --- 6. Sum LKR cost components and apply margin/rounding/deposit rules ---
    costs = {
        "guide": number(guide) * days, "transport": number(vehicle[3]) * days,
        "entrances": number(adult_fee) * adults + (number(child_fee) * children if children else 0),
        "meals": number(meals) * (adults + Decimal(children) / 2) * days,
        "hotels": lodging,
    }
    cost = sum(costs.values())
    margin = number(settings["Margin – day tours" if kind == "Day tour" else "Margin – multi-day tours"])
    deposit_fraction = number(settings["Deposit – multi-day tours"])
    step = number(settings["Round booking total up to next (USD)"])
    if cost <= 0 or fx <= 0 or not 0 <= margin < 1 or not 0 < deposit_fraction <= 1 or step != 5:
        validations["pricing_settings"] = "invalid_settings"
        raise Unavailable("invalid_settings")
    validations["pricing_settings"] = "ok"
    sell = round_up(cost / (fx * (1 - margin)), step)
    due = number(settings["Full payment if starting within (days)"])
    deposit = sell if kind == "Day tour" or (start - today).days <= due else round_up(sell * deposit_fraction, 1)
    rules.extend(["round_up_usd_step_5", "deposit_100pct_day_or_within_due_days"])
    stages.append("sell_and_deposit_computed")
    t_out["public_quote"] = {"total": sell, "deposit": deposit, "balance": sell - deposit}
    return {
        "total": sell, "deposit": deposit, "balance": sell - deposit,
        "cost_lkr": str(cost), "gross_profit_pct": str(100 * (1 - cost / fx / sell)),
        "breakdown": {key: str(value) for key, value in costs.items()},
        "snapshot": rates.digest, "tour_row": rate_row, "transport_row": vehicle_row,
        "hotel_rows": used_hotels,
    }
