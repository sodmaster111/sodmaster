# Codex Prompt — CTO / Оркестрация агентов
@role CTO
@intent Подготовить конфиг CrewAI для 3 агентов (CEO/CMO/CFO) и пример задачи.
@context memory/strategic_memory.md#Архитектура; state/project_state.json
@constraints Python 3.11; MIT/Apache-2.0; совместимость с Render free tier; без внешних платных API
@deliverable Папка `crewai/` с `crew.yaml`, `requirements.txt` и README по запуску локально.
