import asyncio
import sys
import types
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:  # pragma: no cover - defensive path setup
    sys.path.append(str(ROOT_DIR))

from app.cgo import routes
from app.infra import InMemoryJobStore


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    monkeypatch.delenv("SLO_JOB_SEC", raising=False)
    monkeypatch.delenv("TELEGRAM_WEBHOOK", raising=False)
    monkeypatch.delenv("SLACK_WEBHOOK", raising=False)
    yield


def _prepare_job_store(job_id: str) -> InMemoryJobStore:
    store = InMemoryJobStore()
    asyncio.run(store.create(job_id, {"type": "marketing_campaign"}))
    asyncio.run(store.set_status(job_id, "running"))
    return store


def test_job_failure_triggers_alert(monkeypatch):
    class FailingCrew:
        def kickoff(self, inputs):
            raise RuntimeError("boom")

    fake_module = types.ModuleType("agents.cgo_crew")
    fake_module.cgo_crew = FailingCrew()
    agents_pkg = types.ModuleType("agents")
    agents_pkg.cgo_crew = fake_module
    monkeypatch.setitem(sys.modules, "agents", agents_pkg)
    monkeypatch.setitem(sys.modules, "agents.cgo_crew", fake_module)

    alerts = []
    monkeypatch.setattr(
        routes, "send_alert", lambda event, payload: alerts.append((event, payload))
    )
    monkeypatch.setenv("SLO_JOB_SEC", "1000")

    store = _prepare_job_store("job-1")
    asyncio.run(routes._run_marketing_campaign_job(store, "job-1"))

    assert ("job_failed", {"job_id": "job-1", "error": "boom"}) in alerts
    job = asyncio.run(store.get("job-1"))
    assert job is not None and job["status"] == "failed"


def test_latency_slo_miss_triggers_alert(monkeypatch):
    class SlowCrew:
        def kickoff(self, inputs):
            return {"ok": True}

    fake_module = types.ModuleType("agents.cgo_crew")
    fake_module.cgo_crew = SlowCrew()
    agents_pkg = types.ModuleType("agents")
    agents_pkg.cgo_crew = fake_module
    monkeypatch.setitem(sys.modules, "agents", agents_pkg)
    monkeypatch.setitem(sys.modules, "agents.cgo_crew", fake_module)
    alerts = []
    monkeypatch.setattr(
        routes, "send_alert", lambda event, payload: alerts.append((event, payload))
    )
    monkeypatch.setenv("SLO_JOB_SEC", "1")

    store = _prepare_job_store("job-2")
    times = iter([0.0, 0.0, 2.0])

    def fake_monotonic():
        try:
            return next(times)
        except StopIteration:  # pragma: no cover - defensive for extra calls
            return 2.0

    monkeypatch.setattr(routes.time, "monotonic", fake_monotonic)
    asyncio.run(routes._run_marketing_campaign_job(store, "job-2"))

    assert (
        "latency_slo_miss",
        {"job_id": "job-2", "duration_sec": 2.0, "threshold_sec": 1.0},
    ) in alerts
    job = asyncio.run(store.get("job-2"))
    assert job is not None and job["status"] == "done"
