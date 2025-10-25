"""Utility helpers for issuing and validating HMAC JWTs."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Sequence

from fastapi import HTTPException, Request, Response, status


class JWTError(HTTPException):
    """HTTP exception used for JWT validation errors."""

    def __init__(self, detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED) -> None:
        super().__init__(status_code=status_code, detail=detail)


@dataclass
class TokenPair:
    """Pair of access and refresh tokens."""

    access_token: str
    refresh_token: str
    expires_at: datetime


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _jwt_secret() -> bytes:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET is not configured")
    return secret.encode("utf-8")


def _expiry_minutes() -> int:
    value = os.getenv("JWT_EXPIRE_MIN", "30")
    try:
        minutes = int(value)
    except ValueError:  # pragma: no cover - defensive guard
        minutes = 30
    return max(minutes, 1)


def _refresh_days() -> int:
    value = os.getenv("REFRESH_EXPIRE_DAYS", "30")
    try:
        days = int(value)
    except ValueError:  # pragma: no cover - defensive guard
        days = 30
    return max(days, 1)


def _encode(payload: Dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_segment = _base64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_segment = _base64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    signature = hmac.new(_jwt_secret(), signing_input, hashlib.sha256).digest()
    signature_segment = _base64url(signature)
    return f"{header_segment}.{payload_segment}.{signature_segment}"


def _decode(token: str) -> Dict[str, Any]:
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as exc:
        raise JWTError("invalid_token_format") from exc

    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    expected_signature = hmac.new(_jwt_secret(), signing_input, hashlib.sha256).digest()
    provided_signature = _base64url_decode(signature_segment)

    if not hmac.compare_digest(expected_signature, provided_signature):
        raise JWTError("invalid_token_signature")

    try:
        payload_raw = _base64url_decode(payload_segment)
        payload: Dict[str, Any] = json.loads(payload_raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise JWTError("invalid_token_payload") from exc

    return payload


def issue_jwt(user_id: str, roles: Sequence[str]) -> TokenPair:
    """Issue new access/refresh JWT tokens for the provided user id."""

    now = datetime.now(timezone.utc)
    access_expiry = now + timedelta(minutes=_expiry_minutes())
    refresh_expiry = now + timedelta(days=_refresh_days())

    access_payload = {
        "sub": user_id,
        "roles": list(roles),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(access_expiry.timestamp()),
    }
    refresh_payload = {
        "sub": user_id,
        "roles": list(roles),
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(refresh_expiry.timestamp()),
    }

    access_token = _encode(access_payload)
    refresh_token = _encode(refresh_payload)
    return TokenPair(access_token=access_token, refresh_token=refresh_token, expires_at=access_expiry)


def verify(token: str, expected_type: str = "access") -> Dict[str, Any]:
    payload = _decode(token)
    token_type = payload.get("type")
    if expected_type and token_type != expected_type:
        raise JWTError("invalid_token_type")
    exp = payload.get("exp")
    if exp is None:
        raise JWTError("missing_expiration")
    if int(time.time()) >= int(exp):
        raise JWTError("token_expired")
    return payload


def refresh(refresh_token: str) -> TokenPair:
    payload = verify(refresh_token, expected_type="refresh")
    user_id = payload.get("sub")
    if not user_id:
        raise JWTError("invalid_subject")
    roles = payload.get("roles") or []
    if not isinstance(roles, (list, tuple)):
        raise JWTError("invalid_roles")
    return issue_jwt(user_id, roles)


def token_from_request(request: Request) -> Optional[str]:
    header = request.headers.get("Authorization")
    if header and header.startswith("Bearer "):
        return header.split(" ", 1)[1]
    cookie = request.cookies.get("access_token")
    if cookie:
        return cookie
    return None


def apply_cookies(response: Response, tokens: TokenPair) -> None:
    max_age = _expiry_minutes() * 60
    refresh_max_age = _refresh_days() * 24 * 3600
    response.set_cookie(
        "access_token",
        tokens.access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=max_age,
        path="/",
    )
    response.set_cookie(
        "refresh_token",
        tokens.refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=refresh_max_age,
        path="/",
    )


def clear_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
