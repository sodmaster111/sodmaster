import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_wallets():
    response = client.get("/api/v1/wallets")
    assert response.status_code == 200
    data = response.json()
    assert "btc" in data
    assert "eth" in data
    assert "ton" in data


def test_create_subscription():
    response = client.post("/api/v1/subscribe", json={
        "email": "test@example.com",
        "plan": "starter",
        "crypto": "btc",
        "tx_hash": "test_tx_hash_123456789"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["plan"] == "starter"
