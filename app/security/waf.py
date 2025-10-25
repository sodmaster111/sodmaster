"""Middleware primitives that provide lightweight request filtering."""

from __future__ import annotations

import logging
from typing import Iterable, Tuple

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.metrics import record_waf_block

_LOGGER = logging.getLogger("app.security.waf")

_WP_PREFIXES: Tuple[str, ...] = (
    "/wp-admin",
    "/wordpress",
    "/wp/",
    "/blog/wp-admin",
    "/new/wp-admin",
    "/old/wp-admin",
    "/shop/wp-admin",
    "/test/wp-admin",
)


class WordPressScannerShieldMiddleware(BaseHTTPMiddleware):
    """Return quiet 404 responses for known WordPress scanner paths."""

    def __init__(self, app, *, path_prefixes: Iterable[str] | None = None) -> None:
        super().__init__(app)
        prefixes = tuple(path_prefixes or _WP_PREFIXES)
        # Normalise to ensure lookups are consistent
        self._path_prefixes: Tuple[str, ...] = tuple(prefixes)

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        path = request.url.path
        if self._is_blocked(path):
            record_waf_block("wp")
            _LOGGER.debug("Blocked WordPress scanner request", extra={"path": path, "method": request.method})
            return JSONResponse(status_code=404, content={"error": "not_found"})
        return await call_next(request)

    def _is_blocked(self, path: str) -> bool:
        for prefix in self._path_prefixes:
            if path.startswith(prefix):
                return True
        return False
