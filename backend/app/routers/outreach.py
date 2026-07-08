from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..services.outreach_templates import render_outreach_draft

router = APIRouter(prefix="/api/outreach", tags=["outreach"])


@router.post("/generate/{supplier_match_id}", response_model=schemas.OutreachDraftOut)
def generate_outreach_draft(supplier_match_id: int, db: Session = Depends(get_db)):
    match = db.get(models.SupplierMatch, supplier_match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Supplier match not found")

    sol = match.solicitation
    subject, body = render_outreach_draft(
        supplier_name=match.supplier.name,
        nsn=match.matched_nsn or sol.nsn,
        title=sol.title,
        qty=sol.qty,
        specs=sol.specs,
        close_date=sol.close_date.isoformat() if sol.close_date else None,
    )

    draft = models.OutreachDraft(
        supplier_match_id=supplier_match_id,
        draft_subject=subject,
        draft_body=body,
        status="draft",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


@router.get("", response_model=list[schemas.OutreachDraftOut])
def list_outreach_drafts(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.OutreachDraft)
    if status:
        query = query.filter(models.OutreachDraft.status == status)
    return query.order_by(models.OutreachDraft.created_at.desc()).all()


@router.patch("/{draft_id}", response_model=schemas.OutreachDraftOut)
def update_outreach_draft(
    draft_id: int, payload: schemas.OutreachDraftUpdate, db: Session = Depends(get_db)
):
    draft = db.get(models.OutreachDraft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Outreach draft not found")

    if payload.draft_subject is not None:
        draft.draft_subject = payload.draft_subject
    if payload.draft_body is not None:
        draft.draft_body = payload.draft_body
    if payload.status is not None:
        draft.status = payload.status
        if payload.status == "sent":
            draft.sent_at = datetime.utcnow()

    db.commit()
    db.refresh(draft)
    return draft
