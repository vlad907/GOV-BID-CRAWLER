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
}
# Result extraction for both DIBBS and SAM.gov no longer uses selectors at
# all - see extraction.py. Guessing exact CSS classes for either site's
# results wasn't reliable without being able to inspect the live DOM, so
# instead we scan the rendered page for recognizable patterns (NSN format,
# SAM.gov's stable /opp/<id>/view URLs) regardless of surrounding markup.

NSN_MARKETPLACE = {
    "search_input": "input[name='nsn'], input#nsn-search",
    "search_submit": "button[type='submit'], input[type='submit']",
    "result_row": ".supplier-result, .listing-row",
    "result_supplier_name": ".supplier-name, .company-name",
    "result_cage_code": ".cage-code",
    "result_price": ".price",
    "result_link": "a",
}
