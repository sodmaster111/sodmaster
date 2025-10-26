from fastapi import FastAPI

app = FastAPI(title="Sodmaster C-Unit API")

@app.get("/health")
async def health():
    return {"status": "ok"}
