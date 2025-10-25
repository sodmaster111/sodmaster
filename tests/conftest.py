import asyncio
import inspect
import os

import pytest

try:  # pragma: no cover - optional dependency guard for local dev containers
    from fastapi.testclient import TestClient
    from app.main import app
except ModuleNotFoundError:  # pragma: no cover - fallback when FastAPI deps absent locally
    TestClient = None
    app = None

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")


@pytest.fixture()
def client():
    """Provide a FastAPI TestClient for API tests."""
    if TestClient is None or app is None:
        pytest.skip("FastAPI test client dependencies are not available")
    return TestClient(app)


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    """Run async test functions without requiring pytest-asyncio plugin."""

    test_func = pyfuncitem.obj
    if inspect.iscoroutinefunction(test_func):
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(test_func(**pyfuncitem.funcargs))
        finally:
            loop.close()
        return True
    return None
