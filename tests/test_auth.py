import hashlib
import hmac
from typing import Any

import pytest

pytest.importorskip("fastapi")

from app.auth import jwt as jwt_utils
from app.main import app


@pytest.fixture(autouse=True)
def _auth_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("JWT_EXPIRE_MIN", "5")
    monkeypatch.setenv("REFRESH_EXPIRE_DAYS", "5")
    app.state.user_repo.reset()


class DummyResponse:
    def __init__(self, payload: dict[str, Any]):
        self._payload = payload
        self.status_code = 200

    def json(self) -> dict[str, Any]:
        return self._payload


def test_google_callback_sets_cookies_and_roles(client, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")

    async def fake_post(self, url, data=None, headers=None):  # noqa: D401
        assert "googleapis" in url
        return DummyResponse({"email": "admin@example.com"})

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post, raising=False)

    response = client.get("/auth/google/callback?code=sample", allow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/admin"
    access = response.cookies.get("access_token")
    refresh = response.cookies.get("refresh_token")
    assert access
    assert refresh
    payload = jwt_utils.verify(access)
    assert payload["roles"] == ["admin"]


def _telegram_hash(payload: dict[str, Any], token: str) -> str:
    data_check = "\n".join(
        f"{key}={value}" for key, value in sorted(payload.items()) if key != "hash" and value is not None
    )
    secret_key = hashlib.sha256(token.encode()).digest()
    return hmac.new(secret_key, data_check.encode(), hashlib.sha256).hexdigest()


def test_telegram_verify_sets_cookies(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-token")
    payload = {
        "id": 12345,
        "username": "sodmaster",
        "auth_date": 1700000000,
    }
    payload["hash"] = _telegram_hash(payload, "bot-token")

    response = client.post("/auth/telegram/verify", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["user"]["telegram"]["id"] == 12345
    assert response.cookies.get("access_token")
    assert response.cookies.get("refresh_token")


def test_me_endpoint_returns_profile(client, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")

    async def fake_post(self, url, data=None, headers=None):  # noqa: D401
        return DummyResponse({"email": "user@example.com"})

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post, raising=False)

    login_response = client.get("/auth/google/callback?code=code", allow_redirects=False)
    access_token = login_response.cookies.get("access_token")
    assert access_token

    profile_response = client.get("/me", headers={"Authorization": f"Bearer {access_token}"})
    assert profile_response.status_code == 200
    payload = profile_response.json()
    assert payload["email"] == "user@example.com"
    assert payload["roles"] == []
