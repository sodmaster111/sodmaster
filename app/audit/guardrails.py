"""Guardrail definitions and evaluation utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, List, Optional

from .event_bus import AuditEvent, EventBus


@dataclass(frozen=True)
class GuardrailViolation(AuditEvent):
    """Audit event emitted when a guardrail is breached."""

    guardrail_id: str = ""
    reason: str = ""

    def with_payload(self, **updates: Any) -> "GuardrailViolation":
        merged = dict(self.payload)
        merged.update(updates)
        return GuardrailViolation(
            name=self.name,
            c_unit=self.c_unit,
            actor=self.actor,
            subject=self.subject,
            severity=self.severity,
            payload=merged,
            tags=self.tags,
            guardrail_id=self.guardrail_id,
            reason=self.reason,
        )


@dataclass
class Guardrail:
    """Declarative guardrail definition."""

    id: str
    description: str
    severity: str
    predicate: Callable[[AuditEvent], bool]
    reason: Callable[[AuditEvent], str] = field(default=lambda event: "")

    def evaluate(self, event: AuditEvent) -> Optional[GuardrailViolation]:
        if not self.predicate(event):
            return None
        violation_reason = self.reason(event)
        return GuardrailViolation(
            name="guardrail.violation",
            c_unit=event.c_unit,
            actor=event.actor,
            subject=event.subject,
            severity=self.severity,
            payload={"event": event.name, **event.payload},
            guardrail_id=self.id,
            reason=violation_reason,
        )


class GuardrailEngine:
    """Evaluates guardrails against published audit events."""

    def __init__(self, guardrails: Iterable[Guardrail], bus: EventBus) -> None:
        self._guardrails: List[Guardrail] = list(guardrails)
        self._bus = bus

    async def handle_event(self, event: AuditEvent) -> None:
        if isinstance(event, GuardrailViolation):
            return

        for guardrail in self._guardrails:
            violation = guardrail.evaluate(event)
            if violation is not None:
                await self._bus.publish(violation)

    def register(self, guardrail: Guardrail) -> None:
        self._guardrails.append(guardrail)
