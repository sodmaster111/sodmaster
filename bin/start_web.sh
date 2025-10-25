#!/usr/bin/env bash
set -euo pipefail
PORT="${PORT:-10000}"
export PYTHONPATH=".:$PYTHONPATH"
echo "[start_web] python=$(python -V) port=$PORT pwd=$(pwd)"

# Авто-детект точки входа
TARGET="main:app"
python - <<'PY'
import importlib, sys
candidates = ["main", "app.main"]
for mod in candidates:
    try:
        m = importlib.import_module(mod)
        a = getattr(m, "app", None)
        if a is not None:
            print("TARGET_OK", f"{mod}:app")
            sys.exit(0)
    except Exception as e:
        pass
print("TARGET_FALLBACK", "main:app")
PY

# Запуск uvicorn
exec python -m uvicorn main:app --host 0.0.0.0 --port "$PORT" --proxy-headers --timeout-keep-alive 5
