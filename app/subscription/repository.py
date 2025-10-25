"""Persistence layer for subscription invoices."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Iterable, Optional

from .models import SubscriptionRecord, SubscriptionStatus


class SubscriptionRepository:
    """SQLite-backed repository for subscriptions."""

    def __init__(self, db_path: str | Path) -> None:
        path = Path(db_path)
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(path), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = Lock()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id TEXT PRIMARY KEY,
                    tier TEXT NOT NULL,
                    user_wallet TEXT,
                    currency TEXT NOT NULL,
                    amount_usd REAL NOT NULL,
                    tx_hash TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def create(
        self,
        *,
        subscription_id: str,
        tier: str,
        currency: str,
        amount_usd: float,
        user_wallet: Optional[str],
        status: SubscriptionStatus,
        created_at: datetime,
    ) -> SubscriptionRecord:
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO subscriptions (id, tier, user_wallet, currency, amount_usd, tx_hash, status, created_at)
                VALUES (?, ?, ?, ?, ?, NULL, ?, ?)
                """,
                (subscription_id, tier, user_wallet, currency, amount_usd, status.value, created_at.isoformat()),
            )
        return SubscriptionRecord(
            id=subscription_id,
            tier=tier,
            user_wallet=user_wallet,
            currency=currency,
            amount_usd=amount_usd,
            tx_hash=None,
            status=status,
            created_at=created_at,
        )

    def get(self, subscription_id: str) -> Optional[SubscriptionRecord]:
        cursor = self._connection.execute(
            "SELECT id, tier, user_wallet, currency, amount_usd, tx_hash, status, created_at FROM subscriptions WHERE id = ?",
            (subscription_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return SubscriptionRecord(
            id=row["id"],
            tier=row["tier"],
            user_wallet=row["user_wallet"],
            currency=row["currency"],
            amount_usd=row["amount_usd"],
            tx_hash=row["tx_hash"],
            status=SubscriptionStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def update_payment(
        self,
        subscription_id: str,
        *,
        currency: str,
        tx_hash: str,
        status: SubscriptionStatus,
        user_wallet: Optional[str] = None,
    ) -> Optional[SubscriptionRecord]:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                UPDATE subscriptions
                SET currency = ?, tx_hash = ?, status = ?, user_wallet = COALESCE(?, user_wallet)
                WHERE id = ?
                """,
                (currency, tx_hash, status.value, user_wallet, subscription_id),
            )
        if cursor.rowcount == 0:
            return None
        return self.get(subscription_id)

    def count(self) -> int:
        cursor = self._connection.execute("SELECT COUNT(*) FROM subscriptions")
        (count,) = cursor.fetchone()
        return int(count)

    def count_by_status(self, status: SubscriptionStatus) -> int:
        cursor = self._connection.execute(
            "SELECT COUNT(*) FROM subscriptions WHERE status = ?",
            (status.value,),
        )
        (count,) = cursor.fetchone()
        return int(count)

    def all(self) -> Iterable[SubscriptionRecord]:
        cursor = self._connection.execute(
            "SELECT id, tier, user_wallet, currency, amount_usd, tx_hash, status, created_at FROM subscriptions"
        )
        for row in cursor.fetchall():
            yield SubscriptionRecord(
                id=row["id"],
                tier=row["tier"],
                user_wallet=row["user_wallet"],
                currency=row["currency"],
                amount_usd=row["amount_usd"],
                tx_hash=row["tx_hash"],
                status=SubscriptionStatus(row["status"]),
                created_at=datetime.fromisoformat(row["created_at"]),
            )

    def reset(self) -> None:
        with self._lock, self._connection:
            self._connection.execute("DELETE FROM subscriptions")
