"""Strict Pydantic v2 component catalog and turn schema for Mira's UI contract.

Defines the allowed A2UI-backed component payloads (``TourCard``,
``TravellerPicker``, ``JourneyPlan``, ``PriceBreakdown``, ``BookingForm``,
``EnquiryNotice``, etc.) and the top-level ``Turn`` envelope. All models forbid
unexpected fields and sanitize text against angle brackets to prevent HTML/XSS
injection.
"""
from typing import Annotated, Literal
from uuid import UUID
from datetime import date as CalendarDate
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# Safe plain-text string (no '<' or '>' characters) and uppercase record/source ID.
Text = Annotated[str, StringConstraints(max_length=6000, pattern=r"^[^<>]*$")]
Source = Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Z0-9-]{1,60}$")]


class Strict(BaseModel):
    """Base model rejecting any unknown fields in component or turn payloads."""

    model_config = ConfigDict(extra="forbid")


class Card(Strict):
    """Summary card for a published tour shown in discovery or selection turns."""

    type: Literal["TourCard"] = "TourCard"
    id: Source
    title: Text
    duration: Text
    category: Text
    start: Text
    summary: Text
    source: Source


class Picker(Strict):
    """Interactive traveller-count, child-age, and departure-date selector."""

    type: Literal["TravellerPicker"] = "TravellerPicker"
    tour: Source
    date: CalendarDate | None = None
    adults: Annotated[int, Field(ge=1, le=100)] = 2
    ages: list[Annotated[int, Field(ge=0, le=120)]] = Field(default_factory=list, max_length=30)


class Excerpt(Strict):
    """Source-attributed snippet from a tour day, policy document, or destination."""

    type: Literal["ItineraryDay", "PolicySnippet", "DestinationHighlight"]
    source: Source
    heading: Text
    text: Text


class DayStop(Strict):
    """Single day stop within a bespoke or extended ``JourneyPlan``/``InteractiveMap``."""

    evidence: Source | None = None
    source: Source
    name: Text
    passage: Text


class Proposal(Strict):
    """Multi-day custom journey proposal rendered in the trip notebook."""

    type: Literal["JourneyPlan"] = "JourneyPlan"
    days: list[DayStop] = Field(min_length=1,max_length=30)
    selected: int = Field(default=0,ge=0,le=29)


class RouteMap(Strict):
    """Interactive route map synchronized with the selected day index."""

    days: list[DayStop] = Field(min_length=1,max_length=30)
    type: Literal["InteractiveMap"] = "InteractiveMap"
    selected: int = Field(ge=0,le=29)


class Departure(Strict):
    """Standalone departure date selector widget."""

    type: Literal["DateSelector"] = "DateSelector"
    value: CalendarDate | None = None


class SourcePanel(Strict):
    """Contextual side/detail panel backed by a verified dataset source ID."""

    type: Literal["StayCard","ActivityCard","SourceReference","ComparisonPanel","ConfirmationPanel","DestinationCard"]
    source: Source
    heading: Text
    text: Text


class PublicQuote(Strict):
    """Traveller-facing USD quote summary; excludes internal LKR cost and margin."""

    enquiry: UUID | None = None
    enquiry_reference: str | None = None
    id: UUID
    source: Source
    title: Text
    date: CalendarDate
    adults: int
    ages: list[int]
    validity: Literal["recheck_before_booking"] = "recheck_before_booking"
    currency: Literal["USD"] = "USD"
    total: Annotated[int, Field(gt=0)]
    deposit: Annotated[int, Field(gt=0)]
    balance: Annotated[int, Field(ge=0)]


class Breakdown(Strict):
    """Wrapper component displaying a ``PublicQuote`` breakdown card."""

    type: Literal["PriceBreakdown"] = "PriceBreakdown"
    quote: PublicQuote


class Booking(Strict):
    """Booking/contact submission form linked to a persisted quote UUID."""

    type: Literal["BookingForm"] = "BookingForm"
    quote: UUID


class Notice(Strict):
    """Structured notice for specialist handoffs or pricing-unavailable outcomes."""

    type: Literal["EnquiryNotice"] = "EnquiryNotice"
    reference: UUID | None = None
    public_reference: str | None = None
    outcome: Literal[
        "PRICE_UNAVAILABLE",
        "PRICE_VALIDATION_ERROR",
        "PRICING_SERVICE_ERROR",
        "SPECIALIST_HANDOFF",
    ] | None = None
    reason_code: str | None = None
    tour_id: str | None = None
    text: Text


class CancellationPreview(Strict):
    """Two-phase HITL cancellation preview with deterministic P02 refund calculation."""

    type: Literal["CancellationPreview"] = "CancellationPreview"
    target_type: Literal["booking", "enquiry", "quote", "plan"]
    target_id: Text
    booking_reference: Text | None = None
    tour_title: Text
    travel_date: Text | None = None
    travellers: Annotated[int, Field(ge=1, le=200)] = 1
    status: Text
    terms: Text
    paid_amount: Text
    refund_amount: Text
    refund_status: Text
    policy_title: Text = "Cancellation policy"
    requires_confirmation: bool = True


class CancellationStatus(Strict):
    """Result of a confirmed, declined, or pending cancellation action."""

    type: Literal["CancellationStatus"] = "CancellationStatus"
    target_id: Text
    booking_reference: Text | None = None
    status: Literal["cancelled", "kept", "pending_staff", "withdrawn", "abandoned"]
    refund_amount: Text = "0"
    refund_status: Text = "none"
    summary: Text


Component = Annotated[
    Card | Picker | Excerpt | Proposal | RouteMap | Departure | SourcePanel | Breakdown | Booking | Notice | CancellationPreview | CancellationStatus,
    Field(discriminator="type"),
]


class Turn(Strict):
    """Validated assistant turn envelope persisted and returned to the frontend."""

    catalog_version: Literal[1] = 1
    trace: UUID
    text: Text
    sources: list[Source] = Field(max_length=6)
    components: list[Component] = Field(max_length=12)
