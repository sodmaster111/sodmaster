"""Prometheus metric definitions and helpers for the Sodmaster API."""

from __future__ import annotations

from typing import Optional

from app.prometheus import Counter, Histogram, Info


CGO_JOBS_TOTAL = Counter(
    "cgo_jobs_total",
    "Total number of CGO jobs processed partitioned by status.",
    ["status"],
)

CGO_JOB_DURATION_SECONDS = Histogram(
    "cgo_job_duration_seconds",
    "Histogram of CGO job execution time in seconds.",
)

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests processed by the FastAPI application, partitioned by path.",
    ["path"],
)

APP_INFO = Info("app_info", "Application build and runtime information.")


def record_cgo_job_status(status: str, duration_seconds: Optional[float] = None) -> None:
    """Increment CGO job counters and optionally record duration."""

    CGO_JOBS_TOTAL.labels(status=status).inc()
    if duration_seconds is not None:
        CGO_JOB_DURATION_SECONDS.observe(duration_seconds)


def record_http_request(path: str) -> None:
    """Record a handled HTTP request for the provided path."""

    HTTP_REQUESTS_TOTAL.labels(path=path).inc()
