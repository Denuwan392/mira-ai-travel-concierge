"""Retrieval node for Mira's LangGraph workflow."""
from pathlib import Path
from time import perf_counter

from ..observability import elapsed, event
from ..discovery import discover
from ..provider import rank
from .facade import facade_attr
from .state import working


def retrieve(_):
    """Node 2: Select grounded dataset records (policies, destinations, or tours) for the classified action."""
    started = perf_counter()
    w = working.get()
    records, ctx, action = w["records"], w["context"], w["action"]
    ids = {
        "cancellation": ["P02"], "cancel_booking": ["P02"],
        "cancel_request": ["P02"], "cancel_clarify_target": ["P02"], "cancel_preview": ["P02"],
        "cancel_confirm": ["P02"], "cancel_decline": ["P02"], "refund_inquiry": ["P02"], "children": ["P03"], "dietary": ["P04"], "payment": ["P01"],
        "polonnaruwa": ["T09", "T08"],
        "compare": ctx.get("suggestions", [])[:2],
        "destination": [w["named"]], "discover": [ctx.get("tour")],
        "custom": [] if ctx.get("proposal") else ["T08", "T10", "T12"],
        "clarify_plan": ctx.get("custom", {}).get("destination_ids", []) if ctx.get("custom", {}).get("destination_ids") else ["T01", "T09", "T05"],
        "general": ["T01", "T09", "T05"],
        "disambiguate_tour": w.get("ambiguous_tours", []),
        "tour_itinerary": [w.get("named") or ctx.get("tour")],
        "tour_day_detail": [w.get("named") or ctx.get("tour")],
        "tour_inclusions": [w.get("named") or ctx.get("tour")],
        "product_qa": [w.get("named") or ctx.get("tour")],
        "accommodation": [w.get("hotel_source") or "P01"],
        "tour_hotels": [w.get("named") or ctx.get("tour")],
        "galle_cancellation": ["P02"],
        "mirissa_discount": ["D08"],
        "draft_tour": [],
    }.get(action, [])
    rank_fn = facade_attr("rank", rank)
    candidates = list(ids)
    constraints = {}
    keywords = []
    tags = []
    ranking_scores = {}
    selection_reasoning = f"action_map:{action}"

    if action == "destination":
        place = records[w["named"]]["path"].rsplit("/", 1)[-1].removesuffix(".md")
        matched_tours = [key for key, tour in w["tours"].items() if place in tour["destinations"]][:3]
        ids += matched_tours
        candidates = list(ids)
        tags.append(place)
        selection_reasoning = f"destination_and_linked_tours:{place}"
    if action == "general":
        ids = discover(w, rank_fn)
        trace = w["events"][-1]
        candidates = trace["eligible"]
        constraints = trace["constraints"]
        ranking_scores = trace["scores"]
        selection_reasoning = trace["validation"]
    if action == "custom":
        trip = ctx.get("custom", {})
        constraints = trip
        destinations = {name.split()[0].lower() for name in trip.get("destinations", [])}
        keywords = sorted(destinations)
        if ctx.get("proposal") and action == "custom":
            destinations = {Path(records[key]["path"]).stem for key in ctx["proposal"]}
            tags = sorted(destinations)
        if destinations:
            related = sorted(w["tours"], key=lambda key: -len(destinations.intersection(w["tours"][key]["destinations"])))
            scored = {key: len(destinations.intersection(w["tours"][key]["destinations"])) for key in related}
            candidates = [key for key in related if scored[key] > 0]
            ranking_scores = {k: v for k, v in scored.items() if v > 0}
            ids = candidates[:3] or ids
            selection_reasoning = "destination_overlap"
        if not (w.get("trip_id") and ctx.get("proposal")):
            prefs = ctx.get("preferences") or w.get("user_text", "")
            rank_trip = {k: trip[k] for k in ("destinations", "days", "party") if k in trip}
            if prefs:
                rank_trip["preferences"] = prefs
            llm_ranked = rank_fn(w["tours"], rank_trip, w["events"])
            if llm_ranked:
                ids = llm_ranked
                selection_reasoning = "llm_rank"
    w["rows"] = [records[key] for key in ids if key in records]
    if action in {"general", "destination", "custom", "compare", "disambiguate_tour"}:
        new_suggs = [row["id"] for row in w["rows"] if row["type"] == "tour"]
        ctx["suggestions"] = new_suggs
        ctx["empty_filter_result"] = bool(w.get("suggestion_pool") and not new_suggs)
        if not w.get("suggestion_pool") and new_suggs:
            ctx["last_suggestions"] = list(new_suggs)
            hist = list(ctx.get("historical_suggestions") or [])
            if not hist or hist[-1] != new_suggs:
                hist.append(list(new_suggs))
            ctx["historical_suggestions"] = hist[-5:]
    sources = [r["id"] for r in w["rows"]]
    duration = elapsed(started)
    w["events"].append({"stage": "retrieval", "sources": sources, "ms": duration})
    event(
        "RAG",
        "retrieval.completed",
        documents=len(sources),
        sources=sources,
        query="catalogue discovery" if action == "general" else w.get("user_text", ""),
        constraints=constraints,
        keywords=keywords,
        tags=tags,
        candidates=candidates,
        ranking_scores=ranking_scores,
        selection_reasoning=selection_reasoning,
        duration_ms=duration,
    )
    return {}
