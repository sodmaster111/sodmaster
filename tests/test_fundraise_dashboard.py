import asyncio
from datetime import datetime, timedelta, timezone

import pytest

pytest.importorskip("fastapi")

from app.main import app


def _tracker():
    return app.state.fundraise_tracker


def test_fundraise_status_accumulates(client):
    tracker = _tracker()
    asyncio.run(tracker.reset())

    base_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    asyncio.run(
        tracker.record_transaction(
            tier="Founder",
            amount_usd=250_000,
            currency="USDC",
            wallet="0xAA111122223333444455556666777788889999",
            occurred_at=base_time,
        )
    )
    asyncio.run(
        tracker.record_transaction(
            tier="Early",
            amount_usd=75_000,
            currency="ETH",
            wallet="0xbbccddeeff0011223344556677889900aabbcc",
            occurred_at=base_time + timedelta(minutes=2),
        )
    )
    asyncio.run(
        tracker.record_transaction(
            tier="Community",
            amount_usd=12_500,
            currency="USDT",
            wallet="terra1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq",
            occurred_at=base_time + timedelta(minutes=3),
        )
    )

    response = client.get("/api/v1/fundraise/status")
    assert response.status_code == 200
    payload = response.json()

    assert payload["total_usd"] == 337500.0
    assert payload["by_tier"]["Founder"] == 250000.0
    assert payload["by_tier"]["Early"] == 75000.0
    assert payload["by_tier"]["Community"] == 12500.0

    assert len(payload["last_transactions"]) == 3
    latest = payload["last_transactions"][0]
    assert latest["tier"] == "Community"
    assert latest["wallet_truncated"].startswith("terra1")
    assert latest["wallet_truncated"].endswith("qqqq")


def test_websocket_streams_live_updates(client):
    tracker = _tracker()
    asyncio.run(tracker.reset())

    with client.websocket_connect("/ws/fundraise") as websocket:
        initial = websocket.receive_json()
        assert initial["total_usd"] == 0
        assert initial["by_tier"] == {"Founder": 0.0, "Early": 0.0, "Community": 0.0}

        asyncio.run(
            tracker.record_transaction(
                tier="Founder",
                amount_usd=500_000,
                currency="BTC",
                wallet="0xfeedbeadfeedbeadfeedbeadfeedbeadfeedbead",
            )
        )

        update = websocket.receive_json()
        assert update["total_usd"] == 500000.0
        assert update["by_tier"]["Founder"] == 500000.0
        assert update["last_transactions"][0]["wallet_truncated"].startswith("0xfeed")


def test_transaction_history_capped_at_ten(client):
    tracker = _tracker()
    asyncio.run(tracker.reset())

    for index in range(12):
        asyncio.run(
            tracker.record_transaction(
                tier="Community",
                amount_usd=10_000 + index,
                currency="USDC",
                wallet=f"0x{index:02x}{index:02x}{index:02x}{index:02x}{index:02x}{index:02x}{index:02x}{index:02x}",
            )
        )

    payload = client.get("/api/v1/fundraise/status").json()
    assert len(payload["last_transactions"]) == 10
    first_amount = payload["last_transactions"][0]["amount_usd"]
    last_amount = payload["last_transactions"][-1]["amount_usd"]
    assert first_amount == 10_011.0
    assert last_amount == 10_002.0
