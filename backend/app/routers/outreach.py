from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..services import email_service
from ..services.email_service import EmailError, EmailNotConfigured
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

    if payload.recipient_email is not None:
        draft.recipient_email = payload.recipient_email
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


@router.post("/{draft_id}/send", response_model=schemas.OutreachDraftOut)
def send_outreach_draft(draft_id: int, db: Session = Depends(get_db)):
    """Human-triggered send: fires only when the user clicks Send in the UI."""
    draft = db.get(models.OutreachDraft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Outreach draft not found")
    if not draft.recipient_email:
        raise HTTPException(status_code=400, detail="Set a recipient email before sending.")

    try:
        message_id = email_service.send_email(
            draft.recipient_email, draft.draft_subject, draft.draft_body
        )
    except EmailNotConfigured as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EmailError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    draft.message_id = message_id
    draft.status = "sent"
    draft.sent_at = datetime.utcnow()
    db.commit()
    db.refresh(draft)
    return draft


@router.post("/sync-replies")
def sync_replies(db: Session = Depends(get_db)):
    """Pulls supplier replies from the inbox, threads them to the sent draft,
    and extracts a quoted price/lead time. Read-only on the mailbox."""
    sent = (
        db.query(models.OutreachDraft)
        .filter(models.OutreachDraft.message_id.isnot(None))
        .all()
    )
    by_message_id = {d.message_id: d for d in sent}
    if not by_message_id:
        return {"new_replies": 0, "detail": "No sent emails to match replies against yet."}

    try:
        incoming = email_service.fetch_replies(set(by_message_id.keys()))
    except EmailNotConfigured as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EmailError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    new_count = 0
    for item in incoming:
        draft = by_message_id.get(item["in_reply_to"])
        if not draft:
            continue
        # dedupe on the reply's own Message-ID
        exists = (
            db.query(models.EmailReply)
            .filter(models.EmailReply.imap_message_id == item["imap_message_id"])
            .first()
        )
        if exists:
            continue

        price, lead_time = email_service.extract_quote(item["body"])
        db.add(
            models.EmailReply(
                outreach_draft_id=draft.id,
                from_addr=item["from_addr"],
                subject=item["subject"],
                body=item["body"],
                imap_message_id=item["imap_message_id"],
                extracted_price=price,
                extracted_lead_time=lead_time,
                received_at=item["received_at"],
            )
        )
        draft.status = "replied"
        new_count += 1

    db.commit()
    return {"new_replies": new_count}
