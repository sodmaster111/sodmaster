"""Root endpoints for the Sodmaster service."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/", summary="Root")
async def root() -> dict[str, str]:
    """Return a basic health payload for the root endpoint."""

    return {"status": "ok", "service": "sodmaster", "docs": "/docs"}
