"""Data models for subscription management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, validator


class SubscriptionStatus(str, Enum):
    """Lifecycle status for a subscription invoice."""

    pending = "pending"
    paid = "paid"
    failed = "failed"


@dataclass(slots=True)
class SubscriptionRecord:
    """Database representation of a subscription invoice."""

    id: str
    tier: str
    user_wallet: Optional[str]
    currency: str
    amount_usd: float
    tx_hash: Optional[str]
    destination_address: str
    tx_confirmations: int
    status: SubscriptionStatus
    created_at: datetime


class SubscriptionCreate(BaseModel):
    """Request payload for creating a subscription invoice."""

    tier: str = Field(..., description="Subscription tier identifier")
    currency: str = Field(..., description="Requested settlement currency")
    amount_usd: float = Field(..., gt=0, description="Invoice amount in USD")
    user_wallet: Optional[str] = Field(None, description="Optional preferred wallet address")

    @validator("currency")
    def uppercase_currency(cls, value: str) -> str:  # noqa: N805 - pydantic convention
        return value.upper()

    @validator("tier")
    def strip_tier(cls, value: str) -> str:  # noqa: N805 - pydantic convention
        return value.strip()


class SubscriptionWebhook(BaseModel):
    """Webhook payload for confirming a crypto settlement."""

    invoice_id: str
    tx_hash: str
    currency: str
    user_wallet: Optional[str] = None

    @validator("currency")
    def uppercase_currency(cls, value: str) -> str:  # noqa: N805 - pydantic convention
        return value.upper()


class SubscriptionStatusResponse(BaseModel):
    """Serialized representation for status queries."""

    invoice_id: str
    tier: str
    currency: str
    status: SubscriptionStatus
    amount_usd: float
    tx_hash: Optional[str]
    destination_address: str
    tx_confirmations: int
    created_at: datetime


class SubscriptionCreateResponse(BaseModel):
    """Response payload for invoice creation."""

    invoice_id: str
    payment_url: str
    payment_uri: str
    payment_qr: str
    status: SubscriptionStatus
    amount_usd: float
    currency: str
