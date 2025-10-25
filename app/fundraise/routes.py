"""API routes for fundraise dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from .service import FundraiseTracker


router = APIRouter()


def get_tracker(request: Request) -> FundraiseTracker:
    tracker = getattr(request.app.state, "fundraise_tracker", None)
    if tracker is None:
        raise HTTPException(status_code=503, detail="fundraise tracker unavailable")
    return tracker


@router.get("/status")
async def get_status(tracker: FundraiseTracker = Depends(get_tracker)) -> dict:
    return await tracker.status()


__all__ = ["router"]
