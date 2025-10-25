import base64
import hashlib
import hmac
import json
import time

import httpx
import pytest

from app.integrations.telegram.bot_api import TelegramBotAPI, TelegramBotAPIError
from app.integrations.telegram.webhook import verify_init_data, verify_secret_token
from app.integrations.ton import pytoniq_client as pytoniq_module
from app.integrations.ton.tonconnect_validator import decode_connect_payload, verify_wallet_proof


@pytest.mark.asyncio
async def test_bot_api_success(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/bottoken/testMethod"
        return httpx.Response(200, json={"ok": True, "result": {"status": "ok"}})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.telegram.org")
    api = TelegramBotAPI(client=client)
    result = await api.call("testMethod")
    assert result == {"status": "ok"}
    await api.close()
    await client.aclose()


@pytest.mark.asyncio
async def test_bot_api_error(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": False, "description": "bad request"})

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.telegram.org")
    api = TelegramBotAPI(client=client)
    with pytest.raises(TelegramBotAPIError) as exc:
        await api.call("sendMessage")
    assert "bad request" in str(exc.value)
    await api.close()
    await client.aclose()


def _build_init_data(bot_token: str, payload: dict[str, str]) -> dict[str, str]:
    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(payload.items()))
    payload["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return payload


def test_verify_init_data():
    bot_token = "123:ABC"
    now = int(time.time())
    payload = {
        "auth_date": str(now),
        "query_id": "AAEAAQ",
        "user": json.dumps({"id": 1, "username": "test"}),
    }
    signed = _build_init_data(bot_token, payload)
    assert verify_init_data(signed, bot_token, max_age=600)


def test_verify_init_data_expired():
    bot_token = "123:ABC"
    payload = {
        "auth_date": str(int(time.time()) - 1000),
        "user": json.dumps({"id": 1}),
    }
    signed = _build_init_data(bot_token, payload)
    assert not verify_init_data(signed, bot_token, max_age=10)


def test_verify_secret_token():
    headers = {"X-Telegram-Bot-Api-Secret-Token": "secret"}
    assert verify_secret_token(headers, "secret")
    assert not verify_secret_token(headers, "other")


@pytest.mark.asyncio
async def test_pytoniq_client_stub(monkeypatch):
    module = pytoniq_module
    monkeypatch.setattr(module, "pytoniq", None, raising=False)
    client = module.PytoniqClient()
    assert client.is_stub
    with pytest.raises(RuntimeError):
        await client.get_balance("kQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")


def test_tonconnect_helpers():
    payload = {"address": "EQB", "proof": {"timestamp": 123, "state_init": "foo"}}
    secret = "super-secret"
    message = json.dumps(
        {"address": payload["address"], "proof": {"timestamp": 123, "state_init": "foo"}},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    payload["proof"]["signature"] = base64.b64encode(digest).decode()
    assert verify_wallet_proof(payload, secret)

    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    assert decode_connect_payload(encoded) == payload
