import logging
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse

from app.infra import JobStore

logger = logging.getLogger(__name__)

router = APIRouter()


async def _run_marketing_campaign_job(job_store: JobStore, job_id: str) -> None:
    """Execute the CGO Crew job and persist the result via the configured store."""
    from agents.cgo_crew import cgo_crew

    logger.info({"event": "cgo_start", "job_id": job_id})
    try:
        result = cgo_crew.kickoff(inputs={})
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
    request: Request, background_tasks: BackgroundTasks
):
    """Эндпоинт для CGO-AI (MAF), чтобы запустить CGO-Crew (CrewAI)."""

    job_id = str(uuid4())
    job_store: JobStore = request.app.state.job_store

    await job_store.create(job_id, {"type": "marketing_campaign"})
    await job_store.set_status(job_id, "running", None)

    background_tasks.add_task(_run_marketing_campaign_job, job_store, job_id)

    return JSONResponse(
        status_code=202,
        content={"status": "accepted", "job_id": job_id},
    )


@router.get("/jobs/{job_id}")
async def get_job_status(request: Request, job_id: str) -> dict[str, Any]:
    job_store: JobStore = request.app.state.job_store
    job = await job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return {"status": job.get("status"), "result": job.get("result")}
