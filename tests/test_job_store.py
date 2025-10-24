import asyncio
import os
from uuid import uuid4

import pytest

from app.infra.job_store import InMemoryJobStore, RedisJobStore, create_job_store


def test_in_memory_job_store_roundtrip():
    async def scenario() -> None:
        store = InMemoryJobStore()

        await store.create("job-1", {"payload": True})
        job = await store.get("job-1")
        assert job is not None
        assert job["status"] == "pending"
        assert job["result"] is None

        await store.set_status("job-1", "running")
        job = await store.get("job-1")
        assert job["status"] == "running"
        assert job["payload"] == {"payload": True}

        await store.set_status("job-1", "done", {"ok": True})
        job = await store.get("job-1")
        assert job["status"] == "done"
        assert job["result"] == {"ok": True}

        await store.close()

    asyncio.run(scenario())


@pytest.mark.skipif("REDIS_URL" not in os.environ, reason="Redis is not configured")
def test_redis_job_store_roundtrip():
    async def scenario() -> None:
        store = await create_job_store(os.environ.get("REDIS_URL"))
        assert isinstance(store, RedisJobStore)

        job_id = f"test-{uuid4()}"
        await store.create(job_id, {"payload": True})
        await store.set_status(job_id, "done", {"ok": True})
        job = await store.get(job_id)

        assert job is not None
        assert job["status"] == "done"
        assert job["result"] == {"ok": True}
        assert job["payload"] == {"payload": True}

        await store.close()

    asyncio.run(scenario())
