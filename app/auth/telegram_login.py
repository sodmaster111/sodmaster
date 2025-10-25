"""Telegram login widget verification endpoint."""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.auth.jwt import apply_cookies, issue_jwt
from app.users.repository import UserRepository

router = APIRouter(prefix="/auth/telegram", tags=["auth"])


def _bot_token() -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "telegram_bot_token_missing")
    return token


def _build_data_check_string(payload: Dict[str, Any]) -> str:
    pairs = []
    for key in sorted(payload.keys()):
        if key == "hash" or payload[key] is None:
            continue
        pairs.append(f"{key}={payload[key]}")
    return "\n".join(pairs)


def _verify_signature(payload: Dict[str, Any]) -> bool:
    provided_hash = payload.get("hash")
    if not provided_hash:
        return False
    data_check_string = _build_data_check_string(payload)
    secret_key = hashlib.sha256(_bot_token().encode()).digest()
    computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, provided_hash)


@router.post("/verify")
async def telegram_verify(request: Request) -> JSONResponse:
    body: Dict[str, Any] = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid_payload")
    if not _verify_signature(body):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "invalid_signature")
    telegram_id = body.get("id") or body.get("telegram_id")
    if telegram_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "telegram_id_required")
    try:
        telegram_id_int = int(telegram_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid_telegram_id") from exc

    username = body.get("username")
    email = body.get("email")
    user_repo: UserRepository = request.app.state.user_repo
    user = user_repo.upsert_telegram_user(telegram_id_int, username=username, email=email)
    tokens = issue_jwt(user.id, user.roles)
    response = JSONResponse({"status": "ok", "user": user.as_profile()})
    apply_cookies(response, tokens)
    return response
