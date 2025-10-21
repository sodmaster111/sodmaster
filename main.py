from fastapi import FastAPI

app = FastAPI(
    title="Sodmaster C-unit",
    description="API for managing the Sodmaster virtual world."
)


@app.get("/")
def read_root():
    return {"status": "Sodmaster C-unit is online"}


@app.get("/api/status")
def get_status():
    return {
        "world_name": "Sodmaster Virtual",
        "population": 0,
        "state": "Initializing",
    }
