"""Authoritative typed trip state, structured operation extraction, and deterministic state reducer."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from .constants import COUNT
from .parsing import count, parse_date


class ItinerarySegment(BaseModel):
    """Hierarchical destination segment within a custom trip itinerary."""

    segment_id: str
    destination_id: str
    destination_name: str
    days: int = Field(ge=1, le=30)
    allocation_source: Literal["explicit", "inferred"] = "explicit"
    preferences: list[str] = Field(default_factory=list)
    activities: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class TripState(BaseModel):
    """Single authoritative typed state for a trip notebook or conversation."""

    active_goal: Literal["custom_planning", "tour_quoting", "discovery"] | None = None
    turn_intent: str | None = None
    focused_entity_type: Literal["tour", "destination", "quote", "enquiry", "booking", "custom_plan", "policy"] | None = None
    focused_entity_id: str | None = None
    current_suggestions: list[str] = Field(default_factory=list)
    filtered_suggestions: list[str] = Field(default_factory=list)
    historical_suggestions: list[list[str]] = Field(default_factory=list)
    last_retrieval_scope: str | None = None
    pending_clarification: dict | None = None
    pending_task: dict | None = None
    requested_destinations: list[str] = Field(default_factory=list)
    excluded_destinations: list[str] = Field(default_factory=list)
    segments: list[ItinerarySegment] = Field(default_factory=list)
    total_duration_constraint: int | None = None
    duration_days: int | None = None
    departure_date: str | None = None
    adults: int | None = None
    kids: int = 0
    ages: list[int] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    original_preferences: list[str] = Field(default_factory=list)
    excluded_interests: list[str] = Field(default_factory=list)
    transfer_requirements: list[str] = Field(default_factory=list)
    selected_tour: str | None = None
    proposal: list[str] = Field(default_factory=list)
    itinerary_version: int = 0
    selected_day: int = 0
    quote_id: str | None = None
    enquiry_id: str | None = None
    booking_ref: str | None = None
    pending_cancellation: dict | None = None
    confirmed_requirements: dict = Field(default_factory=dict)
    tentative_preferences: dict = Field(default_factory=dict)
    readiness: Literal["clarifying", "provisional", "ready"] = "clarifying"

    @classmethod
    def from_ctx(cls, ctx: dict, records: dict | None = None) -> "TripState":
        custom = ctx.get("custom") or {}
        goal = custom.get("goal")
        active_goal = (
            "custom_planning"
            if goal == "plan_itinerary" or ctx.get("proposal")
            else ("tour_quoting" if ctx.get("tour") else ("discovery" if ctx.get("suggestions") or ctx.get("discovery") else None))
        )
        dest_ids = list(custom.get("destination_ids") or dict.fromkeys(ctx.get("proposal") or []))
        if not dest_ids and records and active_goal != "tour_quoting":
            places = (ctx.get("discovery") or {}).get("constraints", {}).get("places") or (ctx.get("search") or {}).get("places") or []
            slug_to_id = {
                Path(r["path"]).stem: k
                for k, r in records.items()
                if r.get("type") == "destination" and r.get("path")
            }
            dest_ids = [slug_to_id[p] for p in places if p in slug_to_id]
        interests = list(custom.get("interests") or [])
        if not interests and (ctx.get("discovery") or {}).get("interests"):
            interests = [i for i in ctx["discovery"]["interests"] if i not in {"time", "holiday", "trip"}]
        focused_type = ctx.get("focused_entity_type")
        focused_id = ctx.get("focused_entity_id")
        if not focused_id and ctx.get("tour"):
            focused_type, focused_id = "tour", ctx["tour"]
        elif not focused_id and ctx.get("proposal"):
            focused_type, focused_id = "custom_plan", "current_plan"
        hist = list(ctx.get("historical_suggestions") or [])
        if not hist and ctx.get("last_suggestions"):
            hist = [list(ctx["last_suggestions"])]
        raw_segs = custom.get("segments") or []
        segments = [ItinerarySegment.model_validate(s) for s in raw_segs] if raw_segs else []
        derived_days = sum(s.days for s in segments) if segments else custom.get("days")
        if segments and not dest_ids:
            dest_ids = [s.destination_id for s in segments]
        return cls(
            active_goal=active_goal,
            turn_intent=ctx.get("turn_intent"),
            focused_entity_type=focused_type,
            focused_entity_id=focused_id,
            current_suggestions=list(ctx.get("suggestions") or []),
            filtered_suggestions=list(ctx.get("filtered_suggestions") or []),
            historical_suggestions=hist,
            last_retrieval_scope=ctx.get("last_retrieval_scope"),
            pending_clarification=custom.get("pending_clarification"),
            pending_task=ctx.get("pending_task"),
            requested_destinations=dest_ids,
            excluded_destinations=list(custom.get("excluded_destination_ids") or []),
            segments=segments,
            total_duration_constraint=custom.get("total_duration_constraint"),
            duration_days=derived_days,
            departure_date=custom.get("date") or ctx.get("date"),
            adults=custom.get("adults") if custom.get("adults") is not None else ctx.get("adults"),
            kids=custom.get("kids", ctx.get("kids", 0)),
            ages=list(custom.get("ages") or ctx.get("ages") or []),
            interests=interests,
            original_preferences=list(ctx.get("original_preferences") or []),
            excluded_interests=list(custom.get("excluded_interests") or []),
            transfer_requirements=list(custom.get("transfer_requirements") or []),
            selected_tour=ctx.get("tour"),
            proposal=list(ctx.get("proposal") or []),
            itinerary_version=custom.get("itinerary_version", 0),
            selected_day=ctx.get("selected_day", 0),
            quote_id=ctx.get("quote_id"),
            enquiry_id=custom.get("enquiry_id"),
            booking_ref=ctx.get("booking_ref"),
            pending_cancellation=ctx.get("pending_cancellation"),
            confirmed_requirements=dict(ctx.get("confirmed_requirements") or {}),
            tentative_preferences=dict(ctx.get("tentative_preferences") or {}),
            readiness=custom.get("readiness", "clarifying"),
        )

    def sync_to_ctx(self, ctx: dict, destinations_map: dict[str, str]) -> dict:
        if self.active_goal == "custom_planning" or self.requested_destinations or self.duration_days or self.proposal:
            custom = dict(ctx.get("custom") or {})
            custom.update(
                {
                    "goal": "plan_itinerary",
                    "destination_ids": list(self.requested_destinations),
                    "destinations": [destinations_map[d] for d in self.requested_destinations if d in destinations_map],
                    "excluded_destination_ids": list(self.excluded_destinations),
                    "interests": list(self.interests),
                    "excluded_interests": list(self.excluded_interests),
                    "itinerary_version": self.itinerary_version,
                    "readiness": self.readiness,
                }
            )
            if self.segments:
                custom["segments"] = [s.model_dump() for s in self.segments]
                custom["days"] = sum(s.days for s in self.segments)
                custom["destination_ids"] = [s.destination_id for s in self.segments]
                custom["destinations"] = [destinations_map.get(s.destination_id, s.destination_name) for s in self.segments]
            elif self.duration_days is not None:
                custom["days"] = self.duration_days
            if self.total_duration_constraint is not None:
                custom["total_duration_constraint"] = self.total_duration_constraint
            else:
                custom.pop("total_duration_constraint", None)
            if self.transfer_requirements:
                custom["transfer_requirements"] = list(self.transfer_requirements)
            if self.departure_date:
                custom["date"] = self.departure_date
            if self.adults is not None:
                custom["adults"] = self.adults
            if self.kids:
                custom["kids"] = self.kids
            if self.ages:
                custom["ages"] = list(self.ages)
            if self.pending_clarification:
                custom["pending_clarification"] = self.pending_clarification
            else:
                custom.pop("pending_clarification", None)
            if self.enquiry_id:
                custom["enquiry_id"] = self.enquiry_id
            ctx["custom"] = custom
        if self.proposal:
            ctx["proposal"] = list(self.proposal)
            ctx["selected_day"] = min(self.selected_day, len(self.proposal) - 1)
        elif "proposal" in ctx and self.active_goal != "custom_planning":
            ctx.pop("proposal", None)
        if self.selected_tour:
            ctx["tour"] = self.selected_tour
        else:
            ctx.pop("tour", None)
        if self.departure_date and self.active_goal == "tour_quoting":
            ctx["date"] = self.departure_date
        if self.adults is not None:
            ctx["adults"] = self.adults
        if self.pending_cancellation:
            ctx["pending_cancellation"] = dict(self.pending_cancellation)
        else:
            ctx.pop("pending_cancellation", None)
        if self.turn_intent:
            ctx["turn_intent"] = self.turn_intent
        if self.focused_entity_type:
            ctx["focused_entity_type"] = self.focused_entity_type
        else:
            ctx.pop("focused_entity_type", None)
        if self.focused_entity_id:
            ctx["focused_entity_id"] = self.focused_entity_id
        else:
            ctx.pop("focused_entity_id", None)
        if self.current_suggestions:
            ctx["suggestions"] = list(self.current_suggestions)
        if self.filtered_suggestions:
            ctx["filtered_suggestions"] = list(self.filtered_suggestions)
        if self.historical_suggestions:
            ctx["historical_suggestions"] = [list(s) for s in self.historical_suggestions[-5:]]
        if self.last_retrieval_scope:
            ctx["last_retrieval_scope"] = self.last_retrieval_scope
        if self.quote_id:
            ctx["quote_id"] = self.quote_id
        if self.booking_ref:
            ctx["booking_ref"] = self.booking_ref
        if self.original_preferences:
            ctx["original_preferences"] = list(self.original_preferences)
        if self.pending_task:
            ctx["pending_task"] = dict(self.pending_task)
        else:
            ctx.pop("pending_task", None)
        return ctx


class SetDurationOp(BaseModel):
    op: Literal["SET_DURATION"] = "SET_DURATION"
    days: int


class IncrementDurationOp(BaseModel):
    op: Literal["INCREMENT_DURATION"] = "INCREMENT_DURATION"
    delta: int


class DecrementDurationOp(BaseModel):
    op: Literal["DECREMENT_DURATION"] = "DECREMENT_DURATION"
    delta: int


class SetDateOp(BaseModel):
    op: Literal["SET_DATE"] = "SET_DATE"
    date: str


class SetAdultCountOp(BaseModel):
    op: Literal["SET_ADULT_COUNT"] = "SET_ADULT_COUNT"
    adults: int


class SetChildCountOp(BaseModel):
    op: Literal["SET_CHILD_COUNT"] = "SET_CHILD_COUNT"
    kids: int


class SetChildAgesOp(BaseModel):
    op: Literal["SET_CHILD_AGES"] = "SET_CHILD_AGES"
    ages: list[int]


class AddDestinationOp(BaseModel):
    op: Literal["ADD_DESTINATION"] = "ADD_DESTINATION"
    destination_id: str


class RemoveDestinationOp(BaseModel):
    op: Literal["REMOVE_DESTINATION"] = "REMOVE_DESTINATION"
    destination_id: str


class ReplaceDestinationOp(BaseModel):
    op: Literal["REPLACE_DESTINATION"] = "REPLACE_DESTINATION"
    old_id: str
    new_id: str


class SetDestinationsOp(BaseModel):
    op: Literal["SET_DESTINATIONS"] = "SET_DESTINATIONS"
    destination_ids: list[str]


class AddInterestOp(BaseModel):
    op: Literal["ADD_INTEREST"] = "ADD_INTEREST"
    interest: str


class RemoveInterestOp(BaseModel):
    op: Literal["REMOVE_INTEREST"] = "REMOVE_INTEREST"
    interest: str


class SetInterestsOp(BaseModel):
    op: Literal["SET_INTERESTS"] = "SET_INTERESTS"
    interests: list[str]


class SetExclusionOp(BaseModel):
    op: Literal["SET_EXCLUSION"] = "SET_EXCLUSION"
    destination_id: str


class ClearExclusionOp(BaseModel):
    op: Literal["CLEAR_EXCLUSION"] = "CLEAR_EXCLUSION"
    destination_id: str


class RequestPolicyOp(BaseModel):
    op: Literal["REQUEST_POLICY"] = "REQUEST_POLICY"
    topic: str


class RequestQuoteOp(BaseModel):
    op: Literal["REQUEST_QUOTE"] = "REQUEST_QUOTE"


class RequestBookingOp(BaseModel):
    op: Literal["REQUEST_BOOKING"] = "REQUEST_BOOKING"


class RequestCancellationOp(BaseModel):
    op: Literal["REQUEST_CANCELLATION"] = "REQUEST_CANCELLATION"


class SelectCancellationTargetOp(BaseModel):
    op: Literal["SELECT_CANCELLATION_TARGET"] = "SELECT_CANCELLATION_TARGET"
    target_id: str


class PreviewCancellationOp(BaseModel):
    op: Literal["PREVIEW_CANCELLATION"] = "PREVIEW_CANCELLATION"
    target_id: str | None = None


class ConfirmCancellationOp(BaseModel):
    op: Literal["CONFIRM_CANCELLATION"] = "CONFIRM_CANCELLATION"


class DeclineCancellationOp(BaseModel):
    op: Literal["DECLINE_CANCELLATION"] = "DECLINE_CANCELLATION"


class AbandonPlanOp(BaseModel):
    op: Literal["ABANDON_PLAN"] = "ABANDON_PLAN"


class WithdrawQuoteOp(BaseModel):
    op: Literal["WITHDRAW_QUOTE"] = "WITHDRAW_QUOTE"
    quote_id: str | None = None


class WithdrawEnquiryOp(BaseModel):
    op: Literal["WITHDRAW_ENQUIRY"] = "WITHDRAW_ENQUIRY"
    enquiry_id: str | None = None


class RequestRefundInfoOp(BaseModel):
    op: Literal["REQUEST_REFUND_INFORMATION"] = "REQUEST_REFUND_INFORMATION"


class ResumeActivePlanOp(BaseModel):
    op: Literal["RESUME_ACTIVE_PLAN"] = "RESUME_ACTIVE_PLAN"


class StartNewPlanOp(BaseModel):
    op: Literal["START_NEW_PLAN"] = "START_NEW_PLAN"


class RequestClarificationOp(BaseModel):
    op: Literal["REQUEST_CLARIFICATION"] = "REQUEST_CLARIFICATION"
    reason: str


class NoChangeOp(BaseModel):
    op: Literal["NO_CHANGE"] = "NO_CHANGE"


class SetTripDurationOp(BaseModel):
    op: Literal["SET_TRIP_DURATION"] = "SET_TRIP_DURATION"
    days: int
    scope: Literal["trip"] = "trip"
    absolute: bool = True
    fixed_total: bool = False


class IncrementTripDurationOp(BaseModel):
    op: Literal["INCREMENT_TRIP_DURATION"] = "INCREMENT_TRIP_DURATION"
    delta: int
    scope: Literal["trip"] = "trip"
    absolute: bool = False


class DecrementTripDurationOp(BaseModel):
    op: Literal["DECREMENT_TRIP_DURATION"] = "DECREMENT_TRIP_DURATION"
    delta: int
    scope: Literal["trip"] = "trip"
    absolute: bool = False


class SetSegmentDurationOp(BaseModel):
    op: Literal["SET_SEGMENT_DURATION"] = "SET_SEGMENT_DURATION"
    destination_id: str
    days: int
    scope: Literal["segment"] = "segment"
    absolute: bool = True
    fixed_total: bool = False


class IncrementSegmentDurationOp(BaseModel):
    op: Literal["INCREMENT_SEGMENT_DURATION"] = "INCREMENT_SEGMENT_DURATION"
    destination_id: str
    delta: int
    scope: Literal["segment"] = "segment"
    absolute: bool = False


class DecrementSegmentDurationOp(BaseModel):
    op: Literal["DECREMENT_SEGMENT_DURATION"] = "DECREMENT_SEGMENT_DURATION"
    destination_id: str
    delta: int
    scope: Literal["segment"] = "segment"
    absolute: bool = False


class AddSegmentOp(BaseModel):
    op: Literal["ADD_SEGMENT"] = "ADD_SEGMENT"
    destination_id: str
    days: int | None = None
    scope: Literal["segment"] = "segment"
    fixed_total: bool = False
    needs_clarification: bool = False


class RemoveSegmentOp(BaseModel):
    op: Literal["REMOVE_SEGMENT"] = "REMOVE_SEGMENT"
    destination_id: str
    keep_total_duration: bool | None = None
    scope: Literal["segment"] = "segment"


class ReplaceSegmentOp(BaseModel):
    op: Literal["REPLACE_SEGMENT"] = "REPLACE_SEGMENT"
    old_id: str
    new_id: str
    scope: Literal["segment"] = "segment"


class ReorderSegmentsOp(BaseModel):
    op: Literal["REORDER_SEGMENTS"] = "REORDER_SEGMENTS"
    destination_ids: list[str]
    scope: Literal["segment"] = "segment"


class TransferDaysOp(BaseModel):
    op: Literal["TRANSFER_DAYS"] = "TRANSFER_DAYS"
    from_id: str
    to_id: str
    days: int
    scope: Literal["segment"] = "segment"
    fixed_total: bool = True


class SetSegmentPreferencesOp(BaseModel):
    op: Literal["SET_SEGMENT_PREFERENCES"] = "SET_SEGMENT_PREFERENCES"
    destination_id: str
    preferences: list[str]
    scope: Literal["segment"] = "segment"


class SetTotalDurationConstraintOp(BaseModel):
    op: Literal["SET_TOTAL_DURATION_CONSTRAINT"] = "SET_TOTAL_DURATION_CONSTRAINT"
    days: int | None = None
    fixed: bool = True
    scope: Literal["trip"] = "trip"


Operation = Annotated[
    Union[
        SetDurationOp,
        IncrementDurationOp,
        DecrementDurationOp,
        SetTripDurationOp,
        IncrementTripDurationOp,
        DecrementTripDurationOp,
        SetSegmentDurationOp,
        IncrementSegmentDurationOp,
        DecrementSegmentDurationOp,
        AddSegmentOp,
        RemoveSegmentOp,
        ReplaceSegmentOp,
        ReorderSegmentsOp,
        TransferDaysOp,
        SetSegmentPreferencesOp,
        SetTotalDurationConstraintOp,
        SetDateOp,
        SetAdultCountOp,
        SetChildCountOp,
        SetChildAgesOp,
        AddDestinationOp,
        RemoveDestinationOp,
        ReplaceDestinationOp,
        SetDestinationsOp,
        AddInterestOp,
        RemoveInterestOp,
        SetInterestsOp,
        SetExclusionOp,
        ClearExclusionOp,
        RequestPolicyOp,
        RequestQuoteOp,
        RequestBookingOp,
        RequestCancellationOp,
        SelectCancellationTargetOp,
        PreviewCancellationOp,
        ConfirmCancellationOp,
        DeclineCancellationOp,
        AbandonPlanOp,
        WithdrawQuoteOp,
        WithdrawEnquiryOp,
        RequestRefundInfoOp,
        ResumeActivePlanOp,
        StartNewPlanOp,
        RequestClarificationOp,
        NoChangeOp,
    ],
    Field(discriminator="op"),
]


class SemanticInterpretation(BaseModel):
    """Unified structured semantic interpretation returned by Gemini or local fallback."""

    speech_act: Literal[
        "factual_question",
        "filter_recommendations",
        "explore_product",
        "compare_products",
        "request_quote",
        "create_plan",
        "modify_plan",
        "booking_management",
        "hypothetical_question",
        "confirm_action",
        "decline_action",
        "discovery",
        "other",
    ] = "other"
    intent: Literal[
        "plan_mutation",
        "clarification_answer",
        "discovery",
        "policy",
        "quote",
        "booking",
        "cancellation",
        "off_topic",
        "ambiguous",
    ] = "plan_mutation"
    goal_continuation: bool = True
    referenced_entity_type: Literal[
        "tour", "destination", "quote", "enquiry", "booking", "custom_plan", "suggestion_list", "none"
    ] = "none"
    referenced_entity_id: str | None = None
    reference_resolution: Literal["resolved", "ambiguous", "not_found", "none"] = "none"
    retrieval_scope: Literal[
        "focused_tour", "current_suggestions", "historical_suggestions", "catalogue", "custom_plan", "policy", "booking", "none"
    ] = "none"
    requested_facts: list[str] = Field(default_factory=list, max_length=6)
    response_strategy: Literal[
        "answer_fact", "show_tour_cards", "show_itinerary", "show_quote_or_picker", "clarify", "custom_plan", "cancellation_preview", "other"
    ] = "other"
    operations: list[Operation] = Field(default_factory=list, max_length=8)
    tentative: bool = False
    needs_clarification: bool = False
    clarification_question: str | None = Field(default=None, max_length=240)
    confidence: Literal["high", "medium", "low"] = "high"


class ReducerResult(BaseModel):
    state: TripState
    applied_ops: list[str] = Field(default_factory=list)
    changes: list[str] = Field(default_factory=list)
    invalidated_artifacts: list[str] = Field(default_factory=list)
    clarification_needed: str | None = None
    validation_errors: list[str] = Field(default_factory=list)
    replan_required: bool = False


_INTEREST_PHRASES = (
    "whale watching",
    "dolphin watching",
    "beach",
    "safari",
    "wildlife",
    "tea",
    "train",
    "hiking",
    "culture",
    "temple",
    "snorkeling",
    "relaxing",
    "relax",
)


def _find_destinations_in_clause(clause: str, destinations_map: dict[str, str]) -> list[str]:
    found = [
        k
        for k, title in destinations_map.items()
        if re.search(r"\b" + re.escape(title.lower()) + r"\b", clause)
    ]
    if re.search(r"\b(?:southern|south)\s+coast\b", clause) and "D08" in destinations_map and "D08" not in found:
        found.append("D08")
    return found


def extract_operations(message: str, prev_state: TripState, destinations_map: dict[str, str]) -> list[Operation]:
    """Deterministically extract typed ``Operation`` objects from compound/natural user messages."""
    text = (message or "").strip().lower()
    if not text:
        return [NoChangeOp()]

    ops: list[Operation] = []
    # Preserve "not X, I meant Y" and partner/family phrases across "and"/comma splitting
    normalized = re.sub(r"\bnot\s+([a-z\s]+?),\s*(i\s+meant|use|prefer)\b", r"not \1 \2", text)
    normalized = re.sub(r"\b(me|i)\s+and\s+my\s+(wife|husband|partner)\b", r"\1_and_my_\2", normalized)
    normalized = re.sub(r"\bmy\s+(wife|husband|partner)\s+and\s+(i|me)\b", r"my_\1_and_\2", normalized)
    normalized = re.sub(r"\band\s+(i|me)\b", r"with_\1", normalized)
    merged_clauses: list[str] = []
    for sentence in re.split(r"[.;!?]+", normalized):
        sentence = sentence.strip()
        if not sentence:
            continue
        sub_clauses = [c.strip() for c in re.split(r"[,]+|\band\b|\bthen\b", sentence) if c.strip()]
        sent_merged: list[str] = []
        for cl in sub_clauses:
            if (
                sent_merged
                and not re.search(r"\b(?:remove|drop|exclude|add|include|replace|change|make|set|reduce|shorten|extend|start|adults?|kids?|children)\b", cl)
                and _find_destinations_in_clause(cl, destinations_map)
                and _find_destinations_in_clause(sent_merged[-1], destinations_map)
                and not re.search(r"\b(?:remove|drop|exclude|prefer\s+staying)\b", sent_merged[-1])
            ):
                sent_merged[-1] = sent_merged[-1] + " and " + cl
            else:
                sent_merged.append(cl)
        merged_clauses.extend(sent_merged)

    for cl in merged_clauses:
        cl_dests = _find_destinations_in_clause(cl, destinations_map)
        existing_seg_ids = {s.destination_id for s in prev_state.segments}

        # 0. Scoped segment transfers & segment-level duration mutations
        if m := re.search(rf"\b(?:move|transfer|shift)\s+({COUNT})\s+days?\s+from\s+([a-z\s]+?)\s+to\s+([a-z\s]+)\b", cl):
            from_ds = _find_destinations_in_clause(m[2], destinations_map)
            to_ds = _find_destinations_in_clause(m[3], destinations_map)
            if from_ds and to_ds:
                ops.append(TransferDaysOp(from_id=from_ds[0], to_id=to_ds[0], days=count(m[1])))
                continue
        if (m := re.search(rf"\b(?:add|extend(?:\s+stay)?(?:\s+in)?|give)\s+({COUNT})\s+(?:more\s+|extra\s+)?days?\s+(?:to|in|for|at)\s+([a-z\s]+)\b", cl)) and (ds := _find_destinations_in_clause(m[2], destinations_map)):
            d_id = ds[0]
            delta = count(m[1])
            if d_id in existing_seg_ids:
                ops.append(IncrementSegmentDurationOp(destination_id=d_id, delta=delta))
            else:
                ops.append(AddSegmentOp(destination_id=d_id, days=delta))
            continue
        if (m := re.search(rf"\b(?:remove|reduce|cut|shorten|subtract|drop|take\s+away)\s+({COUNT})\s+days?\s+(?:in|from|at|of)\s+([a-z\s]+)\b", cl)) and (ds := _find_destinations_in_clause(m[2], destinations_map)):
            ops.append(DecrementSegmentDurationOp(destination_id=ds[0], delta=count(m[1])))
            continue
        if (m := re.search(rf"\b(?:make|set|keep)\s+([a-z\s]+?)\s+(?:to\s+|at\s+)?({COUNT})\s+days?\b", cl)) and (ds := _find_destinations_in_clause(m[1], destinations_map)):
            d_id = ds[0]
            days_v = count(m[2])
            if d_id in existing_seg_ids:
                ops.append(SetSegmentDurationOp(destination_id=d_id, days=days_v))
            else:
                ops.append(AddSegmentOp(destination_id=d_id, days=days_v))
            continue
        if len(cl_dests) == 1 and (m := re.search(rf"\b({COUNT})[- ]days?\s+(?:in|at)\s+([a-z\s]+)\b", cl)):
            d_id = cl_dests[0]
            days_v = count(m[1])
            if d_id in existing_seg_ids:
                ops.append(SetSegmentDurationOp(destination_id=d_id, days=days_v))
            else:
                ops.append(AddSegmentOp(destination_id=d_id, days=days_v))
            continue

        # 1. Explicit arithmetic & natural trip-level duration operations
        if m := re.search(rf"\b(?:add|extend(?:\s+it)?(?:\s+by)?|squeeze in)\s+({COUNT})\s+(?:more\s+|extra\s+)?days?\b", cl):
            ops.append(IncrementDurationOp(delta=count(m[1])))
        elif re.search(r"\b(?:another\s+)?couple\s+of\s+(?:extra\s+|more\s+)?days?\b", cl):
            ops.append(IncrementDurationOp(delta=2))
        elif re.search(r"\b(?:add\s+(?:another|an?\s+extra|one\s+more)|another|extra|one\s+more)\s+day\b", cl):
            ops.append(IncrementDurationOp(delta=1))
        elif m := re.search(rf"\b(?:reduce|shorten|cut|decrease|subtract)(?:\s+it)?(?:\s+by)?\s+({COUNT})\s+days?\b", cl):
            ops.append(DecrementDurationOp(delta=count(m[1])))
        elif m := re.search(rf"\b({COUNT})\s+days?\s+shorter\b", cl):
            ops.append(DecrementDurationOp(delta=count(m[1])))
        elif re.search(r"\bfortnight\b", cl):
            ops.append(SetDurationOp(days=14))
        elif re.search(r"\b(?:a|one|1)\s+week\b", cl):
            ops.append(SetDurationOp(days=7))
        elif m := re.search(rf"\b(?:make\s+(?:it|the\s+(?:holiday|trip|stay))|update\s+(?:my\s+trip\s+)?to|change\s+(?:it\s+)?to|set\s+(?:duration\s+)?to)\s+({COUNT})[- ]days?\b", cl):
            ops.append(SetDurationOp(days=count(m[1])))
        elif m := re.search(rf"\b({COUNT})[- ]days?\b", cl):
            ops.append(SetDurationOp(days=count(m[1])))

        # 2. Destination operations (negation, comparative, remove, replace, add, set)
        if m := re.search(r"\bnot\s+([a-z\s]+?)\s+(?:i\s+meant|use|prefer)\s+([a-z\s]+)\b", cl):
            old_ds = _find_destinations_in_clause(m[1], destinations_map)
            new_ds = _find_destinations_in_clause(m[2], destinations_map)
            if old_ds and new_ds:
                ops.append(ReplaceDestinationOp(old_id=old_ds[0], new_id=new_ds[0]))
        elif re.search(r"\b(?:sounds?\s+better\s+than|prefer\s+.+\s+(?:over|to))\b", cl):
            ds = _find_destinations_in_clause(cl, destinations_map)
            if len(ds) >= 2:
                ops.append(ReplaceDestinationOp(old_id=ds[-1], new_id=ds[0]))
        elif re.search(r"\b(?:change|replace|switch)\b", cl) and re.search(r"\b(?:to|with|for)\b", cl):
            ds = _find_destinations_in_clause(cl, destinations_map)
            if len(ds) >= 2:
                ops.append(ReplaceDestinationOp(old_id=ds[0], new_id=ds[-1]))
            elif len(ds) == 1:
                ops.append(SetDestinationsOp(destination_ids=ds))
        elif re.search(r"\b(?:remove|drop|exclude|skip|without)\b", cl):
            for d_id in _find_destinations_in_clause(cl, destinations_map):
                ops.append(RemoveDestinationOp(destination_id=d_id))
                ops.append(SetExclusionOp(destination_id=d_id))
        elif re.search(r"\b(?:add|include|also|plus|as well|squeeze)\b", cl):
            for d_id in _find_destinations_in_clause(cl, destinations_map):
                ops.append(AddDestinationOp(destination_id=d_id))
        else:
            ds = _find_destinations_in_clause(cl, destinations_map)
            if ds:
                if prev_state.requested_destinations and re.search(r"\b(?:prefer\s+staying\s+in|stay\s+only\s+in|just)\b", cl):
                    ops.append(SetDestinationsOp(destination_ids=ds))
                elif prev_state.requested_destinations and any(isinstance(o, RemoveDestinationOp) for o in ops):
                    for d_id in ds:
                        ops.append(AddDestinationOp(destination_id=d_id))
                elif not prev_state.requested_destinations or re.search(r"\b(?:plan|visit|cover|covering|trip\s+to)\b", cl):
                    ops.append(SetDestinationsOp(destination_ids=ds))
                else:
                    for d_id in ds:
                        ops.append(AddDestinationOp(destination_id=d_id))

        # 3. Party & Date (explicit + natural-language partner/solo/group expressions)
        if m := re.search(rf"\b({COUNT})\s+adults?\b", cl):
            ops.append(SetAdultCountOp(adults=count(m[1])))
        elif re.search(r"\b(?:me_and_my_(?:wife|husband|partner)|i_and_my_(?:wife|husband|partner)|my_(?:wife|husband|partner)_and_(?:i|me)|(?:just\s+)?(?:the\s+)?two\s+of\s+us)\b", cl):
            ops.append(SetAdultCountOp(adults=2))
        elif re.search(rf"\bmy\s+(?:husband|wife|partner)\b.*?\b({COUNT})\s+(?:kids?|children)\b", cl):
            ops.append(SetAdultCountOp(adults=2))
        elif re.search(r"\b(?:travelling alone|by myself|just me|solo)\b", cl):
            ops.append(SetAdultCountOp(adults=1))
        elif m := re.search(rf"\bgroup\s+of\s+({COUNT})\b", cl):
            ops.append(SetAdultCountOp(adults=count(m[1])))
        if m := re.search(rf"\b({COUNT})\s+(?:kids?|child(?:ren)?)\b", cl):
            ops.append(SetChildCountOp(kids=count(m[1])))
        if m := re.search(r"\b(?:aged|ages?)\s+(?:is\s+|are\s+)?(\d{1,3}(?:\s*(?:,\s*|\band\s+)\d{1,3})*)", cl):
            ops.append(SetChildAgesOp(ages=[int(x) for x in re.findall(r"\d+", m[1])][:30]))
        try:
            if d := parse_date(cl):
                ops.append(SetDateOp(date=d))
        except ValueError:
            pass

        # 4. Interests & Negation
        is_neg_interest = bool(re.search(r"\b(?:don'?t\s+want|no\s+longer|not\s+interested|skip|avoid|remove|rather)\b", cl))
        for phrase in _INTEREST_PHRASES:
            if re.search(r"\b" + re.escape(phrase) + r"\b", cl):
                if is_neg_interest and not re.search(r"\brather\s+" + re.escape(phrase), cl):
                    ops.append(RemoveInterestOp(interest=phrase))
                else:
                    ops.append(AddInterestOp(interest=phrase))

    if not ops:
        return [NoChangeOp()]
    return ops


def detect_ambiguous_request(message: str, prev_state: TripState) -> str | None:
    """Return a targeted clarification question when the user's request is genuinely ambiguous."""
    text = (message or "").strip().lower()
    if re.search(r"\b(?:a little|bit|slightly)\s+(?:longer|more)\b", text) and not re.search(rf"\b({COUNT})\b", text):
        return "How many additional days would you like to add to your itinerary?"
    if re.search(r"\b(?:a little|bit|slightly)\s+shorter\b", text) and not re.search(rf"\b({COUNT})\b", text):
        return "How many days would you like to shorten your trip to?"
    if re.search(r"\bmake\s+[a-z\s]+?\s+shorter\b", text) and not re.search(rf"\b({COUNT})\b", text):
        return "How many days would you like to remove from that destination?"
    if re.search(r"\b(?:move|transfer|shift)\s+.*\bto\s+the\s+coast\b", text) and len(prev_state.segments) > 1:
        return "Which destination segment would you like to move those days from, and should they go to Mirissa or Galle?"
    if re.search(r"\b(?:somewhere|someplace)\s+quieter\b", text):
        current = ", ".join(prev_state.requested_destinations) or "your current stop"
        return f"Would you like to replace {current} with a quieter destination (such as Ella or Anuradhapura), or keep it and focus on relaxed coastal experiences?"
    if re.search(r"\b(?:that instead|do that)\b", text):
        return "Which option or destination would you like to switch to?"
    return None


