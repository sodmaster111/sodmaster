"""Job store implementations for persisting background job state."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any, Dict, Mapping, Optional, Protocol

if TYPE_CHECKING:  # pragma: no cover - imported for typing only
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)


JobRecord = Dict[str, Any]


class JobStore(Protocol):
    """Persistence interface for background jobs."""

    async def get(self, job_id: str) -> Optional[JobRecord]:
        """Return the stored job payload for ``job_id`` if present."""

    async def set_status(
        self, job_id: str, status: str, result: Any | None = None
    ) -> None:
        """Update the status (and optional result) for an existing job."""

    async def create(self, job_id: str, payload: Mapping[str, Any]) -> None:
        """Persist a freshly created job with its payload."""

    async def close(self) -> None:  # pragma: no cover - interface default
        """Release any resources held by the store."""


class InMemoryJobStore(JobStore):
    """Simple job store that keeps state within the process memory."""

    def __init__(self) -> None:
        self._jobs: Dict[str, JobRecord] = {}
        self._lock = asyncio.Lock()

    async def get(self, job_id: str) -> Optional[JobRecord]:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return json.loads(json.dumps(job, default=_json_default))

    async def set_status(
        self, job_id: str, status: str, result: Any | None = None
    ) -> None:
        async with self._lock:
            if job_id not in self._jobs:
                raise KeyError(f"Job '{job_id}' not found")
            self._jobs[job_id]["status"] = status
            self._jobs[job_id]["result"] = result

    async def create(self, job_id: str, payload: Mapping[str, Any]) -> None:
        async with self._lock:
            self._jobs[job_id] = {
                "status": "pending",
                "result": None,
                "payload": dict(payload),
            }

    async def close(self) -> None:  # pragma: no cover - nothing to release
        return None


class RedisJobStore(JobStore):
    """Job store backed by Redis for resilience across restarts."""

    def __init__(self, client: "Redis", key_prefix: str = "jobs") -> None:
        self._redis = client
        self._key_prefix = key_prefix

    async def get(self, job_id: str) -> Optional[JobRecord]:
        raw = await self._redis.get(self._key(job_id))
        if raw is None:
            return None
        if isinstance(raw, bytes):  # pragma: no cover - depends on redis config
            raw = raw.decode("utf-8")
        return json.loads(raw)

    async def set_status(
        self, job_id: str, status: str, result: Any | None = None
    ) -> None:
        key = self._key(job_id)
        raw = await self._redis.get(key)
        if raw is None:
            raise KeyError(f"Job '{job_id}' not found")
        if isinstance(raw, bytes):  # pragma: no cover - depends on redis config
            raw = raw.decode("utf-8")
        record = json.loads(raw)
        record["status"] = status
        record["result"] = result
        await self._redis.set(key, json.dumps(record, default=_json_default))

    async def create(self, job_id: str, payload: Mapping[str, Any]) -> None:
        record = {
            "status": "pending",
            "result": None,
            "payload": dict(payload),
        }
        await self._redis.set(self._key(job_id), json.dumps(record, default=_json_default))

    async def close(self) -> None:
        await self._redis.close()
        try:  # pragma: no cover - depends on redis client implementation
            await self._redis.connection_pool.disconnect(inuse_connections=True)
        except AttributeError:
            logger.debug("Redis client has no connection pool to close")

    def _key(self, job_id: str) -> str:
        return f"{self._key_prefix}:{job_id}"


async def create_job_store(redis_url: str | None) -> JobStore:
    """Create the appropriate job store given the runtime configuration."""

    if redis_url:
        try:
            import redis.asyncio as redis
        except ImportError as exc:  # pragma: no cover - optional dependency guard
            raise RuntimeError("Redis support requested but redis package is missing") from exc

        client = redis.from_url(redis_url, decode_responses=True)
        logger.info("Using RedisJobStore with url=%s", redis_url)
        return RedisJobStore(client)

    logger.info("Using in-memory job store")
    return InMemoryJobStore()


def _json_default(value: Any) -> Any:
    """Gracefully serialise otherwise unsupported values."""

    return str(value)
