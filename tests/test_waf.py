"""Tests for the lightweight WordPress scanner shield middleware."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

_WP_PATHS = [
    "/wp-admin",
    "/wordpress",
    "/wp/index.php",
    "/blog/wp-admin",
    "/new/wp-admin",
    "/old/wp-admin",
    "/shop/wp-admin",
    "/test/wp-admin",
]


def _get_client() -> TestClient:
    return TestClient(app)


@pytest.mark.parametrize("path", _WP_PATHS)
def test_wp_scanner_paths_blocked(path: str):
    client = _get_client()
    response = client.get(path)
    assert response.status_code == 404
    assert response.json() == {"error": "not_found"}


@pytest.mark.parametrize("path", _WP_PATHS)
def test_wp_scanner_metrics_exposed(path: str):
    client = _get_client()
    client.get(path)
    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200
    body = metrics_response.text
    assert "waf_block_total" in body
    assert 'path_group="wp"' in body


def test_wp_shield_does_not_block_legitimate_paths():
    client = _get_client()
    response = client.get("/")
    assert response.status_code == 200
