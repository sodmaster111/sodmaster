from __future__ import annotations

import hashlib
import hmac
import json
import sys
from pathlib import Path

import pytest


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


def _sign(secret: str, payload: dict[str, object]) -> str:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_submit_command_returns_job_id(client):
    payload = {
        "source": "maf",
        "target": "cunit",
        "command": "ping",
        "payload": {"foo": "bar"},
    }

    response = client.post("/a2a/command", json=payload)

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert "job_id" in data

    job = client.app.state.job_store._jobs[data["job_id"]]
    assert job["payload"]["command"]["source"] == "maf"


def test_submit_command_is_idempotent(client):
    payload = {
        "source": "maf",
        "target": "ops",
        "command": "deploy",
        "payload": {"version": "1.2.3"},
        "idempotency_key": "deploy-1.2.3",
    }

    first = client.post("/a2a/command", json=payload)
    second = client.post("/a2a/command", json=payload)

    assert first.status_code == 202
    assert second.status_code == 200
    assert first.json()["job_id"] == second.json()["job_id"] == "deploy-1.2.3"


def test_signature_required_when_secret_set(client, monkeypatch):
    secret = "supersecret"
    monkeypatch.setenv("A2A_SECRET", secret)

    unsigned = client.post(
        "/a2a/command",
        json={"source": "maf", "target": "ops", "command": "noop", "payload": {}},
    )
    assert unsigned.status_code == 401

    payload = {
        "source": "maf",
        "target": "ops",
        "command": "noop",
        "payload": {},
    }
    signature = _sign(secret, payload)
    signed = client.post(
        "/a2a/command",
        json=payload,
        headers={"X-A2A-Signature": signature},
    )
    assert signed.status_code == 202


def test_metrics_include_a2a_route(client):
    payload = {
        "source": "maf",
        "target": "ops",
        "command": "noop",
        "payload": {},
    }
    client.post("/a2a/command", json=payload)

    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200
    assert 'path="/a2a/command"' in metrics_response.text
