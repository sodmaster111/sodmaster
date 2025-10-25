from pydantic import BaseModel, EmailStr
from datetime import datetime
from enum import Enum


class PlanType(str, Enum):
    STARTER = "starter"
    PRO = "pro"
    ALPHA = "alpha"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class CryptoType(str, Enum):
    BTC = "btc"
    ETH = "eth"
    TON = "ton"


class SubscriptionCreate(BaseModel):
    email: EmailStr
    plan: PlanType
    crypto: CryptoType
    tx_hash: str


class SubscriptionResponse(BaseModel):
    id: str
    email: str
    plan: PlanType
    crypto: CryptoType
    amount_usd: int
    status: PaymentStatus
    tx_hash: str
    created_at: datetime
