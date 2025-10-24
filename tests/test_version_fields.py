import importlib
import sys

from fastapi.testclient import TestClient


def _reload_main():
    """Reload ``app.main`` to ensure VERSION reflects current environment."""

    sys.modules.pop("app.main", None)
    return importlib.import_module("app.main")


def test_import_without_environment(monkeypatch):
    monkeypatch.delenv("PYTHON_VERSION", raising=False)
    monkeypatch.delenv("GIT_SHA", raising=False)
    monkeypatch.delenv("BUILD_TIME", raising=False)

    module = _reload_main()

    assert hasattr(module, "VERSION")
    assert isinstance(module.VERSION, dict)


def test_version_endpoint_reflects_loaded_metadata(monkeypatch):
    monkeypatch.setenv("PYTHON_VERSION", "3.12.1")
    monkeypatch.setenv("GIT_SHA", "abcdef123456")
    monkeypatch.setenv("BUILD_TIME", "2024-06-01T12:00:00Z")

    module = _reload_main()
    version = module.VERSION

    client = TestClient(module.app)
    response = client.get("/version")

    assert response.status_code == 200

    payload = response.json()

    assert payload == version
    assert set(payload) == {"python", "git_sha", "build_time"}
    assert payload["python"].count(".") == 2
    assert payload["git_sha"] == "abcdef123456"
    assert payload["build_time"].endswith("Z")
