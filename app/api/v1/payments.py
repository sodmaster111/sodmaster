from fastapi import APIRouter, HTTPException, status
from app.models.subscription import (
    SubscriptionCreate, SubscriptionResponse,
    PlanType, PaymentStatus, CryptoType
)
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/v1", tags=["payments"])

# Временное хранилище (потом заменим на PostgreSQL)
subscriptions_db = {}

PLAN_PRICES = {
    PlanType.STARTER: 100,
    PlanType.PRO: 250,
    PlanType.ALPHA: 500
}

WALLETS = {
    CryptoType.BTC: "bc1q00vwlsur2d33g6w79clw3gmd4wtnx4yvvwt6dz",
    CryptoType.ETH: "0x145add48062C43cd93a725F84817Cb503B4CA108",
    CryptoType.TON: "UQC_uDgg1EDFSwK_SfdEnevfPsfKIs1HhTKrPwS8QXYDG8my"
}


@router.post("/subscribe", status_code=status.HTTP_201_CREATED)
async def create_subscription(sub: SubscriptionCreate) -> SubscriptionResponse:
    """Create new subscription with crypto payment"""

    # Validate transaction hash format
    if len(sub.tx_hash) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid transaction hash"
        )

    # Check if tx_hash already used
    for existing_sub in subscriptions_db.values():
        if existing_sub["tx_hash"] == sub.tx_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Transaction already processed"
            )

    # Create subscription
    sub_id = str(uuid.uuid4())
    subscription = {
        "id": sub_id,
        "email": sub.email,
        "plan": sub.plan,
        "crypto": sub.crypto,
        "amount_usd": PLAN_PRICES[sub.plan],
        "status": PaymentStatus.PENDING,
        "tx_hash": sub.tx_hash,
        "created_at": datetime.utcnow()
    }

    subscriptions_db[sub_id] = subscription

    return SubscriptionResponse(**subscription)


@router.get("/subscriptions/{subscription_id}")
async def get_subscription(subscription_id: str) -> SubscriptionResponse:
    """Get subscription by ID"""
    if subscription_id not in subscriptions_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    return SubscriptionResponse(**subscriptions_db[subscription_id])


@router.get("/subscriptions")
async def list_subscriptions() -> list[SubscriptionResponse]:
    """List all subscriptions (admin endpoint)"""
    return [
        SubscriptionResponse(**sub)
        for sub in subscriptions_db.values()
    ]


@router.get("/wallets")
async def get_wallets():
    """Get crypto wallet addresses"""
    return {
        "btc": WALLETS[CryptoType.BTC],
        "eth": WALLETS[CryptoType.ETH],
        "ton": WALLETS[CryptoType.TON],
        "plans": {
            "starter": PLAN_PRICES[PlanType.STARTER],
            "pro": PLAN_PRICES[PlanType.PRO],
            "alpha": PLAN_PRICES[PlanType.ALPHA]
        }
    }