def hybrid_extract_operations(
    message: str,
    prev_state: TripState,
    destinations_map: dict[str, str],
    events: list,
    interpret_fn=None,
) -> tuple[list[Operation], str | None]:
    """Combine deterministic fast-path extraction with Gemini ``SemanticInterpretation`` for ambiguous/natural turns."""
    det_ops = extract_operations(message, prev_state, destinations_map)
    ambiguous_q = detect_ambiguous_request(message, prev_state)
    is_no_change = len(det_ops) == 1 and isinstance(det_ops[0], NoChangeOp)

    if not is_no_change and not ambiguous_q and prev_state.active_goal == "custom_planning":
        return det_ops, None

    if interpret_fn is not None:
        state_summary = {
            "active_goal": prev_state.active_goal,
            "requested_destinations": prev_state.requested_destinations,
            "excluded_destinations": prev_state.excluded_destinations,
            "duration_days": prev_state.duration_days,
            "departure_date": prev_state.departure_date,
            "adults": prev_state.adults,
            "kids": prev_state.kids,
            "interests": prev_state.interests,
            "pending_clarification": prev_state.pending_clarification,
        }
        llm_res = interpret_fn(message, state_summary, destinations_map, events)
        if llm_res is not None:
            if llm_res.needs_clarification and llm_res.clarification_question:
                return [RequestClarificationOp(reason=llm_res.clarification_question)], llm_res.clarification_question
            valid_ops: list[Operation] = []
            for op in llm_res.operations:
                if hasattr(op, "destination_id") and op.destination_id not in destinations_map:
                    continue
                if hasattr(op, "old_id") and (op.old_id not in destinations_map or op.new_id not in destinations_map):
                    continue
                if hasattr(op, "destination_ids"):
                    op = SetDestinationsOp(destination_ids=[d for d in op.destination_ids if d in destinations_map])
                    if not op.destination_ids:
                        continue
                valid_ops.append(op)
            if valid_ops:
                return valid_ops, None

    if ambiguous_q:
        return [RequestClarificationOp(reason=ambiguous_q)], ambiguous_q
    return det_ops, None


