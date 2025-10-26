try:
    # Preferred: use the app defined in app/main.py
    from app.main import app
except Exception as e:
    # Fallback: minimal FastAPI app so Render can boot even if import path changes
    from fastapi import FastAPI

    app = FastAPI(title="Sodmaster C-Unit API (fallback)")

    @app.get("/health")
    async def health():
        return {"status": "ok", "note": "fallback boot", "import_error": str(e)}
