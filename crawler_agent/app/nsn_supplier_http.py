"""Plain-HTTP lookup of manufacturers/approved sources for an NSN - no
browser needed (the old Selenium version kept crashing Chrome on Linux).

Verified live against nationalstocknumber.info (July 2026) with curl:
  GET https://nationalstocknumber.info/national-stock-number/<13-digit-nsn>
Returns an HTML datasheet with:
  - <h1> nomenclature
  - an <h2>CAGE Codes</h2> section whose following <dl> pairs <dt> CAGE
    code with <dd> company name (these are the manufacturers / approved
    sources you'd reach out to for wholesale pricing)
  - a Cross Reference section listing manufacturer part numbers

CAGE codes identify the *company*; a distributor can quote a part by CAGE +
part number even when the OEM itself won't sell direct.
"""
import re

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://nationalstocknumber.info/national-stock-number"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/149.0 Safari/537.36"
)
PART_NUMBER_RE = re.compile(r"^[A-Z0-9][A-Z0-9\-]{3,}$")


def _digits(nsn: str) -> str:
    return "".join(ch for ch in str(nsn) if ch.isdigit())


def lookup_suppliers(nsn: str, session: requests.Session | None = None) -> dict:
    """Returns {"nsn", "nomenclature", "suppliers": [{cage_code, name, url}],
    "part_numbers": [...]} for one NSN. Never raises on a missing page -
    returns empty lists so a bulk sweep isn't derailed by one bad NSN."""
    sess = session or requests.Session()
    sess.headers.setdefault("User-Agent", USER_AGENT)
    url = f"{BASE_URL}/{_digits(nsn)}"

    try:
        resp = sess.get(url, timeout=20)
    except requests.RequestException:
        return {"nsn": nsn, "nomenclature": None, "suppliers": [], "part_numbers": [], "url": url}

    if resp.status_code != 200:
        return {"nsn": nsn, "nomenclature": None, "suppliers": [], "part_numbers": [], "url": url}

    soup = BeautifulSoup(resp.text, "html.parser")

    h1 = soup.find("h1")
    nomenclature = h1.get_text(strip=True) if h1 else None

    suppliers = []
    cage_heading = soup.find(lambda t: t.name == "h2" and "CAGE" in t.get_text())
    if cage_heading:
        dl = cage_heading.find_next("dl")
        if dl:
            for dt in dl.find_all("dt"):
                dd = dt.find_next_sibling("dd")
                cage = dt.get_text(strip=True)
                if not cage:
                    continue
                suppliers.append(
                    {
                        "cage_code": cage,
                        "name": dd.get_text(" ", strip=True) if dd else cage,
                        "url": url,
                        "source_marketplace": "nationalstocknumber.info",
                        "contact_email": None,
                        "price": None,
                    }
                )

    part_numbers = []
    xref_heading = soup.find(lambda t: t.name == "h2" and "Cross Reference" in t.get_text())
    if xref_heading:
        section = xref_heading.find_parent("section") or xref_heading.parent
        for token in section.get_text(" ", strip=True).split():
            if PART_NUMBER_RE.match(token) and not token.isdigit() and token != _digits(nsn):
                if token not in part_numbers:
                    part_numbers.append(token)

    return {
        "nsn": nsn,
        "nomenclature": nomenclature,
        "suppliers": suppliers,
        "part_numbers": part_numbers[:15],
        "url": url,
    }
