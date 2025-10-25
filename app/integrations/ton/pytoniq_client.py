"""Lightweight adapter around the pytoniq client."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    import pytoniq
    from pytoniq.core import Address
except ImportError:  # pragma: no cover - executed in tests without pytoniq
    pytoniq = None  # type: ignore[assignment]
    Address = None  # type: ignore[assignment]


@dataclass
class PytoniqClient:
    """A very small convenience wrapper around pytoniq.AsyncLiteClient."""

    endpoint: str = "https://sandbox.tonhubapi.com/jsonRPC"
    timeout: float = 10.0
    _client: Any = None

    def __post_init__(self) -> None:
        if pytoniq is None:
            logger.warning("pytoniq is not installed; PytoniqClient will operate in stub mode")
            return

        if not hasattr(pytoniq, "AsyncLiteClient"):
            raise RuntimeError("Installed pytoniq version does not expose AsyncLiteClient")

        # pytoniq ships an AsyncLiteClient that speaks to lite servers via RPC.
        self._client = pytoniq.AsyncLiteClient.from_url(self.endpoint, timeout=self.timeout)

    @property
    def is_stub(self) -> bool:
        return self._client is None

    async def get_balance(self, address: str) -> int:
        if self.is_stub:
            raise RuntimeError("pytoniq is not installed; cannot query TON balances")
        ton_address = Address(address)
        return await self._client.get_balance(ton_address)

    async def send_transaction(self, wallet: Any, destination: str, amount: int, *, payload: bytes | None = None) -> str:
        if self.is_stub:
            raise RuntimeError("pytoniq is not installed; cannot send TON transactions")
        dest_address = Address(destination)
        return await self._client.transfer(wallet=wallet, destination=dest_address, amount=amount, payload=payload)

    async def close(self) -> None:
        if self.is_stub:
            return
        await self._client.close()


__all__ = ["PytoniqClient"]
