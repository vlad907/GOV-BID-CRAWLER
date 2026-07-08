"""Bridges the FastAPI process to a dedicated worker subprocess that owns
the Selenium driver and runs jobs sequentially (one visible Chrome window at
a time). See worker_process.py for why Selenium runs in a separate process
rather than a thread.

No persistence here on purpose - the backend is the single source of truth
once a job's result is polled (see backend/app/services/ingest.py). If this
process restarts mid-job, the backend will just see that job_id as unknown
and can resubmit.
"""
import threading
import uuid
from dataclasses import dataclass
from typing import Any

from .worker_process import HANDLERS, start_worker_process


@dataclass
class Job:
    job_id: str
    type: str
    params: dict[str, Any]
    status: str = "pending"  # pending | running | done | error
    result: dict[str, Any] | None = None
    error: str | None = None


class JobQueue:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._process, self._task_queue, self._result_queue = start_worker_process()
        self._collector = threading.Thread(target=self._collect_results, daemon=True)
        self._collector.start()

    def submit(self, job_type: str, params: dict[str, Any]) -> str:
        if job_type not in HANDLERS:
            raise ValueError(f"Unknown job type: {job_type}")
        job_id = uuid.uuid4().hex
        with self._lock:
            self._jobs[job_id] = Job(job_id=job_id, type=job_type, params=params)
        self._task_queue.put((job_id, job_type, params))
        return job_id

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def _collect_results(self) -> None:
        while True:
            job_id, status, result, error = self._result_queue.get()
            with self._lock:
                job = self._jobs.get(job_id)
                if job is None:
                    continue
                job.status = status
                job.result = result
                job.error = error


job_queue = JobQueue()
