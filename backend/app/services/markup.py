"""Suggests a bid price: default markup over cost, capped to stay competitive
against the last known/benchmark award price for the same or a similar NSN.

This is a starting suggestion for a human to review and adjust, not an
authoritative pricing engine.
"""
from ..config import settings


def suggest_price(
    cost_basis: float,
    benchmark_award_price: float | None = None,
    default_markup_pct: float | None = None,
) -> tuple[float, float]:
    """Returns (markup_pct, suggested_price)."""
    markup_pct = default_markup_pct if default_markup_pct is not None else settings.default_markup_pct
    suggested_price = cost_basis * (1 + markup_pct)

    if benchmark_award_price is not None and suggested_price > benchmark_award_price:
        # undercut the last award price slightly to stay competitive
        suggested_price = benchmark_award_price * 0.97
        markup_pct = (suggested_price / cost_basis) - 1

    return markup_pct, suggested_price
