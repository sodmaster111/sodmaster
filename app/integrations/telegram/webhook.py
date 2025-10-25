"""Utilities for validating Telegram Bot API webhook requests."""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Mapping, MutableMapping


_TELEGRAM_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"


def verify_secret_token(headers: Mapping[str, str], expected_secret: str | None) -> bool:
    """Validate Telegram webhook secret token header.

    Telegram sends the opaque ``X-Telegram-Bot-Api-Secret-Token`` header with
    every webhook request when it is configured on ``setWebhook``. The header is
    a verbatim echo of the configured secret and should be compared using a
    timing-safe check.
    """

    if not expected_secret:
        return True
    provided = headers.get(_TELEGRAM_SECRET_HEADER)
    if provided is None:
        return False
    return hmac.compare_digest(provided, expected_secret)


def verify_init_data(init_data: MutableMapping[str, str], bot_token: str, *, max_age: int = 300) -> bool:
    """Validate Telegram Mini App ``initData`` payload according to the spec."""

    if not bot_token:
        raise ValueError("bot_token is required for initData verification")

    auth_date = init_data.get("auth_date")
    received_hash = init_data.get("hash")
    if not auth_date or not received_hash:
        return False

    try:
        auth_ts = int(auth_date)
    except ValueError:
        return False

    if time.time() - auth_ts > max_age:
        return False

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(init_data.items()) if k != "hash"
    )
    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed_hash, received_hash)


__all__ = ["verify_init_data", "verify_secret_token"]
