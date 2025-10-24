"""Tests for standardized 405 responses."""

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from app.main import app

    return TestClient(app)


def test_get_on_post_endpoint_returns_json_405(client):
    response = client.get("/api/v1/cto/run-research")

    assert response.status_code == 405
    assert response.json() == {
        "error": "method_not_allowed",
        "detail": "use one of: ['POST']",
    }
