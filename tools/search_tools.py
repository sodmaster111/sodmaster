from crewai_tools import BaseTool, ScrapeWebsiteTool, SerperDevTool
from exa_py import Exa
import os

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
