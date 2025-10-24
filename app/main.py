import inspect
import logging
import os
from datetime import datetime
from platform import python_version

import uvicorn
from fastapi import BackgroundTasks, FastAPI, Request, Response, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.a2a import router as a2a_router
from app.cgo.routes import router as cgo_router
from app.infra import InMemoryJobStore, RedisJobStore, get_job_store
from app.metrics import APP_INFO, record_http_request
from app.prometheus import CONTENT_TYPE_LATEST, generate_latest
from app.ops.routes import router as ops_router
from app.services.tasks import run_crew_task, task_results
from starlette.exceptions import HTTPException as StarletteHTTPException

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

logger = logging.getLogger(__name__)

GIT_SHA = os.environ.get("GIT_SHA", "unknown")
BUILD_TIME = datetime.utcnow().isoformat() + "Z"
PYTHON_VERSION = python_version()

logging.info(
    "Application startup | python_version=%s git_sha=%s build_time=%s",
    PYTHON_VERSION,
    GIT_SHA,
    BUILD_TIME,
)

APP_INFO.info({"python": PYTHON_VERSION, "git_sha": GIT_SHA})

CRITICAL_DEPENDENCIES_READY = True


app = FastAPI(
    title="Sodmaster C-unit (MAF Gateway v2.0)",
    description=(
        "Внутренний A2A (Agent-to-Agent) API-шлюз. Управляется COO-AI (MAF) для "
        "делегирования задач департаментам CrewAI."
    ),
)
app.state.job_store = get_job_store()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def ensure_job_store_connection() -> None:
    """Verify the configured job store is ready before serving requests."""

    job_store = app.state.job_store
    try:
        await job_store.ping()
    except Exception:  # pragma: no cover - logged for observability
        logging.exception("Job store ping failed; switching to in-memory store")
        fallback = InMemoryJobStore()
        app.state.job_store = fallback
        await fallback.ping()
        logging.info("redis=unavailable; using in-memory job store")
    else:
        if isinstance(job_store, RedisJobStore):
            logging.info("redis=connected")

app.include_router(a2a_router, prefix="/a2a")
app.include_router(cgo_router, prefix="/api/v1/cgo")
app.include_router(ops_router)


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    record_http_request(path)
    return response


@app.exception_handler(StarletteHTTPException)
async def method_not_allowed_handler(
    request: Request, exc: StarletteHTTPException
) -> Response:
    """Return a structured JSON response when a disallowed method is used."""

    if exc.status_code != status.HTTP_405_METHOD_NOT_ALLOWED:
        return await http_exception_handler(request, exc)

    headers = dict(exc.headers or {})
    allow_header = headers.get("Allow") or headers.get("allow")
    allowed_methods = (
        [method.strip() for method in allow_header.split(",") if method.strip()]
        if allow_header
        else []
    )
    if request.method == "OPTIONS":
        cors_methods = list(dict.fromkeys(allowed_methods + ["OPTIONS"]))
        allow_headers = request.headers.get("access-control-request-headers", "*")
        response_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": ", ".join(cors_methods) if cors_methods else "OPTIONS",
            "Access-Control-Allow-Headers": allow_headers or "*",
        }
        if allowed_methods:
            response_headers["Allow"] = ", ".join(allowed_methods)
        return Response(status_code=status.HTTP_200_OK, headers=response_headers)
    preferred_method = next((method for method in allowed_methods if method != request.method), None)
    if preferred_method is None and allowed_methods:
        preferred_method = allowed_methods[0]
    detail = (
        f"Use {preferred_method} {request.url.path}"
        if preferred_method
        else "Requested method is not allowed"
    )

    logger.warning(
        "method_not_allowed",
        extra={"path": request.url.path, "method": request.method, "allowed": allowed_methods},
    )

    response_headers = {"Allow": ", ".join(allowed_methods)} if allowed_methods else None

    return JSONResponse(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        content={"error": "method_not_allowed", "detail": detail},
        headers=response_headers,
    )


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


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


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
