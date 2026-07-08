"""Finds candidate manufacturers/suppliers for NSNs - plain HTTP, no browser
(see nsn_supplier_http.py for the verified source and structure).

Modes:
  {"nsn": "5310-00-612-9969"}
      -> {"nsn", "suppliers": [...], "part_numbers": [...]}  (single)
  {"targets": [{"solicitation_id": 12, "nsn": "..."}, ...]}
      -> {"bulk": [{"solicitation_id", "nsn", "suppliers", "part_numbers"}]}
Bulk reuses one HTTP session across all NSNs and paces requests politely.
"""
import time
from typing import Any

import requests

from ..nsn_supplier_http import lookup_suppliers

BULK_DELAY_SECONDS = 0.5


def run(params: dict[str, Any]) -> dict[str, Any]:
    targets = params.get("targets")
    if targets:
        session = requests.Session()
        bulk = []
        for target in targets:
            nsn = target.get("nsn")
            if not nsn:
                continue
            found = lookup_suppliers(nsn, session=session)
            bulk.append(
                {
                    "solicitation_id": target.get("solicitation_id"),
                    "nsn": nsn,
                    "suppliers": found["suppliers"],
                    "part_numbers": found["part_numbers"],
                }
            )
            time.sleep(BULK_DELAY_SECONDS)
        return {"bulk": bulk}

    nsn = params.get("nsn")
    if not nsn:
        raise ValueError("nsn_marketplace job requires 'nsn' or 'targets'")
    return lookup_suppliers(nsn)
