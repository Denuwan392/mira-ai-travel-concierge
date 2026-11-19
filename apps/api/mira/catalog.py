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


class PublicQuote(Strict):
    id: UUID
    source: Source
    title: Text
    date: CalendarDate
    adults: int
    ages: list[int]
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
    text: Text


Component = Annotated[Card | Picker | Excerpt | Breakdown | Booking | Notice, Field(discriminator="type")]


class Turn(Strict):
    catalog_version: Literal[1] = 1
    trace: UUID
    text: Text
    sources: list[Source] = Field(max_length=6)
    components: list[Component] = Field(max_length=12)
