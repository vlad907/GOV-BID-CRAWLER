"""Searches DIBBS for open RFQs by NSN or keyword.

See app/selectors.py and the README for why these selectors are best-effort
and app/browser.py for why this drives a real, visible Chrome window instead
of a headless one.
"""
from typing import Any

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..browser import get_driver
from ..config import settings
from ..selectors import DIBBS


def _accept_consent_if_present(driver, wait: WebDriverWait) -> None:
    try:
        button = driver.find_element(By.CSS_SELECTOR, DIBBS["consent_button"])
        button.click()
    except Exception:
        pass  # already past the consent page (persistent profile keeps the cookie)


def run(params: dict[str, Any]) -> dict[str, Any]:
    nsn = params.get("nsn")
    keyword = params.get("keyword")

    driver = get_driver()
    wait = WebDriverWait(driver, settings.page_load_timeout_seconds)

    driver.get(f"{settings.dibbs_base_url}/RFQ/")
    _accept_consent_if_present(driver, wait)

    search_input = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, DIBBS["search_input"]))
    )
    search_input.clear()
    search_input.send_keys(nsn or keyword or "")
    driver.find_element(By.CSS_SELECTOR, DIBBS["search_submit"]).click()

    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, DIBBS["result_row"])))
    soup = BeautifulSoup(driver.page_source, "html.parser")

    items = []
    for row in soup.select(DIBBS["result_row"]):
        solicitation_id = _text(row.select_one(DIBBS["result_solicitation_id"]))
        if not solicitation_id:
            continue  # header row or non-data row

        link_el = row.select_one(DIBBS["result_link"])
        href = link_el.get("href") if link_el else None
        raw_url = f"{settings.dibbs_base_url}{href}" if href and href.startswith("/") else href

        items.append(
            {
                "solicitation_id": solicitation_id,
                "nsn": _text(row.select_one(DIBBS["result_nsn"])) or nsn,
                "title": _text(row.select_one(DIBBS["result_title"])),
                "qty": _parse_int(row.select_one(DIBBS["result_qty"])),
                "close_date": _text(row.select_one(DIBBS["result_close_date"])),
                "raw_url": raw_url,
                "specs": {},
            }
        )

    return {"items": items}


def _text(el) -> str | None:
    return el.get_text(strip=True) if el else None


def _parse_int(el) -> int | None:
    text = _text(el)
    if not text:
        return None
    digits = text.replace(",", "")
    return int(digits) if digits.isdigit() else None
