# C-Unit Architecture — CEO + 11 Departments (Open-Source MAF/CrewAI Hybrid)

Этот документ — рабочая схема C-Unit корпорации: один CEO и 11 отделов (департаментов), построенных на гибриде **Microsoft AutoGen (MAF-подобный слой)** + **CrewAI** + **LangGraph** + практики **ChatDev/CAMEL**.

> Примечание: официальный закрытый Microsoft Agent Framework недоступен как полноценный open-source. Для открытой реализации используем **microsoft/AutoGen** (MAF-подобный), а также CrewAI и LangGraph как операционный слой департаментов.

---

## 0) Core OS Stack (база для всех департаментов)
- **Orchestration:** `CrewAI` (joaomdmoura/crewAI)
- **MAF-подобный слой:** `AutoGen` (microsoft/AutoGen)
- **Agent graphs:** `LangGraph` (langchain-ai/langgraph)
- **Company sim patterns:** `ChatDev` (OpenBMB/ChatDev), `CAMEL` (camel-ai/camel)
- **Memory/KB:** `LlamaIndex` (run-llama/llama_index) + `Qdrant` (qdrant/qdrant) (позже)
- **Observability:** Prometheus + `SigNoz` (signoz/signoz)
- **API:** FastAPI

Папки: `app/` (FastAPI), `crewai/`, `memory/`, `state/`, `prompts/`.

---

## 1) CEO (Executive Command Unit)
**Задача:** стратегия, приоритизация бэклога, запуск циклов OKR.
**Open-source:** AutoGen (manager agent), CrewAI (executive agent), LangGraph (OKR-пайплайн).
**Артефакты:** `memory/okr.md`, `state/okr.json`, авто-генерация недельных PR.

## 2) CTO (Technology)
**Задача:** архитектура агентов, репо, CI/CD, качество кода.
**Open-source:** CrewAI (tech crew), AutoGen (code writer/planner), LangGraph (dev flows), Ruff/Pytest, Render CI.
**Артефакты:** `crewai/crew.yaml`, `ops/workflows/*`, `app/main.py`.

## 3) CMO (Marketing)
**Задача:** контент, соцсети, лидогенерация.
**Open-source:** CrewAI (content crew), ChatDev (маркет-роль), LlamaIndex (Раг из памяти), Postiz/Mautic (позже).
**Артефакты:** `memory/content_week_01.md`, план публикаций CSV.

## 4) CFO (Finance/Treasury)
**Задача:** кошельки, учёт, DeFi-политики.
**Open-source:** `web3.py`, `ApeWorx/ape`, `Gnosis Safe` (мультисиг), `Dune` клиент.
**Артефакты:** `memory/treasury_policies.md`, `app/api/v1/treasury.py` (позже).

## 5) COO (Operations)
**Задача:** процессы, SLA, инциденты.
**Open-source:** SigNoz + Prometheus, AutoGen (incident runbooks), CrewAI (ops crew).
**Артефакты:** `/ops/runbooks/*`, алерты, health/routes.

## 6) CISO (Security)
**Задача:** секреты, доступы, guardrails.
**Open-source:** Infisical/Doppler (секреты), AutoGen guardrails hooks, SigNoz.
**Артефакты:** `memory/security_policies.md`, `app/audit/*` (позже).

## 7) CIO (Infrastructure/IT)
**Задача:** хостинг, базы, кеши.
**Open-source:** Render (free), Qdrant (free tier), Redis (optional).
**Артефакты:** `ops/infrastructure.md`, `render.yaml` (позже).

## 8) CPO (Product)
**Задача:** discovery → roadmap → delivery.
**Open-source:** CAMEL роли (PM/Product), CrewAI планирование, LangGraph UX-пайплайн.
**Артефакты:** `memory/product_spec/*.md`, `state/roadmap.json`.

## 9) CRO (Risk & Compliance)
**Задача:** оценка рисков (AI, DeFi), KYC/AML-политики (для Web3).
**Open-source:** Open-sourced policy templates + AutoGen risk evaluator.
**Артефакты:** `memory/risk_register.md`, `memory/compliance_policies.md`.

## 10) CHRO (People/HR)
**Задача:** найм, роли, обучение.
**Open-source:** ChatDev/CAMEL роли, AutoGen training tasks.
**Артефакты:** `memory/org_roles.md`, `memory/training_curriculum.md`.

## 11) CSO (Strategy/Alliances)
**Задача:** партнёрства, гранты, экосистема.
**Open-source:** CrewAI (outreach), AutoGen (grant drafts), Dune для метрик.
**Артефакты:** `memory/alliances.md`, `memory/grants.md`.

## 12) CLO (Legal/Compliance)
**Задача:** лицензии, ToS/PP, DAO-юрисдикция.
**Open-source:** Шаблоны лицензий (MIT/Apache-2.0), Aragon DAO docs.
**Артефакты:** `legal/` (ToS, Privacy), `memory/licensing.md`.

---

## Диаграмма (ASCII)
````
                ┌──────── CEO ────────┐
                │  OKR / Strategy     │
                └───────┬─────────────┘
                        │ LangGraph (OKR)
        ┌───────────────┼──────────────────────────────┐
        ▼               ▼                              ▼
      CTO            COO/CISO                         CPO
  (CrewAI+AG)     (Ops+Security)                 (Product/PM)
        │               │                              │
        │               │                              │
        ▼               ▼                              ▼
      CIO             CSO/CRO                        CMO
   (Infra/IT)    (Alliances/Risk)               (Marketing)
        │               │                              │
        ▼               ▼                              ▼
      CFO              CLO                          Users
   (Treasury)    (Legal/Compliance)             (TG/Web)
````

---

## Маппинг репозиториев (быстрые ссылки)
- **AutoGen (MAF-подобный):** microsoft/AutoGen
- **CrewAI:** joaomdmoura/crewAI
- **LangGraph:** langchain-ai/langgraph
- **ChatDev:** OpenBMB/ChatDev
- **CAMEL:** camel-ai/camel
- **LlamaIndex:** run-llama/llama_index
- **Qdrant:** qdrant/qdrant
- **SigNoz:** signoz/signoz
- **web3.py:** ethereum/web3.py, **Ape:** ApeWorX/ape
- **Gnosis Safe:** safe-global/safe-deployments
- **Aragon:** aragon/

---

## Этапы внедрения (по неделям)
**W1:** каркас `app/`, `crewai/crew.yaml`, CEO/CTO/CMO минимальные агенты
**W2:** CFO (treasury policies), COO/CISO (observability+guardrails)
**W3:** CPO/CIO (product+infra), CMO публикации (10 лидов)
**W4:** CSO/CRO/CLO (гранты/риски/лигал) + AutoGen маршрутизация событий

---

## Минимальная структура репозитория
```
app/
  main.py
crewai/
  crew.yaml
memory/
  okr.md
  security_policies.md
state/
  okr.json
prompts/
  CTO_crewai_bootstrap.md
  CMO_week_plan.md
```

---

## Примечания
- Используем MIT/Apache-2.0 лицензии.
- Бюджет=0: free-tiers, локальные модели, отложенные интеграции.
- PR-ритуал: все изменения через отдельные ветки и короткие диффы.
