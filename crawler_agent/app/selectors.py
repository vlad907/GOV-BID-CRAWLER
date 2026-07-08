"""CSS selectors for sites still crawled via Selenium.

DIBBS and SAM.gov no longer use Selenium or selectors at all - both are
fetched over plain HTTP against verified structures (see dibbs_http.py and
jobs/sam_search.py). Only the NSN marketplace lookup still drives a real
browser, and its selectors below remain unverified best-effort guesses to
correct on the first real run.
"""

NSN_MARKETPLACE = {
    "search_input": "input[name='nsn'], input#nsn-search",
    "search_submit": "button[type='submit'], input[type='submit']",
    "result_row": ".supplier-result, .listing-row",
    "result_supplier_name": ".supplier-name, .company-name",
    "result_cage_code": ".cage-code",
    "result_price": ".price",
    "result_link": "a",
}
