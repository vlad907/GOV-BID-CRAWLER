from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..services import crawler_client
from ..services.crawler_client import CrawlerAgentError
from ..services.ingest import ingest_nsn_marketplace, ingest_solicitation_search

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
            solicitation_id = (job.params or {}).get("_solicitation_id")
            if solicitation_id is not None:
                ingest_nsn_marketplace(db, solicitation_id, result)

    db.commit()
    db.refresh(job)
    return job
