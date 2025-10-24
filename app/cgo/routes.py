import logging
import os
import time
from time import perf_counter
from typing import Any, Dict, Optional, Union
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from tenacity import RetryCallState, retry, stop_after_attempt, wait_exponential

from app.infra import JobStore
from app.metrics import record_cgo_job_status
from app.ops.alerts import send_alert

logger = logging.getLogger(__name__)

router = APIRouter()


class MarketingCampaignRequest(BaseModel):
    job_id: Optional[str] = None


class MarketingCampaignStatus(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None


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


def _log_retry_attempt(retry_state: RetryCallState) -> None:
    job_id: Optional[str] = None
    if retry_state.args:
        job_id = retry_state.args[0]
    elif "job_id" in retry_state.kwargs:
        job_id = retry_state.kwargs["job_id"]

    logger.info(
        {
            "event": "retry",
            "job_id": job_id,
            "attempt": retry_state.attempt_number,
        }
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(), reraise=True, before=_log_retry_attempt)
def _execute_marketing_campaign(job_id: str) -> Any:
    from agents.cgo_crew import cgo_crew

    return cgo_crew.kickoff(inputs={})


async def _run_marketing_campaign_job(job_store: JobStore, job_id: str) -> None:
    """Execute the CGO Crew job and persist the result via the configured store."""

    logger.info({"event": "cgo_start", "job_id": job_id})
    record_cgo_job_status("running")
    slo_threshold = _resolve_slo_threshold()
    slo_timer_start = time.monotonic()
    start_time = perf_counter()

    try:
        result = _execute_marketing_campaign(job_id)
    except Exception as exc:  # pragma: no cover - safeguard for unexpected issues
        duration = perf_counter() - start_time
        await job_store.set_status(job_id, "failed", {"error": str(exc)})
        record_cgo_job_status("failed", duration)
        logger.exception("CGO marketing campaign job failed", extra={"job_id": job_id})
        send_alert("job_failed", {"job_id": job_id, "reason": str(exc)})
        _check_job_duration(job_id, slo_timer_start, slo_threshold)
        logger.info({"event": "cgo_done", "job_id": job_id, "status": "failed"})
        return

    await job_store.set_status(job_id, "done", result)
    duration = perf_counter() - start_time
    record_cgo_job_status("done", duration)
    _check_job_duration(job_id, slo_timer_start, slo_threshold)
    logger.info({"event": "cgo_done", "job_id": job_id, "status": "done"})


@router.post(
    "/run-marketing-campaign",
    response_model=MarketingCampaignStatus,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_marketing_campaign(
    request: Request,
    background_tasks: BackgroundTasks,
    payload: Optional[MarketingCampaignRequest] = None,
) -> Union[MarketingCampaignStatus, JSONResponse]:
    """Эндпоинт для CGO-AI (MAF), чтобы запустить CGO-Crew (CrewAI)."""

    job_store: JobStore = request.app.state.job_store
    if payload is None:
        payload = MarketingCampaignRequest()

    requested_job_id = payload.job_id
    if requested_job_id:
        existing_job = await job_store.get(requested_job_id)
        if existing_job is not None:
            response_payload = MarketingCampaignStatus(
                status=existing_job.get("status", "unknown"),
                job_id=requested_job_id,
                result=existing_job.get("result"),
            )
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=response_payload.model_dump(),
            )

    job_id = requested_job_id or str(uuid4())
    await job_store.create(
        job_id,
        {
            "type": "marketing_campaign",
            "payload": payload.model_dump(exclude_none=True),
        },
    )
    await job_store.set_status(job_id, "running", None)
    record_cgo_job_status("accepted")

    background_tasks.add_task(_run_marketing_campaign_job, job_store, job_id)

    return MarketingCampaignStatus(job_id=job_id, status="accepted")


@router.get(
    "/jobs/{job_id}",
    response_model=MarketingCampaignStatus,
    status_code=status.HTTP_200_OK,
)
async def get_job_status(request: Request, job_id: str) -> MarketingCampaignStatus:
    job_store: JobStore = request.app.state.job_store
    job = await job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return MarketingCampaignStatus(
        job_id=job_id,
        status=job.get("status", "unknown"),
        result=job.get("result"),
    )
