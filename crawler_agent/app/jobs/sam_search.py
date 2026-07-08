"""Searches SAM.gov's public opportunity search (no account/API key) by
keyword, NAICS, PSC/FSC classification code, and/or set-aside type.

Deliberately loose rather than exactly selector-driven (see extraction.py) -
sam.gov/search is a client-rendered SPA whose internal markup we can't
inspect ahead of time, but its opportunity detail links all follow a stable
`/opp/<id>/view` URL shape regardless of the surrounding card markup, so we
scan for that instead of guessing CSS classes.
"""
import re
import time
from typing import Any
from urllib.parse import urlencode

from ..browser import get_driver
from ..config import settings
from ..extraction import scan_for_links_matching

SET_ASIDE_QUERY_CODES = {
    "SDVOSB": "SDVOSBC",
    "SBA": "SBA",
    "WOSB": "WOSB",
    "HUBZONE": "HZC",
    "8A": "8A",
}

OPPORTUNITY_LINK_PATTERN = re.compile(r"^/opp/[^/]+/view")


def run(params: dict[str, Any]) -> dict[str, Any]:
    keyword = params.get("keyword")
    naics_code = params.get("naics_code")
    classification_code = params.get("classification_code")
    set_aside_type = params.get("set_aside_type")

    query = {"index": "opp", "sort": "-relevance", "is_active": "true", "page": "1"}
    if keyword:
        query["keywords"] = keyword
    if naics_code:
        query["naics"] = naics_code
    if classification_code:
        query["psc"] = classification_code
    if set_aside_type:
        query["typeOfSetAside"] = SET_ASIDE_QUERY_CODES.get(
            set_aside_type.upper(), set_aside_type
        )

    driver = get_driver()
    driver.get(f"{settings.sam_gov_base_url}/search/?{urlencode(query)}")
    time.sleep(5)  # SPA needs a moment to fetch results and render them

    items = scan_for_links_matching(
        driver.page_source, settings.sam_gov_base_url, OPPORTUNITY_LINK_PATTERN
    )
    for item in items:
        item["naics_code"] = naics_code
        item["set_aside_type"] = set_aside_type
        item["is_sdvosb"] = bool(set_aside_type and set_aside_type.upper() == "SDVOSB")

    return {"items": items}
