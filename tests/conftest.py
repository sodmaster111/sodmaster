import pytest

try:  # pragma: no cover - optional dependency guard for local dev containers
    from fastapi.testclient import TestClient
    from app.main import app
except ModuleNotFoundError:  # pragma: no cover - fallback when FastAPI deps absent locally
    TestClient = None
    app = None


@pytest.fixture()
def client():
    """Provide a FastAPI TestClient for API tests."""
    if TestClient is None or app is None:
        pytest.skip("FastAPI test client dependencies are not available")
    return TestClient(app)
