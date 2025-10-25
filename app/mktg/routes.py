"""FastAPI routes exposing the Marketing crew."""

from __future__ import annotations

import asyncio
import logging
from time import perf_counter
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from pydantic import BaseModel

from app.crews.mktg.crew import MarketingPayload, build_marketing_crew
from app.infra import JobStore

logger = logging.getLogger(__name__)

router = APIRouter()


class PlanRequest(MarketingPayload):
    job_id: Optional[str] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None


class PublishRequest(BaseModel):
    plan_job_id: str
    trigger_webdev: bool = False
    job_id: Optional[str] = None


class PublishResponse(BaseModel):
    job_id: str
    status: str
    detail: Dict[str, Any]


async def _execute_plan_job(job_store: JobStore, job_id: str, payload: Dict[str, Any]) -> None:
    crew = build_marketing_crew()
    await job_store.set_status(job_id, "running")
    start = perf_counter()
    logger.info({"event": "mktg_start", "job_id": job_id})

    try:
        result = crew.kickoff(payload)
    except Exception as exc:  # pragma: no cover - defensive
        duration = perf_counter() - start
        await job_store.set_status(job_id, "failed", {"error": str(exc)})
        logger.exception("Marketing crew job failed", extra={"job_id": job_id})
        logger.info({"event": "mktg_failed", "job_id": job_id, "error": str(exc)})
        return

    duration = perf_counter() - start
    await job_store.set_status(job_id, "done", result)
    logger.info({"event": "mktg_done", "job_id": job_id, "duration": duration})


async def _execute_publish_job(
    job_store: JobStore, job_id: str, *, plan_job_id: str, trigger_webdev: bool
) -> None:
    await job_store.set_status(job_id, "running")
    logger.info({"event": "mktg_publish_start", "job_id": job_id, "plan": plan_job_id})
    await asyncio.sleep(0)
    result = {
        "status": "queued",
        "plan_job_id": plan_job_id,
        "trigger_webdev": trigger_webdev,
        "note": "WebDev trigger is stubbed in this environment",
    }
    await job_store.set_status(job_id, "done", result)
    logger.info({"event": "mktg_publish_done", "job_id": job_id})


@router.post("/plan", status_code=status.HTTP_202_ACCEPTED, response_model=JobStatusResponse)
async def plan_campaign(
    request: Request,
    background_tasks: BackgroundTasks,
    payload: PlanRequest,
) -> JobStatusResponse:
    job_store: JobStore = request.app.state.job_store

    if payload.job_id:
        existing = await job_store.get(payload.job_id)
        if existing is not None:
            return JobStatusResponse(
                job_id=payload.job_id,
                status=existing.get("status", "unknown"),
                result=existing.get("result"),
            )

    job_id = payload.job_id or str(uuid4())
    await job_store.create(
        job_id,
        {"type": "mktg.plan", "payload": payload.model_dump(exclude_none=True)},
    )
    await job_store.set_status(job_id, "accepted")

    background_tasks.add_task(
        _execute_plan_job,
        job_store,
        job_id,
        payload.model_dump(exclude={"job_id"}, exclude_none=True),
    )

    return JobStatusResponse(job_id=job_id, status="accepted")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(request: Request, job_id: str) -> JobStatusResponse:
    job_store: JobStore = request.app.state.job_store
    record = await job_store.get(job_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobStatusResponse(
        job_id=job_id,
        status=record.get("status", "unknown"),
        result=record.get("result"),
    )


@router.post("/publish", status_code=status.HTTP_202_ACCEPTED, response_model=PublishResponse)
async def publish_campaign(
    request: Request,
    background_tasks: BackgroundTasks,
    payload: PublishRequest,
) -> PublishResponse:
    job_store: JobStore = request.app.state.job_store

    plan_record = await job_store.get(payload.plan_job_id)
    if plan_record is None or plan_record.get("status") != "done":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Plan job must complete before publishing",
        )

    if payload.job_id:
        existing = await job_store.get(payload.job_id)
        if existing is not None:
            return PublishResponse(
                job_id=payload.job_id,
                status=existing.get("status", "unknown"),
                detail=existing.get("result", {}),
            )

    job_id = payload.job_id or str(uuid4())
    await job_store.create(
        job_id,
        {
            "type": "mktg.publish",
            "payload": payload.model_dump(exclude_none=True),
        },
    )
    await job_store.set_status(job_id, "accepted")

    background_tasks.add_task(
        _execute_publish_job,
        job_store,
        job_id,
        plan_job_id=payload.plan_job_id,
        trigger_webdev=payload.trigger_webdev,
    )

    return PublishResponse(job_id=job_id, status="accepted", detail={})


__all__ = ["router"]
