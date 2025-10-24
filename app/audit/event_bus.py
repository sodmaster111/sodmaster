"""Lightweight publish/subscribe event bus for audit events."""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Iterable, List, Optional

AuditEventHandler = Callable[["AuditEvent"], Optional[Awaitable[None]] | None]


@dataclass(frozen=True)
class AuditEvent:
    """Envelope describing an audit event published to the bus."""

    name: str
    c_unit: str
    actor: str
    subject: str
    severity: str = "info"
    payload: dict[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def with_payload(self, **updates: Any) -> "AuditEvent":
        """Return a copy of the event with additional payload attributes."""

        merged = dict(self.payload)
        merged.update(updates)
        return AuditEvent(
            name=self.name,
            c_unit=self.c_unit,
            actor=self.actor,
            subject=self.subject,
            severity=self.severity,
            payload=merged,
            tags=self.tags,
        )


class EventBus:
    """Synchronous event bus with async-aware handlers."""

    def __init__(self) -> None:
        self._subscribers: List[AuditEventHandler] = []
        self._lock = asyncio.Lock()

    def subscribe(self, handler: AuditEventHandler) -> None:
        """Register a new event handler."""

        self._subscribers.append(handler)

    async def publish(self, event: AuditEvent) -> None:
        """Publish the event to all registered subscribers."""

        async with self._lock:
            handlers: Iterable[AuditEventHandler] = list(self._subscribers)

        for handler in handlers:
            try:
                result = handler(event)
                if inspect.isawaitable(result):
                    await result  # type: ignore[func-returns-value]
            except Exception:
                # Defensive guard so one faulty subscriber does not break the pipeline.
                # Logged at publish site to retain the failing event context.
                import logging

                logging.getLogger(__name__).exception(
                    "Audit event handler failed", extra={"event": event.name}
                )

    def publish_nowait(self, event: AuditEvent) -> None:
        """Publish the event without awaiting completion of subscribers."""

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self.publish(event))
            return

        loop.create_task(self.publish(event))
