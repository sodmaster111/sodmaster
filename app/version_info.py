"""Utilities for exposing build and runtime metadata."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict

_VERSION_FILE = Path(__file__).with_name("version_env.json")


def _load_from_file() -> Dict[str, str]:
    """Load version metadata from a JSON file if it exists."""

    if not _VERSION_FILE.exists():
        return {}

    try:
        with _VERSION_FILE.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
            if isinstance(data, dict):
                return {str(key): str(value) for key, value in data.items()}
    except (OSError, json.JSONDecodeError):  # pragma: no cover - logged upstream if needed
        return {}
    return {}


def load_version() -> Dict[str, str]:
    """Return version metadata using environment variables with sensible fallbacks."""

    env = {**_load_from_file(), **os.environ}
    git_sha = env.get("GIT_SHA") or "unknown"
    build_time = env.get("BUILD_TIME") or "unknown"
    python_runtime = env.get("PY_RUNTIME") or sys.version

    return {"git_sha": git_sha, "build_time": build_time, "python": python_runtime}
