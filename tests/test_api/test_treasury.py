import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_balances():
    response = client.get("/api/v1/treasury/balances")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data


def test_get_prices():
    response = client.get("/api/v1/treasury/prices")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_get_portfolio_value():
    response = client.get("/api/v1/treasury/portfolio-value")
    assert response.status_code == 200
    data = response.json()
    assert "total_usd" in data["data"]


def test_get_wallet_addresses():
    response = client.get("/api/v1/treasury/wallets")
    assert response.status_code == 200
    data = response.json()
    assert "btc" in data["data"]
    assert "eth" in data["data"]
