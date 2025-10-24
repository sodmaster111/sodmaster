import sys
from pathlib import Path

from fastapi.testclient import TestClient
from platform import python_version

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app.main import app


client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz():
    response = client.get("/readyz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["dependencies_ready"] is True


def test_version():
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"git_sha", "build_time", "python"}
    assert isinstance(data["git_sha"], str)
    assert isinstance(data["build_time"], str)
    assert data["python"] == python_version()
