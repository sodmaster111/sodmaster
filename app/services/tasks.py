import logging
from typing import Any, Dict


logger = logging.getLogger(__name__)


# --- КЭШ РЕЗУЛЬТАТОВ (Временная Память) ---
task_results: Dict[str, Dict[str, Any]] = {}


def run_crew_task(crew, task_id: str, inputs: Dict[str, Any]) -> None:
    """Запускает Crew в фоновом режиме."""
    logger.info("run_crew_task: kickoff", extra={"task_id": task_id})
    try:
        result = crew.kickoff(inputs=inputs)
        task_results[task_id] = {"status": "complete", "result": result}
        logger.info("run_crew_task: complete", extra={"task_id": task_id})
    except Exception as exc:  # pragma: no cover - защитный блок от неожиданных ошибок
        task_results[task_id] = {"status": "error", "message": str(exc)}
        logger.exception("run_crew_task: failed", extra={"task_id": task_id})
