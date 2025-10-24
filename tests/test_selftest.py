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

    for key in ("healthz", "readyz", "version", "cgo_submit", "cgo_poll"):
        assert key in payload
        assert payload[key]["status"] in {"ok", "error"}

    assert payload["cgo_submit"]["status"] == "ok"
    assert payload["cgo_poll"]["status"] == "ok"
