"""User-facing API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.auth.jwt import JWTError, token_from_request, verify
from app.users.repository import UserRepository

router = APIRouter()


@router.get("/me")
async def me(request: Request) -> dict:
    token = token_from_request(request)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing_token")
    try:
        payload = verify(token, expected_type="access")
    except JWTError as exc:
        raise exc
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_token")
    user_repo: UserRepository = request.app.state.user_repo
    user = user_repo.get(user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user_not_found")
    return user.as_profile()
