"""Shared, non-headless Chrome driver, reused across jobs.

Kept as a single long-lived window rather than spinning up/tearing down a
browser per job: fewer process launches looks less like a bot, and it's
faster once warm.
"""
import os
import threading

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from .config import settings

_driver: webdriver.Chrome | None = None
_lock = threading.Lock()

# Chrome refuses to start against a profile dir it thinks is already in use,
# and reports that as an opaque "Chrome instance exited" session-creation
# failure rather than a clear "profile locked" error. If this process (or a
# previous crashed/killed run of it) left one of these behind, Chrome will
# never get past that check on its own - clear them before every launch
# attempt. Safe here because this profile dir is dedicated to this one
# service; nothing else should ever be using it concurrently.
_SINGLETON_FILES = ("SingletonLock", "SingletonCookie", "SingletonSocket")


def _clear_stale_singleton_files() -> None:
    for name in _SINGLETON_FILES:
        path = os.path.join(settings.chrome_profile_dir, name)
        if os.path.islink(path) or os.path.exists(path):
            os.remove(path)


def get_driver() -> webdriver.Chrome:
    global _driver
    with _lock:
        if _driver is None:
            _clear_stale_singleton_files()
            options = Options()
            # Deliberately NOT headless - see README for why.
            options.add_argument(f"--user-data-dir={settings.chrome_profile_dir}")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            # /dev/shm is often tiny on fresh Linux VMs/mini PCs regardless of
            # total system RAM, and Chrome's renderer process crashes hard
            # (with no useful error message) when it runs out of that shared
            # memory. Harmless no-op on macOS. See crawler_agent/README.md.
            options.add_argument("--disable-dev-shm-usage")
            _driver = webdriver.Chrome(options=options)
            _driver.set_page_load_timeout(settings.page_load_timeout_seconds)
        return _driver


def shutdown_driver() -> None:
    global _driver
    with _lock:
        if _driver is not None:
            _driver.quit()
            _driver = None
