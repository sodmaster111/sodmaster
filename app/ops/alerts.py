"""Notification helpers for operational alerts."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Dict, Iterable, Tuple

logger = logging.getLogger(__name__)


def _iter_configured_webhooks() -> Iterable[Tuple[str, str]]:
    """Yield configured webhook destinations as (name, url) tuples."""

    for env_name in ("TELEGRAM_WEBHOOK", "SLACK_WEBHOOK"):
        url = os.getenv(env_name, "").strip()
        if url:
            yield env_name, url


def send_alert(event: str, payload: Dict[str, object]) -> bool:
    """Send an alert payload to the configured webhook destinations.

    Returns ``True`` if at least one request was attempted successfully.
    """

    body = json.dumps({"event": event, "payload": payload}).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    delivered = False
    webhooks = list(_iter_configured_webhooks())
    if not webhooks:
        logger.info({"event": "alert_skipped", "trigger": event, "reason": "no_webhook"})
        return False

    for name, url in webhooks:
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=5):  # nosec: B310 - trusted config
                delivered = True
        except urllib.error.URLError:
            logger.exception("Failed to send alert", extra={"event": event, "webhook": name})

    log_event = {"event": "alert_sent" if delivered else "alert_skipped", "trigger": event}
    if not delivered:
        log_event["reason"] = "delivery_failed"
    logger.info(log_event)
    return delivered
