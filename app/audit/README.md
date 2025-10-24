# Audit Trail and Guardrails

This package implements the audit/event bus integration for the Sodmaster
service. The stack is composed of:

* **Event bus (`event_bus.py`)** – lightweight publish/subscribe dispatcher for
  structured audit events.
* **Guardrails (`guardrails.py`)** – declarative checks that evaluate events and
  emit `guardrail.violation` notifications when breached.
* **Audit trail (`service.py`)** – high-level façade that registers C-Units,
  bootstraps the guardrails, and attaches default sinks (structured logging,
  Prometheus counters, alert delivery).

## Default C-Units

The bootstrap configuration (`bootstrap_default_audit_trail`) registers three
controllable units:

| ID          | Purpose                               |
| ----------- | ------------------------------------- |
| `core.cgo`  | CGO marketing campaign orchestration  |
| `core.a2a`  | Agent-to-agent command dispatch       |
| `core.ops`  | Platform-level operational controls   |

Each emitted event must reference a known C-Unit. Unknown identifiers raise an
error to ensure observability gaps are caught during development.

## Guardrail catalogue

Two guardrails are enabled out of the box:

1. `cgo-job-failure` – triggered by `cgo.job.failed` events.
2. `a2a-command-failure` – triggered by `a2a.command.failed` events.

Violations are logged at `WARNING` level, exported to Prometheus via the
`guardrail_violations_total` counter, and escalated with a `guardrail_violation`
alert (reusing `app.ops.alerts.send_alert`).

New guardrails can be registered at runtime by calling
`AuditTrail.register_guardrail`.

## Event history

The audit trail keeps a rolling history (100 events by default) in memory. Tests
or diagnostics can inspect `AuditTrail.history` to verify integration flows.

## Integration helpers

Use `AuditTrail.emit` (async) or `emit_nowait` to publish structured events. For
long-running background jobs, pass the audit trail instance directly to avoid
re-fetching from the FastAPI application state.
