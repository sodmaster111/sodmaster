"""Simple in-memory rate limiter suitable for low-volume webhook validation."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from threading import Lock


class RateLimitExceeded(Exception):
    """Raised when a caller exceeds the configured request budget."""


@dataclass
class RateLimitConfig:
    limit: int
    window_seconds: float


class RateLimiter:
    """Basic sliding-window limiter keyed by caller identifier."""

    def __init__(self, *, limit: int, window_seconds: float) -> None:
        self._config = RateLimitConfig(limit=limit, window_seconds=window_seconds)
        self._events: dict[str, deque[float]] = {}
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        """Return True if a request for ``key`` should proceed."""

        now = time.monotonic()
        with self._lock:
            queue = self._events.setdefault(key, deque())
            window_start = now - self._config.window_seconds
            while queue and queue[0] < window_start:
                queue.popleft()
            if len(queue) >= self._config.limit:
                return False
            queue.append(now)
        return True

    def assert_allow(self, key: str) -> None:
        """Raise :class:`RateLimitExceeded` if the request should be rejected."""

        if not self.allow(key):
            raise RateLimitExceeded(f"rate limit exceeded for key={key}")
