"""Root endpoints for the Sodmaster service."""

from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()


@router.get("/", summary="Root")
async def root() -> dict[str, str]:
    """Return a basic health payload for the root endpoint."""

    return {"status": "ok", "service": "sodmaster", "docs": "/docs"}


@router.head("/", summary="Root (HEAD)")
async def root_head() -> Response:
    """Return an empty response for HEAD requests to the root endpoint."""

    return Response(status_code=200)
