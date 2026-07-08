"""Searches DIBBS for open RFQs - plain HTTP, no browser (see dibbs_http.py
for the verified URL/table structure this is built on).

Each DIBBS query returns at most 50 records (the grid's server-side page
size; its ASP.NET postback paging rejects non-browser POSTs, so we don't
fight it). Broad coverage comes from fanning out many cheap queries instead:
sweeping recent posted-dates and/or lists of 4-digit FSC codes.

Modes, chosen from params:
  {"nsn": "5310-00-612-9969"}      -> exact NSN lookup
  {"fsc": "5310"}                  -> one 4-digit FSC
  {"classification_code": "53"}    -> sweep every known FSC in that PSC group
  {"posted_date": "07-06-2026"}    -> posted that day, all FSCs
  {}                               -> sweep the last `days` (default 3) of
                                      posted-dates plus the default FSC list
Optional: {"days": 3}, {"fsc_list": ["5310", ...]} to control the sweep.
"""
import time
from datetime import date, timedelta
from typing import Any

from ..dibbs_http import DibbsSession, parse_rfq_table

# Part-heavy FSC codes grouped by 2-digit PSC group, so the UI's PSC field
# ("53 = Hardware") expands into a real sweep. Not exhaustive - extend freely.
FSC_GROUPS: dict[str, list[str]] = {
    "29": ["2910", "2915", "2920", "2930", "2940", "2990", "2995"],
    "31": ["3110", "3120", "3130"],
    "47": ["4710", "4720", "4730"],
    "53": ["5305", "5306", "5307", "5310", "5315", "5320", "5325", "5330",
           "5331", "5340", "5355", "5360", "5365"],
    "59": ["5905", "5910", "5915", "5920", "5935", "5940", "5961", "5962",
           "5975", "5985", "5995", "5999"],
    "61": ["6105", "6110", "6145", "6150"],
}
DEFAULT_FSC_SWEEP = FSC_GROUPS["53"] + FSC_GROUPS["31"] + FSC_GROUPS["59"]

# Pause between fanned-out queries - keep the footprint polite.
SWEEP_DELAY_SECONDS = 1.0

# One consented session reused across jobs - the consent handshake only
# happens once per process lifetime.
_session: DibbsSession | None = None


def _get_session() -> DibbsSession:
    global _session
    if _session is None:
        _session = DibbsSession()
    return _session


def _search(session: DibbsSession, category: str, type_srch: str, value: str) -> list[dict]:
    html = session.fetch_search_page(category, type_srch, value)
    return parse_rfq_table(html)


def _dedupe(items: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    unique = []
    for item in items:
        key = (item["solicitation_id"], item["nsn"], (item["specs"] or {}).get("purchase_request"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def run(params: dict[str, Any]) -> dict[str, Any]:
    session = _get_session()

    nsn = params.get("nsn")
    fsc = params.get("fsc")
    classification_code = str(params.get("classification_code") or "")
    posted_date = params.get("posted_date")
    days = int(params.get("days") or 3)
    fsc_list = params.get("fsc_list")

    if nsn:
        digits = "".join(ch for ch in str(nsn) if ch.isdigit())
        return {"items": _search(session, "nsn", "cq", digits)}

    if fsc or len(classification_code) == 4:
        return {"items": _search(session, "fsc", "cq", str(fsc or classification_code))}

    if posted_date:
        return {"items": _search(session, "post", "dt", posted_date)}

    # Broad sweep: recent posted-dates + an FSC list.
    if not fsc_list:
        fsc_list = FSC_GROUPS.get(classification_code[:2], DEFAULT_FSC_SWEEP) if classification_code else DEFAULT_FSC_SWEEP

    items: list[dict] = []
    for offset in range(days):
        day = (date.today() - timedelta(days=offset)).strftime("%m-%d-%Y")
        items.extend(_search(session, "post", "dt", day))
        time.sleep(SWEEP_DELAY_SECONDS)
    for code in fsc_list:
        items.extend(_search(session, "fsc", "cq", str(code)))
        time.sleep(SWEEP_DELAY_SECONDS)

    return {"items": _dedupe(items)}
