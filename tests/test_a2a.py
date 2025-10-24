from __future__ import annotations

import logging
import hashlib
import hmac
import json
import sys
import time
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


def test_job_executes_in_background(client, caplog):
    caplog.set_level(logging.INFO)
    payload = {
        "source": "maf",
        "target": "ops",
        "command": "ping",
        "payload": {"value": 42},
    }

    response = client.post("/a2a/command", json=payload)
    job_id = response.json()["job_id"]

    for _ in range(5):
        status_response = client.get(f"/a2a/jobs/{job_id}")
        body = status_response.json()
        if body["status"] == "done":
            assert body["result"] == {"status": "pong", "echo": {"value": 42}}
            break
        time.sleep(0.1)
    else:
        pytest.fail("A2A job did not complete in time")

    assert any(
        getattr(record, "event", None) == "a2a_start" and getattr(record, "job_id", None) == job_id
        for record in caplog.records
    )
    assert any(
        getattr(record, "event", None) == "a2a_done" and getattr(record, "job_id", None) == job_id
        for record in caplog.records
    )


def test_job_failure_is_reported(client, caplog):
    caplog.set_level(logging.INFO)
    payload = {
        "source": "maf",
        "target": "ops",
        "command": "unknown",
        "payload": {},
    }

    response = client.post("/a2a/command", json=payload)
    job_id = response.json()["job_id"]

    for _ in range(5):
        status_response = client.get(f"/a2a/jobs/{job_id}")
        body = status_response.json()
        if body["status"] == "failed":
            assert "Unsupported A2A command" in body["result"]["reason"]
            break
        time.sleep(0.1)
    else:
        pytest.fail("A2A job did not fail in time")

    assert any(
        getattr(record, "event", None) == "a2a_start" and getattr(record, "job_id", None) == job_id
        for record in caplog.records
    )
    assert any(
        getattr(record, "event", None) == "a2a_failed" and getattr(record, "job_id", None) == job_id
        for record in caplog.records
    )

    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200
    assert 'status="failed"' in metrics_response.text


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


def test_a2a_metrics_capture_lifecycle(client):
    payload = {
        "source": "maf",
        "target": "ops",
        "command": "ping",
        "payload": {"value": 99},
    }

    response = client.post("/a2a/command", json=payload)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    deadline = time.time() + 5
    while time.time() < deadline:
        status_response = client.get(f"/a2a/jobs/{job_id}")
        if status_response.json()["status"] == "done":
            break
        time.sleep(0.05)
    else:
        pytest.fail("A2A job did not finish for metrics capture")

    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200
    body = metrics_response.text

    assert "a2a_jobs_total" in body
    assert 'status="accepted"' in body
    assert 'status="running"' in body
    assert 'status="done"' in body
    assert "a2a_job_duration_seconds_count" in body
