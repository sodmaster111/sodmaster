import logging
import os

from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI

# Импорт наших новых инструментов
from tools.search_tools import scrape_tool, serper_tool, exa_search_tool
from tools.image_tools import LeonardoImageTool

# Настройка "Мозга" (OpenRouter)
logger = logging.getLogger(__name__)
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

# --- СПЕЦИАЛИСТЫ (AGENTS) CGO-AI ---

# 1. Market Researcher (Аналитик)
researcher = Agent(
  role='Market Researcher',
  goal='Найти вирусные тренды и инсайты в нише "AI+Crypto" и "TON"',
  backstory="""Ты - элитный аналитик, специализирующийся на
  пересечении ИИ и Web3. Твоя задача - находить 'альфа-информацию'
  до того, как она станет мейнстримом, используя ExaSearch.""",
  verbose=True,
  llm=llm,
  tools=[exa_search_tool, serper_tool]
)

# 2. Content Strategist (Копирайтер)
strategist = Agent(
  role='Content Strategist',
  goal='Создать виральный контент-план (статьи, посты в X) на основе отчета аналитика.',
  backstory="""Ты - гений маркетинга, который превращает
  сложные ИИ-концепции в простые, захватывающие посты,
  которые генерируют хайп для 'Genesis Avatar' NFT.""",
  verbose=True,
  llm=llm,
  tools=[serper_tool, scrape_tool]
)

# 3. Visual Artist (Дизайнер)
artist = Agent(
  role='Visual Artist',
  goal='Создать 1-2 впечатляющих изображения для контент-плана.',
  backstory="""Ты - ИИ-художник, обученный на Leonardo.
  Ты создаешь визуал, который идеально дополняет контент
  и привлекает внимание к нашему "AI+Crypto" бренду.""",
  verbose=True,
  llm=llm,
  tools=[LeonardoImageTool()]
)

# --- ЗАДАЧИ (TASKS) ---
research_task = Task(
  description='Проанализируй текущие тренды в TON и AI. Найди 3 болевые точки аудитории.',
  expected_output='Подробный отчет на 300 слов о 3 трендах.',
  agent=researcher
)

strategy_task = Task(
  description='На основе отчета о трендах, напиши 3 вирусных твита для X и 1 короткий блог-пост для Telegram.',
  expected_output='Готовый контент-план (3 твита и 1 пост).',
  agent=strategist
)

image_task = Task(
  description='На основе контент-плана, создай 1 промпт и сгенерируй 1 изображение для самого вирусного твита.',
  expected_output='URL сгенерированного изображения от Leonardo AI.',
  agent=artist
)

# --- ДЕПАРТАМЕНТ (CREW) ---
cgo_crew = Crew(
  agents=[researcher, strategist, artist],
  tasks=[research_task, strategy_task, image_task],
  process=Process.sequential,
  verbose=2
)

print("Департамент CGO-AI (Crew) инициализирован.")
