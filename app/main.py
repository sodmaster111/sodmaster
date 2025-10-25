import inspect
import logging
import os
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Request, Response, WebSocket, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.a2a import router as a2a_router
from app.auth.google_oauth import router as google_auth_router
from app.auth.telegram_login import router as telegram_auth_router
from app.audit.service import CUnit, bootstrap_default_audit_trail
from app.api.v1.health import router as health_router
from app.api.v1.payments import router as payments_router
from app.cgo.routes import router as cgo_router
from app.infra import InMemoryJobStore, RedisJobStore, get_job_store
from app.metrics import APP_INFO, record_http_request
from app.marketing import router as marketing_router
from app.mktg.routes import router as mktg_router
from app.prometheus import CONTENT_TYPE_LATEST, generate_latest
from app.payments import PaymentRouter
from app.payments.verification import TransactionVerifier
from app.ops.routes import router as ops_router
from app.miniapp.routes import router as miniapp_router
from app.webdev.routes import router as webdev_router
from app.root.routes import router as root_router
from app.security.rate_limit import RateLimiter
from app.security.waf import WordPressScannerShieldMiddleware
from app.services.tasks import run_crew_task, task_results
from app.subscription import router as subscription_router
from app.treasury import router as treasury_router
from app.subscription.repository import SubscriptionRepository
from app.version_info import load_version
from app.fundraise.service import FundraiseTracker
from app.fundraise.routes import router as fundraise_router
from app.fundraise.websocket import handle_fundraise_websocket
from app.users.repository import UserRepository
from app.users.routes import router as users_router
from starlette.exceptions import HTTPException as StarletteHTTPException

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

VERSION = load_version()

PYTHON_VERSION = VERSION.get("python", "unknown")
GIT_SHA = VERSION.get("git_sha", "unknown")
BUILD_TIME = VERSION.get("build_time", "unknown")

APP_INFO.info({"python": PYTHON_VERSION, "git_sha": GIT_SHA})

CRITICAL_DEPENDENCIES_READY = True


app = FastAPI(
    title="Sodmaster C-unit (MAF Gateway v2.0)",
    description=(
        "Внутренний A2A (Agent-to-Agent) API-шлюз. Управляется COO-AI (MAF) для "
        "делегирования задач департаментам CrewAI."
    ),
)

app.include_router(health_router)

job_store = get_job_store()
job_store_backend = "redis" if isinstance(job_store, RedisJobStore) else "memory"

audit_trail = bootstrap_default_audit_trail()
audit_trail.register_c_unit(
    CUnit(
        id="core.subscription",
        name="Subscription Billing",
        description="Subscription invoicing and settlement for crypto-ready plans",
        owners=("product", "finance"),
    )
)

subscription_db_path = Path(
    os.environ.get("SUBSCRIPTION_DB_PATH", "/tmp/sodmaster_subscriptions.db")
)
subscription_repo = SubscriptionRepository(subscription_db_path)
fundraise_tracker = FundraiseTracker()
payment_router = PaymentRouter()
transaction_verifier = TransactionVerifier()
webhook_rate_limiter = RateLimiter(limit=10, window_seconds=60.0)
user_repository = UserRepository()

logging.info(
    "Application startup | python_version=%s git_sha=%s build_time=%s job_store=%s",
    VERSION["python"],
    VERSION["git_sha"],
    VERSION["build_time"],
    job_store_backend,
)

if job_store_backend == "memory":
    logging.info("Job store persistence disabled; set REDIS_URL to enable persistence")

app.state.job_store = job_store
app.state.audit_trail = audit_trail
app.state.subscription_repo = subscription_repo
app.state.job_store_backend = job_store_backend
app.state.redis_connected = isinstance(job_store, RedisJobStore)
app.state.fundraise_tracker = fundraise_tracker
app.state.treasury_whitelist = {}
app.state.payment_router = payment_router
app.state.transaction_verifier = transaction_verifier
app.state.webhook_rate_limiter = webhook_rate_limiter
app.state.user_repo = user_repository

app.add_middleware(WordPressScannerShieldMiddleware)
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
    backend = "redis" if isinstance(job_store, RedisJobStore) else "memory"
    redis_connected = False
    try:
        await job_store.ping()
    except Exception:  # pragma: no cover - logged for observability
        logging.exception("Job store ping failed; switching to in-memory store")
        fallback = InMemoryJobStore()
        app.state.job_store = fallback
        await fallback.ping()
        logging.info("redis=unavailable; using in-memory job store")
        backend = "memory"
    else:
        if isinstance(job_store, RedisJobStore):
            logging.info("redis=connected")
            redis_connected = True

    app.state.job_store_backend = backend
    app.state.redis_connected = redis_connected
    if backend == "memory" and not redis_connected:
        logging.info("Job store persistence disabled; set REDIS_URL to enable persistence")

app.include_router(root_router)
app.include_router(a2a_router, prefix="/a2a")
app.include_router(cgo_router, prefix="/api/v1/cgo")
app.include_router(ops_router)
app.include_router(webdev_router, prefix="/api/v1/webdev")
app.include_router(mktg_router, prefix="/api/v1/mktg")
app.include_router(marketing_router)
app.include_router(miniapp_router)
app.include_router(subscription_router)
app.include_router(fundraise_router, prefix="/api/v1/fundraise")
app.include_router(treasury_router)
app.include_router(google_auth_router)
app.include_router(telegram_auth_router)
app.include_router(users_router)
app.include_router(payments_router)


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
    """Return a consistent JSON payload and keep logs quiet for 405 errors."""

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

    logging.getLogger("uvicorn.error").debug("405 %s %s", request.method, request.url.path)

    response_headers = {"Allow": ", ".join(allowed_methods)} if allowed_methods else None

    return JSONResponse(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        content={"error": "method_not_allowed", "detail": f"use one of: {allowed_methods}"},
        headers=response_headers,
    )

@app.head("/")
async def root_head():
    return Response(status_code=200)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    return {"status": "ok", "dependencies_ready": CRITICAL_DEPENDENCIES_READY}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.websocket("/ws/fundraise")
async def fundraise_stream(websocket: WebSocket):
    tracker: FundraiseTracker = app.state.fundraise_tracker
    await handle_fundraise_websocket(websocket, tracker)


@app.get("/version")
def version():
    return dict(VERSION)


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
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