def _sync_segments_from_flat(candidate: TripState, destinations_map: dict[str, str], *, source: str = "inferred") -> None:
    """Ensure ``candidate.segments`` matches ``requested_destinations`` and ``duration_days`` when flat ops run."""
    dests = [d for d in candidate.requested_destinations if d in destinations_map]
    total = candidate.duration_days or sum(s.days for s in candidate.segments) or 0
    if not dests or total < 1:
        if not dests:
            candidate.segments = []
        return
    n = len(dests)
    if total < n:
        total = n
        candidate.duration_days = n
    base = total // n
    rem = total % n
    old_map = {s.destination_id: s for s in candidate.segments}
    new_segs: list[ItinerarySegment] = []
    for idx, d_id in enumerate(dests):
        days = base + (1 if idx < rem else 0)
        old = old_map.get(d_id)
        new_segs.append(
            ItinerarySegment(
                segment_id=old.segment_id if old else f"seg_{d_id}",
                destination_id=d_id,
                destination_name=destinations_map[d_id],
                days=days,
                allocation_source=old.allocation_source if old else source,
                preferences=list(old.preferences) if old else [],
            )
        )
    candidate.segments = new_segs
    candidate.duration_days = sum(s.days for s in new_segs)


def reduce_state(prev_state: TripState, ops: list[Operation], destinations_map: dict[str, str]) -> ReducerResult:
    """Apply validated ``Operation`` objects deterministically onto ``prev_state``."""
    candidate = prev_state.model_copy(deep=True)
    applied: list[str] = []
    changes: list[str] = []
    invalidated: list[str] = []
    errors: list[str] = []
    clarification_needed: str | None = None
    replan_required = False
    used_scoped_segment_op = False

    # Bootstrap segments if prev_state had flat destinations + duration_days but no segments yet
    if not candidate.segments and candidate.requested_destinations and candidate.duration_days:
        _sync_segments_from_flat(candidate, destinations_map, source="inferred")

    for op in ops:
        if isinstance(op, (SetDurationOp, SetTripDurationOp)):
            if not 1 <= op.days <= 30:
                errors.append(f"Invalid duration: {op.days} days (must be 1–30)")
                break
            if candidate.duration_days != op.days:
                candidate.duration_days = op.days
                if isinstance(op, SetTripDurationOp) and op.fixed_total:
                    candidate.total_duration_constraint = op.days
                replan_required = True
                changes.append(f"duration={op.days}")
                if candidate.segments:
                    _sync_segments_from_flat(candidate, destinations_map, source="inferred")
            applied.append(f"{op.op}({op.days})")
        elif isinstance(op, (IncrementDurationOp, IncrementTripDurationOp)):
            base = candidate.duration_days or len(candidate.proposal) or 0
            new_days = base + op.delta
            if not 1 <= new_days <= 30:
                errors.append(f"Invalid incremented duration: {new_days}")
                break
            candidate.duration_days = new_days
            replan_required = True
            changes.append(f"duration={new_days}")
            if candidate.segments:
                _sync_segments_from_flat(candidate, destinations_map, source="inferred")
            applied.append(f"{op.op}({op.delta})")
        elif isinstance(op, (DecrementDurationOp, DecrementTripDurationOp)):
            base = candidate.duration_days or len(candidate.proposal) or 0
            new_days = base - op.delta
            if new_days < 1:
                errors.append(f"Cannot reduce duration below 1 day (got {new_days})")
                break
            candidate.duration_days = new_days
            replan_required = True
            changes.append(f"duration={new_days}")
            if candidate.segments:
                _sync_segments_from_flat(candidate, destinations_map, source="inferred")
            applied.append(f"{op.op}({op.delta})")
        elif isinstance(op, SetTotalDurationConstraintOp):
            candidate.total_duration_constraint = op.days if op.fixed else None
            applied.append(f"SET_TOTAL_DURATION_CONSTRAINT({op.days},{op.fixed})")
        elif isinstance(op, AddSegmentOp):
            used_scoped_segment_op = True
            if op.destination_id not in destinations_map:
                errors.append(f"Unknown destination: {op.destination_id}")
                break
            if op.destination_id in candidate.excluded_destinations:
                candidate.excluded_destinations.remove(op.destination_id)
            existing = next((s for s in candidate.segments if s.destination_id == op.destination_id), None)
            if existing:
                if op.days:
                    new_d = existing.days + op.days
                    if new_d > 30:
                        errors.append(f"Segment duration exceeds 30 days: {new_d}")
                        break
                    existing.days = new_d
                    existing.allocation_source = "explicit"
            else:
                if op.days is None and candidate.total_duration_constraint and candidate.segments:
                    clarification_needed = (
                        f"Your trip is currently fixed at {candidate.total_duration_constraint} days. "
                        f"How many days would you like in {destinations_map[op.destination_id]}, and which existing stop should be shortened?"
                    )
                    break
                seg_days = op.days if op.days is not None else 2
                if not 1 <= seg_days <= 30:
                    errors.append(f"Invalid segment duration: {seg_days}")
                    break
                candidate.segments.append(
                    ItinerarySegment(
                        segment_id=f"seg_{op.destination_id}",
                        destination_id=op.destination_id,
                        destination_name=destinations_map[op.destination_id],
                        days=seg_days,
                        allocation_source="explicit" if op.days is not None else "inferred",
                    )
                )
            if op.destination_id not in candidate.requested_destinations:
                candidate.requested_destinations.append(op.destination_id)
            total = sum(s.days for s in candidate.segments)
            if total > 30:
                errors.append(f"Total trip duration {total} exceeds maximum 30 days")
                break
            candidate.duration_days = total
            replan_required = True
            changes.append(f"segment_add={op.destination_id}:{op.days}")
            applied.append(f"ADD_SEGMENT({op.destination_id},{op.days})")
        elif isinstance(op, SetSegmentDurationOp):
            used_scoped_segment_op = True
            if not 1 <= op.days <= 30:
                errors.append(f"Invalid segment duration: {op.days}")
                break
            seg = next((s for s in candidate.segments if s.destination_id == op.destination_id), None)
            if not seg:
                if op.destination_id not in destinations_map:
                    errors.append(f"Unknown destination: {op.destination_id}")
                    break
                seg = ItinerarySegment(
                    segment_id=f"seg_{op.destination_id}",
                    destination_id=op.destination_id,
                    destination_name=destinations_map[op.destination_id],
                    days=op.days,
                    allocation_source="explicit",
                )
                candidate.segments.append(seg)
                if op.destination_id not in candidate.requested_destinations:
                    candidate.requested_destinations.append(op.destination_id)
            else:
                seg.days = op.days
                seg.allocation_source = "explicit"
            total = sum(s.days for s in candidate.segments)
            if total > 30:
                errors.append(f"Total trip duration {total} exceeds 30 days")
                break
            candidate.duration_days = total
            replan_required = True
            changes.append(f"segment_set={op.destination_id}:{op.days}")
            applied.append(f"SET_SEGMENT_DURATION({op.destination_id},{op.days})")
        elif isinstance(op, IncrementSegmentDurationOp):
            used_scoped_segment_op = True
            seg = next((s for s in candidate.segments if s.destination_id == op.destination_id), None)
            if not seg:
                errors.append(f"Destination {op.destination_id} is not in the itinerary")
                break
            if op.delta < 1 or seg.days + op.delta > 30:
                errors.append(f"Invalid segment increment: {op.delta}")
                break
            seg.days += op.delta
            seg.allocation_source = "explicit"
            total = sum(s.days for s in candidate.segments)
            if total > 30:
                errors.append(f"Total trip duration {total} exceeds 30 days")
                break
            candidate.duration_days = total
            replan_required = True
            changes.append(f"segment_inc={op.destination_id}:+{op.delta}")
            applied.append(f"INCREMENT_SEGMENT_DURATION({op.destination_id},{op.delta})")
        elif isinstance(op, DecrementSegmentDurationOp):
            used_scoped_segment_op = True
            seg = next((s for s in candidate.segments if s.destination_id == op.destination_id), None)
            if not seg:
                errors.append(f"Destination {op.destination_id} is not in the itinerary")
                break
            if op.delta < 1 or seg.days - op.delta < 1:
                errors.append(f"Cannot remove {op.delta} days from {seg.destination_name} (currently {seg.days} days; must remain at least 1 day or remove the destination explicitly)")
                break
            seg.days -= op.delta
            seg.allocation_source = "explicit"
            candidate.duration_days = sum(s.days for s in candidate.segments)
            replan_required = True
            changes.append(f"segment_dec={op.destination_id}:-{op.delta}")
            applied.append(f"DECREMENT_SEGMENT_DURATION({op.destination_id},{op.delta})")
        elif isinstance(op, TransferDaysOp):
            used_scoped_segment_op = True
            from_seg = next((s for s in candidate.segments if s.destination_id == op.from_id), None)
            to_seg = next((s for s in candidate.segments if s.destination_id == op.to_id), None)
            if not from_seg or not to_seg:
                errors.append("Both source and target destinations must be in the itinerary to transfer days")
                break
            if op.days < 1 or from_seg.days - op.days < 1:
                errors.append(f"Cannot transfer {op.days} days from {from_seg.destination_name} (only {from_seg.days} days allocated)")
                break
            from_seg.days -= op.days
            to_seg.days += op.days
            from_seg.allocation_source = "explicit"
            to_seg.allocation_source = "explicit"
            candidate.duration_days = sum(s.days for s in candidate.segments)
            replan_required = True
            changes.append(f"transfer={op.from_id}->{op.to_id}:{op.days}")
            applied.append(f"TRANSFER_DAYS({op.from_id}->{op.to_id},{op.days})")
        elif isinstance(op, RemoveSegmentOp):
            used_scoped_segment_op = True
            seg = next((s for s in candidate.segments if s.destination_id == op.destination_id), None)
            if not seg:
                errors.append(f"Destination {op.destination_id} is not in the itinerary")
                break
            remaining = [s for s in candidate.segments if s.destination_id != op.destination_id]
            if not remaining:
                errors.append("Cannot remove the only destination in the itinerary")
                break
            if op.keep_total_duration is None:
                rem_names = ", ".join(s.destination_name for s in remaining)
                clarification_needed = (
                    f"If I remove {seg.destination_name} ({seg.days} days), should I shorten your trip to "
                    f"{sum(s.days for s in remaining)} days in {rem_names}, or keep all {sum(s.days for s in candidate.segments)} days and reassign those {seg.days} days?"
                )
                candidate.pending_clarification = {
                    "type": "remove_segment_duration",
                    "destination_id": op.destination_id,
                    "removed_days": seg.days,
                    "question": clarification_needed,
                }
                break
            if op.keep_total_duration:
                remaining[0].days += seg.days
            candidate.segments = remaining
            candidate.requested_destinations = [s.destination_id for s in remaining]
            if op.destination_id not in candidate.excluded_destinations:
                candidate.excluded_destinations.append(op.destination_id)
            candidate.duration_days = sum(s.days for s in remaining)
            replan_required = True
            changes.append(f"segment_removed={op.destination_id}")
            applied.append(f"REMOVE_SEGMENT({op.destination_id})")
        elif isinstance(op, ReplaceSegmentOp):
            used_scoped_segment_op = True
            if op.new_id not in destinations_map:
                errors.append(f"Unknown destination: {op.new_id}")
                break
            for s in candidate.segments:
                if s.destination_id == op.old_id:
                    s.destination_id = op.new_id
                    s.destination_name = destinations_map[op.new_id]
                    s.segment_id = f"seg_{op.new_id}"
            candidate.requested_destinations = [s.destination_id for s in candidate.segments]
            if op.old_id not in candidate.excluded_destinations:
                candidate.excluded_destinations.append(op.old_id)
            replan_required = True
            applied.append(f"REPLACE_SEGMENT({op.old_id}->{op.new_id})")
        elif isinstance(op, ReorderSegmentsOp):
            used_scoped_segment_op = True
            seg_map = {s.destination_id: s for s in candidate.segments}
            if set(op.destination_ids) == set(seg_map) and len(op.destination_ids) == len(candidate.segments):
                candidate.segments = [seg_map[d] for d in op.destination_ids]
                candidate.requested_destinations = list(op.destination_ids)
                replan_required = True
                changes.append(f"reordered={','.join(op.destination_ids)}")
            applied.append(f"REORDER_SEGMENTS({op.destination_ids})")
        elif isinstance(op, SetSegmentPreferencesOp):
            for s in candidate.segments:
                if s.destination_id == op.destination_id:
                    s.preferences = list(dict.fromkeys([*s.preferences, *op.preferences]))
            replan_required = True
            applied.append(f"SET_SEGMENT_PREFERENCES({op.destination_id})")
        elif isinstance(op, SetDateOp):
            if candidate.departure_date != op.date:
                candidate.departure_date = op.date
                if candidate.quote_id:
                    invalidated.append("quote")
                    candidate.quote_id = None
                changes.append(f"date={op.date}")
            applied.append(f"SET_DATE({op.date})")
        elif isinstance(op, SetAdultCountOp):
            if not 1 <= op.adults <= 100:
                errors.append(f"Invalid adult count: {op.adults}")
                break
            if candidate.adults != op.adults:
                candidate.adults = op.adults
                if candidate.quote_id:
                    invalidated.append("quote")
                    candidate.quote_id = None
                changes.append(f"adults={op.adults}")
            applied.append(f"SET_ADULT_COUNT({op.adults})")
        elif isinstance(op, SetChildCountOp):
            candidate.kids = op.kids
            applied.append(f"SET_CHILD_COUNT({op.kids})")
        elif isinstance(op, SetChildAgesOp):
            candidate.ages = list(op.ages)
            candidate.kids = len(op.ages)
            applied.append(f"SET_CHILD_AGES({op.ages})")
        elif isinstance(op, AddDestinationOp):
            if op.destination_id in destinations_map:
                if op.destination_id in candidate.excluded_destinations:
                    candidate.excluded_destinations.remove(op.destination_id)
                if op.destination_id not in candidate.requested_destinations:
                    candidate.requested_destinations.append(op.destination_id)
                    replan_required = True
                    changes.append(f"added_destination={op.destination_id}")
            applied.append(f"ADD_DESTINATION({op.destination_id})")
        elif isinstance(op, RemoveDestinationOp):
            if op.destination_id in candidate.requested_destinations:
                candidate.requested_destinations = [d for d in candidate.requested_destinations if d != op.destination_id]
                candidate.segments = [s for s in candidate.segments if s.destination_id != op.destination_id]
                replan_required = True
                changes.append(f"removed_destination={op.destination_id}")
            applied.append(f"REMOVE_DESTINATION({op.destination_id})")
        elif isinstance(op, ReplaceDestinationOp):
            if op.new_id in destinations_map:
                if op.old_id in candidate.requested_destinations:
                    candidate.requested_destinations = list(
                        dict.fromkeys(op.new_id if d == op.old_id else d for d in candidate.requested_destinations)
                    )
                else:
                    candidate.requested_destinations = [op.new_id]
                if op.old_id not in candidate.excluded_destinations:
                    candidate.excluded_destinations.append(op.old_id)
                if op.new_id in candidate.excluded_destinations:
                    candidate.excluded_destinations.remove(op.new_id)
                replan_required = True
                changes.append(f"replaced_{op.old_id}_with_{op.new_id}")
            applied.append(f"REPLACE_DESTINATION({op.old_id}->{op.new_id})")
        elif isinstance(op, SetDestinationsOp):
            valid_ids = [d for d in op.destination_ids if d in destinations_map]
            if valid_ids and valid_ids != candidate.requested_destinations:
                candidate.requested_destinations = valid_ids
                for d in valid_ids:
                    if d in candidate.excluded_destinations:
                        candidate.excluded_destinations.remove(d)
                replan_required = True
                changes.append(f"destinations={','.join(valid_ids)}")
            applied.append(f"SET_DESTINATIONS({valid_ids})")
        elif isinstance(op, SetExclusionOp):
            if op.destination_id not in candidate.excluded_destinations:
                candidate.excluded_destinations.append(op.destination_id)
            candidate.requested_destinations = [d for d in candidate.requested_destinations if d != op.destination_id]
            candidate.segments = [s for s in candidate.segments if s.destination_id != op.destination_id]
            applied.append(f"SET_EXCLUSION({op.destination_id})")
        elif isinstance(op, ClearExclusionOp):
            candidate.excluded_destinations = [d for d in candidate.excluded_destinations if d != op.destination_id]
            applied.append(f"CLEAR_EXCLUSION({op.destination_id})")
        elif isinstance(op, AddInterestOp):
            if op.interest in candidate.excluded_interests:
                candidate.excluded_interests.remove(op.interest)
            if op.interest not in candidate.interests:
                candidate.interests.append(op.interest)
                replan_required = True
                changes.append(f"added_interest={op.interest}")
            applied.append(f"ADD_INTEREST({op.interest})")
        elif isinstance(op, RemoveInterestOp):
            removed = False
            new_interests = [i for i in candidate.interests if op.interest not in i and i not in op.interest]
            if len(new_interests) != len(candidate.interests):
                candidate.interests = new_interests
                removed = True
            if op.interest not in candidate.excluded_interests:
                candidate.excluded_interests.append(op.interest)
                removed = True
            if removed:
                replan_required = True
                changes.append(f"removed_interest={op.interest}")
            applied.append(f"REMOVE_INTEREST({op.interest})")
        elif isinstance(op, SetInterestsOp):
            candidate.interests = list(dict.fromkeys(op.interests))
            replan_required = True
            applied.append(f"SET_INTERESTS({candidate.interests})")
        elif isinstance(op, RequestPolicyOp):
            candidate.turn_intent = "policy"
            applied.append(f"REQUEST_POLICY({op.topic})")
        elif isinstance(op, ResumeActivePlanOp):
            candidate.active_goal = "custom_planning"
            applied.append("RESUME_ACTIVE_PLAN")
        elif isinstance(op, StartNewPlanOp):
            candidate = TripState(active_goal="custom_planning")
            replan_required = True
            applied.append("START_NEW_PLAN")

    if errors:
        return ReducerResult(state=prev_state, validation_errors=errors)

    if clarification_needed:
        return ReducerResult(state=candidate, applied_ops=applied, clarification_needed=clarification_needed)

    if not used_scoped_segment_op and candidate.requested_destinations and candidate.duration_days:
        has_dur_op = any(isinstance(o, (SetDurationOp, SetTripDurationOp, IncrementDurationOp, DecrementDurationOp)) for o in ops)
        has_set_dests = any(isinstance(o, SetDestinationsOp) for o in ops)
        if has_set_dests and not has_dur_op and prev_state.duration_days:
            candidate.duration_days = prev_state.duration_days
            _sync_segments_from_flat(candidate, destinations_map, source="inferred")
        elif not candidate.segments or {s.destination_id for s in candidate.segments} != set(candidate.requested_destinations):
            _sync_segments_from_flat(candidate, destinations_map, source="inferred")

    if candidate.segments:
        candidate.duration_days = sum(s.days for s in candidate.segments)
        candidate.requested_destinations = [s.destination_id for s in candidate.segments]
        candidate.proposal = [s.destination_id for s in candidate.segments for _ in range(s.days)]

    if candidate.requested_destinations or candidate.duration_days or candidate.proposal:
        candidate.active_goal = "custom_planning"
    if candidate.requested_destinations and candidate.duration_days:
        candidate.readiness = "ready" if (candidate.adults and candidate.departure_date) else "provisional"
    else:
        candidate.readiness = "clarifying"
    if replan_required:
        candidate.itinerary_version += 1

    return ReducerResult(
        state=candidate,
        applied_ops=applied,
        changes=changes,
        invalidated_artifacts=invalidated,
        replan_required=replan_required,
    )


