"""Utilities for exposing build and runtime metadata."""

from __future__ import annotations

import datetime as dt
import os
import sys
from typing import Dict


def load_version() -> Dict[str, str]:
    """Return version metadata using environment variables with sensible fallbacks."""

    return {
        "python": os.getenv(
            "PYTHON_VERSION",
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        ),
        "git_sha": os.getenv("GIT_SHA", "unknown"),
        "build_time": os.getenv(
            "BUILD_TIME",
            dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        ),
    }
