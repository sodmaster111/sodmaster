"""Async wrapper for interacting with the Telegram Bot API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional

import httpx


class TelegramBotAPIError(RuntimeError):
    """Raised when the Telegram Bot API returns an error response."""

    def __init__(self, method: str, description: str, *, status_code: int | None = None) -> None:
        message = f"Telegram Bot API call '{method}' failed: {description}"
        if status_code is not None:
            message = f"{message} (status={status_code})"
        super().__init__(message)
        self.method = method
        self.description = description
        self.status_code = status_code


@dataclass(frozen=True)
class LocalBotAPICredentials:
    """Credentials required to bootstrap an official local Bot API server."""

    api_id: str
    api_hash: str

    @classmethod
    def load_from_env(cls) -> "LocalBotAPICredentials | None":
        api_id = os.getenv("TELEGRAM_API_ID")
        api_hash = os.getenv("TELEGRAM_API_HASH")
        if not api_id or not api_hash:
            return None
        return cls(api_id=api_id, api_hash=api_hash)


class TelegramBotAPI:
    """Tiny async helper around the official Telegram Bot API endpoints.

    The wrapper keeps the HTTP layer lightweight to make it simple to integrate
    with background tasks or FastAPI route handlers. By default the bot token is
    loaded from the ``TELEGRAM_BOT_TOKEN`` environment variable. When the
    optional self-hosted Bot API server is used, the ``base_url`` should point
    to the reverse proxy (e.g. ``https://bot-api.internal``) while the
    ``LocalBotAPICredentials`` are used to configure the upstream server.
    """

    def __init__(
        self,
        *,
        token: str | None = None,
        base_url: str | None = None,
        timeout: float = 10.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

        self._token = token
        self._base_url = base_url or os.getenv("TELEGRAM_BOT_API_BASE", "https://api.telegram.org")
        self._timeout = timeout
        self._client = client
        self._owns_client = client is None

    @property
    def token(self) -> str:
        return self._token

    @property
    def base_url(self) -> str:
        return self._base_url.rstrip("/")

    def _method_path(self, method: str) -> str:
        return f"/bot{self._token}/{method}"

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self._timeout)
        return self._client

    async def close(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    async def __aenter__(self) -> "TelegramBotAPI":
        self._ensure_client()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    async def call(
        self,
        method: str,
        *,
        params: Mapping[str, Any] | None = None,
        files: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Execute an arbitrary Bot API method and return the response payload."""

        client = self._ensure_client()
        response = await client.post(self._method_path(method), data=params, files=files)
        if response.status_code != 200:
            raise TelegramBotAPIError(method, response.text, status_code=response.status_code)

        payload = response.json()
        if not payload.get("ok"):
            description = payload.get("description", "unknown error")
            raise TelegramBotAPIError(method, description)
        return payload["result"]

    async def send_message(
        self,
        chat_id: int | str,
        text: str,
        *,
        parse_mode: str | None = None,
        disable_web_page_preview: bool | None = None,
        extra: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a message to a chat with safe defaults."""

        params: Dict[str, Any] = {"chat_id": chat_id, "text": text}
        if parse_mode:
            params["parse_mode"] = parse_mode
        if disable_web_page_preview is not None:
            params["disable_web_page_preview"] = disable_web_page_preview
        if extra:
            params.update(extra)

        return await self.call("sendMessage", params=params)

    async def set_webhook(
        self,
        url: str,
        *,
        secret_token: str | None = None,
        allowed_updates: Iterable[str] | None = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"url": url}
        if secret_token:
            params["secret_token"] = secret_token
        if allowed_updates:
            params["allowed_updates"] = list(allowed_updates)
        return await self.call("setWebhook", params=params)

    async def delete_webhook(self, *, drop_pending_updates: bool = False) -> Dict[str, Any]:
        params = {"drop_pending_updates": drop_pending_updates}
        return await self.call("deleteWebhook", params=params)


__all__ = [
    "LocalBotAPICredentials",
    "TelegramBotAPI",
    "TelegramBotAPIError",
]
