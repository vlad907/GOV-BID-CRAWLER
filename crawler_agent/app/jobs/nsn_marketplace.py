"""Searches an NSN parts marketplace for candidate suppliers/listings.

See app/selectors.py and the README for why these selectors are best-effort.
"""
from typing import Any

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..browser import get_driver
from ..config import settings
from ..selectors import NSN_MARKETPLACE


def _text(el) -> str | None:
    return el.get_text(strip=True) if el else None


def _parse_price(el) -> float | None:
    text = _text(el)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit() or ch == ".")
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


def run(params: dict[str, Any]) -> dict[str, Any]:
    nsn = params.get("nsn")
    if not nsn:
        raise ValueError("nsn_marketplace job requires a 'nsn' param")

    driver = get_driver()
    wait = WebDriverWait(driver, settings.page_load_timeout_seconds)

    driver.get(settings.nsn_marketplace_base_url)
    search_input = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, NSN_MARKETPLACE["search_input"]))
    )
    search_input.clear()
    search_input.send_keys(nsn)
    driver.find_element(By.CSS_SELECTOR, NSN_MARKETPLACE["search_submit"]).click()

    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, NSN_MARKETPLACE["result_row"])))
    soup = BeautifulSoup(driver.page_source, "html.parser")

    suppliers = []
    for row in soup.select(NSN_MARKETPLACE["result_row"]):
        name = _text(row.select_one(NSN_MARKETPLACE["result_supplier_name"]))
        if not name:
            continue

        link_el = row.select_one(NSN_MARKETPLACE["result_link"])
        href = link_el.get("href") if link_el else None
        url = (
            f"{settings.nsn_marketplace_base_url}{href}"
            if href and href.startswith("/")
            else href
        )

        suppliers.append(
            {
                "name": name,
                "cage_code": _text(row.select_one(NSN_MARKETPLACE["result_cage_code"])),
                "price": _parse_price(row.select_one(NSN_MARKETPLACE["result_price"])),
                "url": url,
                "source_marketplace": settings.nsn_marketplace_base_url,
                "contact_email": None,
            }
        )

    return {"nsn": nsn, "suppliers": suppliers}
