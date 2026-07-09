"""Historical award-price lookup for benchmarking bids.

For NSNs: DIBBS Awards search (exact past DLA award prices + awardee CAGE).
For SAM.gov solicitations without an NSN: USASpending.gov's free API, keyed
by PSC, as a coarser recent-award-amount benchmark.

Modes:
  {"nsn": "5310-00-612-9969"}   -> {"nsn", "awards": [...], "stats": {...}}
  {"psc": "5310"}               -> USASpending recent awards for that PSC
  {"targets": [{"solicitation_id", "nsn"?, "psc"?}, ...]}
      -> {"bulk": [{"solicitation_id", "awards", "stats", "source"}]}
"""
import time
from statistics import mean, median
from typing import Any

import requests

from ..dibbs_http import DibbsSession, parse_awards_table

USASPENDING_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
BULK_DELAY_SECONDS = 0.5

_session: DibbsSession | None = None


def _get_session() -> DibbsSession:
    global _session
    if _session is None:
        _session = DibbsSession()
    return _session


def _empty_stats() -> dict[str, Any]:
    return {
        "count": 0,
        "delivery_order_count": 0,
        "typical": None,
        "low": None,
        "high": None,
        "avg": None,
        "last": None,
        "contract_ceiling": None,
    }


def _stats_from_awards(awards: list[dict]) -> dict[str, Any]:
    """Builds a per-unit-ish price signal from DLA awards.

    The parent "Award/Basic" IDIQ row is a contract ceiling, not a buy, so we
    base the real numbers on Delivery Orders (actual recurring purchases) and
    keep the ceiling only as separate context. Median is the headline
    ("typical") since it ignores the occasional bulk-order outlier.
    """
    deliveries = [a["price"] for a in awards if a.get("award_type") == "delivery_order" and a.get("price")]
    basics = [a["price"] for a in awards if a.get("award_type") == "basic" and a.get("price")]

    # Fall back to all priced rows if this NSN has no delivery orders at all.
    priced = deliveries if deliveries else [a["price"] for a in awards if a.get("price")]
    if not priced:
        return _empty_stats()

    # last = most recent delivery-order price (awards come newest-first)
    last = next(
        (a["price"] for a in awards if a.get("award_type") == "delivery_order" and a.get("price")),
        priced[0],
    )
    return {
        "count": len(priced),
        "delivery_order_count": len(deliveries),
        "typical": round(median(priced), 2),
        "low": round(min(priced), 2),
        "high": round(max(priced), 2),
        "avg": round(mean(priced), 2),
        "last": last,
        "contract_ceiling": round(max(basics), 2) if basics else None,
    }


def _dibbs_awards(nsn: str) -> dict[str, Any]:
    digits = "".join(ch for ch in str(nsn) if ch.isdigit())
    html = _get_session().fetch_awards_page(digits)
    awards = parse_awards_table(html)
    return {
        "nsn": nsn,
        "source": "dibbs_awards",
        "awards": awards,
        "stats": _stats_from_awards(awards),
    }


def _usaspending_by_psc(psc: str) -> dict[str, Any]:
    body = {
        "filters": {"award_type_codes": ["A", "B", "C", "D"], "psc_codes": [str(psc)]},
        "fields": ["Award ID", "Recipient Name", "Award Amount", "Action Date"],
        "sort": "Award Amount",
        "order": "desc",
        "limit": 25,
    }
    try:
        resp = requests.post(USASPENDING_URL, json=body, timeout=30)
        resp.raise_for_status()
        results = resp.json().get("results", [])
    except requests.RequestException:
        results = []

    awards = [
        {
            "award_number": r.get("Award ID"),
            "awardee_cage": None,
            "awardee_name": r.get("Recipient Name"),
            "price": r.get("Award Amount"),
            "award_date": r.get("Action Date"),
            "nomenclature": None,
        }
        for r in results
        if r.get("Award Amount")
    ]
    prices = [a["price"] for a in awards if a.get("price")]
    stats = _empty_stats()
    if prices:
        stats.update(
            count=len(prices),
            typical=round(median(prices), 2),
            low=round(min(prices), 2),
            high=round(max(prices), 2),
            avg=round(mean(prices), 2),
            last=prices[0],
        )
    return {"psc": psc, "source": "usaspending", "awards": awards, "stats": stats}


def _lookup(nsn: str | None, psc: str | None) -> dict[str, Any]:
    if nsn:
        return _dibbs_awards(nsn)
    if psc:
        return _usaspending_by_psc(psc)
    return {"source": None, "awards": [], "stats": _stats([])}


def run(params: dict[str, Any]) -> dict[str, Any]:
    targets = params.get("targets")
    if targets:
        bulk = []
        for t in targets:
            found = _lookup(t.get("nsn"), t.get("psc"))
            found["solicitation_id"] = t.get("solicitation_id")
            bulk.append(found)
            time.sleep(BULK_DELAY_SECONDS)
        return {"bulk": bulk}

    return _lookup(params.get("nsn"), params.get("psc"))
