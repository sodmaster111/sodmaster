#!/usr/bin/env bash
set -euo pipefail

echo "[start_web] env summary"
echo "PUBLIC_BASE_URL=${PUBLIC_BASE_URL:-undefined}"
echo "ENVIRONMENT=${ENVIRONMENT:-development}"
echo "PORT=${PORT:-10000}"

# Ensure python deps
python -m pip install --upgrade pip
pip install -r requirements.txt

# DB migrations (if using alembic or similar, optional)
if [ -f "alembic.ini" ]; then
  echo "[start_web] running alembic upgrade head"
  alembic upgrade head || true
fi

# Run any prestart checks (optional)
python - <<'PY'
import os,sys
# Print quick health-check info for logs
print("PY:SHOW ENV KEYS:", ",".join([k for k in os.environ.keys() if k.upper().startswith("TON")][:10]))
PY

# Start uvicorn on $PORT (Render provides $PORT)
export UVICORN_CMD="uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --log-level info"
echo "[start_web] running: $UVICORN_CMD"
exec $UVICORN_CMD
