"""Loose, pattern-based extraction used instead of exact CSS selectors for
result parsing - we don't have a way to inspect either site's live DOM ahead
of time, and exact selectors are too brittle to guess correctly. Scanning
for recognizable patterns (NSN format, SAM.gov's stable opportunity URL
shape) works regardless of the surrounding markup, at the cost of messier
titles/context than a hand-tuned scraper would produce.
"""
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

# Federal Supply Class (4 digits) + 9-digit item identifier - the standard
# NSN format, independent of any one site's markup.
NSN_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{3}-\d{4}\b")


def scan_for_nsn_items(html: str, base_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    seen_nsns = set()

    for text_node in soup.find_all(string=NSN_PATTERN):
        match = NSN_PATTERN.search(text_node)
        if not match:
            continue
        nsn = match.group()
        if nsn in seen_nsns:
            continue
        seen_nsns.add(nsn)

        # Walk up a few levels from the raw text node to a container likely
        # to hold the rest of the row/card (title, link, etc.).
        container = text_node.parent
        for _ in range(4):
            if container is None:
                break
            if container.find("a") or len(container.get_text(strip=True)) > len(nsn) + 20:
                break
            container = container.parent

        link = container.find("a") if container else None
        href = link.get("href") if link else None
        raw_url = urljoin(base_url, href) if href else None
        title = container.get_text(" ", strip=True)[:300] if container else nsn

        items.append(
            {
                "solicitation_id": href or nsn,
                "nsn": nsn,
                "title": title,
                "description": None,
                "qty": None,
                "raw_url": raw_url,
                "specs": {},
            }
        )

    return items


def scan_for_links_matching(html: str, base_url: str, href_pattern: "re.Pattern[str]") -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    seen_hrefs = set()

    for link in soup.find_all("a", href=href_pattern):
        href = link.get("href")
        if not href or href in seen_hrefs:
            continue
        seen_hrefs.add(href)

        # Prefer the link's own text; fall back to its parent container's
        # text if the link itself is just an icon/empty wrapper.
        title = link.get_text(" ", strip=True)
        if not title and link.parent:
            title = link.parent.get_text(" ", strip=True)[:300]

        items.append(
            {
                "solicitation_id": href,
                "nsn": None,
                "title": title or href,
                "description": None,
                "qty": None,
                "raw_url": urljoin(base_url, href),
                "specs": {},
            }
        )

    return items
