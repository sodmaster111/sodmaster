import logging
from typing import Any, Dict
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

try:  # pragma: no cover - совместимость Pydantic v1/v2
    from pydantic import ConfigDict
except ImportError:  # pragma: no cover
    ConfigDict = None  # type: ignore

from agents.cgo_crew import cgo_crew
from app.services.tasks import run_crew_task, task_results


logger = logging.getLogger(__name__)


class CampaignIn(BaseModel):
    """Входные данные для запуска маркетинговой кампании."""

    campaign_name: str = Field(..., description="Название кампании")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Дополнительные параметры кампании"
    )

    if ConfigDict is not None:  # type: ignore[attr-defined]
        model_config = ConfigDict(extra="allow")  # type: ignore[assignment]
    else:  # pragma: no cover - ветка для Pydantic v1
        class Config:  # type: ignore[assignment]
            extra = "allow"


router = APIRouter(prefix="/api/v1/cgo", tags=["cgo"])


@router.post("/run-marketing-campaign", status_code=202)
async def run_marketing_campaign(
    payload: CampaignIn, background_tasks: BackgroundTasks
):
    """Эндпоинт для CGO-AI (MAF), чтобы запустить CGO-Crew (CrewAI)."""

    job_id = f"cgo_job_{uuid4().hex}"
    payload_dump = payload.model_dump()
    logger.info(
        "CGO run-marketing-campaign: start",
        extra={"job_id": job_id, "payload": payload_dump},
    )

    task_results[job_id] = {"status": "queued", "payload": payload_dump}

    background_tasks.add_task(run_crew_task, cgo_crew, job_id, payload_dump)
    logger.info("CGO run-marketing-campaign: scheduled", extra={"job_id": job_id})

    return JSONResponse(
        status_code=202,
        content={"status": "accepted", "job_id": job_id},
    )
