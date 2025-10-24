import logging
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from tenacity import RetryCallState, retry, stop_after_attempt, wait_exponential

from app.infra import JobStore

logger = logging.getLogger(__name__)

router = APIRouter()


JOBS: Dict[str, Dict[str, Any]] = {}


class MarketingCampaignRequest(BaseModel):
    job_id: Optional[str] = None


def _log_retry_attempt(retry_state: RetryCallState) -> None:
    job_id: Optional[str] = None
    if retry_state.args:
        job_id = retry_state.args[0]
    elif "job_id" in retry_state.kwargs:
        job_id = retry_state.kwargs["job_id"]

    logger.info({"event": "retry", "job_id": job_id, "attempt": retry_state.attempt_number})


@retry(stop=stop_after_attempt(3), wait=wait_exponential(), reraise=True, before=_log_retry_attempt)
def _execute_marketing_campaign(job_id: str) -> Any:
    from agents.cgo_crew import cgo_crew

    return cgo_crew.kickoff(inputs={})


def _run_marketing_campaign_job(job_id: str) -> None:
    """Execute the CGO Crew job and persist the result in the in-memory registry."""
    logger.info({"event": "cgo_start", "job_id": job_id})
    try:
        result = _execute_marketing_campaign(job_id)
    except Exception as exc:  # pragma: no cover - safeguard for unexpected issues
        await job_store.set_status(
            job_id,
            "failed",
            {"error": str(exc)},
        )
        logger.exception("CGO marketing campaign job failed", extra={"job_id": job_id})
        logger.info({"event": "cgo_done", "job_id": job_id, "status": "failed"})
        return

    await job_store.set_status(job_id, "done", result)
    logger.info({"event": "cgo_done", "job_id": job_id, "status": "done"})


@router.post("/run-marketing-campaign")
async def run_marketing_campaign(
    background_tasks: BackgroundTasks,
    payload: Optional[MarketingCampaignRequest] = None,
):
    """Эндпоинт для CGO-AI (MAF), чтобы запустить CGO-Crew (CrewAI)."""

    if payload is None:
        payload = MarketingCampaignRequest()
    requested_job_id = payload.job_id

    if requested_job_id and requested_job_id in JOBS:
        job = JOBS[requested_job_id]
        response_payload: Dict[str, Any] = {
            "status": job["status"],
            "job_id": requested_job_id,
        }
        if "result" in job:
            response_payload["result"] = job["result"]
        return JSONResponse(status_code=200, content=response_payload)

    job_id = requested_job_id or str(uuid4())
    JOBS[job_id] = {"status": "running", "result": None}

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
