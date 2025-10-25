import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["version"] == "0.1.0"
    assert payload["service"] == "sodmaster-c-unit"
    assert "timestamp" in payload
    assert payload["python_version"].count(".") == 2


def test_ready_endpoint(client):
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is True
    assert payload["checks"] == {
        "api": "ok",
        "database": "not_configured",
        "redis": "not_configured",
    }


def test_health_head_request(client):
    response = client.head("/api/v1/health")
    assert response.status_code == 200
    assert response.content in (b"", None)
