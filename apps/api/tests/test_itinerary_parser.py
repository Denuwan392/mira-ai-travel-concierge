"""Unit tests for ``mira.itinerary_parser.parse_tour_markdown`` on T07, T08, and T09."""
import pytest
from mira.data import DATA, content
from mira.itinerary_parser import parse_tour_markdown, TourItinerary, DaySchedule


def test_t09_cultural_triangle_itinerary_parser():
    """Verify T09 parses into 7 structured ``DaySchedule`` items with meals, hotels, and tickets."""
    records = content()
    assert "T09" in records
    t09_raw = records["T09"]
    
    tour = parse_tour_markdown(t09_raw, t09_raw["body"])
    assert isinstance(tour, TourItinerary)
    assert tour.id == "T09"
    assert tour.title == "Cultural Triangle Sri Lanka Package"
    assert tour.duration == "6 nights / 7 days"
    assert len(tour.days) == 7

    # Check each day's title and contents
    assert tour.days[0].day == 1
    assert "Colombo to Anuradhapura" in tour.days[0].title
    assert tour.days[0].meals == "Dinner"
    assert "Anuradhapura Heritage Lodge" in tour.days[0].accommodation
    assert tour.days[0].source == "T09"

    assert tour.days[1].day == 2
    assert "Anuradhapura" in tour.days[1].title
    assert "Sri Maha Bodhi" in tour.days[1].description
    assert tour.days[1].entrance_tickets == "Anuradhapura sacred city"

    assert tour.days[2].day == 3
    assert "Anuradhapura to Sigiriya" in tour.days[2].title
    assert "Mihintale" in tour.days[2].description

    assert tour.days[3].day == 4
    assert "Sigiriya and Polonnaruwa" in tour.days[3].title
    assert "Sigiriya at sunrise" in tour.days[3].description
    assert "Sigiriya, Polonnaruwa" in tour.days[3].entrance_tickets
    assert "Sigiriya Village" in tour.days[3].accommodation

    assert tour.days[4].day == 5
    assert "Dambulla to Kandy" in tour.days[4].title
    assert "Dambulla, spice garden, Temple of the Tooth" in tour.days[4].entrance_tickets

    assert tour.days[5].day == 6
    assert "Kandy" in tour.days[5].title
    assert "Peradeniya gardens" in tour.days[5].entrance_tickets

    assert tour.days[6].day == 7
    assert "Kandy to Colombo" in tour.days[6].title
    assert tour.days[6].accommodation == "None"


def test_t08_highlights_itinerary_parser():
    """Verify T08 parses into 8 days including train and Nuwara Eliya hotel metadata."""
    records = content()
    assert "T08" in records
    t08_raw = records["T08"]
    
    tour = parse_tour_markdown(t08_raw, t08_raw["body"])
    assert len(tour.days) == 8
    assert tour.days[0].day == 1
    assert "Airport to Negombo" in tour.days[0].title
    assert tour.days[4].day == 5
    assert "Train to Nuwara Eliya" in tour.days[4].title
    assert "Heaven Seven" in tour.days[4].accommodation


def test_t07_kandy_stay_itinerary_parser():
    """Verify T07 parses into 3 days with expected start/end titles."""
    records = content()
    assert "T07" in records
    t07_raw = records["T07"]
    
    tour = parse_tour_markdown(t07_raw, t07_raw["body"])
    assert len(tour.days) == 3
    assert tour.days[0].day == 1
    assert "Arrive in Kandy" in tour.days[0].title
    assert tour.days[2].day == 3
    assert "Departure" in tour.days[2].title
