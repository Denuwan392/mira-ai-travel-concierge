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


def test_q1043_comprehensive_financial_breakdown_audit():
    """Verify exact financial breakdown of Q-1043 per authoritative workbook rules:
    - Guide: 7 days * 9,500 = 66,500 LKR
    - Transport (Van for 4 travellers: 2 adults + 2 children): 7 days * 26,000 = 182,000 LKR
    - Entrance fees: (2 * 38,000) + (2 * 19,000) = 114,000 LKR
    - Meals: (2 + 2 * 0.5) * 4,500 * 7 = 3 * 4,500 * 7 = 94,500 LKR
    - Hotels (2 adults in 1 double room for 6 nights):
        2 nights H12 @ 20,000 = 40,000 LKR
        2 nights H02 @ 28,000 = 56,000 LKR
        2 nights H03 @ 25,000 = 50,000 LKR
        Double room subtotal = 146,000 LKR
    - Child extra beds (2 children across 6 nights):
        2 children * 2 nights H12 @ 4,500 = 18,000 LKR
        2 children * 2 nights H02 @ 6,000 = 24,000 LKR
        2 children * 2 nights H03 @ 5,500 = 22,000 LKR
        Extra bed subtotal = 64,000 LKR
    - Total hotel buy cost: 146,000 + 64,000 = 210,000 LKR
    - Total buy cost: 66,500 + 182,000 + 114,000 + 94,500 + 210,000 = 667,000 LKR
    - Selling price (25% margin, 300 FX, rounded up to $5):
        667,000 / (300 * 0.75) = 2,964.44... -> USD 2,965
    - Deposit (25% rounded up to whole dollar):
        2,965 * 0.25 = 741.25 -> USD 742

    Omission proof:
    If child extra beds (64,000 LKR) were omitted:
        Buy cost = 603,000 LKR
        603,000 / (300 * 0.75) = 2,680.00 -> USD 2,680
        Deposit = 2,680 * 0.25 = USD 670
    This mathematically demonstrates that sample_quotes.md Q-1043 omitted the extra beds.
    """
    res = price("T09", date(2027, 4, 12), 2, [7, 10], TODAY)
    assert res["total"] == 2965
    assert res["deposit"] == 742
    assert Decimal(res["cost_lkr"]) == Decimal("667000")

    # Verify that omitting 64,000 extra bed cost yields exactly 2,680 / 670
    omitted_cost = Decimal("667000") - Decimal("64000")
    omitted_sell = round_up(omitted_cost / (Decimal(300) * (Decimal(1) - Decimal("0.25"))), Decimal(5))
    omitted_deposit = round_up(omitted_sell * Decimal("0.25"), Decimal(1))
    assert omitted_cost == Decimal("603000")
    assert omitted_sell == 2680
    assert omitted_deposit == 670


def test_child_extra_bed_costing_multi_night():
    """Verify child extra bed scales strictly with number of children and nights."""
    # 2 adults, 0 children on T09 (May 2027, shoulder season)
    p0 = price("T09", date(2027, 5, 3), 2, [], TODAY)
    assert Decimal(p0["cost_lkr"]) == Decimal("477500")

    # 2 adults, 1 child (age 8) on T09:
    # Additional transport: group is 3 -> still Car (18,000/day)
    # Additional entrance: 1 child entrance (19,000)
    # Additional meals: 0.5 * 4,500 * 7 = 15,750
    # Additional extra beds: (2 * 4,500) + (2 * 6,000) + (2 * 5,500) = 32,000
    # Total increase = 19,000 + 15,750 + 32,000 = 66,750 LKR
    p1 = price("T09", date(2027, 5, 3), 2, [8], TODAY)
    assert Decimal(p1["cost_lkr"]) == Decimal("477500") + Decimal("66750")

    # 2 adults, 2 children (ages 8, 10) on T09:
    # Transport changes from Car (18,000 * 7 = 126,000) to Van (26,000 * 7 = 182,000) -> +56,000
    # Entrances: + 2 * 19,000 = +38,000
    # Meals: + 2 * 0.5 * 4,500 * 7 = +31,500
    # Extra beds: 2 children * 32,000 = +64,000
    # Total increase = 56,000 + 38,000 + 31,500 + 64,000 = 189,500 LKR
    p2 = price("T09", date(2027, 5, 3), 2, [8, 10], TODAY)
    assert Decimal(p2["cost_lkr"]) == Decimal("477500") + Decimal("189500")
    assert Decimal(p2["cost_lkr"]) == Decimal("667000")


def test_infant_cost_exemptions():
    """Infants (under 2) have 0 transport seat, 0 entrance, 0 meal cost, and 0 bed cost."""
    p_adults = price("T09", date(2027, 5, 3), 2, [], TODAY)
    p_with_infant = price("T09", date(2027, 5, 3), 2, [1], TODAY)
    assert Decimal(p_with_infant["cost_lkr"]) == Decimal(p_adults["cost_lkr"])
    assert p_with_infant["total"] == p_adults["total"]
    assert p_with_infant["deposit"] == p_adults["deposit"]


def test_single_parent_with_child_occupancy():
    """1 adult + 1 child (age 8):
    Occupancy rule: 1 single room + 1 child extra bed.
    """
    res = price("T07", date(2026, 12, 1), 1, [8], TODAY)
    # T07 is 3 days, 2 nights at H03 (Earl's Regency Kandy).
    # Season: Peak (01 Dec 2026 - 15 Jan 2027).
    # Single room: 20,000/night * 2 = 40,000 LKR.
    # Child extra bed: 5,500/night * 2 = 11,000 LKR.
    # Hotels subtotal = 51,000 LKR.
    # Guide: 3 days * 7,500 = 22,500 LKR.
    # Transport (2 pax -> Car): 3 days * 18,000 = 54,000 LKR.
    # Entrances: Adult 6,000 + Child 3,000 = 9,000 LKR.
    # Meals: (1 + 0.5) * 4,500 * 3 = 20,250 LKR.
    # Total buy cost = 51,000 + 22,500 + 54,000 + 9,000 + 20,250 = 156,750 LKR.
    # Selling price: 156,750 / (300 * 0.75) = 696.66... -> 700 USD.
    # Deposit: Starts within 30 days -> 100% -> 700 USD.
    assert Decimal(res["cost_lkr"]) == Decimal("156750")
    assert res["total"] == 700
    assert res["deposit"] == 700


def test_private_party_limit_counts_infants():
    with pytest.raises(Unavailable, match="group_size"):
        price("T01", date(2027, 1, 10), 20, [1], TODAY)
