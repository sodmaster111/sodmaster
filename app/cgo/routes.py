import logging
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse

from app.infra.job_store import JobStore

logger = logging.getLogger(__name__)

router = APIRouter()


async def _run_marketing_campaign_job(job_id: str, job_store: JobStore) -> None:
    """Execute the CGO Crew job and persist the result in the in-memory registry."""
    from agents.cgo_crew import cgo_crew

    logger.info({"event": "cgo_start", "job_id": job_id})
    try:
        result = cgo_crew.kickoff(inputs={})
    except Exception as exc:  # pragma: no cover - safeguard for unexpected issues
        await job_store.set_status(job_id, "failed", {"error": str(exc)})
        logger.exception("CGO marketing campaign job failed", extra={"job_id": job_id})
        logger.info({"event": "cgo_done", "job_id": job_id, "status": "failed"})
        return

    await job_store.set_status(job_id, "done", result)
    logger.info({"event": "cgo_done", "job_id": job_id, "status": "done"})


@router.post("/run-marketing-campaign")
async def run_marketing_campaign(
    background_tasks: BackgroundTasks, request: Request
):
    """Эндпоинт для CGO-AI (MAF), чтобы запустить CGO-Crew (CrewAI)."""

    job_store: JobStore = request.app.state.job_store
    job_id = str(uuid4())
    await job_store.create(job_id, payload={})
    await job_store.set_status(job_id, "running")

    background_tasks.add_task(_run_marketing_campaign_job, job_id, job_store)

    return JSONResponse(
        status_code=202,
        content={"status": "accepted", "job_id": job_id},
    )


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str, request: Request) -> Dict[str, Any]:
    job_store: JobStore = request.app.state.job_store
    job = await job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return {"status": job.get("status"), "result": job.get("result")}
