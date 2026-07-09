"""Owns the Selenium driver in a dedicated OS process, not a thread.

Kept separate from the FastAPI process mainly so a hung or crashed job
(a wedged Chrome/chromedriver) can't take the API down with it. On shutdown,
this process quits the driver cleanly (see the SIGTERM handler below) so a
restart doesn't leave an orphaned Chrome holding the profile dir's lock
files - if that ever does happen anyway (e.g. a hard kill), browser.py
clears stale lock files before the next launch, since a leftover lock is
what actually causes Selenium's opaque "Chrome instance exited" error.
"""
import multiprocessing
import signal
from multiprocessing.context import SpawnContext
from typing import Any

from .browser import shutdown_driver
from .jobs import dibbs_search, nsn_marketplace, price_history, sam_search

HANDLERS = {
    "dibbs_search": dibbs_search.run,
    "sam_search": sam_search.run,
    "nsn_marketplace": nsn_marketplace.run,
    "price_history": price_history.run,
}


def _worker_loop(task_queue: Any, result_queue: Any) -> None:
    def _handle_shutdown(signum: int, frame: Any) -> None:
        shutdown_driver()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    while True:
        job_id, job_type, params = task_queue.get()
        result_queue.put((job_id, "running", None, None))

        handler = HANDLERS.get(job_type)
        if handler is None:
            result_queue.put((job_id, "error", None, f"Unknown job type: {job_type}"))
            continue

        try:
            result = handler(params)
            result_queue.put((job_id, "done", result, None))
        except Exception as exc:  # noqa: BLE001 - surface any scrape failure to the caller
            result_queue.put((job_id, "error", None, str(exc)))


def start_worker_process() -> tuple[multiprocessing.Process, Any, Any]:
    ctx: SpawnContext = multiprocessing.get_context("spawn")
    task_queue = ctx.Queue()
    result_queue = ctx.Queue()
    process = ctx.Process(target=_worker_loop, args=(task_queue, result_queue), daemon=True)
    process.start()
    return process, task_queue, result_queue
