import hashlib
import hmac
import json
from types import SimpleNamespace

import pytest

from app.main import app
from app.payments import PaymentRouter


@pytest.fixture(autouse=True)
def reset_subscription_repo():
    repo = app.state.subscription_repo
    repo.reset()
    yield
    repo.reset()


@pytest.fixture()
def webhook_context(monkeypatch):
    secret = "test-webhook-secret"
    monkeypatch.setenv("A2A_SECRET", secret)

    original_verifier = app.state.transaction_verifier

    class DummyVerifier:
        async def verify(self, currency, tx_hash, destination):
            return SimpleNamespace(confirmations=6, raw={"currency": currency, "tx": tx_hash, "destination": destination})

    app.state.transaction_verifier = DummyVerifier()
    try:
        yield secret
    finally:
        app.state.transaction_verifier = original_verifier


def _sign_payload(payload: dict, secret: str) -> tuple[str, dict[str, str]]:
    body = json.dumps(payload, separators=(",", ":"))
    signature = hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-A2A-Signature": signature,
    }
    return body, headers


def test_create_subscription_invoice(client):
    payload = {"tier": "growth", "currency": "btc", "amount_usd": 249}
    response = client.post("/api/v1/subscribe/create", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["invoice_id"]
    assert data["payment_url"].endswith(f"{data['invoice_id']}?currency=btc")
    assert data["payment_uri"] == f"bitcoin:{PaymentRouter.BTC_ADDR}"
    assert data["payment_qr"].startswith("https://api.qrserver.com")
    assert data["status"] == "pending"
    assert data["amount_usd"] == pytest.approx(249)

    record = app.state.subscription_repo.get(data["invoice_id"])
    assert record is not None
    assert record.tier == "growth"
    assert record.status.value == "pending"
    assert record.destination_address == PaymentRouter.BTC_ADDR
    assert record.tx_confirmations == 0

    metrics_response = client.get("/metrics")
    metrics_body = metrics_response.text
    assert "subscription_total_usd" in metrics_body
    assert "subscription_count" in metrics_body
    assert f'payments_total{{currency="BTC"}}' in metrics_body


def test_subscription_status_not_found(client):
    response = client.get("/api/v1/subscribe/status/unknown")
    assert response.status_code == 404
    assert response.json()["detail"] == "invoice_not_found"


def test_subscription_webhook_e2e(client, webhook_context):
    create_payload = {"tier": "starter", "currency": "ETH", "amount_usd": 99}
    create_response = client.post("/api/v1/subscribe/create", json=create_payload)
    assert create_response.status_code == 200
    invoice_id = create_response.json()["invoice_id"]

    webhook_payload = {"invoice_id": invoice_id, "tx_hash": "0xabc123", "currency": "ETH"}
    body, headers = _sign_payload(webhook_payload, webhook_context)
    webhook_response = client.post("/api/v1/subscribe/webhook", data=body, headers=headers)
    assert webhook_response.status_code == 200

    status_response = client.get(f"/api/v1/subscribe/status/{invoice_id}")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["status"] == "paid"
    assert status_data["tx_hash"] == "0xabc123"
    assert status_data["tx_confirmations"] == 6
    assert status_data["destination_address"] == PaymentRouter.ETH_ADDR

    history = app.state.audit_trail.history
    assert any(event.name == "subscription.invoice.paid" and event.subject == invoice_id for event in history)

    metrics_body = client.get("/metrics").text
    assert "subscription_conversion_rate" in metrics_body
    assert "confirmations_pending_total" in metrics_body

    parsed_metrics = {
        line.split(" ")[0]: line.split(" ")[1]
        for line in metrics_body.splitlines()
        if line.startswith("subscription_conversion_rate")
    }
    assert float(parsed_metrics["subscription_conversion_rate"]) == pytest.approx(1.0)


def test_webhook_missing_invoice(client, webhook_context):
    payload = {"invoice_id": "missing", "tx_hash": "0xdead", "currency": "BTC"}
    body, headers = _sign_payload(payload, webhook_context)
    response = client.post("/api/v1/subscribe/webhook", data=body, headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "invoice_not_found"
