import logging
from time import perf_counter
from typing import Any, Dict
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from app.metrics import record_cgo_job_status

logger = logging.getLogger(__name__)

router = APIRouter()


JOBS: Dict[str, Dict[str, Any]] = {}


def _mark_job_status(job_id: str, status: str, result: Any = None) -> None:
    JOBS[job_id] = {"status": status, "result": result}


def _run_marketing_campaign_job(job_id: str) -> None:
    """Execute the CGO Crew job and persist the result in the in-memory registry."""
    from agents.cgo_crew import cgo_crew
    logger.info({"event": "cgo_start", "job_id": job_id})
    record_cgo_job_status("running")
    start_time = perf_counter()
    try:
        result = cgo_crew.kickoff(inputs={})
    except Exception as exc:  # pragma: no cover - safeguard for unexpected issues
        duration = perf_counter() - start_time
        _mark_job_status(job_id, "failed", {"error": str(exc)})
        record_cgo_job_status("failed", duration)
        logger.exception("CGO marketing campaign job failed", extra={"job_id": job_id})
        logger.info({"event": "cgo_done", "job_id": job_id, "status": "failed"})
        return

    duration = perf_counter() - start_time
    _mark_job_status(job_id, "done", result)
    record_cgo_job_status("done", duration)
    logger.info({"event": "cgo_done", "job_id": job_id, "status": "done"})


@router.post("/run-marketing-campaign")
async def run_marketing_campaign(background_tasks: BackgroundTasks):
    """Эндпоинт для CGO-AI (MAF), чтобы запустить CGO-Crew (CrewAI)."""

    job_id = str(uuid4())
    _mark_job_status(job_id, "running", None)
    record_cgo_job_status("accepted")

    background_tasks.add_task(_run_marketing_campaign_job, job_id)

    return JSONResponse(
        status_code=202,
        content={"status": "accepted", "job_id": job_id},
    )


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> Dict[str, Any]:
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return {"status": job["status"], "result": job.get("result")}
