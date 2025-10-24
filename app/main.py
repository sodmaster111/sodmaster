import inspect
import logging
import os
from datetime import datetime
from platform import python_version

import uvicorn
from fastapi import BackgroundTasks, FastAPI

from app.cgo.routes import router as cgo_router
from app.infra import InMemoryJobStore, JobStore, RedisJobStore
from app.ops.routes import router as ops_router
from app.services.tasks import run_crew_task, task_results
from app.infra.job_store import InMemoryJobStore, create_job_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

GIT_SHA = os.environ.get("GIT_SHA", "unknown")
BUILD_TIME = datetime.utcnow().isoformat() + "Z"
PYTHON_VERSION = python_version()

logging.info(
    "Application startup | python_version=%s git_sha=%s build_time=%s",
    PYTHON_VERSION,
    GIT_SHA,
    BUILD_TIME,
)

CRITICAL_DEPENDENCIES_READY = True


app = FastAPI(
    title="Sodmaster C-unit (MAF Gateway v2.0)",
    description=(
        "Внутренний A2A (Agent-to-Agent) API-шлюз. Управляется COO-AI (MAF) для "
        "делегирования задач департаментам CrewAI."
    ),
)


def _create_job_store() -> JobStore:
    redis_url = os.environ.get("REDIS_URL", "").strip()
    if redis_url:
        try:
            store = RedisJobStore(redis_url)
            logging.info("Using RedisJobStore")
            return store
        except Exception:  # pragma: no cover - logged for observability
            logging.exception("Failed to initialise RedisJobStore, falling back")

    logging.info("Using InMemoryJobStore")
    return InMemoryJobStore()


app.state.job_store = _create_job_store()

app.include_router(cgo_router, prefix="/api/v1/cgo")
app.include_router(ops_router)

app.state.job_store = InMemoryJobStore()


@app.on_event("startup")
async def configure_job_store() -> None:
    redis_url = os.environ.get("REDIS_URL")
    app.state.job_store = await create_job_store(redis_url)


@app.on_event("shutdown")
async def shutdown_job_store() -> None:
    job_store = getattr(app.state, "job_store", None)
    close = getattr(job_store, "close", None)
    if callable(close):
        await close()


@app.on_event("shutdown")
async def _shutdown_job_store() -> None:
    job_store = getattr(app.state, "job_store", None)
    if job_store is None:
        return

    close = getattr(job_store, "close", None)
    if callable(close):  # pragma: no branch - minimal branching for coverage
        result = close()
        if inspect.isawaitable(result):
            await result


@app.get("/")
def read_root():
    # Проверка, что API-ключи загружены
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "NOT_SET")
    leonardo_key = os.environ.get("LEONARDO_API_KEY", "NOT_SET")
    return {
        "status": "Sodmaster C-Unit MAF Gateway is online.",
        "openrouter_status": "LOADED" if openrouter_key != "NOT_SET" else "MISSING",
        "leonardo_status": "LOADED" if leonardo_key != "NOT_SET" else "MISSING",
        "exa_status": "LOADED"
        if os.environ.get("EXA_API_KEY", "NOT_SET") != "NOT_SET"
        else "MISSING",
        "serper_status": "LOADED"
        if os.environ.get("SERPER_API_KEY", "NOT_SET") != "NOT_SET"
        else "MISSING",
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    return {"status": "ok", "dependencies_ready": CRITICAL_DEPENDENCIES_READY}


@app.get("/version")
def version():
    return {"git_sha": GIT_SHA, "build_time": BUILD_TIME, "python": PYTHON_VERSION}


@app.post("/api/v1/cto/run-research")
async def run_cto_task(background_tasks: BackgroundTasks):
    """Эндпоинт для CTO-AI (MAF), чтобы запустить CTO-Crew (CrewAI)."""
    from agents.cto_crew import cto_crew

    task_id = "cto_task_latest"
    task_results[task_id] = {"status": "running"}

    background_tasks.add_task(run_crew_task, cto_crew, task_id, {})

    return {"status": "CTO Crew Task Started", "task_id": task_id}


@app.get("/api/v1/get-task-result/{task_id}")
async def get_task_result(task_id: str):
    """Проверяет статус и результат выполненной задачи Crew."""
    result = task_results.get(task_id, {"status": "not_found"})
    return result


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
