import asyncio
import os
from uuid import uuid4

import pytest

from app.infra import InMemoryJobStore, RedisJobStore


def test_in_memory_job_store_lifecycle():
    async def _run() -> None:
        store = InMemoryJobStore()

        await store.ping()

        await store.create("job-1", {"foo": "bar"})
        job = await store.get("job-1")
        assert job is not None
        assert job["status"] == "pending"
        assert job["payload"] == {"foo": "bar"}

        await store.set_status("job-1", "running")
        job = await store.get("job-1")
        assert job is not None
        assert job["status"] == "running"
        assert job["result"] is None

        await store.set_status("job-1", "done", {"ok": True})
        job = await store.get("job-1")
        assert job is not None
        assert job["status"] == "done"
        assert job["result"] == {"ok": True}

    asyncio.run(_run())


REDIS_URL = os.getenv("REDIS_URL")


@pytest.mark.skipif(not REDIS_URL, reason="REDIS_URL is not configured")
def test_redis_job_store_lifecycle():
    async def _run() -> None:
        store = RedisJobStore(REDIS_URL)
        await store.ping()
        job_id = f"job-{uuid4()}"

        try:
            await store.create(job_id, {"hello": "world"})
            job = await store.get(job_id)
            assert job is not None
            assert job["payload"] == {"hello": "world"}
            assert job["status"] == "pending"

            await store.set_status(job_id, "running")
            job = await store.get(job_id)
            assert job is not None
            assert job["status"] == "running"

            await store.set_status(job_id, "done", {"ok": True})
            job = await store.get(job_id)
            assert job is not None
            assert job["status"] == "done"
            assert job["result"] == {"ok": True}
        finally:
            # Clean up created key to avoid polluting shared Redis instances.
            await store._redis.delete(store._key(job_id))  # type: ignore[attr-defined]
            close = getattr(store, "close", None)
            if callable(close):
                await close()

    asyncio.run(_run())
