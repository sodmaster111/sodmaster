"""Fundraise tracking utilities for the dashboard."""

from __future__ import annotations

import asyncio
from asyncio import QueueEmpty
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Deque, Dict, Optional


TIER_LABELS: tuple[str, ...] = ("Founder", "Early", "Community")


def _truncate_wallet(wallet: Optional[str]) -> Optional[str]:
    if not wallet:
        return None
    if len(wallet) <= 10:
        return wallet
    return f"{wallet[:6]}…{wallet[-4:]}"


@dataclass(slots=True)
class FundraiseTransaction:
    """Internal representation of a contribution event."""

    occurred_at: datetime
    amount_usd: float
    currency: str
    tier: str
    wallet: Optional[str]

    def as_payload(self) -> Dict[str, object]:
        return {
            "time": self.occurred_at.isoformat(),
            "amount_usd": round(self.amount_usd, 2),
            "currency": self.currency,
            "tier": self.tier,
            "wallet": self.wallet,
            "wallet_truncated": _truncate_wallet(self.wallet),
        }


class FundraiseTracker:
    """Thread-safe accumulator for fundraise progress."""

    def __init__(self, *, goal_usd: float = 1_000_000.0) -> None:
        self._goal = float(goal_usd)
        self._total = 0.0
        self._by_tier: Dict[str, float] = {tier: 0.0 for tier in TIER_LABELS}
        self._transactions: Deque[FundraiseTransaction] = deque(maxlen=10)
        self._lock = asyncio.Lock()
        self._subscribers: set[asyncio.Queue[dict]] = set()

    @property
    def goal_usd(self) -> float:
        return self._goal

    async def reset(self) -> None:
        async with self._lock:
            self._total = 0.0
            for tier in TIER_LABELS:
                self._by_tier[tier] = 0.0
            self._transactions.clear()
            snapshot = self._serialize()
        await self._publish(snapshot)

    async def record_transaction(
        self,
        *,
        tier: str,
        amount_usd: float,
        currency: str,
        wallet: Optional[str] = None,
        occurred_at: Optional[datetime] = None,
    ) -> dict:
        normalized_tier = tier if tier in self._by_tier else "Community"
        event_time = occurred_at or datetime.now(timezone.utc)

        async with self._lock:
            self._total += float(amount_usd)
            self._by_tier.setdefault(normalized_tier, 0.0)
            self._by_tier[normalized_tier] += float(amount_usd)

            txn = FundraiseTransaction(
                occurred_at=event_time,
                amount_usd=float(amount_usd),
                currency=currency,
                tier=normalized_tier,
                wallet=wallet,
            )
            self._transactions.appendleft(txn)
            snapshot = self._serialize()

        await self._publish(snapshot)
        return snapshot

    async def status(self) -> dict:
        async with self._lock:
            return self._serialize()

    def subscribe(self) -> asyncio.Queue[dict]:
        queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=1)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict]) -> None:
        self._subscribers.discard(queue)

    async def _publish(self, snapshot: dict) -> None:
        if not self._subscribers:
            return
        for queue in tuple(self._subscribers):
            try:
                queue.put_nowait(snapshot)
            except asyncio.QueueFull:
                try:
                    _ = queue.get_nowait()
                except QueueEmpty:
                    pass
                queue.put_nowait(snapshot)

    def _serialize(self) -> dict:
        return {
            "total_usd": round(self._total, 2),
            "by_tier": {tier: round(self._by_tier.get(tier, 0.0), 2) for tier in TIER_LABELS},
            "last_transactions": [txn.as_payload() for txn in list(self._transactions)],
        }


def truncate_wallet(wallet: Optional[str]) -> Optional[str]:
    """Expose wallet truncation for re-use in tests or UI helpers."""

    return _truncate_wallet(wallet)


__all__ = ["FundraiseTracker", "truncate_wallet", "TIER_LABELS"]
