import sys
import types
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:  # pragma: no cover - defensive path setup
    sys.path.append(str(ROOT_DIR))

from app.cgo import routes


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    monkeypatch.delenv("SLO_JOB_SEC", raising=False)
    monkeypatch.delenv("TELEGRAM_WEBHOOK", raising=False)
    monkeypatch.delenv("SLACK_WEBHOOK", raising=False)
    yield


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
    monkeypatch.setattr(routes, "send_alert", lambda event, payload: alerts.append((event, payload)))
    monkeypatch.setenv("SLO_JOB_SEC", "1000")

    routes._run_marketing_campaign_job("job-1")

    assert ("job_failed", {"job_id": "job-1", "error": "boom"}) in alerts
    assert routes.JOBS["job-1"]["status"] == "failed"


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
    times = iter([0.0, 2.0])
    monkeypatch.setattr(routes.time, "monotonic", lambda: next(times))

    alerts = []
    monkeypatch.setattr(routes, "send_alert", lambda event, payload: alerts.append((event, payload)))
    monkeypatch.setenv("SLO_JOB_SEC", "1")

    routes._run_marketing_campaign_job("job-2")

    assert ("latency_slo_miss", {"job_id": "job-2", "duration_sec": 2.0, "threshold_sec": 1.0}) in alerts
    assert routes.JOBS["job-2"]["status"] == "done"
