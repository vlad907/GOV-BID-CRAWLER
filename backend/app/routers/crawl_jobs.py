from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..services import crawler_client
from ..services.crawler_client import CrawlerAgentError
from ..services.ingest import (
    ingest_nsn_marketplace,
    ingest_nsn_marketplace_bulk,
    ingest_price_history,
    ingest_price_history_bulk,
    ingest_solicitation_search,
)

router = APIRouter(prefix="/api/crawl-jobs", tags=["crawl-jobs"])

# job type -> source value stored on the resulting Solicitation rows
SEARCH_JOB_SOURCES = {"dibbs_search": "dibbs", "sam_search": "sam"}


class CrawlJobCreate(BaseModel):
    type: str  # "dibbs_search" | "sam_search" | "nsn_marketplace"
    params: dict[str, Any] = {}
    # for nsn_marketplace jobs, which solicitation to attach matches to
    solicitation_id: Optional[int] = None


@router.post("", response_model=schemas.CrawlJobOut)
def create_crawl_job(payload: CrawlJobCreate, db: Session = Depends(get_db)):
    params = dict(payload.params)
    if payload.solicitation_id is not None:
        params["_solicitation_id"] = payload.solicitation_id

    try:
        job_id = crawler_client.submit_job(payload.type, params)
    except CrawlerAgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    job = models.CrawlJob(job_id=job_id, type=payload.type, params=params, status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


class BulkRequest(BaseModel):
    source: Optional[str] = None
    is_sdvosb: Optional[bool] = None
    active_only: bool = True
    only_missing: bool = True  # skip solicitations already looked up
    limit: int = 50


def _filtered_solicitations(payload: BulkRequest, db: Session) -> list[models.Solicitation]:
    from datetime import datetime

    query = db.query(models.Solicitation)
    if payload.source:
        query = query.filter(models.Solicitation.source == payload.source)
    if payload.is_sdvosb is not None:
        query = query.filter(models.Solicitation.is_sdvosb == payload.is_sdvosb)
    if payload.active_only:
        query = query.filter(
            (models.Solicitation.close_date.is_(None))
            | (models.Solicitation.close_date >= datetime.utcnow())
        )
    return query.order_by(models.Solicitation.created_at.desc()).all()


def _submit_bulk_job(job_type: str, targets: list[dict], db: Session) -> models.CrawlJob:
    try:
        job_id = crawler_client.submit_job(job_type, {"targets": targets})
    except CrawlerAgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    job = models.CrawlJob(
        job_id=job_id, type=job_type, params={"target_count": len(targets)}, status="pending"
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.post("/find-suppliers-bulk", response_model=schemas.CrawlJobOut)
def find_suppliers_bulk(payload: BulkRequest, db: Session = Depends(get_db)):
    """Fans a supplier lookup across many NSN-bearing solicitations at once."""
    targets = []
    for sol in _filtered_solicitations(payload, db):
        if not sol.nsn:
            continue
        if payload.only_missing and sol.supplier_matches:
            continue
        targets.append({"solicitation_id": sol.id, "nsn": sol.nsn})
        if len(targets) >= payload.limit:
            break

    if not targets:
        raise HTTPException(
            status_code=400,
            detail="No solicitations with an NSN need suppliers (try unchecking 'only missing').",
        )
    return _submit_bulk_job("nsn_marketplace", targets, db)


@router.post("/find-prices-bulk", response_model=schemas.CrawlJobOut)
def find_prices_bulk(payload: BulkRequest, db: Session = Depends(get_db)):
    """Fans a historical-price lookup across many solicitations at once -
    by NSN (DIBBS awards) or, lacking one, by PSC (USASpending)."""
    targets = []
    for sol in _filtered_solicitations(payload, db):
        if payload.only_missing and sol.price_lookup is not None:
            continue
        psc = (sol.specs or {}).get("psc") if sol.specs else None
        if not sol.nsn and not psc:
            continue
        targets.append({"solicitation_id": sol.id, "nsn": sol.nsn, "psc": psc})
        if len(targets) >= payload.limit:
            break

    if not targets:
        raise HTTPException(
            status_code=400,
            detail="No solicitations need a price lookup (try unchecking 'only missing').",
        )
    return _submit_bulk_job("price_history", targets, db)


@router.get("/{job_id}", response_model=schemas.CrawlJobOut)
def get_crawl_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(models.CrawlJob).filter(models.CrawlJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Unknown job_id")

    if job.status in ("done", "error"):
        return job

    try:
        remote = crawler_client.get_job_status(job_id)
    except CrawlerAgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    job.status = remote["status"]
    if remote["status"] == "error":
        job.error = remote.get("error")
    elif remote["status"] == "done":
        result = remote.get("result") or {}
        job.result = result
        if job.type in SEARCH_JOB_SOURCES:
            ingest_solicitation_search(db, SEARCH_JOB_SOURCES[job.type], result)
        elif job.type == "nsn_marketplace":
            if "bulk" in result:
                ingest_nsn_marketplace_bulk(db, result)
            else:
                solicitation_id = (job.params or {}).get("_solicitation_id")
                if solicitation_id is not None:
                    ingest_nsn_marketplace(db, solicitation_id, result)
        elif job.type == "price_history":
            if "bulk" in result:
                ingest_price_history_bulk(db, result)
            else:
                solicitation_id = (job.params or {}).get("_solicitation_id")
                if solicitation_id is not None:
                    ingest_price_history(db, solicitation_id, result)

    db.commit()
    db.refresh(job)
    return job
