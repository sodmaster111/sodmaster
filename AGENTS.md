# AGENTS.md — Sodmaster AI Corporation

## О проекте
Sodmaster - первая полностью автономная AI-корпорация, управляемая AI-агентами (C-Units).

## Технологический стек
- Backend: Python 3.11, FastAPI, Uvicorn, PostgreSQL, Redis
- AI Layer: OpenAI Codex, CrewAI, Microsoft Agent Framework
- Blockchain: TON, Ethereum, Bitcoin (multi-chain payments)
- Deployment: Render.com, GitHub Actions CI/CD
- Frontend: Astro static site (sodmaster.online)

## Архитектура C-Units (AI Департаменты)
1. DevCrew - Codex агенты (разработка, ревью, тестирование)
2. FinanceCrew - DeFi агенты, управление кошельками, крипто-платежи
3. MarketingCrew - контент, аналитика, growth hacking
4. SupportCrew - Telegram боты, customer support

## Структура репозитория
```
sodmaster/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── agents/              # AI агенты (C-Units)
│   ├── blockchain/          # TON/ETH/BTC интеграция
│   ├── api/                 # REST API endpoints
│   │   └── v1/              # API version 1
│   └── admin/               # Owner dashboard
├── docs/                    # Документация
│   ├── architecture/        # Архитектурные решения (ADR)
│   ├── api/                 # API документация
│   └── deployment/          # Инструкции по деплою
├── tests/                   # Тесты
│   ├── unit/                # Юнит-тесты
│   ├── integration/         # Интеграционные тесты
│   └── e2e/                 # End-to-end тесты
├── .github/workflows/       # GitHub Actions CI/CD
├── requirements.txt         # Production зависимости
├── runtime.txt              # Python версия для Render
└── AGENTS.md                # Этот файл
```

## Правила работы для AI-агентов
1. Все изменения через Pull Requests - никакого прямого коммита в main
2. Формат изменений: unified diff (минимальные патчи)
3. Issues с тегом codex:prompt для новых задач
4. Тесты обязательны для любого PR (pytest)
5. CI/CD проверяет код перед мержем
6. Безопасность: никаких hardcoded секретов, только ENV variables

## Команды для разработки
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest tests/

## Environment Variables (Render)
PYTHON_VERSION=3.11.9
PORT=10000
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
OPENAI_API_KEY=sk-...
TON_WALLET_ADDRESS=UQC_...
ETH_WALLET_ADDRESS=0x145...
BTC_WALLET_ADDRESS=bc1q...

## Деплой процесс
1. Push в main branch → GitHub Actions → Render автодеплой
2. Render запускает: pip install -r requirements.txt
3. Render стартует: uvicorn app.main:app --host 0.0.0.0 --port $PORT
4. Health check: GET /health должен вернуть 200 OK
