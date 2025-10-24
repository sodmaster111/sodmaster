"""High-level audit trail orchestration."""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Iterable, List

from .event_bus import AuditEvent, EventBus
from .guardrails import Guardrail, GuardrailEngine, GuardrailViolation
from app.metrics import record_audit_event, record_guardrail_violation

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CUnit:
    """Represents a controllable unit (C-Unit) in the platform."""

    id: str
    name: str
    description: str
    owners: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


class AuditTrail:
    """Facade around the audit event bus, guardrails, and sinks."""

    def __init__(
        self,
        *,
        c_units: Iterable[CUnit],
        guardrails: Iterable[Guardrail] | None = None,
        history_limit: int = 100,
    ) -> None:
        self._bus = EventBus()
        self._c_units: Dict[str, CUnit] = {unit.id: unit for unit in c_units}
        self._history: Deque[AuditEvent] = deque(maxlen=history_limit)
        self._guardrail_engine = GuardrailEngine(list(guardrails or ()), self._bus)
        self._bus.subscribe(self._guardrail_engine.handle_event)
        self._bus.subscribe(self._log_sink)
        self._bus.subscribe(self._metrics_sink)

    @property
    def c_units(self) -> Dict[str, CUnit]:
        return dict(self._c_units)

    @property
    def history(self) -> List[AuditEvent]:
        return list(self._history)

    def register_c_unit(self, c_unit: CUnit) -> None:
        self._c_units[c_unit.id] = c_unit

    def register_guardrail(self, guardrail: Guardrail) -> None:
        self._guardrail_engine.register(guardrail)

    async def emit(self, event: AuditEvent) -> None:
        if event.c_unit not in self._c_units:
            raise ValueError(f"Unknown C-Unit: {event.c_unit}")

        await self._bus.publish(event)
        self._history.append(event)

    def emit_nowait(self, event: AuditEvent) -> None:
        if event.c_unit not in self._c_units:
            raise ValueError(f"Unknown C-Unit: {event.c_unit}")
        self._bus.publish_nowait(event)
        self._history.append(event)

    def subscribe(self, handler):
        self._bus.subscribe(handler)

    @staticmethod
    def _log_sink(event: AuditEvent) -> None:
        if isinstance(event, GuardrailViolation):
            logger.warning(
                "Guardrail violation", extra={"guardrail": event.guardrail_id, **event.payload}
            )
        else:
            logger.info(
                "Audit event", extra={"event": event.name, "c_unit": event.c_unit, **event.payload}
            )

    @staticmethod
    def _metrics_sink(event: AuditEvent) -> None:
        if isinstance(event, GuardrailViolation):
            record_guardrail_violation(event.guardrail_id, event.severity)
        record_audit_event(event.c_unit, event.severity)


def bootstrap_default_audit_trail() -> AuditTrail:
    """Create the default audit trail configuration for the FastAPI app."""

    default_c_units = [
        CUnit(
            id="core.cgo",
            name="CGO Marketing",
            description="Marketing campaign orchestration via CGO Crew",
            owners=("cgo", "ops"),
        ),
        CUnit(
            id="core.a2a",
            name="Agent-to-Agent Gateway",
            description="Inter-agent command dispatch",
            owners=("platform",),
        ),
        CUnit(
            id="core.ops",
            name="Operations",
            description="Platform operations and observability",
            owners=("ops",),
        ),
    ]

    guardrails = [
        Guardrail(
            id="cgo-job-failure",
            description="CGO job failures must raise a guardrail violation",
            severity="high",
            predicate=lambda event: event.name == "cgo.job.failed",
            reason=lambda event: event.payload.get("error", "Unknown failure"),
        ),
        Guardrail(
            id="a2a-command-failure",
            description="A2A command failures trigger guardrail notifications",
            severity="high",
            predicate=lambda event: event.name == "a2a.command.failed",
            reason=lambda event: event.payload.get("reason", "Unknown failure"),
        ),
    ]

    trail = AuditTrail(c_units=default_c_units, guardrails=guardrails)
    trail.subscribe(_alert_sink)
    return trail


def _alert_sink(event: AuditEvent) -> None:
    if not isinstance(event, GuardrailViolation):
        return

    if event.severity not in {"high", "critical"}:
        return

    try:
        from app.ops.alerts import send_alert

        payload = {
            "guardrail_id": event.guardrail_id,
            "reason": event.reason,
            "event": event.payload.get("event"),
            "subject": event.subject,
        }
        send_alert("guardrail_violation", payload)
    except Exception:
        logger.exception("Failed to send guardrail alert")
