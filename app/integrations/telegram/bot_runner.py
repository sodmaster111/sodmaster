"""Runtime helpers for running Telegram bots using aiogram."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, List

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from aiogram import Bot, Dispatcher
    from aiogram.client.session.aiohttp import AiohttpSession
    from aiogram.enums import ParseMode
    from aiogram.types import Update
except ImportError:  # pragma: no cover - executed when aiogram is unavailable
    Bot = None  # type: ignore[assignment]
    Dispatcher = None  # type: ignore[assignment]
    AiohttpSession = None  # type: ignore[assignment]
    ParseMode = None  # type: ignore[assignment]
    Update = Any  # type: ignore[misc]


Handler = Callable[[Any], Awaitable[Any]]


@dataclass
class TelegramBotRunner:
    """Thin bootstrapper around aiogram with graceful fallbacks."""

    token: str | None = None
    parse_mode: str | None = "HTML"
    aiohttp_timeout: float = 10.0
    handlers: List[tuple[str, Handler]] = field(default_factory=list)
    _bot: Any = field(init=False, default=None)
    _dispatcher: Any = field(init=False, default=None)

    def __post_init__(self) -> None:
        self.token = self.token or os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured for bot runner")

        if Bot is None or Dispatcher is None:
            logger.info("aiogram is not installed; TelegramBotRunner operating in stub mode")
            return

        if AiohttpSession is not None:
            session = AiohttpSession(timeout=self.aiohttp_timeout)
        else:  # pragma: no cover - new aiogram releases may remove the session class
            session = None

        parse_mode = self.parse_mode
        if parse_mode is None and ParseMode is not None:
            parse_mode = ParseMode.HTML
        self._bot = Bot(token=self.token, parse_mode=parse_mode, session=session)
        self._dispatcher = Dispatcher()

        for event, handler in self.handlers:
            self.register_handler(event, handler)

    @property
    def is_stub(self) -> bool:
        return self._bot is None or self._dispatcher is None

    def register_handler(self, event: str, handler: Handler) -> None:
        """Register a handler for dispatcher events.

        In stub mode the handler is simply stored for later inspection which
        keeps unit tests lightweight. When aiogram is available the handler is
        attached to the dispatcher using ``dispatcher["event"].register`` API.
        """

        if self.is_stub:
            self.handlers.append((event, handler))
            return

        if not hasattr(self._dispatcher, event):
            raise AttributeError(f"Unsupported aiogram dispatcher event: {event}")
        registry = getattr(self._dispatcher, event)
        registry.register(handler)

    async def handle_update(self, update: Update) -> None:
        if self.is_stub:
            logger.debug("Stub runner received update: %s", update)
            for _, handler in self.handlers:
                await handler(update)
            return

        await self._dispatcher.feed_update(self._bot, update)

    async def start_polling(self) -> None:
        if self.is_stub:
            raise RuntimeError("aiogram is not installed; polling is unavailable")

        await self._dispatcher.start_polling(self._bot)

    async def start_webhook(
        self,
        *,
        url: str,
        secret_token: str | None = None,
        drop_pending_updates: bool = True,
    ) -> None:
        if self.is_stub:
            raise RuntimeError("aiogram is not installed; webhook runner is unavailable")

        await self._bot.set_webhook(url=url, secret_token=secret_token, drop_pending_updates=drop_pending_updates)

    async def shutdown(self) -> None:
        if self.is_stub:
            return
        await self._dispatcher.storage.close()
        await self._dispatcher.storage.wait_closed()
        session = getattr(self._bot, "session", None)
        if session:
            await session.close()


__all__ = ["TelegramBotRunner"]
