"""Plain-HTTP client for DIBBS RFQ search - no browser needed.

Verified live against www.dibbs.bsm.dla.mil (July 2026) with curl:

- A fresh session 302s to /dodwarning.aspx (DoD consent interstitial).
  GETting that page yields ASP.NET hidden fields; POSTing them back with
  butAgree=OK marks the session consented, after which all RFQ pages
  return 200 with real data.
- Search URL shapes (all on /RFQ/RfqRecs.aspx):
    by 4-digit FSC:    ?category=fsc&TypeSrch=cq&Value=5310
    by posted date:    ?category=post&TypeSrch=dt&Value=07-06-2026
    by 13-digit NSN:   ?category=nsn&TypeSrch=cq&Value=5310006129969
- Results table id: ctl00_cph1_grdRfqSearch. Columns (verified header row):
    # | NSN/Part Number | Nomenclature | Technical Documents | Solicitation
    | RFQ/Quote Status | Purchase Request | Issued | Return By
- Total count in span#ctl00_cph1_lblRecCount ("Records Found:2038").
- The grid shows at most 50 records per query. Its ASP.NET postback paging
  rejects non-browser POSTs (ViewState/event validation bounces to the
  DIBBS error page), so callers broaden coverage by fanning out more
  queries (per FSC, per posted-date) rather than paging one query.
"""
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.dibbs.bsm.dla.mil"
RFQ_URL = f"{BASE_URL}/RFQ/RfqRecs.aspx"
AWARDS_URL = f"{BASE_URL}/Awards/AwdRecs.aspx"
AWARDS_TABLE_ID = "ctl00_cph1_grdAwardSearch"
PRICE_RE = re.compile(r"\$?([\d,]+\.\d{2})")
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/149.0 Safari/537.36"
)
TABLE_ID = "ctl00_cph1_grdRfqSearch"
REC_COUNT_ID = "ctl00_cph1_lblRecCount"
NSN_RE = re.compile(r"\b\d{4}-\d{2}-\d{3}-\d{4}\b")
QTY_RE = re.compile(r"QTY:\s*([\d,]+)")


def _hidden_fields(html: str) -> dict[str, str]:
    return {
        m.group(1): m.group(2)
        for m in re.finditer(
            r'<input type="hidden" name="([^"]+)"[^>]*value="([^"]*)"', html
        )
    }


class DibbsSession:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self._consented = False

    def _consent(self) -> None:
        warning_url = f"{BASE_URL}/dodwarning.aspx?goto=%2fRFQ%2fRfqRecs.aspx"
        resp = self.session.get(warning_url, timeout=30)
        fields = _hidden_fields(resp.text)
        if fields:
            fields["butAgree"] = "OK"
            self.session.post(
                warning_url,
                data=fields,
                headers={"Referer": warning_url},
                timeout=30,
                allow_redirects=False,
            )
        self._consented = True

    def _fetch(self, url: str, category: str, type_srch: str, value: str) -> str:
        if not self._consented:
            self._consent()
        params = {"category": category, "TypeSrch": type_srch, "Value": value}
        resp = self.session.get(url, params=params, timeout=30)
        # Session can expire back to the consent page; redo the handshake once.
        if "dodwarning" in resp.url or "butAgree" in resp.text:
            self._consented = False
            self._consent()
            resp = self.session.get(url, params=params, timeout=30)
        return resp.text

    def fetch_search_page(self, category: str, type_srch: str, value: str) -> str:
        return self._fetch(RFQ_URL, category, type_srch, value)

    def fetch_awards_page(self, nsn_digits: str) -> str:
        return self._fetch(AWARDS_URL, "nsn", "cq", nsn_digits)


def _iso_date(mmddyyyy: str) -> str | None:
    try:
        return datetime.strptime(mmddyyyy.strip(), "%m-%d-%Y").date().isoformat()
    except ValueError:
        return None


def parse_rfq_table(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id=TABLE_ID)
    if table is None:
        return []

    items = []
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 9:
            continue  # pager, header, or spacer rows
        nsn_text = cells[1].get_text(strip=True)
        if not NSN_RE.search(nsn_text):
            continue

        sol_cell = cells[4]
        sol_link = sol_cell.find("a")
        solicitation_id = sol_link.get_text(strip=True) if sol_link else sol_cell.get_text(strip=True)
        pdf_url = sol_link.get("href") if sol_link else None
        package_link = next(
            (a.get("href") for a in sol_cell.find_all("a") if "rfqrec" in (a.get("href") or "").lower()),
            None,
        )

        qty_match = QTY_RE.search(cells[6].get_text(" ", strip=True))

        items.append(
            {
                "solicitation_id": solicitation_id,
                "nsn": NSN_RE.search(nsn_text).group(),
                "title": cells[2].get_text(" ", strip=True),
                "description": None,
                "qty": int(qty_match.group(1).replace(",", "")) if qty_match else None,
                "close_date": _iso_date(cells[8].get_text(strip=True)),
                "raw_url": package_link or pdf_url,
                "specs": {
                    "technical_documents": cells[3].get_text(" ", strip=True) or None,
                    "purchase_request": cells[6].get_text(" ", strip=True) or None,
                    "issued": _iso_date(cells[7].get_text(strip=True)),
                    "solicitation_pdf": pdf_url,
                    "status": cells[5].get_text(" ", strip=True)[:40] or None,
                },
            }
        )

    return items


def parse_awards_table(html: str) -> list[dict]:
    """Historical DLA awards for an NSN. Verified column layout of
    ctl00_cph1_grdAwardSearch:
      # | Award/Basic Number | Delivery Order Number | Delivery Order Counter
      | Last Mod Posting Date | Awardee CAGE Code | Total Contract Price
      | Award Date | Posted Date | NSN/Part Number | Nomenclature
      | Purchase Request | Solicitation
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id=AWARDS_TABLE_ID)
    if table is None:
        return []

    awards = []
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 11:
            continue  # header/pager/spacer
        price_match = PRICE_RE.search(cells[6].get_text(" ", strip=True))
        if not price_match:
            continue

        award_number = cells[1].find("a")
        awards.append(
            {
                "award_number": (
                    award_number.get_text(strip=True) if award_number else cells[1].get_text(strip=True)
                ).split("»")[0].strip(),
                "awardee_cage": cells[5].get_text(strip=True) or None,
                "price": float(price_match.group(1).replace(",", "")),
                "award_date": _iso_date(cells[7].get_text(strip=True)),
                "nomenclature": cells[10].get_text(" ", strip=True) or None,
            }
        )

    return awards
