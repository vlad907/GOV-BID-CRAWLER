from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .job_queue import job_queue
from .jobs import dibbs_search, nsn_marketplace, sam_search

job_queue.register("dibbs_search", dibbs_search.run)
job_queue.register("sam_search", sam_search.run)
job_queue.register("nsn_marketplace", nsn_marketplace.run)

app = FastAPI(title="Crawler Agent")


class JobCreate(BaseModel):
    type: str
    params: dict[str, Any] = {}


class JobStatusOut(BaseModel):
    job_id: str
    status: str
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None


@app.post("/jobs")
def create_job(payload: JobCreate):
    try:
        job_id = job_queue.submit(payload.type, payload.params)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job_id": job_id, "status": "pending"}


@app.get("/jobs/{job_id}", response_model=JobStatusOut)
def get_job(job_id: str):
    job = job_queue.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    return JobStatusOut(job_id=job.job_id, status=job.status, result=job.result, error=job.error)


@app.get("/health")
def health():
    return {"status": "ok"}
