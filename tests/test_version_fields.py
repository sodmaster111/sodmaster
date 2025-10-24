import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app.version_info import load_version


@pytest.mark.parametrize(
    "git_sha, build_time, python_runtime",
    [
        (
            "2b1c9fe",
            "2024-01-01T00:00:00Z",
            "CPython 3.12.0",  # representative placeholder
        )
    ],
)
def test_load_version_from_environment(monkeypatch, git_sha, build_time, python_runtime):
    monkeypatch.setenv("GIT_SHA", git_sha)
    monkeypatch.setenv("BUILD_TIME", build_time)
    monkeypatch.setenv("PY_RUNTIME", python_runtime)

    version = load_version()

    assert set(version) == {"git_sha", "build_time", "python"}
    assert version["git_sha"] == git_sha
    assert version["build_time"] == build_time
    assert version["python"] == python_runtime

    parsed = datetime.fromisoformat(build_time.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
