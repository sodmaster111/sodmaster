import uvicorn

# BackgroundTasks обеспечивает запуск задач в фоне без блокировки API
from fastapi import FastAPI, BackgroundTasks
import os

# Импорт наших новых Департаментов (Crews)
from agents.cgo_crew import cgo_crew
from agents.cto_crew import cto_crew

# from microsoft_agent_framework import Workflow, Agent  # Заглушка: импортируй реальные классы MAF

# Инициализация MAF C-Suite (Заглушки)
# MAF обеспечивает надежность и чекпоинтинг для C-Units [cite: 370, 872]
# ceo_workflow = Workflow(name="CEO-AI", definition="...")
# cto_workflow = Workflow(name="CTO-AI", definition="...")
# cfo_workflow = Workflow(name="CFO-AI", definition="...")
# cro_workflow = Workflow(name="CRO-AI", definition="...")
# cpo_workflow = Workflow(name="CPO-AI", definition="...")
# cgo_workflow = Workflow(name="CGO-AI", definition="...")

# COO-AI управляет этим API-шлюзом [cite: 376, 876]
# coo_workflow = Workflow(name="COO-AI", definition="api_gateway_manager")

app = FastAPI(
    title="Sodmaster C-unit (MAF Gateway v2.0)",
    description="Внутренний A2A (Agent-to-Agent) API-шлюз. Управляется COO-AI (MAF) для делегирования задач департаментам CrewAI."
)

# --- КЭШ РЕЗУЛЬТАТОВ (Временная Память) ---
task_results = {}


# --- ФОНОВЫЕ ЗАДАЧИ (Чтобы API отвечал мгновенно) ---
def run_crew_task(crew, task_id: str, inputs: dict):
    """Запускает Crew в фоновом режиме."""
    try:
        result = crew.kickoff(inputs=inputs)
        task_results[task_id] = {"status": "complete", "result": result}
    except Exception as e:
        task_results[task_id] = {"status": "error", "message": str(e)}


# --- ОСНОВНЫЕ ЭНДПОИНТЫ API ---

@app.get("/")
def read_root():
    # Проверка, что API-ключи загружены
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "NOT_SET")
    leonardo_key = os.environ.get("LEONARDO_API_KEY", "NOT_SET")
    return {
        "status": "Sodmaster C-Unit MAF Gateway is online.",
        "openrouter_status": "LOADED" if openrouter_key != "NOT_SET" else "MISSING",
        "leonardo_status": "LOADED" if leonardo_key != "NOT_SET" else "MISSING",
        "exa_status": "LOADED" if os.environ.get("EXA_API_KEY", "NOT_SET") != "NOT_SET" else "MISSING",
        "serper_status": "LOADED" if os.environ.get("SERPER_API_KEY", "NOT_SET") != "NOT_SET" else "MISSING"
    }


@app.post("/api/v1/cgo/run-marketing-campaign")
async def run_cgo_task(background_tasks: BackgroundTasks):
    """
    Эндпоинт для CGO-AI (MAF), чтобы запустить CGO-Crew (CrewAI).
    """
    task_id = "cgo_task_latest"
    task_results[task_id] = {"status": "running"}

    # Запускаем Crew в фоне, чтобы API мгновенно отдал ответ
    background_tasks.add_task(run_crew_task, cgo_crew, task_id, {})

    return {"status": "CGO Crew Task Started", "task_id": task_id}


@app.post("/api/v1/cto/run-research")
async def run_cto_task(background_tasks: BackgroundTasks):
    """
    Эндпоинт для CTO-AI (MAF), чтобы запустить CTO-Crew (CrewAI).
    """
    task_id = "cto_task_latest"
    task_results[task_id] = {"status": "running"}

    background_tasks.add_task(run_crew_task, cto_crew, task_id, {})

    return {"status": "CTO Crew Task Started", "task_id": task_id}


@app.get("/api/v1/get-task-result/{task_id}")
async def get_task_result(task_id: str):
    """
    Проверяет статус и результат выполненной задачи Crew.
    """
    result = task_results.get(task_id, {"status": "not_found"})
    return result


# Заглушка: Запуск MAF C-Suite
# print("Инициализация MAF C-Suite Workflows...")
# ceo_workflow.start()
# cto_workflow.start()
# ...

if __name__ == "__main__":
    # Uvicorn будет запущен Render, эта строка для локального теста
    uvicorn.run(app, host="0.0.0.0", port=8000)
