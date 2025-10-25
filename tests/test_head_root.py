"""Regression tests ensuring HEAD requests are accepted at the root level."""

from fastapi.testclient import TestClient

from app.main import app


def test_head_root_returns_200_with_empty_body():
    client = TestClient(app)
    response = client.head("/")
    assert response.status_code == 200
    assert response.text == ""
