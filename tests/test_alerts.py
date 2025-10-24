import json
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:  # pragma: no cover - defensive path setup
    sys.path.append(str(ROOT_DIR))

from app.ops.alerts import send_alert


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    monkeypatch.delenv("ALERT_WEBHOOK", raising=False)
    yield


def test_send_alert_skips_when_no_webhooks(caplog):
    caplog.set_level("INFO")

    delivered = send_alert("job_failed", {"job_id": "123"})

    assert delivered is False
    assert any(
        record.msg
        == {"event": "alert_skipped", "trigger": "job_failed", "reason": "no_webhook"}
        for record in caplog.records
    )


def test_send_alert_posts_to_configured_webhooks(monkeypatch, caplog):
    caplog.set_level("INFO")

    payloads = []

    def fake_urlopen(request, timeout=0):  # pragma: no cover - helper for tests
        payloads.append(
            {
                "url": request.full_url,
                "data": json.loads(request.data.decode("utf-8")),
                "headers": dict(request.header_items()),
            }
        )
        return mock.MagicMock()

    monkeypatch.setenv("ALERT_WEBHOOK", "https://alerts.example")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    delivered = send_alert("job_failed", {"job_id": "abc"})

    assert delivered is True
    assert payloads == [
        {
            "url": "https://alerts.example",
            "data": {"event": "job_failed", "payload": {"job_id": "abc"}},
            "headers": {"Content-type": "application/json"},
        },
    ]
    assert any(
        record.msg == {"event": "alert_sent", "trigger": "job_failed"}
        for record in caplog.records
    )
