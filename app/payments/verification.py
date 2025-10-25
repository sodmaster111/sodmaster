"""Blockchain transaction verification helpers."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Callable, Mapping

import httpx


class TransactionVerificationError(RuntimeError):
    """Raised when a blockchain transaction cannot be validated."""


@dataclass
class VerificationResult:
    """Represents the outcome of a verification request."""

    confirmations: int
    raw: Mapping[str, object]


class TransactionVerifier:
    """Verify incoming blockchain transactions using public explorer APIs."""

    def __init__(
        self,
        *,
        http_client_factory: Callable[[], httpx.AsyncClient] | None = None,
        etherscan_api_key: str | None = None,
    ) -> None:
        self._http_client_factory = http_client_factory or (lambda: httpx.AsyncClient(timeout=10.0))
        self._etherscan_api_key = etherscan_api_key or os.getenv("ETHERSCAN_API_KEY", "")

    async def verify(self, currency: str, tx_hash: str, destination: str) -> VerificationResult:
        """Return the confirmation count for the transaction or raise an error."""

        normalised = currency.upper()
        if normalised == "BTC":
            return await self._verify_btc(tx_hash, destination)
        if normalised == "ETH":
            return await self._verify_eth(tx_hash, destination)
        if normalised == "TON":
            return await self._verify_ton(tx_hash, destination)
        raise TransactionVerificationError(f"Unsupported currency: {currency}")

    async def _verify_btc(self, tx_hash: str, destination: str) -> VerificationResult:
        async with self._http_client_factory() as client:
            tx_url = f"https://blockstream.info/api/tx/{tx_hash}"
            response = await client.get(tx_url)
            response.raise_for_status()
            tx_data = response.json()

            outputs = tx_data.get("vout", [])
            if not any(out.get("scriptpubkey_address") == destination for out in outputs):
                raise TransactionVerificationError("destination_mismatch")

            status = tx_data.get("status") or {}
            if not status.get("confirmed"):
                return VerificationResult(confirmations=0, raw=tx_data)

            block_height = status.get("block_height")
            tip_response = await client.get("https://blockstream.info/api/blocks/tip/height")
            tip_response.raise_for_status()
            tip_height = int(tip_response.text.strip())
            confirmations = max(0, tip_height - int(block_height) + 1)
            return VerificationResult(confirmations=confirmations, raw=tx_data)

    async def _verify_eth(self, tx_hash: str, destination: str) -> VerificationResult:
        async with self._http_client_factory() as client:
            params = {
                "module": "proxy",
                "action": "eth_getTransactionByHash",
                "txhash": tx_hash,
            }
            if self._etherscan_api_key:
                params["apikey"] = self._etherscan_api_key
            response = await client.get("https://api.etherscan.io/api", params=params)
            response.raise_for_status()
            data = response.json()

            result = data.get("result")
            if not result:
                raise TransactionVerificationError("transaction_not_found")

            to_address = (result.get("to") or "").lower()
            if to_address != destination.lower():
                raise TransactionVerificationError("destination_mismatch")

            block_hex = result.get("blockNumber")
            if block_hex in (None, "0x", "0x0"):
                return VerificationResult(confirmations=0, raw=data)

            block_number = int(block_hex, 16)

            latest_params = {"module": "proxy", "action": "eth_blockNumber"}
            if self._etherscan_api_key:
                latest_params["apikey"] = self._etherscan_api_key
            latest_response = await client.get("https://api.etherscan.io/api", params=latest_params)
            latest_response.raise_for_status()
            latest_data = latest_response.json()
            latest_block_hex = latest_data.get("result")
            if not latest_block_hex:
                raise TransactionVerificationError("cannot_fetch_latest_block")
            latest_block = int(latest_block_hex, 16)

            confirmations = max(0, latest_block - block_number + 1)
            merged = json.loads(json.dumps(data))  # ensure Mapping[str, object]
            return VerificationResult(confirmations=confirmations, raw=merged)

    async def _verify_ton(self, tx_hash: str, destination: str) -> VerificationResult:
        async with self._http_client_factory() as client:
            url = f"https://tonapi.io/v2/blockchain/transactions/{tx_hash}"
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            in_msg = data.get("in_msg") or {}
            dest = ((in_msg.get("destination") or {}).get("address") or "").lower()
            if dest != destination.lower():
                raise TransactionVerificationError("destination_mismatch")

            status = data.get("status", "pending")
            if status != "finalized":
                return VerificationResult(confirmations=0, raw=data)

            lt = data.get("lt")
            confirmations = 1 if lt else 0
            return VerificationResult(confirmations=confirmations, raw=data)
