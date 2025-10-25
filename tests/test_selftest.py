import asyncio
import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app.main import app


def test_selftest_endpoint():
    """Ensure /ops/selftest returns a structured in-process diagnostic report."""

    client = TestClient(app)

    response = client.get("/ops/selftest")
    assert response.status_code == 200

    payload = response.json()
    assert payload["meta"]["overall_status"] == "ok"
    assert payload["meta"]["job_store"] in {"memory", "redis"}
    assert payload["meta"]["redis_connected"] in {True, False}
    assert payload["meta"]["crew_tools"] in {"available", "stub"}

    for key in (
        "healthz",
        "readyz",
        "version",
        "cgo_submit",
        "cgo_poll",
        "a2a_submit",
        "a2a_poll",
    ):
        assert key in payload
        assert payload[key]["status"] in {"ok", "error"}
        assert payload[key]["method"] in {"GET", "POST"}

    assert payload["cgo_submit"]["status"] == "ok"
    assert payload["cgo_poll"]["status"] == "ok"
    assert payload["cgo_submit"]["method"] == "POST"
    assert payload["a2a_submit"]["status"] == "ok"
    assert payload["a2a_submit"]["method"] == "POST"


def test_selftest_handles_missing_crewai_tools(monkeypatch):
    """Selftest remains successful even when crewai_tools dependency is missing."""

    import app.ops.selftest as selftest_module

    with monkeypatch.context() as patcher:
        patcher.setitem(sys.modules, "crewai_tools", None)
        selftest_module = importlib.reload(selftest_module)
        report = asyncio.run(selftest_module.run_selftest(app))

    # Reload the module to restore the default import behaviour for subsequent tests.
    importlib.reload(selftest_module)

    assert report["meta"]["overall_status"] == "ok"
    assert report["meta"]["crew_tools"] == "stub"
