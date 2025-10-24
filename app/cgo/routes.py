import logging
import os
import time
from typing import Any, Dict
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from tenacity import RetryCallState, retry, stop_after_attempt, wait_exponential

from app.infra import JobStore

from app.metrics import record_cgo_job_status

from app.ops.alerts import send_alert

logger = logging.getLogger(__name__)

router = APIRouter()


JOBS: Dict[str, Dict[str, Any]] = {}


def _resolve_slo_threshold() -> float:
    """Return the configured latency SLO threshold in seconds."""

    value = os.getenv("SLO_JOB_SEC", "60")
    try:
        return float(value)
    except ValueError:
        logger.warning(
            {"event": "invalid_slo_config", "value": value, "default": 60},
        )
        return 60.0


def _check_job_duration(job_id: str, start_ts: float, threshold: float) -> None:
    """Emit an alert if the job execution time breached the latency SLO."""

    duration = time.monotonic() - start_ts
    if duration > threshold:
        send_alert(
            "latency_slo_miss",
            {
                "job_id": job_id,
                "duration_sec": duration,
                "threshold_sec": threshold,
            },
        )


def _run_marketing_campaign_job(job_id: str) -> None:
    """Execute the CGO Crew job and persist the result in the in-memory registry."""
    from agents.cgo_crew import cgo_crew
    logger.info({"event": "cgo_start", "job_id": job_id})
    slo_threshold = _resolve_slo_threshold()
    start_ts = time.monotonic()
    try:
        result = _execute_marketing_campaign(job_id)
    except Exception as exc:  # pragma: no cover - safeguard for unexpected issues
        duration = perf_counter() - start_time
        _mark_job_status(job_id, "failed", {"error": str(exc)})
        record_cgo_job_status("failed", duration)
        logger.exception("CGO marketing campaign job failed", extra={"job_id": job_id})
        send_alert("job_failed", {"job_id": job_id, "error": str(exc)})
        _check_job_duration(job_id, start_ts, slo_threshold)
        logger.info({"event": "cgo_done", "job_id": job_id, "status": "failed"})
        return

    JOBS[job_id] = {"status": "done", "result": result}
    _check_job_duration(job_id, start_ts, slo_threshold)
    logger.info({"event": "cgo_done", "job_id": job_id, "status": "done"})


@router.post("/run-marketing-campaign")
async def run_marketing_campaign(
    background_tasks: BackgroundTasks,
    payload: Optional[MarketingCampaignRequest] = None,
):
    """Эндпоинт для CGO-AI (MAF), чтобы запустить CGO-Crew (CrewAI)."""

    job_id = str(uuid4())
    _mark_job_status(job_id, "running", None)
    record_cgo_job_status("accepted")

    background_tasks.add_task(_run_marketing_campaign_job, job_store, job_id)

    return JSONResponse(
        status_code=202,
        content={"status": "accepted", "job_id": job_id},
    )


@router.get("/jobs/{job_id}")
async def get_job_status(request: Request, job_id: str) -> Dict[str, Any]:
    job_store: JobStore = request.app.state.job_store
    job = await job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return {"status": job.get("status"), "result": job.get("result")}
