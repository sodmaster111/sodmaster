import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_admin_page():
    response = client.get("/admin")
    assert response.status_code == 200
    assert b"Admin Dashboard" in response.content
