"""FastAPI routes for subscription management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.audit.service import AuditTrail

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


def _get_repo(request: Request) -> SubscriptionRepository:
    repo = getattr(request.app.state, "subscription_repo", None)
    if repo is None:
        raise RuntimeError("Subscription repository is not configured")
    return repo


def _get_audit_trail(request: Request) -> AuditTrail | None:
    return getattr(request.app.state, "audit_trail", None)


@router.post("/create", response_model=SubscriptionCreateResponse)
async def create_subscription(
    payload: SubscriptionCreate,
    repo: SubscriptionRepository = Depends(_get_repo),
    audit_trail: AuditTrail | None = Depends(_get_audit_trail),
) -> SubscriptionCreateResponse:
    return await create_subscription_invoice(payload, repo, audit_trail)


@router.post("/webhook")
async def subscription_webhook(
    payload: SubscriptionWebhook,
    repo: SubscriptionRepository = Depends(_get_repo),
    audit_trail: AuditTrail | None = Depends(_get_audit_trail),
) -> dict[str, str]:
    try:
        record = await record_subscription_settlement(payload, repo, audit_trail)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invoice_not_found") from exc
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
