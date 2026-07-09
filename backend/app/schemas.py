from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class SolicitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    solicitation_id: str
    nsn: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    qty: Optional[int] = None
    naics_code: Optional[str] = None
    set_aside_type: Optional[str] = None
    is_sdvosb: bool
    close_date: Optional[datetime] = None
    specs: Optional[dict[str, Any]] = None
    raw_url: Optional[str] = None
    status: str
    created_at: datetime
    nmr_may_apply: bool = False
    price_stats: Optional[dict[str, Any]] = None
    price_source: Optional[str] = None
    focus_score: Optional[float] = None
    focus_reason: Optional[str] = None


class PriceLookupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: Optional[str] = None
    stats: Optional[dict[str, Any]] = None
    awards: Optional[list[dict[str, Any]]] = None
    created_at: datetime


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    cage_code: Optional[str] = None
    source_marketplace: Optional[str] = None
    contact_email: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None


class SupplierMatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    solicitation_id: int
    supplier_id: int
    matched_nsn: Optional[str] = None
    source_page_url: Optional[str] = None
    scraped_price: Optional[float] = None
    created_at: datetime
    supplier: SupplierOut


class OutreachDraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_match_id: int
    draft_subject: str
    draft_body: str
    status: str
    sent_at: Optional[datetime] = None
    created_at: datetime


class OutreachDraftUpdate(BaseModel):
    draft_subject: Optional[str] = None
    draft_body: Optional[str] = None
    status: Optional[str] = None


class BidDraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    solicitation_id: int
    cost_basis: Optional[float] = None
    suggested_markup_pct: Optional[float] = None
    suggested_price: Optional[float] = None
    benchmark_award_price: Optional[float] = None
    status: str
    submitted_at: Optional[datetime] = None
    created_at: datetime


class BidDraftUpdate(BaseModel):
    cost_basis: Optional[float] = None
    suggested_markup_pct: Optional[float] = None
    suggested_price: Optional[float] = None
    status: Optional[str] = None


class CrawlJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: str
    type: str
    status: str
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
