import pytest

pytest.importorskip("fastapi")

from app.main import app


@pytest.fixture(autouse=True)
def reset_whitelist():
    app.state.treasury_whitelist.clear()
    yield
    app.state.treasury_whitelist.clear()


def test_whitelist_wallet_requires_authorized_role(client):
    response = client.post(
        "/api/v1/treasury/whitelist_wallet",
        json={"chain": "eth", "address": "0xabc"},
        headers={"X-Org-Roles": "analyst"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "insufficient_role"


def test_whitelist_wallet_missing_role_header(client):
    response = client.post(
        "/api/v1/treasury/whitelist_wallet",
        json={"chain": "eth", "address": "0xabc"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "role_header_required"


def test_whitelist_wallet_authorized_roles_can_register(client):
    response = client.post(
        "/api/v1/treasury/whitelist_wallet",
        json={"chain": "ton", "address": "UQABC123"},
        headers={"X-Org-Roles": "cfo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "status": "whitelisted",
        "chain": "TON",
        "address": "UQABC123",
    }

    assert "TON" in app.state.treasury_whitelist
    assert "UQABC123" in app.state.treasury_whitelist["TON"]

    # CLO alone should also pass
    clo_response = client.post(
        "/api/v1/treasury/whitelist_wallet",
        json={"chain": "btc", "address": "bc1qxyz"},
        headers={"X-Org-Roles": "CLO"},
    )
    assert clo_response.status_code == 200
    assert "BC1QXYZ" in {addr.upper() for addr in app.state.treasury_whitelist["BTC"]}
