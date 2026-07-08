"""Searches SAM.gov opportunities via its own public search API - the same
JSON endpoint the sam.gov/search SPA calls, no account or API key required.

Verified live (July 2026):
  GET https://sam.gov/api/prod/sgs/v1/search/?index=opp&page=0&size=25
      &mode=search&responseType=json&is_active=true
      [&q=...&psc=...&naics=...&typeOfSetAside=SDVOSBC]
Response: _embedded.results[] with title, solicitationNumber, responseDate,
publishDate, descriptions[].content (HTML), _id; page.totalElements.
Detail page: https://sam.gov/opp/<_id>/view
"""
import re
from datetime import datetime, timezone
from typing import Any

import requests

SEARCH_API = "https://sam.gov/api/prod/sgs/v1/search/"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/149.0 Safari/537.36"
)
PAGE_SIZE = 25

SET_ASIDE_QUERY_CODES = {
    "SDVOSB": "SDVOSBC",
    "SBA": "SBA",
    "WOSB": "WOSB",
    "HUBZONE": "HZC",
    "8A": "8A",
}

TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str | None) -> str | None:
    if not text:
        return None
    return TAG_RE.sub(" ", text).replace("&nbsp;", " ").strip() or None


def run(params: dict[str, Any]) -> dict[str, Any]:
    keyword = params.get("keyword")
    naics_code = params.get("naics_code")
    classification_code = params.get("classification_code")
    set_aside_type = params.get("set_aside_type")
    max_pages = int(params.get("max_pages") or 4)

    query: dict[str, Any] = {
        "index": "opp",
        "size": PAGE_SIZE,
        "mode": "search",
        "responseType": "json",
        "is_active": "true",
    }
    if keyword:
        query["q"] = keyword
        query["qMode"] = "ALL"
    if naics_code:
        query["naics"] = naics_code
    if classification_code:
        query["psc"] = classification_code
    if set_aside_type:
        query["typeOfSetAside"] = SET_ASIDE_QUERY_CODES.get(
            str(set_aside_type).upper(), set_aside_type
        )

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    items: list[dict] = []
    for page in range(max_pages):
        query["page"] = page
        resp = session.get(SEARCH_API, params=query, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("_embedded", {}).get("results", [])
        if not results:
            break

        for r in results:
            # SAM marks some notices "active" whose response deadline has
            # long passed (e.g. standing Multiple Award Schedules) - skip
            # anything no longer biddable.
            response_date = r.get("responseDate")
            if response_date:
                try:
                    deadline = datetime.fromisoformat(response_date.replace("Z", "+00:00"))
                    if deadline < datetime.now(timezone.utc):
                        continue
                except ValueError:
                    pass

            descriptions = r.get("descriptions") or []
            description = _strip_html(descriptions[0].get("content")) if descriptions else None
            opp_id = r.get("_id")

            items.append(
                {
                    "solicitation_id": r.get("solicitationNumber") or opp_id,
                    "nsn": None,
                    "title": r.get("title"),
                    "description": description,
                    "qty": None,
                    "naics_code": naics_code,
                    "set_aside_type": set_aside_type,
                    "is_sdvosb": bool(
                        set_aside_type and str(set_aside_type).upper() == "SDVOSB"
                    ),
                    "close_date": r.get("responseDate"),
                    "raw_url": f"https://sam.gov/opp/{opp_id}/view" if opp_id else None,
                    "specs": {
                        "notice_type": (r.get("type") or {}).get("value"),
                        "published": r.get("publishDate"),
                    },
                }
            )

        total = data.get("page", {}).get("totalElements", 0)
        if (page + 1) * PAGE_SIZE >= total:
            break

    return {"items": items}
