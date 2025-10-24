import sys
from pathlib import Path

import pytest
from fastapi import status


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _reset_job_store(monkeypatch):
    from app.main import app
    from app.infra import InMemoryJobStore

    store = InMemoryJobStore()
    monkeypatch.setattr(app.state, "job_store", store)
    yield store


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from app.main import app

    return TestClient(app)


def test_get_on_a2a_command_returns_method_not_allowed_json(client):
    response = client.get("/a2a/command")

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert response.json() == {
        "error": "method_not_allowed",
        "detail": "Use POST /a2a/command",
    }


def test_get_on_cgo_run_marketing_campaign_returns_method_not_allowed_json(client):
    response = client.get("/api/v1/cgo/run-marketing-campaign")

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert response.json() == {
        "error": "method_not_allowed",
        "detail": "Use POST /api/v1/cgo/run-marketing-campaign",
    }


def test_options_preflight_includes_cors_headers(client):
    response = client.options("/a2a/command")

    assert response.status_code == status.HTTP_200_OK
    allow_methods = response.headers.get("access-control-allow-methods", "")
    assert "POST" in allow_methods
    assert "OPTIONS" in allow_methods
    assert response.headers.get("access-control-allow-origin") == "*"


def test_post_a2a_command_uses_declared_status_and_model(client):
    payload = {
        "source": "maf",
        "target": "ops",
        "command": "noop",
        "payload": {},
    }

    response = client.post("/a2a/command", json=payload)

    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()
    assert data["status"] == "accepted"
    assert "job_id" in data


def test_post_cgo_marketing_campaign_returns_accepted_model(client, monkeypatch):
    monkeypatch.setattr(
        "app.cgo.routes._execute_marketing_campaign",
        lambda job_id: {"ok": True},
    )

    response = client.post("/api/v1/cgo/run-marketing-campaign")

    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()
    assert data["status"] == "accepted"
    assert "job_id" in data
    assert "result" in data
