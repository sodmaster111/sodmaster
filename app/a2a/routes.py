"""Agent-to-Agent (A2A) command submission endpoints."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import os
import random
import time
from typing import Any, Dict, Optional, Union
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.infra import JobStore
from app.metrics import record_a2a_job_status

logger = logging.getLogger(__name__)

router = APIRouter()

_SIGNATURE_HEADER = "X-A2A-Signature"
_SECRET_ENV = "A2A_SECRET"
_signature_warning_emitted = False


class A2ACommand(BaseModel):
    """Incoming A2A command payload."""

    source: str
    target: str
    command: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = Field(default=None, description="Deterministic job id")


class A2ACommandResult(BaseModel):
    """Response model describing the status of a submitted command."""

    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None


async def _verify_signature(request: Request) -> None:
    """Validate the optional HMAC signature for the request."""

    global _signature_warning_emitted

    secret = os.getenv(_SECRET_ENV, "")
    if not secret:
        if not _signature_warning_emitted:
            logger.warning(
                "A2A secret missing; signature validation disabled",
            )
            _signature_warning_emitted = True
        return

    signature = request.headers.get(_SIGNATURE_HEADER, "")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing A2A signature")

    body = await request.body()
    computed = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, computed):
        raise HTTPException(status_code=401, detail="Invalid A2A signature")


async def _resolve_job(
    job_store: JobStore,
    command: A2ACommand,
) -> tuple[str, Optional[Dict[str, Any]]]:
    """Return a job id and existing record (if present)."""

    job_id = command.idempotency_key or str(uuid4())
    if command.idempotency_key:
        existing_job = await job_store.get(job_id)
        if existing_job is not None:
            return job_id, existing_job
    return job_id, None


def _serialise_job(job_id: str, job: Dict[str, Any]) -> A2ACommandResult:
    return A2ACommandResult(
        job_id=job_id,
        status=job.get("status", "unknown"),
        result=job.get("result"),
    )


async def _run_a2a_job(job_id: str, job_store: JobStore, payload: Dict[str, Any]) -> None:
    """Execute the A2A job in the background and persist its lifecycle events."""

    start_time = time.perf_counter()
    command_payload = payload.get("command", {})
    command_name = command_payload.get("command", "unknown")
    command_args = command_payload.get("payload", {})
    log_extra = {"event": "a2a_start", "job_id": job_id, "command": command_name}

    logger.info("Starting A2A job", extra=log_extra)

    await job_store.set_status(job_id, "running", None)
    record_a2a_job_status("running")

    try:
        sleep_for = random.uniform(0.05, 0.2)
        await asyncio.sleep(sleep_for)

        if command_name == "ping":
            result = {"status": "pong", "echo": command_args}
        elif command_name == "noop":
            result = {"status": "noop"}
        else:
            raise ValueError(f"Unsupported A2A command: {command_name}")

        await job_store.set_status(job_id, "done", result)
        record_a2a_job_status("done", time.perf_counter() - start_time)
        logger.info(
            "A2A job completed",
            extra={"event": "a2a_done", "job_id": job_id, "command": command_name},
        )
    except Exception as exc:
        await job_store.set_status(job_id, "failed", {"reason": str(exc)})
        record_a2a_job_status("failed", time.perf_counter() - start_time)
        logger.exception(
            "A2A job failed",
            extra={"event": "a2a_failed", "job_id": job_id, "command": command_name},
        )


@router.post(
    "/command",
    response_model=A2ACommandResult,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_command(
    request: Request, command: A2ACommand, background_tasks: BackgroundTasks
) -> Union[JSONResponse, A2ACommandResult]:
    """Persist an A2A command and return its tracking identifier."""

    await _verify_signature(request)

    job_store: JobStore = request.app.state.job_store
    job_id, existing_job = await _resolve_job(job_store, command)
    if existing_job is not None:
        result = _serialise_job(job_id, existing_job)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=result.model_dump(exclude_none=True),
        )

    payload = {
        "type": "a2a_command",
        "command": command.model_dump(exclude_none=True),
    }
    await job_store.create(job_id, payload)
    await job_store.set_status(job_id, "accepted", None)
    record_a2a_job_status("accepted")

    background_tasks.add_task(_run_a2a_job, job_id, job_store, payload)

    response = A2ACommandResult(job_id=job_id, status="accepted")
    return response


@router.get(
    "/jobs/{job_id}",
    response_model=A2ACommandResult,
    status_code=status.HTTP_200_OK,
)
async def get_job_status(request: Request, job_id: str) -> A2ACommandResult:
    """Return the status for a previously submitted A2A command."""

    job_store: JobStore = request.app.state.job_store
    job = await job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return _serialise_job(job_id, job)
