"""Simplified payment endpoints for integration tests and CI health checks."""

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.payments.gateway import PaymentRouter

router = APIRouter(prefix="/api/v1", tags=["payments"])


@router.get("/wallets")
async def list_wallets() -> dict[str, str]:
    """Return static crypto wallets for CI smoke tests."""

    return {
        "btc": PaymentRouter.BTC_ADDR,
        "eth": PaymentRouter.ETH_ADDR,
        "ton": PaymentRouter.TON_WALLET_1,
    }


class SubscriptionRequest(BaseModel):
    email: str
    plan: str
    crypto: str
    tx_hash: str


class SubscriptionResponse(BaseModel):
    email: str
    plan: str
    status: str = "pending"


@router.post("/subscribe", status_code=status.HTTP_201_CREATED, response_model=SubscriptionResponse)
async def create_subscription(request: SubscriptionRequest) -> SubscriptionResponse:
    """Acknowledge subscription creation without external integrations."""

    return SubscriptionResponse(email=request.email, plan=request.plan)
