"""Routes for Telegram Mini Apps bootstrap and webhook validation."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.integrations.telegram.webhook import verify_init_data, verify_secret_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/miniapp", tags=["telegram-miniapp"])


class InitDataRequest(BaseModel):
    init_data: str = Field(..., description="Raw initData string from Telegram WebApp")
    max_age: Optional[int] = Field(default=300, description="Max allowed age in seconds")


class InitDataResponse(BaseModel):
    ok: bool
    user: Optional[Dict[str, Any]] = None
    auth_date: Optional[int] = None


class MiniAppWebhookEvent(BaseModel):
    event: str
    payload: Dict[str, Any] = Field(default_factory=dict)


@router.post("/verify", response_model=InitDataResponse)
async def verify_init_data_endpoint(request: InitDataRequest) -> InitDataResponse:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="bot token is not configured")

    data = {key: value for key, value in parse_qsl(request.init_data, keep_blank_values=True)}
    if not verify_init_data(data, token, max_age=request.max_age or 300):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="invalid_init_data")

    user: Optional[Dict[str, Any]] = None
    if "user" in data:
        try:
            user = json.loads(data["user"])
        except json.JSONDecodeError:
            logger.warning("Failed to decode Telegram user payload")

    auth_date = None
    if "auth_date" in data:
        try:
            auth_date = int(data["auth_date"])
        except ValueError:
            auth_date = None

    return InitDataResponse(ok=True, user=user, auth_date=auth_date)


@router.post("/webhook")
async def miniapp_webhook(request: Request, event: MiniAppWebhookEvent) -> JSONResponse:
    expected_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    if not verify_secret_token(request.headers, expected_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid_webhook_secret")

    logger.info("Received miniapp webhook", extra={"event": event.event})
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"status": "accepted"})
