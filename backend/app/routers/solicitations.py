from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..services.nmr import nmr_may_apply

router = APIRouter(prefix="/api/solicitations", tags=["solicitations"])


def _to_out(sol: models.Solicitation) -> schemas.SolicitationOut:
    out = schemas.SolicitationOut.model_validate(sol)
    unit_price = (sol.specs or {}).get("unit_price") if sol.specs else None
    estimated_value = unit_price * sol.qty if unit_price and sol.qty else None
    out.nmr_may_apply = nmr_may_apply(sol.set_aside_type, estimated_value)
    return out


@router.get("", response_model=list[schemas.SolicitationOut])
def list_solicitations(
    source: Optional[str] = None,
    set_aside_type: Optional[str] = None,
    is_sdvosb: Optional[bool] = None,
    nsn: Optional[str] = None,
    q: Optional[str] = None,
    active_only: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(models.Solicitation)
    if source:
        query = query.filter(models.Solicitation.source == source)
    if set_aside_type:
        query = query.filter(models.Solicitation.set_aside_type == set_aside_type)
    if is_sdvosb is not None:
        query = query.filter(models.Solicitation.is_sdvosb == is_sdvosb)
    if nsn:
        query = query.filter(models.Solicitation.nsn.contains(nsn))
    if q:
        query = query.filter(
            (models.Solicitation.title.contains(q))
            | (models.Solicitation.description.contains(q))
        )
    if active_only:
        query = query.filter(
            (models.Solicitation.close_date.is_(None))
            | (models.Solicitation.close_date >= datetime.utcnow())
        )
    results = query.order_by(models.Solicitation.created_at.desc()).all()
    return [_to_out(s) for s in results]


@router.get("/{solicitation_id}", response_model=schemas.SolicitationOut)
def get_solicitation(solicitation_id: int, db: Session = Depends(get_db)):
    sol = db.get(models.Solicitation, solicitation_id)
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitation not found")
    return _to_out(sol)


@router.get("/{solicitation_id}/matches", response_model=list[schemas.SupplierMatchOut])
def get_solicitation_matches(solicitation_id: int, db: Session = Depends(get_db)):
    sol = db.get(models.Solicitation, solicitation_id)
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitation not found")
    return sol.supplier_matches


@router.get("/{solicitation_id}/bid-drafts", response_model=list[schemas.BidDraftOut])
def get_solicitation_bid_drafts(solicitation_id: int, db: Session = Depends(get_db)):
    sol = db.get(models.Solicitation, solicitation_id)
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitation not found")
    return sol.bid_drafts
