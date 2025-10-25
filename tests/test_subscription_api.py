import pytest

from app.main import app


@pytest.fixture(autouse=True)
def reset_subscription_repo():
    repo = app.state.subscription_repo
    repo.reset()
    yield
    repo.reset()


def test_create_subscription_invoice(client):
    payload = {"tier": "growth", "currency": "btc", "amount_usd": 249}
    response = client.post("/api/v1/subscribe/create", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["invoice_id"]
    assert data["payment_url"].endswith(f"{data['invoice_id']}?currency=btc")
    assert data["status"] == "pending"
    assert data["amount_usd"] == pytest.approx(249)

    record = app.state.subscription_repo.get(data["invoice_id"])
    assert record is not None
    assert record.tier == "growth"
    assert record.status.value == "pending"

    metrics_response = client.get("/metrics")
    metrics_body = metrics_response.text
    assert "subscription_total_usd" in metrics_body
    assert "subscription_count" in metrics_body


def test_subscription_status_not_found(client):
    response = client.get("/api/v1/subscribe/status/unknown")
    assert response.status_code == 404
    assert response.json()["detail"] == "invoice_not_found"


def test_subscription_webhook_e2e(client):
    create_payload = {"tier": "starter", "currency": "ETH", "amount_usd": 99}
    create_response = client.post("/api/v1/subscribe/create", json=create_payload)
    assert create_response.status_code == 200
    invoice_id = create_response.json()["invoice_id"]

    webhook_payload = {"invoice_id": invoice_id, "tx_hash": "0xabc123", "currency": "ETH"}
    webhook_response = client.post("/api/v1/subscribe/webhook", json=webhook_payload)
    assert webhook_response.status_code == 200

    status_response = client.get(f"/api/v1/subscribe/status/{invoice_id}")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["status"] == "paid"
    assert status_data["tx_hash"] == "0xabc123"

    history = app.state.audit_trail.history
    assert any(event.name == "subscription.invoice.paid" and event.subject == invoice_id for event in history)

    metrics_body = client.get("/metrics").text
    assert "subscription_conversion_rate" in metrics_body

    parsed_metrics = {
        line.split(" ")[0]: line.split(" ")[1]
        for line in metrics_body.splitlines()
        if line.startswith("subscription_conversion_rate")
    }
    assert float(parsed_metrics["subscription_conversion_rate"]) == pytest.approx(1.0)


def test_webhook_missing_invoice(client):
    response = client.post(
        "/api/v1/subscribe/webhook",
        json={"invoice_id": "missing", "tx_hash": "0xdead", "currency": "BTC"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "invoice_not_found"
