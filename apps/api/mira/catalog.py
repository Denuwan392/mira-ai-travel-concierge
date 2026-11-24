from typing import Annotated, Literal
from uuid import UUID
from datetime import date as CalendarDate
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Text = Annotated[str, StringConstraints(max_length=6000, pattern=r"^[^<>]*$")]
Source = Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Z0-9-]{1,60}$")]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Card(Strict):
    type: Literal["TourCard"] = "TourCard"
    id: Source
    title: Text
    duration: Text
    category: Text
    start: Text
    summary: Text
    source: Source


class Picker(Strict):
    type: Literal["TravellerPicker"] = "TravellerPicker"
    tour: Source
    date: CalendarDate | None = None
    adults: Annotated[int, Field(ge=1, le=100)] = 2
    ages: list[Annotated[int, Field(ge=0, le=120)]] = Field(default_factory=list, max_length=30)


class Excerpt(Strict):
    type: Literal["ItineraryDay", "PolicySnippet", "DestinationHighlight"]
    source: Source
    heading: Text
    text: Text


class DayStop(Strict):
    evidence: Source | None = None
    source: Source
    name: Text
    passage: Text


class Proposal(Strict):
    type: Literal["JourneyPlan"] = "JourneyPlan"
    days: list[DayStop] = Field(min_length=1,max_length=30)
    selected: int = Field(default=0,ge=0,le=29)


class RouteMap(Strict):
    days: list[DayStop] = Field(min_length=1,max_length=30)
    type: Literal["InteractiveMap"] = "InteractiveMap"
    selected: int = Field(ge=0,le=29)


class Departure(Strict):
    type: Literal["DateSelector"] = "DateSelector"
    value: CalendarDate | None = None


class SourcePanel(Strict):
    type: Literal["StayCard","ActivityCard","SourceReference","ComparisonPanel","ConfirmationPanel","DestinationCard"]
    source: Source
    heading: Text
    text: Text


class PublicQuote(Strict):
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
    type: Literal["PriceBreakdown"] = "PriceBreakdown"
    quote: PublicQuote


class Booking(Strict):
    type: Literal["BookingForm"] = "BookingForm"
    quote: UUID


class Notice(Strict):
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


Component = Annotated[Card | Picker | Excerpt | Proposal | RouteMap | Departure | SourcePanel | Breakdown | Booking | Notice, Field(discriminator="type")]


class Turn(Strict):
    catalog_version: Literal[1] = 1
    trace: UUID
    text: Text
    sources: list[Source] = Field(max_length=6)
    components: list[Component] = Field(max_length=12)
