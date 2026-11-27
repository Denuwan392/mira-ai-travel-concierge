"""Semantic confidence, publication and citation boundaries for the discovery path."""
import pytest

from mira.discovery import DiscoveryResult, InterpretedDiscoveryResult, discover, model_rank
from mira.data import content


@pytest.mark.parametrize("selection", [
    {"id": "T15", "evidence": 0},
    {"id": "T01", "evidence": 99},
    {"id": "T01", "evidence": 0},
])
def test_invalid_model_citation(selection):
    result = DiscoveryResult(intent="discovery", picks=[selection])
    trip = {"evidence": {"T01": ["A walk", "An elephant safari"]}, "interests": ["elephant"]}
    with pytest.raises(ValueError):
        model_rank(trip, lambda *a, **kw: result, [], {})


def test_valid_abstention():
    result = DiscoveryResult(intent="unsupported", picks=[])
    trip = {"evidence": {"T01": ["A walk"]}, "interests": []}
    assert model_rank(trip, lambda *a, **kw: result, [], {}) == []


def test_draft_and_out_of_pool_ids_cannot_override_local_evidence():
    w = {"context": {}, "events": [], "records": content(), "discovery_message": "Elephants in one day"}
    def bad_rank(pool, brief, events):
        assert "T15" not in pool and "T15" not in brief["evidence"]
        return ["T15"]
    assert discover(w, bad_rank) == ["T01"]


def test_published_destination_ranking():
    w = {"context": {}, "events": [], "records": content(), "discovery_message": "Which towns have a scenic railway?"}
    ids = discover(w, lambda *args: None)
    assert "D05" in ids
    assert all(content()[k]["type"] == "destination" for k in ids)


def test_unfamiliar_phrase_can_reach_gemini_without_lexical_overlap():
    from mira.data import published

    w = {"context": {}, "events": [], "records": published(), "discovery_message": "Pachyderms please"}
    def grounded_rank(pool, trip, events):
        assert "T13" in pool and "elephant" in trip["concepts"]
        idx = next(i for i, line in enumerate(trip["evidence"]["T13"]) if "elephants" in line)
        result = InterpretedDiscoveryResult(intent="discovery", picks=[{"id": "T13", "evidence": idx}],
                                 interpretations=[{"phrase": "Pachyderms", "concept": "elephant"}])
        return model_rank(trip, lambda *args, **kwargs: result, events, {})
    assert discover(w, grounded_rank) == ["T13"]
    assert w["context"]["discovery"]["interests"] == ["elephant"]


def test_named_place_cannot_rescue_unrelated_activity(app_client):
    from conftest import turn
    result = turn(app_client, "I want to see elephants near Ella")
    assert not any(c.type == "TourCard" for c in result.components)
    assert "couldn’t find" in result.text
