"""Lightweight SBA Non-Manufacturer Rule (NMR) flagging.

Not a compliance engine — just surfaces a warning badge so a human can check
whether a small-business manufacturer or waiver is required before bidding as
a reseller. See FAR 19.505 and https://www.sba.gov/partners/contracting-officials/small-business-procurement/nonmanufacturer-rule
"""
from ..config import settings

SOCIOECONOMIC_SET_ASIDES = {"SDVOSB", "8A", "HUBZONE", "WOSB", "EDWOSB"}


def nmr_may_apply(set_aside_type: str | None, estimated_value: float | None) -> bool:
    if not set_aside_type or estimated_value is None:
        return False

    normalized = set_aside_type.strip().upper().replace("-", "").replace(" ", "")
    if normalized in SOCIOECONOMIC_SET_ASIDES:
        return estimated_value > settings.nmr_socioeconomic_set_aside_threshold

    if "SMALL" in normalized or normalized == "SBA":
        return estimated_value > settings.nmr_general_set_aside_threshold

    return False
