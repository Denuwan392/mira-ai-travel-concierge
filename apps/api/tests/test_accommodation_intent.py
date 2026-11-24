"""Regression tests for intent-first accommodation retrieval and A2UI composition."""
import pytest
from conftest import turn
from mira.catalog import SourcePanel, Notice, Card, Excerpt, Picker


def test_hotel_recommendation_in_mirissa(app_client):
    """User: 'Suggest me a hotel in Mirissa.' -> Identifies Mirissa Bay Villas (T11), renders StayCard, no TourCards."""
    output = turn(app_client, "Suggest me a hotel in Mirissa.")
    
    # 1. Directly answers the question identifying Mirissa Bay Villas from T11
    assert "Mirissa Bay Villas" in output.text
    assert "Sri Lanka Beach Stay" in output.text or "T11" in output.sources
    assert "unconfirmed" in output.text
    
    # 2. Renders exactly one StayCard
    stay_cards = [c for c in output.components if isinstance(c, SourcePanel) and c.type == "StayCard"]
    assert len(stay_cards) == 1
    assert "Mirissa Bay Villas" in stay_cards[0].heading
    assert stay_cards[0].source == "T11"
    
    # 3. Renders an EnquiryNotice
    notices = [c for c in output.components if isinstance(c, Notice)]
    assert len(notices) >= 1
    assert "Specialist confirmation" in notices[0].text
    
    # 4. Irrelevant TourCards must be suppressed (zero TourCards)
    tour_cards = [c for c in output.components if isinstance(c, Card)]
    assert len(tour_cards) == 0


def test_hotel_recommendation_in_kandy(app_client):
    """User: 'Where can I stay in Kandy?' -> Recommends Hotel Suisse, StayCard rendered, no TourCards."""
    output = turn(app_client, "Where can I stay in Kandy?")
    assert "Hotel Suisse" in output.text
    assert "unconfirmed" in output.text
    
    stay_cards = [c for c in output.components if isinstance(c, SourcePanel) and c.type == "StayCard"]
    assert len(stay_cards) == 1
    assert "Hotel Suisse" in stay_cards[0].heading
    assert stay_cards[0].source == "T07"
    
    tour_cards = [c for c in output.components if isinstance(c, Card)]
    assert len(tour_cards) == 0


def test_hotel_references_in_selected_published_tour(app_client):
    """User: 'What hotels are included in Highlights of Sri Lanka?' -> Lists partner properties with StayCards."""
    output = turn(app_client, "What hotels are included in Highlights of Sri Lanka?")
    assert "Highlights of Sri Lanka" in output.text
    assert "Hotel Suisse" in output.text
    assert "Sigiriya Village" in output.text
    
    stay_cards = [c for c in output.components if isinstance(c, SourcePanel) and c.type == "StayCard"]
    assert len(stay_cards) >= 1
    assert any("Hotel Suisse" in c.heading or "Sigiriya Village" in c.heading for c in stay_cards)


def test_standalone_hotel_rate_question_protected(app_client):
    """User: 'What is the room rate for Mirissa Bay Villas per night?' -> Explains rates unconfirmed standalone."""
    output = turn(app_client, "What is the room rate for Mirissa Bay Villas per night?")
    assert "Mirissa Bay Villas" in output.text
    assert "unconfirmed" in output.text
    assert "wholesale package rates" in output.text or "holiday packages" in output.text
    
    # Must NOT leak expired contractor buy rates (e.g. 42000, 35000, 29000 LKR)
    assert "42,000" not in output.text and "42000" not in output.text
    assert "35,000" not in output.text and "35000" not in output.text
    assert "29,000" not in output.text and "29000" not in output.text
    
    notices = [c for c in output.components if isinstance(c, Notice)]
    assert len(notices) >= 1


def test_alternative_hotel_request(app_client):
    """User: 'Do you have an alternative hotel in Kandy?' -> Mentions Hotel Suisse and alternative Hotel Topaz."""
    output = turn(app_client, "Do you have an alternative hotel in Kandy?")
    assert "Hotel Suisse" in output.text
    assert "Hotel Topaz" in output.text
    stay_cards = [c for c in output.components if isinstance(c, SourcePanel) and c.type == "StayCard"]
    assert len(stay_cards) == 1


def test_destination_discovery_request_distinct_from_hotel(app_client):
    """User: 'Tell me about Mirissa' -> Destination query, NOT accommodation; renders tours visiting Mirissa."""
    output = turn(app_client, "Tell me about Mirissa")
    # Must route to destination discovery
    assert "published journeys that visit Mirissa" in output.text
    tour_cards = [c for c in output.components if isinstance(c, Card)]
    assert len(tour_cards) > 0  # Tour cards ARE shown for general destination query


def test_beach_stay_package_discovery_request_distinct_from_hotel(app_client):
    """User: 'Recommend a beach stay package in Mirissa' -> Package query, surfaces TourCard for T11."""
    output = turn(app_client, "Recommend a beach stay package in Mirissa")
    tour_cards = [c for c in output.components if isinstance(c, Card)]
    assert len(tour_cards) >= 1
    assert any(c.id == "T11" for c in tour_cards)


def test_accommodation_follow_up_after_selecting_tour(app_client):
    """User selects tour then asks: 'Which hotels are included in this tour?'"""
    turn(app_client, "@tour T09")
    output = turn(app_client, "Which hotels are included in this tour?")
    assert "Cultural Triangle Sri Lanka Package" in output.text
    assert "Sigiriya Village" in output.text
    assert "Hotel Suisse" in output.text
    stay_cards = [c for c in output.components if isinstance(c, SourcePanel) and c.type == "StayCard"]
    assert len(stay_cards) >= 1


def test_duplicate_a2ui_source_suppression_and_no_tour_cards(app_client):
    """Ensure accommodation query suppresses duplicate source panels and TourCards."""
    output = turn(app_client, "Can you recommend a hotel in Mirissa?")
    assert len(output.sources) <= 2
    # Verify no duplicate headings among components
    headings = [getattr(c, "heading", None) for c in output.components if getattr(c, "heading", None)]
    assert len(headings) == len(set(headings))
    # No TourCard flood
    assert not any(isinstance(c, Card) for c in output.components)


def test_internal_hotel_financial_data_protection(app_client):
    """Ensure internal contractor rates, margins, and expired hotel costs are never leaked."""
    for query in [
        "What does Hotel Suisse cost per night?",
        "How much is the room rate at Sigiriya Village?",
        "Can I buy just the room at Mirissa Bay Villas?"
    ]:
        output = turn(app_client, query)
        assert "unconfirmed" in output.text or "specialist" in output.text.lower()
        # Verify no LKR wholesale contractor amounts
        assert "LKR" not in output.text
        assert "margin" not in output.text.lower()
        assert "buy rate" not in output.text.lower()
        assert "contract rate" not in output.text.lower()


def test_hotel_enquiry_reference_matches_saved_row(app_client):
    from mira.store import db
    output = turn(app_client, "What is the room rate for Mirissa Bay Villas per night?")
    notice = next(c for c in output.components if isinstance(c, Notice))
    with db() as conn:
        row = conn.execute("SELECT trace FROM enquiries WHERE id=?", (str(notice.reference),)).fetchone()
    assert row and row["trace"] == str(output.trace)
