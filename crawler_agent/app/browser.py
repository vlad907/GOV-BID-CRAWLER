"""Shared, non-headless Chrome driver, reused across jobs.

Kept as a single long-lived window rather than spinning up/tearing down a
browser per job: fewer process launches looks less like a bot, and it's
faster once warm.
"""
import threading

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from .config import settings

_driver: webdriver.Chrome | None = None
_lock = threading.Lock()


def get_driver() -> webdriver.Chrome:
    global _driver
    with _lock:
        if _driver is None:
            options = Options()
            # Deliberately NOT headless - see README for why.
            options.add_argument(f"--user-data-dir={settings.chrome_profile_dir}")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            _driver = webdriver.Chrome(options=options)
            _driver.set_page_load_timeout(settings.page_load_timeout_seconds)
        return _driver


def shutdown_driver() -> None:
    global _driver
    with _lock:
        if _driver is not None:
            _driver.quit()
            _driver = None
