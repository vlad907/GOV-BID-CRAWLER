from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..services.markup import suggest_price

router = APIRouter(prefix="/api/bid-drafts", tags=["bid-drafts"])


class BidDraftCreate(BaseModel):
    solicitation_id: int
    benchmark_award_price: Optional[float] = None
    markup_pct: Optional[float] = None
    cost_basis: Optional[float] = None  # override; else derived from cheapest supplier match


@router.get("", response_model=list[schemas.BidDraftOut])
def list_bid_drafts(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.BidDraft)
    if status:
        query = query.filter(models.BidDraft.status == status)
    return query.order_by(models.BidDraft.created_at.desc()).all()


@router.post("", response_model=schemas.BidDraftOut)
def create_bid_draft(payload: BidDraftCreate, db: Session = Depends(get_db)):
    sol = db.get(models.Solicitation, payload.solicitation_id)
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitation not found")

    cost_basis = payload.cost_basis
    if cost_basis is None:
        priced_matches = [m.scraped_price for m in sol.supplier_matches if m.scraped_price]
        cost_basis = min(priced_matches) if priced_matches else None
    if cost_basis is None:
        raise HTTPException(
            status_code=400,
            detail="No cost basis available: provide cost_basis or add a priced supplier match first.",
        )

    # Fall back to the historical award benchmark (last, else avg) when the
    # caller didn't pass one explicitly.
    benchmark = payload.benchmark_award_price
    if benchmark is None and sol.price_lookup and sol.price_lookup.stats:
        stats = sol.price_lookup.stats
        # typical (median delivery-order price) is the robust unit benchmark
        benchmark = stats.get("typical") or stats.get("last") or stats.get("avg")

    markup_pct, suggested_price = suggest_price(cost_basis, benchmark, payload.markup_pct)

    draft = models.BidDraft(
        solicitation_id=payload.solicitation_id,
        cost_basis=cost_basis,
        suggested_markup_pct=markup_pct,
        suggested_price=suggested_price,
        benchmark_award_price=benchmark,
        status="draft",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


@router.patch("/{draft_id}", response_model=schemas.BidDraftOut)
def update_bid_draft(draft_id: int, payload: schemas.BidDraftUpdate, db: Session = Depends(get_db)):
    draft = db.get(models.BidDraft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Bid draft not found")

    for field in ("cost_basis", "suggested_markup_pct", "suggested_price"):
        value = getattr(payload, field)
        if value is not None:
            setattr(draft, field, value)

    if payload.status is not None:
        draft.status = payload.status
        if payload.status == "submitted":
            draft.submitted_at = datetime.utcnow()

    db.commit()
    db.refresh(draft)
    return draft