def _extract_requested_facts(text: str) -> list[str]:
    facts: list[str] = []
    if re.search(r"\b(?:include|visit|cover|go\s+to|stop\s+at|through)\b", text):
        facts.append("destination_coverage")
    if re.search(r"\b(?:how\s+many\s+days?|how\s+long|duration|nights?|ten\s+days|\d+\s+days?)\b", text):
        facts.append("duration")
    if re.search(r"\b(?:hotel|hotels|accommodation|stay|lodging|resort)\b", text):
        facts.append("accommodation")
    if re.search(r"\b(?:meal|meals|breakfast|lunch|dinner|food)\b", text):
        facts.append("meals")
    if re.search(r"\b(?:elephant|elephants|leopard|wildlife|safari|whale|dolphin|animal)\b", text):
        facts.append("wildlife")
    if re.search(r"\b(?:depart|departure|start|starting|pick\s*up)\b", text):
        facts.append("departure")
    if re.search(r"\b(?:train|rail|railway)\b", text):
        facts.append("train")
    if re.search(r"\b(?:day\s+\d+|(?:first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th)\s+day)\b", text):
        facts.append("day_detail")
    return facts


def resolve_dialogue_turn(
    message: str,
    prev_state: TripState,
    records: dict,
    tours: dict,
    *,
    owned_bookings: list[dict] | None = None,
    latest_quote_id: str | None = None,
    empty_filter_result: bool = False,
    interpret_fn=None,
    events: list | None = None,
) -> SemanticInterpretation:
    """Resolve speech act, coreferences, and retrieval scope against authoritative state."""
    from ..search import tour_days

    text = (message or "").strip().lower()
    active_list = list(prev_state.current_suggestions or [])
    hist_list = list(prev_state.historical_suggestions[-1]) if prev_state.historical_suggestions else []
    focused_tour = prev_state.focused_entity_id if prev_state.focused_entity_type == "tour" else prev_state.selected_tour
    if not focused_tour and len(active_list) == 1:
        focused_tour = active_list[0]

    # 1. Optional Gemini structured semantic interpretation with full dialogue state
    llm_res: SemanticInterpretation | None = None
    if interpret_fn is not None and events is not None:
        destinations = {k: r["title"] for k, r in records.items() if r.get("type") == "destination"}
        state_summary = {
            "active_goal": prev_state.active_goal,
            "focused_entity_type": prev_state.focused_entity_type,
            "focused_entity_id": focused_tour,
            "selected_tour": prev_state.selected_tour,
            "current_suggestions": active_list,
            "historical_suggestions": prev_state.historical_suggestions[-2:],
            "requested_destinations": prev_state.requested_destinations,
            "duration_days": prev_state.duration_days,
            "departure_date": prev_state.departure_date,
            "adults": prev_state.adults,
            "quote_id": prev_state.quote_id or latest_quote_id,
            "booking_refs": [b.get("id") for b in (owned_bookings or [])],
            "has_proposal": bool(prev_state.proposal),
        }
        llm_res = interpret_fn(message, state_summary, destinations, events)

    # Validate any LLM-resolved entity ID against authoritative records/ownership
    if llm_res is not None and llm_res.referenced_entity_id:
        eid = llm_res.referenced_entity_id
        etype = llm_res.referenced_entity_type
        valid_id = (
            (etype == "tour" and eid in tours)
            or (etype == "destination" and eid in records and records[eid].get("type") == "destination")
            or (etype == "quote" and eid == (prev_state.quote_id or latest_quote_id))
            or (etype == "booking" and any(eid in {b.get("id"), b.get("quote")} for b in (owned_bookings or [])))
            or (etype == "custom_plan" and bool(prev_state.proposal))
        )
        if not valid_id:
            llm_res.referenced_entity_id = None
            llm_res.reference_resolution = "none"

    # 2. Deterministic coreference & speech-act resolution (reliable fallback & validator)
    is_mutation_verb = bool(re.search(r"\b(?:add|remove|drop|replace|switch|make\s+it|change\s+it|set\s+to|update|extend|shorten|plan|build|create|design)\b", text))
    is_question = "?" in text or bool(re.match(r"^(?:does|is|are|do|will|can|could|would|how|which|what|when|where)\b", text))
    is_quote_q = bool(re.search(r"\b(?:how\s+much|cost|price|quote|rate|rates)\b", text))
    is_policy_hypothetical = bool(re.search(r"\b(?:what\s+would\s+happen\s+if\s+i\s+cancel|if\s+i\s+cancel|refund\s+policy|cancellation\s+policy)\b", text))

    # 2a. Scoped follow-up filter ("Which ones go through Ella?", "Which of those...", "Any of them...")
    if re.search(r"\b(?:which\s+(?:ones?|of\s+(?:those|these|them))|do\s+(?:any|either|both)\s+(?:of\s+(?:those|these|them))?|any\s+of\s+(?:those|these|them))\b", text) and (active_list or hist_list):
        scope = "current_suggestions" if active_list else "historical_suggestions"
        return SemanticInterpretation(
            speech_act="filter_recommendations",
            intent="discovery",
            goal_continuation=True,
            referenced_entity_type="suggestion_list",
            reference_resolution="resolved",
            retrieval_scope=scope,
            response_strategy="show_tour_cards",
        )

    # 2b. Ordinal reference ("the first option", "second one", etc.)
    if ord_m := re.search(r"\b(?:the\s+)?(first|1st|second|2nd|third|3rd|last)(?:\s+(?:one|tour|option|package|itinerary|course))?\b", text):
        idx_map = {"first": 0, "1st": 0, "second": 1, "2nd": 1, "third": 2, "3rd": 2, "last": -1}
        idx = idx_map[ord_m.group(1)]
        if empty_filter_result and not active_list and hist_list:
            cand = hist_list[idx] if -len(hist_list) <= idx < len(hist_list) else None
            cand_title = tours[cand]["title"] if cand and cand in tours else "the earlier option"
            return SemanticInterpretation(
                speech_act="explore_product",
                intent="ambiguous",
                reference_resolution="ambiguous",
                retrieval_scope="historical_suggestions",
                needs_clarification=True,
                clarification_question=(
                    f"None of the options matched your last filter. Did you mean {ord_m.group(0)} from the earlier list "
                    f"({cand_title}), or would you like to see other tours?"
                ),
                response_strategy="clarify",
            )
        pool_list = active_list or hist_list
        if -len(pool_list) <= idx < len(pool_list) and pool_list[idx] in tours:
            chosen = pool_list[idx]
            return SemanticInterpretation(
                speech_act="explore_product",
                intent="discovery",
                referenced_entity_type="tour",
                referenced_entity_id=chosen,
                reference_resolution="resolved",
                retrieval_scope="focused_tour",
                response_strategy="show_itinerary" if re.search(r"\b(?:itinerary|days?|schedule|details?|plan|route)\b", text) else "show_tour_cards",
            )

    # 2c. Comparative / descriptive references ("shorter package", "cheaper one", "both options", "the one that includes X")
    pool_list = active_list or hist_list
    if pool_list and re.search(r"\b(?:both\s+(?:options?|tours?|packages?)|compare\s+(?:them|both|those|these))\b", text):
        return SemanticInterpretation(
            speech_act="compare_products",
            intent="discovery",
            referenced_entity_type="suggestion_list",
            reference_resolution="resolved",
            retrieval_scope="current_suggestions" if active_list else "historical_suggestions",
            response_strategy="show_tour_cards",
        )
    if pool_list and (comp_m := re.search(r"\bthe\s+(shorter|shortest|longer|longest|cheaper|cheapest)\s+(?:one|tour|package|option|course)?\b", text)):
        kind = comp_m.group(1)
        if kind in {"shorter", "shortest", "longer", "longest"}:
            ranked = sorted(
                [tid for tid in pool_list if tid in tours],
                key=lambda tid: tour_days(tours[tid]),
                reverse=kind in {"longer", "longest"},
            )
            if ranked:
                if len(ranked) > 1 and tour_days(tours[ranked[0]]) == tour_days(tours[ranked[1]]):
                    return SemanticInterpretation(
                        speech_act="explore_product",
                        intent="ambiguous",
                        reference_resolution="ambiguous",
                        needs_clarification=True,
                        clarification_question="Those options have the same duration. Which tour title would you like to explore?",
                        response_strategy="clarify",
                    )
                return SemanticInterpretation(
                    speech_act="explore_product",
                    intent="discovery",
                    referenced_entity_type="tour",
                    referenced_entity_id=ranked[0],
                    reference_resolution="resolved",
                    retrieval_scope="focused_tour",
                    response_strategy="show_itinerary" if "itinerary" in text else "show_tour_cards",
                )
        else:
            # Cheaper / cheapest: only resolve if prices are verified; otherwise clarify
            return SemanticInterpretation(
                speech_act="explore_product",
                intent="ambiguous",
                reference_resolution="ambiguous",
                needs_clarification=True,
                clarification_question="Tour prices depend on your travel date and group size. Which option would you like to price first?",
                response_strategy="clarify",
            )
    if pool_list and (inc_m := re.search(r"\bthe\s+one\s+(?:that\s+)?(?:includes?|with|visiting)\s+([a-z\s-]+)", text)):
        target_phrase = inc_m.group(1).strip().rstrip("?.!")
        matched = [
            tid for tid in pool_list
            if tid in tours and (
                target_phrase in " ".join(tours[tid].get("destinations", [])).replace("-", " ")
                or target_phrase in tours[tid].get("body", "").lower()
                or target_phrase in tours[tid].get("title", "").lower()
            )
        ]
        if len(matched) == 1:
            return SemanticInterpretation(
                speech_act="explore_product",
                intent="discovery",
                referenced_entity_type="tour",
                referenced_entity_id=matched[0],
                reference_resolution="resolved",
                retrieval_scope="focused_tour",
                response_strategy="show_itinerary" if "itinerary" in text else "show_tour_cards",
            )
        if len(matched) > 1:
            return SemanticInterpretation(
                speech_act="explore_product",
                intent="ambiguous",
                reference_resolution="ambiguous",
                needs_clarification=True,
                clarification_question=f"Both {' and '.join(tours[m]['title'] for m in matched[:2])} include {target_phrase}. Which one would you like?",
                response_strategy="clarify",
            )

    # 2d. Named historical/session references ("previous quotation", "our booking", "trip we discussed earlier")
    if re.search(r"\b(?:my\s+previous\s+quot(?:e|ation)|last\s+quot(?:e|ation))\b", text) and (prev_state.quote_id or latest_quote_id):
        qid = prev_state.quote_id or latest_quote_id
        return SemanticInterpretation(
            speech_act="explore_product",
            intent="quote",
            referenced_entity_type="quote",
            referenced_entity_id=qid,
            reference_resolution="resolved",
            retrieval_scope="focused_tour",
            response_strategy="show_quote_or_picker",
        )
    if re.search(r"\b(?:our|my)\s+booking\b", text) and owned_bookings:
        if len(owned_bookings) == 1:
            return SemanticInterpretation(
                speech_act="booking_management",
                intent="booking",
                referenced_entity_type="booking",
                referenced_entity_id=owned_bookings[0]["id"],
                reference_resolution="resolved",
                retrieval_scope="booking",
                response_strategy="other",
            )
    if re.search(r"\b(?:trip|tour|package)\s+we\s+discussed\s+earlier\b", text):
        earlier = focused_tour or (hist_list[0] if len(hist_list) == 1 else None)
        if earlier and earlier in tours:
            return SemanticInterpretation(
                speech_act="explore_product",
                intent="discovery",
                referenced_entity_type="tour",
                referenced_entity_id=earlier,
                reference_resolution="resolved",
                retrieval_scope="focused_tour",
                response_strategy="show_tour_cards",
            )
        if len(hist_list) > 1:
            return SemanticInterpretation(
                speech_act="explore_product",
                intent="ambiguous",
                reference_resolution="ambiguous",
                needs_clarification=True,
                clarification_question=f"Earlier we looked at {', '.join(tours[t]['title'] for t in hist_list[:3] if t in tours)}. Which one did you mean?",
                response_strategy="clarify",
            )

    # 2e. Anaphoric pronoun ("it", "that", "this one", "this tour") with focused_tour
    has_pronoun = bool(re.search(r"\b(?:it|that|this\s+(?:one|tour|package|trip)|the\s+(?:tour|package))\b", text))
    if is_policy_hypothetical:
        return SemanticInterpretation(
            speech_act="hypothetical_question",
            intent="policy",
            referenced_entity_type="tour" if focused_tour else "none",
            referenced_entity_id=focused_tour,
            reference_resolution="resolved" if focused_tour else "none",
            retrieval_scope="policy",
            response_strategy="answer_fact",
        )
    unknown_named_tour = bool(re.search(
        r"\b(?:how much is|price (?:of|for)|quote for)\s+(?:the\s+|a\s+)?(?!(?:this|that|the)\s+(?:tour|trip|quote|package)\b)[a-z]+\s+(?:tour|trip|expedition|package|safari)\b",
        text,
    ))
    if is_quote_q and not unknown_named_tour and (focused_tour or has_pronoun):
        if focused_tour:
            return SemanticInterpretation(
                speech_act="request_quote",
                intent="quote",
                referenced_entity_type="tour",
                referenced_entity_id=focused_tour,
                reference_resolution="resolved",
                retrieval_scope="focused_tour",
                response_strategy="show_quote_or_picker",
            )
        if len(active_list) > 1:
            return SemanticInterpretation(
                speech_act="request_quote",
                intent="ambiguous",
                reference_resolution="ambiguous",
                needs_clarification=True,
                clarification_question=f"Which of these tours would you like to quote: {', '.join(tours[t]['title'] for t in active_list[:3] if t in tours)}?",
                response_strategy="clarify",
            )
    is_catalogue_search = bool(re.search(r"\b(?:tours|packages|options|courses|holidays|recommend|show\s+me)\b", text))
    if (focused_tour and has_pronoun and is_question and not is_mutation_verb) or (
        focused_tour and not is_mutation_verb and not is_catalogue_search and _extract_requested_facts(text) and is_question
        and prev_state.active_goal != "custom_planning"
    ):
        facts = _extract_requested_facts(text)
        if facts:
            return SemanticInterpretation(
                speech_act="factual_question",
                intent="discovery",
                goal_continuation=True,
                referenced_entity_type="tour",
                referenced_entity_id=focused_tour,
                reference_resolution="resolved",
                retrieval_scope="focused_tour",
                requested_facts=facts,
                response_strategy="answer_fact",
            )

    # 2f. Read-only destination question during custom planning ("What is Ella like?" -> do not mutate plan)
    if prev_state.active_goal == "custom_planning" and is_question and not is_mutation_verb and re.search(r"\b(?:what\s+(?:is|are)|tell\s+me\s+about|where\s+is)\b", text):
        return SemanticInterpretation(
            speech_act="factual_question",
            intent="policy",
            goal_continuation=True,
            retrieval_scope="custom_plan",
            response_strategy="answer_fact",
        )

    if llm_res is not None:
        return llm_res

    return SemanticInterpretation(
        speech_act="other",
        intent="plan_mutation" if prev_state.active_goal == "custom_planning" else "discovery",
        goal_continuation=prev_state.active_goal == "custom_planning",
    )
