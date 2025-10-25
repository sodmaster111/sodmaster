import pytest
from fastapi.testclient import TestClient

# Import app correctly
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_readiness_endpoint():
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
