"""Scores how attractive a solicitation is to bid on as a reseller.

The best targets are proven, repeat-buy parts with a stable, workable unit
price - that means a predictable margin. Needs a price lookup to score;
without award history there's nothing to judge, so it returns None.
"""
import math
from typing import Any


def focus_score(stats: dict[str, Any] | None, qty: int | None) -> tuple[float | None, str | None]:
    if not stats or not stats.get("typical"):
        return None, None

    typical = stats["typical"]
    do_count = stats.get("delivery_order_count") or stats.get("count") or 0
    low = stats.get("low") or typical
    high = stats.get("high") or typical

    # Proven recurring demand: more past delivery orders = steadier work.
    # log so a handful already scores well and it saturates.
    demand = min(1.0, math.log10(do_count + 1) / math.log10(30))

    # Price stability: a tight low..high band = predictable margin.
    spread_ratio = (high / low) if low else 99
    stability = max(0.0, min(1.0, 1.5 - spread_ratio / 2))

    # Workable price band: avoid sub-$25 trinkets (margin too thin) and
    # five-figure+ items (capital/qualification heavy). Peak around $50-$3k.
    if typical < 25:
        band = 0.3
    elif typical <= 3000:
        band = 1.0
    elif typical <= 10000:
        band = 0.6
    else:
        band = 0.25

    score = round(100 * (0.45 * demand + 0.30 * stability + 0.25 * band), 1)

    bits = []
    if do_count >= 3:
        bits.append(f"{do_count} past buys")
    if spread_ratio <= 1.25:
        bits.append("stable price")
    if 25 <= typical <= 3000:
        bits.append("workable unit price")
    reason = ", ".join(bits) or "limited history"
    return score, reason
