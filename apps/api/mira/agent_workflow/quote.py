"""Pricing / quotation node for Mira's LangGraph workflow."""
import logging
from datetime import date
from time import perf_counter
from uuid import uuid4

from ..catalog import PublicQuote
from ..data import Unavailable, as_of, price
from ..observability import elapsed, event
from ..rates_repository import current_rates
from .enquiry import quote_enquiry
from .state import working


def quote_node(_):
    """Node 3 (optional): Calculate a live USD quote from the rate workbook or capture the unavailability reason."""
    w = working.get()
    ctx = w["context"]
    before = perf_counter()
    event("PRICING", "pricing.started", level=logging.DEBUG, tour_id=ctx["tour"])
    rates = None
    pricing_trace: dict = {}
    try:
        rates = current_rates()
        value = price(ctx["tour"], date.fromisoformat(ctx["date"]), ctx["adults"], ctx.get("ages", []), as_of(), rates, trace_out=pricing_trace)
        w["internal"] = value
        quote_enquiry(w, "verified_quote")
        w["quote"] = PublicQuote(enquiry=w["enquiry"], enquiry_reference=w["enquiry_reference"],
            id=uuid4(), source=ctx["tour"], title=w["tours"][ctx["tour"]]["title"],
            date=ctx["date"], adults=ctx["adults"], ages=ctx.get("ages", []),
            **{k: value[k] for k in ("total", "deposit", "balance")},
        )
    except (Unavailable, ValueError) as exc:
        if w.get("explicit_quote") and isinstance(exc, Unavailable) and str(exc) == "rate_import_invalid":
            raise
        w["reason"] = str(exc) if isinstance(exc, Unavailable) else "invalid_travel_details"
    w["events"].append({"stage": "pricing", "outcome": w.get("reason", "verified"),
                        "snapshot": w.get("internal", {}).get("snapshot"), "rate_digest": rates.digest if rates else None,
                        "ms": round((perf_counter()-before)*1000)})
    quote = w.get("quote")
    reason = w.get("reason")
    event("PRICING", "pricing.completed", tour_id=ctx["tour"], rate_status="verified" if quote else "unavailable",
          quote_id=str(quote.id) if quote else None, rule=reason, duration_ms=elapsed(before), **pricing_trace)
    return {}
