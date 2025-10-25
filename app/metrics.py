"""Prometheus metric definitions and helpers for the Sodmaster API."""

from __future__ import annotations

from typing import Optional

from app.prometheus import Counter, Histogram, Info


A2A_JOBS_TOTAL = Counter(
    "a2a_jobs_total",
    "Total number of A2A jobs processed partitioned by status.",
    ["status"],
)

A2A_JOB_DURATION_SECONDS = Histogram(
    "a2a_job_duration_seconds",
    "Histogram of A2A job execution time in seconds.",
)

CGO_JOBS_TOTAL = Counter(
    "cgo_jobs_total",
    "Total number of CGO jobs processed partitioned by status.",
    ["status"],
)

CGO_JOB_DURATION_SECONDS = Histogram(
    "cgo_job_duration_seconds",
    "Histogram of CGO job execution time in seconds.",
)

AUX_AUDIT_EVENTS_TOTAL = Counter(
    "audit_events_total",
    "Total number of audit events partitioned by c_unit and severity.",
    ["c_unit", "severity"],
)

GUARDRAIL_VIOLATIONS_TOTAL = Counter(
    "guardrail_violations_total",
    "Total guardrail violations partitioned by guardrail id and severity.",
    ["guardrail_id", "severity"],
)

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests processed by the FastAPI application, partitioned by path.",
    ["path"],
)

CREW_JOBS_TOTAL = Counter(
    "crew_jobs_total",
    "Total number of crew jobs processed partitioned by crew and status.",
    ["crew", "status"],
)

CREW_JOB_DURATION_SECONDS = Histogram(
    "crew_job_duration_seconds",
    "Histogram of crew job execution time in seconds partitioned by crew.",
    ["crew"],
)

WAF_BLOCK_TOTAL = Counter(
    "waf_block_total",
    "Total number of requests blocked by the application firewall partitioned by path group.",
    ["path_group"],
)

APP_INFO = Info("app_info", "Application build and runtime information.")


def record_cgo_job_status(status: str, duration_seconds: Optional[float] = None) -> None:
    """Increment CGO job counters and optionally record duration."""

    CGO_JOBS_TOTAL.labels(status=status).inc()
    if duration_seconds is not None:
        CGO_JOB_DURATION_SECONDS.observe(duration_seconds)


def record_a2a_job_status(status: str, duration_seconds: Optional[float] = None) -> None:
    """Increment A2A job counters and optionally record duration."""

    A2A_JOBS_TOTAL.labels(status=status).inc()
    if duration_seconds is not None:
        A2A_JOB_DURATION_SECONDS.observe(duration_seconds)


def record_http_request(path: str) -> None:
    """Record a handled HTTP request for the provided path."""

    HTTP_REQUESTS_TOTAL.labels(path=path).inc()


def record_crew_job_status(crew: str, status: str) -> None:
    """Increment counters for crew job lifecycle events."""

    CREW_JOBS_TOTAL.labels(crew=crew, status=status).inc()


def record_crew_job_duration(crew: str, duration_seconds: float) -> None:
    """Observe the duration of a crew job execution."""

    CREW_JOB_DURATION_SECONDS.labels(crew=crew).observe(duration_seconds)


def record_waf_block(path_group: str) -> None:
    """Increment counters for blocked requests handled by the WAF layer."""

    WAF_BLOCK_TOTAL.labels(path_group=path_group).inc()


def record_audit_event(c_unit: str, severity: str) -> None:
    """Increment counters for emitted audit events."""

    AUX_AUDIT_EVENTS_TOTAL.labels(c_unit=c_unit, severity=severity).inc()


def record_guardrail_violation(guardrail_id: str, severity: str) -> None:
    """Increment counters for guardrail violation events."""

    GUARDRAIL_VIOLATIONS_TOTAL.labels(guardrail_id=guardrail_id, severity=severity).inc()
