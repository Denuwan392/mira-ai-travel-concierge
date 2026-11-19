import hashlib
import os
import re
from pathlib import Path
from zipfile import BadZipFile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_CEILING
from functools import lru_cache

import yaml
from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel

ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA = Path(os.getenv("MIRA_DATA", ROOT / "GenAI-Intern-Take-Home-Assignment/ceylon-compass-dataset"))
WORKBOOK = DATA / "rates/rate_sheet_2026-27.xlsx"
HISTORIC = {"T14"}


def clean(value: str) -> str:
    return re.sub(r"[<>]", "", value).strip()


def public_text(value: str) -> str:
    return "\n".join(clean(line) for line in value.splitlines()
                     if not re.search(r"[$€£]|\b(?:USD|LKR|GP|margin|discount)\b|https?://", line, re.I))


@lru_cache
def content():
    records = {}
    duplicates = set()
    for path in sorted(DATA.glob("content/*/*.md")):
        try:
            _, header, body = path.read_text().split("---", 2)
            meta = yaml.safe_load(header)
            key = meta["id"]
            if key in records:
                duplicates.add(key)
            records[key] = {
                **{k: meta[k] for k in ("id", "type", "title", "status")},
                "category": meta.get("category", ""), "duration": meta.get("duration", ""),
                "start": meta.get("start", ""), "destinations": meta.get("destinations", []),
                "body": body.strip(), "path": str(path.relative_to(DATA)),
            }
        except (ValueError, KeyError, TypeError, yaml.YAMLError):
            continue
    return {key: row for key, row in records.items() if key not in duplicates}


def published():
    return {k: r for k, r in content().items()
            if r["status"] == "published" and k not in HISTORIC}


def tour_card(row):
    intro = next((line for line in row["body"].splitlines() if line and not line.startswith("#")), "")
    return {k: row[k] for k in ("id", "title", "duration", "category", "start")} | {
        "summary": public_text(intro), "source": row["id"]}


class Unavailable(ValueError):
    pass


def number(value):
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
    digest: str
    settings: tuple
    fx_end: date
    seasons: tuple
    tours: tuple
    hotels: tuple
    transport: tuple
    epoch: datetime


def load_rates():
    return parse_rates(WORKBOOK.read_bytes())


@lru_cache(maxsize=3)
def parse_rates(raw):
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
    rows = list(matches)
    if len(rows) != 1:
        raise Unavailable(code)
    return rows[0]


def as_of():
    from zoneinfo import ZoneInfo
    value = os.getenv("AS_OF_DATE")
    return date.fromisoformat(value) if value else datetime.now(ZoneInfo("Asia/Colombo")).date()


def round_up(value, step):
    return int((value / step).to_integral_value(rounding=ROUND_CEILING) * step)


def price(tour, start, adults, ages, today, rates=None):
    try:
        return calculate(tour, start, adults, ages, today, rates or load_rates())
    except Unavailable:
        raise
    except (OSError, BadZipFile, TypeError, KeyError, IndexError, ValueError, ArithmeticError) as exc:
        raise Unavailable("rate_import_invalid") from exc


def calculate(tour, start, adults, ages, today, rates):
    if tour not in published() or published()[tour]["type"] != "tour":
        raise Unavailable("not_published")
    if adults < 1 or any(type(age) is not int or not 0 <= age <= 120 for age in ages):
        raise Unavailable("unsupported_party")
    adults += sum(age >= 12 for age in ages)
    children = sum(2 <= age <= 11 for age in ages)
    size = adults + children
    settings = {row[0]: row[1] for _, row in rates.settings}
    if len(settings) != len(rates.settings):
        raise Unavailable("ambiguous_settings")
    if size > number(settings["Max group size"]):
        raise Unavailable("group_size")
    if start < today or start > rates.fx_end or today > rates.fx_end:
        raise Unavailable("date_or_fx_expired")
    workbook_id = {"T13": "T-13"}.get(tour, tour)
    rate_row, row = one(((i, r) for i, r in rates.tours if r[0] == workbook_id), "tour_rate")
    _, title, kind, days, nights, guide, adult_fee, child_fee, meals, hotels, notes = row
    if tour == "T06" or notes or kind not in {"Day tour", "Multi-day"}:
        raise Unavailable("conflicting_tour_scope")
    if re.sub(r"[^\w]", "", title.lower()) != re.sub(r"[^\w]", "", published()[tour]["title"].lower()):
        raise Unavailable("conflicting_tour_title")
    if type(days) is not int or type(nights) is not int or not 0 <= nights < days <= 60:
        raise Unavailable("invalid_duration")
    if start + timedelta(days=days - 1) > rates.fx_end:
        raise Unavailable("date_or_fx_expired")
    for offset in range(days):
        when = start + timedelta(days=offset)
        one((r for _, r in rates.seasons if day(r[1], rates.epoch) <= when <= day(r[2], rates.epoch)),
            "season_rate")
    vehicle_row, vehicle = one(((i, r) for i, r in rates.transport if r[1] <= size <= r[2]),
                               "transport_rate")
    hotel_ids = [] if hotels == "–" else [part.strip() for part in hotels.split(",")]
    if len(hotel_ids) != nights:
        raise Unavailable("hotel_schedule")
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
            raise Unavailable("unconfirmed_hotel_rate")
        for count, amount in zip((adults // 2, adults % 2, children), rate[5:8]):
            if count:
                lodging += count * number(amount) * multiplier
        used_hotels.append(hotel_row)
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
        raise Unavailable("invalid_settings")
    sell = round_up(cost / (fx * (1 - margin)), step)
    due = number(settings["Full payment if starting within (days)"])
    deposit = sell if kind == "Day tour" or (start - today).days <= due else round_up(sell * deposit_fraction, 1)
    return {
        "total": sell, "deposit": deposit, "balance": sell - deposit,
        "cost_lkr": str(cost), "gross_profit_pct": str(100 * (1 - cost / fx / sell)),
        "breakdown": {key: str(value) for key, value in costs.items()},
        "snapshot": rates.digest, "tour_row": rate_row, "transport_row": vehicle_row,
        "hotel_rows": used_hotels,
    }
