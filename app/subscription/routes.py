"""FastAPI routes for subscription management."""

from __future__ import annotations

import hashlib
import hmac
import os

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.audit.service import AuditTrail
from app.payments import PaymentRouter
from app.payments.verification import TransactionVerificationError, TransactionVerifier
from app.security.rate_limit import RateLimitExceeded

from .models import (
    SubscriptionCreate,
    SubscriptionCreateResponse,
    SubscriptionStatusResponse,
    SubscriptionWebhook,
)
from .repository import SubscriptionRepository
from .service import (
    create_subscription_invoice,
    get_subscription_status,
    record_subscription_settlement,
)

router = APIRouter(prefix="/api/v1/subscribe", tags=["subscription"])

_SIGNATURE_HEADER = "X-A2A-Signature"
_SECRET_ENV = "A2A_SECRET"


def _get_repo(request: Request) -> SubscriptionRepository:
    repo = getattr(request.app.state, "subscription_repo", None)
    if repo is None:
        raise RuntimeError("Subscription repository is not configured")
    return repo


def _get_audit_trail(request: Request) -> AuditTrail | None:
    return getattr(request.app.state, "audit_trail", None)


def _get_payment_router(request: Request) -> PaymentRouter:
    router = getattr(request.app.state, "payment_router", None)
    if router is None:
        raise RuntimeError("Payment router is not configured")
    return router


def _get_verifier(request: Request) -> TransactionVerifier:
    verifier = getattr(request.app.state, "transaction_verifier", None)
    if verifier is None:
        raise RuntimeError("Transaction verifier is not configured")
    return verifier


def _enforce_rate_limit(request: Request) -> None:
    limiter = getattr(request.app.state, "webhook_rate_limiter", None)
    if limiter is None:
        return
    client = request.client.host if request.client else "anonymous"
    try:
        limiter.assert_allow(client)
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="rate_limit_exceeded") from exc


async def _verify_signature(request: Request) -> None:
    secret = os.getenv(_SECRET_ENV, "")
    if not secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="webhook_signature_not_configured")

    signature = request.headers.get(_SIGNATURE_HEADER)
    if not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_signature")

    body = await request.body()
    computed = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, computed):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_signature")


@router.post("/create", response_model=SubscriptionCreateResponse)
async def create_subscription(
    payload: SubscriptionCreate,
    repo: SubscriptionRepository = Depends(_get_repo),
    payment_router: PaymentRouter = Depends(_get_payment_router),
    audit_trail: AuditTrail | None = Depends(_get_audit_trail),
) -> SubscriptionCreateResponse:
    try:
        return await create_subscription_invoice(payload, repo, payment_router, audit_trail)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/webhook")
async def subscription_webhook(
    request: Request,
    payload: SubscriptionWebhook,
    repo: SubscriptionRepository = Depends(_get_repo),
    verifier: TransactionVerifier = Depends(_get_verifier),
    audit_trail: AuditTrail | None = Depends(_get_audit_trail),
) -> dict[str, str]:
    _enforce_rate_limit(request)
    await _verify_signature(request)
    try:
        record = await record_subscription_settlement(payload, repo, verifier, audit_trail)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invoice_not_found") from exc
    except TransactionVerificationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"status": "updated", "invoice_id": record.id}


@router.get("/status/{invoice_id}", response_model=SubscriptionStatusResponse)
async def subscription_status(
    invoice_id: str,
    repo: SubscriptionRepository = Depends(_get_repo),
) -> SubscriptionStatusResponse:
    result = get_subscription_status(invoice_id, repo)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invoice_not_found")
    return result
