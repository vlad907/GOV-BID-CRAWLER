"""In-memory job queue. One worker thread processes jobs sequentially so
only one visible Chrome window is ever driving at a time.

No persistence here on purpose - the backend is the single source of truth
once a job's result is polled (see backend/app/services/ingest.py). If this
process restarts mid-job, the backend will just see that job_id as unknown
and can resubmit.
"""
import queue
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

JobHandler = Callable[[dict[str, Any]], dict[str, Any]]


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
        self._queue: queue.Queue[str] = queue.Queue()
        self._handlers: dict[str, JobHandler] = {}
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def register(self, job_type: str, handler: JobHandler) -> None:
        self._handlers[job_type] = handler

    def submit(self, job_type: str, params: dict[str, Any]) -> str:
        if job_type not in self._handlers:
            raise ValueError(f"Unknown job type: {job_type}")
        job_id = uuid.uuid4().hex
        with self._lock:
            self._jobs[job_id] = Job(job_id=job_id, type=job_type, params=params)
        self._queue.put(job_id)
        return job_id

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def _run(self) -> None:
        while True:
            job_id = self._queue.get()
            with self._lock:
                job = self._jobs[job_id]
                job.status = "running"
            try:
                handler = self._handlers[job.type]
                result = handler(job.params)
                with self._lock:
                    job.result = result
                    job.status = "done"
            except Exception as exc:  # noqa: BLE001 - surface any scrape failure to the caller
                with self._lock:
                    job.error = str(exc)
                    job.status = "error"


job_queue = JobQueue()
