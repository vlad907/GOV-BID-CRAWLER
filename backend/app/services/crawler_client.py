"""HTTP client for the crawler_agent service running on the second machine.

Protocol: backend POSTs a job, then polls GET /jobs/{id} until status is
done/error. The crawler agent has no persistent DB of its own; the backend
is the single source of truth once a job result comes back.
"""
from typing import Any, Optional

import requests

from ..config import settings


class CrawlerAgentError(RuntimeError):
    pass


def submit_job(job_type: str, params: dict[str, Any]) -> str:
    resp = requests.post(
        f"{settings.crawler_agent_url}/jobs",
        json={"type": job_type, "params": params},
        timeout=15,
    )
    if resp.status_code != 200:
        raise CrawlerAgentError(f"Crawler agent rejected job: {resp.status_code} {resp.text[:300]}")
    return resp.json()["job_id"]


def get_job_status(job_id: str) -> dict[str, Any]:
    resp = requests.get(f"{settings.crawler_agent_url}/jobs/{job_id}", timeout=15)
    if resp.status_code == 404:
        raise CrawlerAgentError(f"Unknown job_id {job_id}")
    if resp.status_code != 200:
        raise CrawlerAgentError(f"Crawler agent error: {resp.status_code} {resp.text[:300]}")
    return resp.json()
