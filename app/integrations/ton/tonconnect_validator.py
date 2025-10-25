"""Helpers for validating TON Connect authentication payloads."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any, Dict, Mapping


def decode_connect_payload(payload: str) -> Dict[str, Any]:
    """Decode the base64url payload sent by TON Connect clients."""

    padding = '=' * (-len(payload) % 4)
    decoded = base64.urlsafe_b64decode(payload + padding)
    return json.loads(decoded)


def verify_wallet_proof(payload: Mapping[str, Any], secret: str) -> bool:
    """Verify TON Connect proof signature using shared secret."""

    if not secret:
        raise ValueError("secret is required to validate TON Connect proof")
    proof = payload.get("proof")
    if not isinstance(proof, Mapping):
        return False

    signature = proof.get("signature")
    state_init = proof.get("state_init")
    if not signature or not state_init:
        return False

    message = json.dumps(
        {
            "address": payload.get("address"),
            "proof": {"timestamp": proof.get("timestamp"), "state_init": state_init},
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    try:
        provided = base64.b64decode(signature)
    except Exception:
        return False
    return hmac.compare_digest(digest, provided)


__all__ = ["decode_connect_payload", "verify_wallet_proof"]
