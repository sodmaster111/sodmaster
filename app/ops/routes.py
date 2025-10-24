"""Operational routes for Sodmaster."""

import logging

from fastapi import APIRouter, Request

from .selftest import run_selftest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/selftest")
async def selftest(request: Request) -> dict:
    """Execute the in-process self-test suite and return its report."""

    logger.info("Received /ops/selftest request")
    report = await run_selftest(request.app)
    return report
