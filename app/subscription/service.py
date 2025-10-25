"""Business logic for subscription creation and settlement."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.audit.event_bus import AuditEvent
from app.audit.service import AuditTrail
from app.metrics import (
    record_payment_routed,
    record_subscription_created,
    set_confirmations_pending,
    set_subscription_conversion_rate,
)
from app.payments import PaymentRouter
from app.payments.verification import TransactionVerifier

from .models import (
    SubscriptionCreate,
    SubscriptionCreateResponse,
    SubscriptionRecord,
    SubscriptionStatus,
    SubscriptionStatusResponse,
    SubscriptionWebhook,
)
from .repository import SubscriptionRepository


def _refresh_conversion_metric(repo: SubscriptionRepository) -> None:
    total = repo.count()
    if total == 0:
        set_subscription_conversion_rate(0.0)
        return
    paid = repo.count_by_status(SubscriptionStatus.paid)
    rate = paid / total if total else 0.0
    set_subscription_conversion_rate(rate)


def _refresh_pending_confirmation_metric(repo: SubscriptionRepository) -> None:
    pending = repo.count_by_status(SubscriptionStatus.pending)
    set_confirmations_pending(pending)


def _build_payment_url(invoice_id: str, currency: str) -> str:
    return f"https://pay.sodmaster.example/invoice/{invoice_id}?currency={currency.lower()}"


async def create_subscription_invoice(
    payload: SubscriptionCreate,
    repo: SubscriptionRepository,
    router: PaymentRouter,
    audit_trail: Optional[AuditTrail] = None,
) -> SubscriptionCreateResponse:
    invoice_id = uuid4().hex
    created_at = datetime.now(tz=timezone.utc)
    payment_route = router.route(payload.currency)
    record = repo.create(
        subscription_id=invoice_id,
        tier=payload.tier,
        currency=payload.currency,
        amount_usd=payload.amount_usd,
        user_wallet=payload.user_wallet,
        destination_address=payment_route.destination,
        status=SubscriptionStatus.pending,
        created_at=created_at,
    )
    record_subscription_created(payload.amount_usd)
    record_payment_routed(payment_route.currency)
    _refresh_conversion_metric(repo)
    _refresh_pending_confirmation_metric(repo)

    if audit_trail is not None:
        event = AuditEvent(
            name="subscription.invoice.created",
            c_unit="core.subscription",
            actor="subscription.api",
            subject=invoice_id,
            severity="info",
            payload={
                "tier": payload.tier,
                "currency": payload.currency,
                "amount_usd": payload.amount_usd,
            },
        )
        await audit_trail.emit(event)

    return SubscriptionCreateResponse(
        invoice_id=invoice_id,
        payment_url=_build_payment_url(invoice_id, payload.currency),
        payment_uri=payment_route.payment_uri,
        payment_qr=payment_route.payment_qr,
        status=record.status,
        amount_usd=record.amount_usd,
        currency=record.currency,
    )


async def record_subscription_settlement(
    payload: SubscriptionWebhook,
    repo: SubscriptionRepository,
    verifier: TransactionVerifier,
    audit_trail: Optional[AuditTrail] = None,
) -> SubscriptionRecord:
    existing = repo.get(payload.invoice_id)
    if existing is None:
        raise KeyError(payload.invoice_id)

    verification = await verifier.verify(payload.currency, payload.tx_hash, existing.destination_address)

    record = repo.update_payment(
        payload.invoice_id,
        currency=payload.currency,
        tx_hash=payload.tx_hash,
        status=SubscriptionStatus.paid,
        user_wallet=payload.user_wallet,
        tx_confirmations=verification.confirmations,
    )
    if record is None:
        raise KeyError(payload.invoice_id)

    _refresh_conversion_metric(repo)
    _refresh_pending_confirmation_metric(repo)

    if audit_trail is not None:
        event = AuditEvent(
            name="subscription.invoice.paid",
            c_unit="core.subscription",
            actor="subscription.webhook",
            subject=payload.invoice_id,
            severity="info",
            payload={
                "currency": payload.currency,
                "tx_hash": payload.tx_hash,
                "user_wallet": payload.user_wallet,
                "confirmations": record.tx_confirmations,
            },
        )
        await audit_trail.emit(event)

    return record


def get_subscription_status(
    invoice_id: str,
    repo: SubscriptionRepository,
) -> Optional[SubscriptionStatusResponse]:
    record = repo.get(invoice_id)
    if record is None:
        return None
    return SubscriptionStatusResponse(
        invoice_id=record.id,
        tier=record.tier,
        currency=record.currency,
        status=record.status,
        amount_usd=record.amount_usd,
        tx_hash=record.tx_hash,
        destination_address=record.destination_address,
        tx_confirmations=record.tx_confirmations,
        created_at=record.created_at,
    )
