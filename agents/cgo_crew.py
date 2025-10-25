import logging
import os

from crewai import Agent, Crew, Process, Task
from langchain_openai import ChatOpenAI

# Импорт наших новых инструментов
from tools.search_tools import (
    CREW_TOOLS_AVAILABLE as SEARCH_TOOLS_AVAILABLE,
    exa_search_tool,
    scrape_tool,
    serper_tool,
)
from tools.image_tools import (
    CREW_TOOLS_AVAILABLE as IMAGE_TOOLS_AVAILABLE,
    LeonardoImageTool,
)

logger = logging.getLogger(__name__)


def _build_real_crew() -> Crew:
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")

    if not openrouter_api_key:
        logger.warning(
            "OPENROUTER_API_KEY is not set. Initializing the OpenRouter client without authentication."
        )

    llm = ChatOpenAI(
        model=os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-haiku"),
        api_key=openrouter_api_key or None,
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        temperature=0.2,
    )

    researcher = Agent(
        role="Market Researcher",
        goal='Найти вирусные тренды и инсайты в нише "AI+Crypto" и "TON"',
        backstory=(
            """Ты - элитный аналитик, специализирующийся на пересечении ИИ и Web3. "
            "Твоя задача - находить 'альфа-информацию' до того, как она станет мейнстримом, "
            "используя ExaSearch."""
        ),
        verbose=True,
        llm=llm,
        tools=[exa_search_tool, serper_tool],
    )

    strategist = Agent(
        role="Content Strategist",
        goal=(
            "Создать виральный контент-план (статьи, посты в X) на основе отчета аналитика."
        ),
        backstory=(
            """Ты - гений маркетинга, который превращает сложные ИИ-концепции в "
            "простые, захватывающие посты, которые генерируют хайп для 'Genesis Avatar' NFT."""
        ),
        verbose=True,
        llm=llm,
        tools=[serper_tool, scrape_tool],
    )

    artist = Agent(
        role="Visual Artist",
        goal="Создать 1-2 впечатляющих изображения для контент-плана.",
        backstory=(
            """Ты - ИИ-художник, обученный на Leonardo. Ты создаешь визуал, "
            "который идеально дополняет контент и привлекает внимание к нашему 'AI+Crypto' бренду."""
        ),
        verbose=True,
        llm=llm,
        tools=[LeonardoImageTool()],
    )

    research_task = Task(
        description="Проанализируй текущие тренды в TON и AI. Найди 3 болевые точки аудитории.",
        expected_output="Подробный отчет на 300 слов о 3 трендах.",
        agent=researcher,
    )

    strategy_task = Task(
        description=(
            "На основе отчета о трендах, напиши 3 вирусных твита для X и 1 короткий блог-пост для Telegram."
        ),
        expected_output="Готовый контент-план (3 твита и 1 пост).",
        agent=strategist,
    )

    image_task = Task(
        description=(
            "На основе контент-плана, создай 1 промпт и сгенерируй 1 изображение для самого вирусного твита."
        ),
        expected_output="URL сгенерированного изображения от Leonardo AI.",
        agent=artist,
    )

    return Crew(
        agents=[researcher, strategist, artist],
        tasks=[research_task, strategy_task, image_task],
        process=Process.sequential,
        verbose=2,
    )


class _StubCrew:
    def kickoff(self, inputs):  # pragma: no cover - exercised in tests
        logger.warning(
            "cgo_crew_stubbed",
            extra={
                "search_tools": SEARCH_TOOLS_AVAILABLE,
                "image_tools": IMAGE_TOOLS_AVAILABLE,
            },
        )
        return {
            "status": "stub",
            "reason": "crew_ai_tools_unavailable",
            "inputs": inputs,
        }


if SEARCH_TOOLS_AVAILABLE and IMAGE_TOOLS_AVAILABLE:
    try:
        cgo_crew = _build_real_crew()
        print("Департамент CGO-AI (Crew) инициализирован.")
    except Exception as exc:  # pragma: no cover - guard against optional deps
        logger.warning("cgo_crew_init_failed", exc_info=exc)
        cgo_crew = _StubCrew()
else:
    cgo_crew = _StubCrew()
