"""Searches DIBBS for open RFQs by NSN or keyword.

Deliberately loose rather than exactly selector-driven (see extraction.py) -
we scan whatever page we land on for NSN-shaped text instead of requiring an
exact results-table selector to match. Best-effort attempts to click past
the consent page and use the real search box still happen first, but their
failure doesn't block the scan - even landing on the wrong page still
returns whatever looks like a part, which is enough to start with.
"""
import time
from typing import Any

from selenium.webdriver.common.by import By

from ..browser import get_driver
from ..config import settings
from ..extraction import scan_for_nsn_items
from ..selectors import DIBBS


def _try_click(driver, selector: str) -> bool:
    # CSS comma-separated selectors are a native "match any of these" - no
    # need to try each one individually.
    try:
        driver.find_element(By.CSS_SELECTOR, selector).click()
        return True
    except Exception:
        return False


def _try_search(driver, query: str) -> None:
    try:
        box = driver.find_element(By.CSS_SELECTOR, DIBBS["search_input"])
        box.clear()
        box.send_keys(query)
    except Exception:
        return  # no recognizable search box on this page - scan whatever's here as-is

    if not _try_click(driver, DIBBS["search_submit"]):
        try:
            box.submit()  # fall back to submitting the form directly
        except Exception:
            pass


def run(params: dict[str, Any]) -> dict[str, Any]:
    nsn = params.get("nsn")
    keyword = params.get("keyword")
    query = nsn or keyword or ""

    driver = get_driver()
    driver.get(f"{settings.dibbs_base_url}/RFQ/")
    time.sleep(3)  # let the page settle before poking at it

    if _try_click(driver, DIBBS["consent_button"]):
        time.sleep(2)

    if query:
        _try_search(driver, query)
        time.sleep(3)

    items = scan_for_nsn_items(driver.page_source, settings.dibbs_base_url)
    return {"items": items}
