from fastapi import APIRouter, status
from pydantic import BaseModel
from datetime import datetime
import sys

router = APIRouter(prefix="/api/v1", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    service: str
    python_version: str


class ReadinessResponse(BaseModel):
    ready: bool
    checks: dict


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.utcnow().isoformat(),
        service="sodmaster-c-unit",
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> ReadinessResponse:
    checks = {
        "api": "ok",
        "database": "not_configured",
        "redis": "not_configured"
    }
    ready = all(v in ["ok", "not_configured"] for v in checks.values())
    return ReadinessResponse(ready=ready, checks=checks)


@router.head("/health")
async def health_head():
    return None
