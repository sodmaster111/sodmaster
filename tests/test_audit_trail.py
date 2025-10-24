import pytest

from app.audit.event_bus import AuditEvent


@pytest.mark.asyncio
async def test_default_audit_trail_registered(client):
    audit_trail = client.app.state.audit_trail

    assert "core.cgo" in audit_trail.c_units
    assert "core.a2a" in audit_trail.c_units

    await audit_trail.emit(
        AuditEvent(
            name="cgo.job.accepted",
            c_unit="core.cgo",
            actor="test",
            subject="job-1",
        )
    )

    assert any(event.subject == "job-1" for event in audit_trail.history)


@pytest.mark.asyncio
async def test_guardrail_violation_triggers_alert(monkeypatch, client):
    audit_trail = client.app.state.audit_trail
    captured = {}

    def fake_send_alert(event: str, payload: dict[str, object]) -> bool:
        captured["event"] = event
        captured["payload"] = payload
        return True

    monkeypatch.setattr("app.ops.alerts.send_alert", fake_send_alert)

    await audit_trail.emit(
        AuditEvent(
            name="cgo.job.failed",
            c_unit="core.cgo",
            actor="test",
            subject="job-2",
            severity="error",
            payload={"error": "boom"},
        )
    )

    violation = next(
        (event for event in audit_trail.history if event.subject == "job-2"),
        None,
    )
    assert violation is not None
    assert captured["event"] == "guardrail_violation"
    assert captured["payload"]["guardrail_id"] == "cgo-job-failure"
    assert captured["payload"]["subject"] == "job-2"
