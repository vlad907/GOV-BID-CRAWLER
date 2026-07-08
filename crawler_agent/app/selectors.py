"""All CSS selectors / XPaths for external sites, centralized so they're easy
to find and fix in one place when a site's markup doesn't match reality.

None of these have been verified against the live sites (see README) - treat
every value here as a first guess to confirm/correct during the first real
run.
"""

DIBBS = {
    # DoD warning/consent interstitial shown before the real app loads.
    "consent_button": "input[type='submit'], button#accept, a#accept",
    # RFQ search form (dibbs.bsm.dla.mil/RFQ/)
    "search_input": "input#txtSearch, input[name='ttype']",
    "search_submit": "input[type='submit'][value*='Search'], button[type='submit']",
    # Results table rows
    "result_row": "table.rfq-results tr, table#gvResults tr",
    "result_nsn": ".nsn, td:nth-child(2)",
    "result_title": ".description, td:nth-child(3)",
    "result_solicitation_id": ".solicitation-number, td:nth-child(1)",
    "result_qty": ".qty, td:nth-child(4)",
    "result_close_date": ".close-date, td:nth-child(5)",
    "result_link": "a",
}

SAM_GOV = {
    # sam.gov's opportunity search is a client-rendered SPA - Selenium waits
    # for result cards to actually appear in the DOM after JS runs.
    "result_card": "ct-app-search-result, .usa-card, li[data-notice-id]",
    "result_solicitation_id": ".notice-id, .solicitation-number",
    "result_title": "h3, .card-title, a.title-link",
    "result_naics": ".naics",
    "result_set_aside": ".set-aside, .type-of-set-aside",
    "result_close_date": ".response-date, .deadline",
    "result_link": "a",
}

NSN_MARKETPLACE = {
    "search_input": "input[name='nsn'], input#nsn-search",
    "search_submit": "button[type='submit'], input[type='submit']",
    "result_row": ".supplier-result, .listing-row",
    "result_supplier_name": ".supplier-name, .company-name",
    "result_cage_code": ".cage-code",
    "result_price": ".price",
    "result_link": "a",
}
