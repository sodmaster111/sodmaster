# Audit & Guardrails Architecture

This document summarises the audit/event bus integration that powers
observability across CGO and A2A C-Units.

## Event lifecycle

1. **Emission** – application code publishes an `AuditEvent` through the
   `AuditTrail`. Events carry the C-Unit identifier, actor, subject, severity,
   and arbitrary payload metadata.
2. **Dispatch** – the `EventBus` fans out each event to registered subscribers.
   The default configuration attaches:
   * the `GuardrailEngine` – evaluates guardrails and emits
     `guardrail.violation` events when predicates match;
   * the logging sink – records structured JSON logs; and
   * the metrics sink – updates the Prometheus counters described below.
3. **Escalation** – guardrail violations with `high` or `critical` severity are
   forwarded to `app.ops.alerts.send_alert` as `guardrail_violation` alerts.

## Default audit vocabulary

| Event name               | Description                                           |
| ------------------------ | ----------------------------------------------------- |
| `cgo.job.accepted`       | CGO job persisted and background worker scheduled     |
| `cgo.job.completed`      | CGO job finished successfully                         |
| `cgo.job.failed`         | CGO job raised an exception                           |
| `a2a.command.accepted`   | A2A command stored and queued for execution           |
| `a2a.command.completed`  | A2A command finished successfully                     |
| `a2a.command.failed`     | A2A command raised an exception                       |
| `guardrail.violation`    | Derived event emitted by a guardrail breach           |

All events reference their source C-Unit (`core.cgo`, `core.a2a`, or `core.ops`).
Unknown identifiers are rejected to prevent silent misconfigurations.

## Metrics & dashboard

Two new Prometheus counters support monitoring dashboards:

* `audit_events_total{c_unit, severity}` – volume of emitted audit events.
* `guardrail_violations_total{guardrail_id, severity}` – guardrail breach
  cardinality.

Example Grafana panels:

* **Audit heatmap:** `sum by (c_unit)(rate(audit_events_total[5m]))`
* **Guardrail alerts:** `sum by (guardrail_id)(increase(guardrail_violations_total[1h]))`

These metrics can be combined with the existing CGO/A2A job latency histograms
for a single operational dashboard.

## Alert routing

`guardrail.violation` events trigger a `guardrail_violation` alert through the
existing webhook integration. The payload includes:

```json
{
  "guardrail_id": "cgo-job-failure",
  "reason": "<error message>",
  "event": "cgo.job.failed",
  "subject": "<job id>"
}
```

Teams can extend alert routing by subscribing additional handlers via
`AuditTrail.subscribe`.

## Extending the system

1. Register a new C-Unit (`AuditTrail.register_c_unit`) with metadata about the
   owning team.
2. Emit events referencing the new C-Unit through `AuditTrail.emit`.
3. Add guardrails by instantiating `Guardrail` objects and registering them with
   the audit trail.
4. Export custom metrics or alerts by subscribing new sinks to the audit trail.

Tests covering the integration reside in `tests/test_audit_trail.py`.
