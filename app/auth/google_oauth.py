"""Routes handling Google OAuth2 login flow."""

from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.auth.jwt import apply_cookies, issue_jwt
from app.users.repository import UserRepository

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

router = APIRouter(prefix="/auth/google", tags=["auth"])


def _google_client_id() -> str:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "google_client_id_missing")
    return client_id


def _google_client_secret() -> str:
    secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not secret:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "google_client_secret_missing")
    return secret


def _decode_id_token(id_token: str) -> Dict[str, Any]:
    try:
        _header, payload_segment, _signature = id_token.split(".")
        payload_bytes = base64.urlsafe_b64decode(payload_segment + "=" * (-len(payload_segment) % 4))
        return json.loads(payload_bytes)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid_google_token") from exc


async def _exchange_code(code: str, redirect_uri: str) -> Dict[str, Any]:
    data = {
        "code": code,
        "client_id": _google_client_id(),
        "client_secret": _google_client_secret(),
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(GOOGLE_TOKEN_URL, data=data, headers={"Accept": "application/json"})
    if response.status_code >= 400:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "google_exchange_failed")
    try:
        payload = response.json()
    except json.JSONDecodeError as exc:  # pragma: no cover - unexpected
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "google_invalid_response") from exc
    return payload

@router.get("/login")
async def google_login(request: Request) -> RedirectResponse:
    redirect_uri = request.url_for("google_callback")
    params = {
        "client_id": _google_client_id(),
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": redirect_uri,
        "access_type": "offline",
        "prompt": "consent",
    }
    target = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(target, status_code=status.HTTP_302_FOUND)


@router.get("/callback", name="google_callback")
async def google_callback(request: Request, code: Optional[str] = None) -> RedirectResponse:
    if not code:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "missing_code")
    redirect_uri = request.url_for("google_callback")
    token_payload = await _exchange_code(code, redirect_uri)
    email = token_payload.get("email")
    if not email:
        id_token = token_payload.get("id_token")
        if id_token:
            email = _decode_id_token(id_token).get("email")
    if not email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "email_not_found")

    user_repo: UserRepository = request.app.state.user_repo
    user = user_repo.upsert_google_user(email)
    tokens = issue_jwt(user.id, user.roles)
    response = RedirectResponse("/admin", status_code=status.HTTP_302_FOUND)
    apply_cookies(response, tokens)
    return response
