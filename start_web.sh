#!/usr/bin/env bash
set -euo pipefail
uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}
