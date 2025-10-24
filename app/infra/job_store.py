"""Job store abstractions and implementations."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional, Protocol

try:  # pragma: no cover - optional dependency guard during import time
    import redis.asyncio as redis
except ModuleNotFoundError:  # pragma: no cover - redis is optional for tests
    redis = None

logger = logging.getLogger(__name__)


JobRecord = Dict[str, Any]


class JobStore(Protocol):
    """Protocol describing the minimum interface for persisting jobs."""

    async def get(self, job_id: str) -> Optional[JobRecord]:
        """Retrieve a job by identifier."""

    async def set_status(
        self, job_id: str, status: str, result: Any | None = None
    ) -> None:
        """Persist a new status (and optional result) for the job."""

    async def create(self, job_id: str, payload: Dict[str, Any]) -> None:
        """Create a new job entry with the provided payload."""


class InMemoryJobStore:
    """Simple in-memory job persistence for local development and tests."""

    def __init__(self) -> None:
        self._jobs = {}
        self._lock = asyncio.Lock()

    async def get(self, job_id: str) -> Optional[JobRecord]:
        async with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job is not None else None

    async def set_status(
        self, job_id: str, status: str, result: Any | None = None
    ) -> None:
        async with self._lock:
            job = self._jobs.setdefault(job_id, {"payload": None})
            job["status"] = status
            job["result"] = result

    async def create(self, job_id: str, payload: Dict[str, Any]) -> None:
        async with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "payload": dict(payload),
                "status": "pending",
                "result": None,
            }


class RedisJobStore:
    """Redis-backed job store using the asyncio client."""

    def __init__(self, redis_url: str, namespace: str = "jobs") -> None:
        if redis is None:  # pragma: no cover - safety check when redis missing
            raise RuntimeError("redis library is required for RedisJobStore")

        self._redis = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        self._namespace = namespace

    def _key(self, job_id: str) -> str:
        return f"{self._namespace}:{job_id}"

    async def get(self, job_id: str) -> Optional[JobRecord]:
        data = await self._redis.get(self._key(job_id))
        if data is None:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:  # pragma: no cover - unexpected state
            logger.warning("Redis job payload corrupted", extra={"job_id": job_id})
            return None

    async def set_status(
        self, job_id: str, status: str, result: Any | None = None
    ) -> None:
        job = await self.get(job_id) or {
            "id": job_id,
            "payload": None,
        }
        job["status"] = status
        job["result"] = result
        await self._redis.set(self._key(job_id), self._dumps(job))

    async def create(self, job_id: str, payload: Dict[str, Any]) -> None:
        record = {
            "id": job_id,
            "payload": dict(payload),
            "status": "pending",
            "result": None,
        }
        await self._redis.set(self._key(job_id), self._dumps(record))

    @staticmethod
    def _dumps(payload: JobRecord) -> str:
        return json.dumps(payload, default=str)

    async def close(self) -> None:
        await self._redis.aclose()
