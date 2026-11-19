from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

import pytest

from mira.data import Unavailable, load_rates, number, price, round_up

from conftest import TODAY


@pytest.mark.parametrize("tour,start,adults,ages,expected", [
    ("T01", "2027-01-10", 2, [], (66000, 315, 315)),
    ("T09", "2027-05-03", 2, [], (477500, 2125, 532)),
    ("T09", "2027-04-12", 2, [7, 10], (667000, 2965, 742)),
    ("T08", "2026-12-01", 2, [], (563000, 2505, 2505)),
    ("T05", "2027-03-15", 2, [1], (57000, 275, 275)),
    ("T07", "2026-12-14", 2, [], (170500, 760, 760)),
    ("T07", "2026-12-01", 1, [], (136000, 605, 605)),
], ids=["Q1041", "Q1042", "Q1043-workbook", "Q1044", "infant", "mixed-season", "single"])
def test_exact_quote(tour, start, adults, ages, expected):
    result = price(tour, date.fromisoformat(start), adults, ages, TODAY)
    assert (Decimal(result["cost_lkr"]), result["total"], result["deposit"]) == expected


@pytest.mark.parametrize("n,total,vehicle_row", [(3, 410, 2), (4, 540, 3), (8, 910, 3), (9, 1095, 4), (20, 2115, 4)])
def test_group_boundaries(n, total, vehicle_row):
    result = price("T01", date(2027, 1, 10), n, [], TODAY)
    assert (result["total"], result["transport_row"]) == (total, vehicle_row)


@pytest.mark.parametrize("age,total", [(1, 315), (2, 365), (11, 365), (12, 410)])
def test_age_boundaries(age, total):
    assert price("T01", date(2027, 1, 10), 2, [age], TODAY)["total"] == total


@pytest.mark.parametrize("day_count,deposit", [(30, 780), (31, 195)])
def test_full_payment_boundary(day_count, deposit):
    assert price("T07", TODAY + timedelta(days=day_count), 2, [], TODAY)["deposit"] == deposit


@pytest.mark.parametrize("tour,start,adults,reason", [
    ("T01", "2027-01-10", 21, "group_size"),
    ("T01", "2027-01-10", 0, "unsupported_party"),
    ("T01", "2027-11-01", 2, "date_or_fx_expired"),
    ("T01", "2026-11-18", 2, "date_or_fx_expired"),
    ("T11", "2027-01-20", 2, "hotel_rate_missing_or_ambiguous"),
    ("T07", "2027-01-20", 2, "hotel_rate_missing_or_ambiguous"),
    ("T12", "2027-04-10", 1, "missing_amount"),
    ("T15", "2027-04-10", 2, "not_published"),
    ("T14", "2027-04-10", 2, "not_published"),
    ("T06", "2027-04-10", 2, "conflicting_tour_scope"),
    ("T10", "2027-04-10", 2, "tour_rate"),
])
def test_refuses(tour, start, adults, reason):
    with pytest.raises(Unavailable, match=f"^{reason}$"):
        price(tour, date.fromisoformat(start), adults, [], TODAY)


@pytest.mark.parametrize("malformed", ["28,000", "LKR 280,00", "USD 50", "LKR -10", True, float("nan")])
def test_no_permissive_coercion(malformed):
    with pytest.raises(Unavailable):
        number(malformed)


def test_lkr_string_regression():
    assert number("LKR 28,000") == Decimal("28000")


def test_rounding_exact_boundary():
    assert round_up(Decimal("315.000"), Decimal(5)) == 315
    assert round_up(Decimal("315.001"), Decimal(5)) == 320


def test_duplicate_tour_row_refused():
    rates = load_rates()
    with pytest.raises(Unavailable, match="tour_rate"):
        price("T01", date(2027, 1, 10), 2, [], TODAY,
              replace(rates, tours=(*rates.tours, rates.tours[0])))
