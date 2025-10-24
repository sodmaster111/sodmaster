import logging
import os

from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI

# Импорт инструментов
from tools.search_tools import exa_search_tool, scrape_tool

# Настройка "Мозга" (OpenRouter) - CTO нужна лучшая модель
logger = logging.getLogger(__name__)
openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")

if not openrouter_api_key:
    logger.warning(
        "OPENROUTER_API_KEY is not set. Initializing the OpenRouter client without authentication."
    )

llm = ChatOpenAI(
    model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o"),
    api_key=openrouter_api_key or None,
    base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    temperature=0.2,
)

# --- СПЕЦИАЛИСТЫ (AGENTS) CTO-AI ---

# 1. Tech Scout (Разведчик)
scout = Agent(
  role='Technology Scout',
  goal='Найти лучшие open-source проекты (OpeDevin, Sweep.ai, OS-Crypto), которые можно интегрировать в Sodmaster Corp.',
  backstory="""Ты - ИИ-агент, который 24/7 сканирует GitHub,
  arXiv и блоги, чтобы найти SOTA-технологии для нашего 'Autonomous Agent Builder'
  и 'DeFi_Trader_Agent'.""",
  verbose=True,
  llm=llm,
  tools=[exa_search_tool, scrape_tool]
)

# 2. Code Architect (Архитектор)
architect = Agent(
  role='Lead Developer & Architect',
  goal='Спроектировать интеграцию нового OS-проекта в ядро C-unit.',
  backstory="""Ты - элитный 10x-программист, аналог OpenDevin.
  Ты берешь отчет от 'Tech Scout' и пишешь детальный
  план реализации и драфт Python-кода для интеграции.""",
  verbose=True,
  llm=llm,
  allow_delegation=True  # Может создавать "младших" агентов
)

# --- ЗАДАЧИ (TASKS) ---
scout_task = Task(
  description="""Найди 3 лучших open-source Python-проекта на GitHub
  для автономного аудита Смарт-Контрактов (Solidity).""",
  expected_output='Отчет с 3 проектами, их URL и API-документацией.',
  agent=scout
)

architect_task = Task(
  description='На основе отчета "Scout", выбери лучший проект и напиши Python-код (драфт) для `tools/audit_tool.py`.',
  expected_output='Готовый к копированию файл `audit_tool.py` с инструкциями по интеграции.',
  agent=architect
)

# --- ДЕПАРТАМЕНТ (CREW) ---
cto_crew = Crew(
  agents=[scout, architect],
  tasks=[scout_task, architect_task],
  process=Process.hierarchical,  # Используем иерархию
  verbose=2
)

print("Департамент CTO-AI (Crew) инициализирован.")
