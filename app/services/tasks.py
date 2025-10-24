from typing import Any, Dict


# --- КЭШ РЕЗУЛЬТАТОВ (Временная Память) ---
task_results: Dict[str, Dict[str, Any]] = {}


def run_crew_task(crew, task_id: str, inputs: Dict[str, Any]) -> None:
    """Запускает Crew в фоновом режиме."""
    try:
        result = crew.kickoff(inputs=inputs)
        task_results[task_id] = {"status": "complete", "result": result}
    except Exception as exc:  # pragma: no cover - защитный блок от неожиданных ошибок
        task_results[task_id] = {"status": "error", "message": str(exc)}
