"""Operational self-test executed entirely in-process."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import sys
import time
from datetime import datetime, timezone
from importlib import import_module
from types import ModuleType
from typing import Any, AsyncIterator, Dict, Optional, Tuple

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

logger = logging.getLogger(__name__)


async def run_selftest(app: FastAPI) -> Dict[str, Any]:
    """Run the operational self-test suite against the provided FastAPI app.

    Every check is executed through an in-process ASGI client to avoid any
    network dependencies.
    """

    logger.info("Starting self-test execution")

    started_at = datetime.now(tz=timezone.utc)
    monotonic_started = time.monotonic()
    report: Dict[str, Any] = {}

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://selftest") as client:
        report["healthz"] = await _run_endpoint_check(client, "GET", "/healthz")
        report["readyz"] = await _run_endpoint_check(client, "GET", "/readyz")
        report["version"] = await _run_endpoint_check(client, "GET", "/version")

        async with _override_cgo_crew() as override_status:
            if not override_status:
                reason = "Unable to initialise CGO crew simulation"
                logger.warning(reason)
                report["cgo_submit"] = {
                    "method": "POST",
                    "path": "/api/v1/cgo/run-marketing-campaign",
                    "status": "error",
                    "reason": reason,
                }
                report["cgo_poll"] = {
                    "method": "GET",
                    "path": "/api/v1/cgo/jobs/<unknown>",
                    "status": "error",
                    "reason": "CGO submission skipped due to earlier failure",
                }
            else:
                report["cgo_submit"], report["cgo_poll"] = await _run_cgo_flow(client)

        report["a2a_submit"], report["a2a_poll"] = await _run_a2a_flow(client)

    overall_status = "ok"
    for key, value in report.items():
        if not isinstance(value, dict):
            continue
        if value.get("status") != "ok":
            overall_status = "error"
            break

    finished_at = datetime.now(tz=timezone.utc)
    report["meta"] = {
        "overall_status": overall_status,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_ms": int((time.monotonic() - monotonic_started) * 1000),
    }

    logger.info("Self-test execution completed", extra={"overall_status": overall_status})

    return report


async def _run_endpoint_check(
    client: AsyncClient,
    method: str,
    path: str,
    *,
    expected_status: int = 200,
    json: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute an HTTP request against the ASGI app and capture diagnostic info."""

    logger.info("Self-test: %s %s", method, path)

    started = time.monotonic()
    try:
        response = await client.request(method, path, json=json)
    except Exception as exc:  # pragma: no cover - defensive guard for unexpected issues
        logger.exception("Self-test request failed", extra={"method": method, "path": path})
        return {
            "method": method,
            "path": path,
            "status": "error",
            "reason": str(exc),
        }

    payload = _safe_json(response)

    result: Dict[str, Any] = {
        "method": method,
        "path": path,
        "status": "ok" if response.status_code == expected_status else "error",
        "http_status": response.status_code,
        "duration_ms": int((time.monotonic() - started) * 1000),
        "response": payload,
    }

    if response.status_code != expected_status:
        result["reason"] = f"Expected HTTP {expected_status}, received {response.status_code}"

    return result


async def _run_cgo_flow(client: AsyncClient) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Submit a CGO job and poll its status using the internal client."""

    submit_result = await _run_endpoint_check(
        client,
        "POST",
        "/api/v1/cgo/run-marketing-campaign",
        expected_status=202,
        json={},
    )

    if submit_result.get("status") != "ok":
        return submit_result, {
            "method": "GET",
            "path": "/api/v1/cgo/jobs/<unknown>",
            "status": "error",
            "reason": "CGO submission failed, polling skipped",
        }

    payload = submit_result.get("response", {}) or {}
    job_id = payload.get("job_id")
    if not job_id:
        return submit_result, {
            "method": "GET",
            "path": "/api/v1/cgo/jobs/<unknown>",
            "status": "error",
            "reason": "CGO submission did not return a job_id",
        }

    poll_result: Optional[Dict[str, Any]] = None

    for attempt in range(2):
        await asyncio.sleep(0.1 * (attempt + 1))
        poll_attempt = await _run_endpoint_check(
            client,
            "GET",
            f"/api/v1/cgo/jobs/{job_id}",
            expected_status=200,
        )

        poll_result = poll_attempt
        response_payload = poll_attempt.get("response", {}) or {}
        job_status = response_payload.get("status")

        if job_status in {"done", "failed"}:
            return submit_result, poll_attempt

    if poll_result is None:
        poll_result = {
            "method": "GET",
            "path": f"/api/v1/cgo/jobs/{job_id}",
            "status": "error",
            "reason": "CGO polling did not execute",
        }
    else:
        poll_result = poll_result.copy()
        poll_result["status"] = "error"
        poll_result["reason"] = (
            f"Job {job_id} did not complete after the polling window"
        )

    return submit_result, poll_result


async def _run_a2a_flow(client: AsyncClient) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Submit an A2A command and poll its status using the internal client."""

    payload = {
        "source": "selftest",
        "target": "ops",
        "command": "ping",
        "payload": {},
    }

    submit_result = await _run_endpoint_check(
        client,
        "POST",
        "/a2a/command",
        expected_status=202,
        json=payload,
    )

    if submit_result.get("status") != "ok":
        return submit_result, {
            "method": "GET",
            "path": "/a2a/jobs/<unknown>",
            "status": "error",
            "reason": "A2A submission failed, polling skipped",
        }

    payload = submit_result.get("response", {}) or {}
    job_id = payload.get("job_id")
    if not job_id:
        return submit_result, {
            "method": "GET",
            "path": "/a2a/jobs/<unknown>",
            "status": "error",
            "reason": "A2A submission did not return a job_id",
        }

    status_result = await _run_endpoint_check(
        client,
        "GET",
        f"/a2a/jobs/{job_id}",
        expected_status=200,
    )

    if status_result.get("status") != "ok":
        status_result = status_result.copy()
        status_result["reason"] = status_result.get(
            "reason",
            f"A2A job {job_id} polling returned HTTP {status_result.get('http_status')}",
        )

    return submit_result, status_result


def _safe_json(response: Any) -> Any:
    try:
        return response.json()
    except Exception:  # pragma: no cover - fallback when payload is not JSON
        return {"raw": response.text}


def _create_selftest_crew() -> Any:
    class _SelftestCrew:
        def kickoff(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "origin": "selftest",
                "inputs": inputs,
                "status": "ok",
            }

    return _SelftestCrew()


@contextlib.asynccontextmanager
async def _override_cgo_crew() -> AsyncIterator[bool]:
    """Temporarily patch the CGO crew to a lightweight self-test implementation."""

    stub_instance = _create_selftest_crew()
    original_module: Optional[ModuleType] = None
    created_stub_module = False

    try:
        module = import_module("agents.cgo_crew")
    except Exception as exc:  # pragma: no cover - module import issues during self-test
        logger.warning(
            "Unable to import agents.cgo_crew (%s). Using self-test stub module.",
            exc,
        )
        original_module = sys.modules.get("agents.cgo_crew")
        module = ModuleType("agents.cgo_crew")
        module.cgo_crew = stub_instance
        sys.modules["agents.cgo_crew"] = module
        created_stub_module = True
        try:
            yield True
        finally:
            if created_stub_module:
                if original_module is None:
                    sys.modules.pop("agents.cgo_crew", None)
                else:
                    sys.modules["agents.cgo_crew"] = original_module
        return

    original_attr = getattr(module, "cgo_crew", None)
    module.cgo_crew = stub_instance

    try:
        yield True
    finally:
        module.cgo_crew = original_attr
