"""Routing helpers for directing subscription payments to founder wallets."""

from __future__ import annotations

import itertools
import os
import threading
from dataclasses import dataclass
from typing import Iterable, Tuple
from urllib.parse import quote


@dataclass(frozen=True)
class PaymentDestination:
    """Represents a single blockchain destination and its routing weight."""

    address: str
    weight: float = 1.0


@dataclass(frozen=True)
class PaymentRoute:
    """Resolved routing details for a currency."""

    currency: str
    destination: str
    payment_uri: str
    payment_qr: str
    path: Tuple[PaymentDestination, ...]


class PaymentRouter:
    """Route subscription payments across supported blockchains."""

    BTC_ADDR = "bc1q00vwlsur2d33g6w79clw3gmd4wtnx4yvvwt6dz"
    ETH_ADDR = "0x145add48062C43cd93a725F84817Cb503B4CA108"
    TON_WALLET_1 = "UQC_uDgg1EDFSwK_SfdEnevfPsfKIs1HhTKrPwS8QXYDG8my"

    _TON_WALLET_ENV = ("TON_WALLET_1", "TON_WALLET_2", "TON_WALLET_3")
    _TON_WEIGHTING = (0.60, 0.25, 0.15)

    def __init__(
        self,
        *,
        ton_wallets: Iterable[str] | None = None,
        ton_weights: Iterable[float] | None = None,
    ) -> None:
        wallets = tuple(ton_wallets) if ton_wallets is not None else self._load_ton_wallets()
        if not wallets:
            raise ValueError("TON routing requires at least one configured wallet")

        weights = tuple(ton_weights) if ton_weights is not None else self._TON_WEIGHTING
        if len(weights) != len(wallets):
            if ton_weights is not None:
                raise ValueError("ton_weights must align with ton_wallets length")
            weights = self._rebalance_weights(len(wallets))

        destinations = tuple(
            PaymentDestination(address=wallet, weight=weight)
            for wallet, weight in zip(wallets, weights)
        )

        self._ton_destinations: Tuple[PaymentDestination, ...] = destinations
        self._ton_cycle = self._build_cycle(destinations)
        self._lock = threading.Lock()

    def route(self, currency: str) -> PaymentRoute:
        """Return the routing configuration for the requested currency."""

        normalised = currency.upper()
        if normalised == "BTC":
            return self._build_route(normalised, self.BTC_ADDR)
        if normalised == "ETH":
            return self._build_route(normalised, self.ETH_ADDR)
        if normalised == "TON":
            destination = self._route_ton()
            return self._build_route(normalised, destination, path=self._ton_destinations)
        raise ValueError(f"Unsupported currency: {currency}")

    def _route_ton(self) -> str:
        with self._lock:
            return next(self._ton_cycle)

    def _build_route(
        self,
        currency: str,
        destination: str,
        *,
        path: Tuple[PaymentDestination, ...] | None = None,
    ) -> PaymentRoute:
        payment_uri = self._build_payment_uri(currency, destination)
        qr_url = self._build_qr(payment_uri)
        return PaymentRoute(
            currency=currency,
            destination=destination,
            payment_uri=payment_uri,
            payment_qr=qr_url,
            path=path or (PaymentDestination(address=destination),),
        )

    @staticmethod
    def _build_payment_uri(currency: str, destination: str) -> str:
        if currency == "BTC":
            return f"bitcoin:{destination}"
        if currency == "ETH":
            return f"ethereum:{destination}"
        if currency == "TON":
            return f"ton://transfer/{destination}"
        raise ValueError(f"Unsupported currency for payment URI: {currency}")

    @staticmethod
    def _build_qr(payment_uri: str) -> str:
        encoded = quote(payment_uri, safe="")
        return f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded}"

    def _build_cycle(self, destinations: Tuple[PaymentDestination, ...]):
        slots: list[str] = []
        for destination in destinations:
            count = max(1, int(round(destination.weight * 100)))
            slots.extend([destination.address] * count)
        if not slots:
            raise ValueError("Unable to build TON routing cycle without destinations")
        return itertools.cycle(slots)

    def _load_ton_wallets(self) -> Tuple[str, ...]:
        fallback = self.TON_WALLET_1
        wallets: list[str] = []
        for index, env_key in enumerate(self._TON_WALLET_ENV):
            value = os.getenv(env_key)
            if value:
                wallets.append(value)
            elif index == 0 and fallback:
                wallets.append(fallback)
        # Filter any accidental blanks
        filtered = tuple(wallet for wallet in wallets if wallet)
        if not filtered:
            return (fallback,)
        return filtered

    @staticmethod
    def _rebalance_weights(count: int) -> Tuple[float, ...]:
        if count <= 0:
            raise ValueError("count must be positive")
        if count == 1:
            return (1.0,)
        base_weights = list(PaymentRouter._TON_WEIGHTING)
        if count <= len(base_weights):
            return tuple(base_weights[:count])
        # Evenly distribute remaining weight after existing allocation
        remaining = 1.0 - sum(base_weights)
        extra = remaining / (count - len(base_weights)) if count > len(base_weights) else 0.0
        weights = base_weights + [extra] * (count - len(base_weights))
        return tuple(weights)
