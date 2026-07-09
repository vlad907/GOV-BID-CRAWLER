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


def _stats(prices: list[float]) -> dict[str, Any]:
    if not prices:
        return {"count": 0, "low": None, "high": None, "avg": None, "median": None, "last": None}
    return {
        "count": len(prices),
        "low": round(min(prices), 2),
        "high": round(max(prices), 2),
        "avg": round(mean(prices), 2),
        "median": round(median(prices), 2),
        "last": prices[0],  # awards come newest-first from DIBBS
    }


def _dibbs_awards(nsn: str) -> dict[str, Any]:
    digits = "".join(ch for ch in str(nsn) if ch.isdigit())
    html = _get_session().fetch_awards_page(digits)
    awards = parse_awards_table(html)
    return {
        "nsn": nsn,
        "source": "dibbs_awards",
        "awards": awards,
        "stats": _stats([a["price"] for a in awards if a.get("price")]),
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
    return {
        "psc": psc,
        "source": "usaspending",
        "awards": awards,
        "stats": _stats([a["price"] for a in awards if a.get("price")]),
    }


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
