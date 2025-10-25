import logging
import os

from exa_py import Exa

logger = logging.getLogger(__name__)

try:  # pragma: no cover - exercised in integration flows
    import crewai_tools as ct
except Exception:  # pragma: no cover - defensive guard for optional dependency
    ct = None
    logger.warning("crew_ai_tools_unavailable")
if ct is not None:
    BaseTool = ct.BaseTool
    ScrapeWebsiteTool = ct.ScrapeWebsiteTool
    SerperDevTool = ct.SerperDevTool
    CREW_TOOLS_AVAILABLE = True
else:

    class BaseTool:  # type: ignore[override] - stub to satisfy typing/runtime usage
        """Minimal stub replicating CrewAI BaseTool behaviour."""

        name: str = "crew_ai_stub_base_tool"
        description: str = "Stub for crewai tools when dependency is unavailable."

        def __call__(self, *args, **kwargs):
            return self._run(*args, **kwargs)

        async def _arun(self, *args, **kwargs):  # pragma: no cover - sync flows dominate
            return self._run(*args, **kwargs)

        def _run(self, *args, **kwargs):  # pragma: no cover - to be overridden
            raise NotImplementedError

    class _StubTool(BaseTool):
        def __init__(self, *, name: str, description: str):
            self.name = name
            self.description = description

        def _run(self, *_args, **_kwargs):
            logger.info("crew_ai_tools_stub_invoked", extra={"tool": self.name})
            return {
                "status": "stub",
                "reason": "crew_ai_tools_unavailable",
            }

    class ScrapeWebsiteTool(_StubTool):
        def __init__(self):
            super().__init__(
                name="ScrapeWebsiteTool",
                description="Stub implementation: crewai_tools package unavailable.",
            )

    class SerperDevTool(_StubTool):
        def __init__(self):
            super().__init__(
                name="SerperDevTool",
                description="Stub implementation: crewai_tools package unavailable.",
            )

    CREW_TOOLS_AVAILABLE = False

# Инициализируем Exa (Exa — это наша стратегическая замена Google)
exa = Exa(api_key=os.environ.get("EXA_API_KEY"))

# Создаем ExaSearchTool
class ExaSearchTool(BaseTool):
    name: str = "Exa Advanced Search Tool"
    description: str = "Продвинутый ИИ-поиск. Используй для глубокого анализа, поиска трендов и ответов на сложные вопросы."
    
    def _run(self, query: str) -> str:
        try:
            response = exa.search_and_contents(query, type="magic", num_results=5)
            return str(response)
        except Exception as e:
            return f"Ошибка при поиске Exa: {e}"

# Оборачиваем стандартные инструменты для нашего Crew
scrape_tool = ScrapeWebsiteTool()
serper_tool = SerperDevTool()
exa_search_tool = ExaSearchTool()

print("Модуль tools/search_tools.py инициализирован.")
