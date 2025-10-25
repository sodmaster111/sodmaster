"""FastAPI routes exposing the WebDev crew capabilities."""

from __future__ import annotations

import logging
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from pydantic import BaseModel

from app.crews.webdev.crew import WebDevPayload, build_webdev_crew
from app.infra import JobStore
from app.metrics import record_crew_job_status

logger = logging.getLogger(__name__)

router = APIRouter()


class GenerateSiteRequest(WebDevPayload):
    job_id: Optional[str] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None


class SyncContentResponse(BaseModel):
    pages: List[Dict[str, Any]]


def _read_markdown_title(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("# ").strip() or fallback
    return fallback


def _collect_repository_pages() -> List[Dict[str, Any]]:
    pages: List[Dict[str, Any]] = []
    readme = Path("README.md")
    if readme.exists():
        content = readme.read_text(encoding="utf-8")
        pages.append(
            {
                "slug": "readme",
                "title": _read_markdown_title(content, "README"),
                "body": content,
                "format": "md",
            }
        )

    docs_root = Path("docs")
    if docs_root.exists():
        for md_file in sorted(docs_root.rglob("*.md")):
            content = md_file.read_text(encoding="utf-8")
            relative_slug = "/".join(md_file.relative_to(docs_root).with_suffix("").parts)
            pages.append(
                {
                    "slug": relative_slug,
                    "title": _read_markdown_title(content, md_file.stem.replace("-", " ").title()),
                    "body": content,
                    "format": "md",
                }
            )
    return pages


async def _execute_webdev_job(job_store: JobStore, job_id: str, payload: Dict[str, Any]) -> None:
    crew = build_webdev_crew()
    await job_store.set_status(job_id, "running")
    start = perf_counter()
    logger.info({"event": "webdev_start", "job_id": job_id})

    try:
        result = crew.kickoff(payload)
    except Exception as exc:  # pragma: no cover - defensive guard
        duration = perf_counter() - start
        await job_store.set_status(job_id, "failed", {"error": str(exc)})
        logger.exception("Webdev crew job failed", extra={"job_id": job_id})
        logger.info({"event": "webdev_failed", "job_id": job_id, "error": str(exc)})
        return

    duration = perf_counter() - start
    await job_store.set_status(job_id, "done", result)
    logger.info({"event": "webdev_done", "job_id": job_id, "duration": duration})


@router.post("/generate-site", status_code=status.HTTP_202_ACCEPTED, response_model=JobStatusResponse)
async def generate_site(
    request: Request,
    background_tasks: BackgroundTasks,
    payload: GenerateSiteRequest,
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
        {"type": "webdev.generate_site", "payload": payload.model_dump(exclude_none=True)},
    )
    await job_store.set_status(job_id, "accepted")
    record_crew_job_status("webdev", "accepted")

    background_tasks.add_task(
        _execute_webdev_job,
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


@router.post("/sync-content", response_model=SyncContentResponse)
async def sync_content() -> SyncContentResponse:
    pages = _collect_repository_pages()
    return SyncContentResponse(pages=pages)
