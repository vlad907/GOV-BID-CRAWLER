"""Searches SAM.gov's public opportunity search (no account/API key) by
keyword, NAICS, PSC/FSC classification code, and/or set-aside type.

See app/selectors.py and the README for why these selectors are best-effort -
sam.gov/search is a client-rendered SPA, and its DOM was not verified live
while building this.
"""
from typing import Any
from urllib.parse import urlencode

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..browser import get_driver
from ..config import settings
from ..selectors import SAM_GOV

SET_ASIDE_QUERY_CODES = {
    "SDVOSB": "SDVOSBC",
    "SBA": "SBA",
    "WOSB": "WOSB",
    "HUBZONE": "HZC",
    "8A": "8A",
}


def _text(el) -> str | None:
    return el.get_text(strip=True) if el else None


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
    wait = WebDriverWait(driver, settings.page_load_timeout_seconds)

    driver.get(f"{settings.sam_gov_base_url}/search/?{urlencode(query)}")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, SAM_GOV["result_card"])))
    soup = BeautifulSoup(driver.page_source, "html.parser")

    items = []
    for card in soup.select(SAM_GOV["result_card"]):
        solicitation_id = _text(card.select_one(SAM_GOV["result_solicitation_id"]))
        if not solicitation_id:
            continue

        link_el = card.select_one(SAM_GOV["result_link"])
        href = link_el.get("href") if link_el else None
        raw_url = (
            f"{settings.sam_gov_base_url}{href}"
            if href and href.startswith("/")
            else href
        )

        set_aside_text = _text(card.select_one(SAM_GOV["result_set_aside"]))
        is_sdvosb = bool(set_aside_text and "SERVICE-DISABLED VETERAN" in set_aside_text.upper())

        items.append(
            {
                "solicitation_id": solicitation_id,
                "nsn": None,
                "title": _text(card.select_one(SAM_GOV["result_title"])),
                "description": None,
                "qty": None,
                "naics_code": _text(card.select_one(SAM_GOV["result_naics"])),
                "set_aside_type": set_aside_text,
                "is_sdvosb": is_sdvosb,
                "close_date": _text(card.select_one(SAM_GOV["result_close_date"])),
                "raw_url": raw_url,
                "specs": {},
            }
        )

    return {"items": items}
