import os

import uvicorn
from fastapi import BackgroundTasks, FastAPI

from agents.cto_crew import cto_crew
from app.cgo.routes import router as cgo_router
from app.services.tasks import run_crew_task, task_results

app = FastAPI(
    title="Sodmaster C-unit (MAF Gateway v2.0)",
    description=(
        "Внутренний A2A (Agent-to-Agent) API-шлюз. Управляется COO-AI (MAF) для "
        "делегирования задач департаментам CrewAI."
    ),
)

app.include_router(cgo_router, prefix="/api/v1/cgo")


@app.get("/")
def read_root():
    # Проверка, что API-ключи загружены
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "NOT_SET")
    leonardo_key = os.environ.get("LEONARDO_API_KEY", "NOT_SET")
    return {
        "status": "Sodmaster C-Unit MAF Gateway is online.",
        "openrouter_status": "LOADED" if openrouter_key != "NOT_SET" else "MISSING",
        "leonardo_status": "LOADED" if leonardo_key != "NOT_SET" else "MISSING",
        "exa_status": "LOADED"
        if os.environ.get("EXA_API_KEY", "NOT_SET") != "NOT_SET"
        else "MISSING",
        "serper_status": "LOADED"
        if os.environ.get("SERPER_API_KEY", "NOT_SET") != "NOT_SET"
        else "MISSING",
    }


@app.post("/api/v1/cto/run-research")
async def run_cto_task(background_tasks: BackgroundTasks):
    """Эндпоинт для CTO-AI (MAF), чтобы запустить CTO-Crew (CrewAI)."""
    task_id = "cto_task_latest"
    task_results[task_id] = {"status": "running"}

    background_tasks.add_task(run_crew_task, cto_crew, task_id, {})

    return {"status": "CTO Crew Task Started", "task_id": task_id}


@app.get("/api/v1/get-task-result/{task_id}")
async def get_task_result(task_id: str):
    """Проверяет статус и результат выполненной задачи Crew."""
    result = task_results.get(task_id, {"status": "not_found"})
    return result


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
