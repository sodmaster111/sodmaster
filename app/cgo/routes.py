from fastapi import APIRouter, BackgroundTasks

from agents.cgo_crew import cgo_crew
from app.services.tasks import run_crew_task, task_results

router = APIRouter()


@router.post("/run-marketing-campaign")
async def run_marketing_campaign(background_tasks: BackgroundTasks):
    """Эндпоинт для CGO-AI (MAF), чтобы запустить CGO-Crew (CrewAI)."""
    task_id = "cgo_task_latest"
    task_results[task_id] = {"status": "running"}

    # Запускаем Crew в фоне, чтобы API мгновенно отдал ответ
    background_tasks.add_task(run_crew_task, cgo_crew, task_id, {})

    return {"status": "CGO Crew Task Started", "task_id": task_id}
