---
doc_type: proposal
status: draft
created: 2026-01-28
updated: 2026-01-28
based_on: architecture-integrity-research.md
tags:
  - architecture
  - roadmap
  - documentation
---

# План доработок системы архитектурного контроля

> На основе исследования: [architecture-integrity-research.md](./architecture-integrity-research.md)  
> Проект: bz2-video-transcriber  
> Дата: 2026-01-28

---

## Текущее состояние

### Что уже есть

| Компонент | Статус | Позиция в индустрии |
|-----------|--------|---------------------|
| ADR (13 документов) | ✅ Работает | Лучше 90% проектов |
| arch-checker | ✅ Работает | Уникально |
| doc-sync | ✅ Работает | Уникально |
| architecture-summary | ✅ Работает | Опережает индустрию |
| arch-audit workflow | ✅ Работает | Редкая практика |
| Diátaxis+ Framework | ✅ Работает | Уникально |

### Выявленные gaps

| Gap | Влияние | Источник |
|-----|---------|----------|
| **Реактивность** — проверки после кода | Деградация накапливается до обнаружения | Все исследования |
| **Нет CI интеграции** — ручной запуск | Можно забыть проверить | Все исследования |
| **CLAUDE.md не оптимизирован** | Context drift в длинных сессиях | Claude, ChatGPT |
| **Нет метрик** — субъективная оценка | Сложно измерить прогресс | Perplexity |
| **Агенты не как MCP** — текстовые инструкции | Не интегрированы в agentic workflows | Perplexity, ChatGPT |

---

## Цели доработок

```
┌─────────────────────────────────────────────────────────────────┐
│                       ЦЕЛЕВОЕ СОСТОЯНИЕ                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Проактивность                                                  │
│  └─ Архитектура проверяется ДО написания кода                   │
│                                                                 │
│  Автоматизация                                                  │
│  └─ CI блокирует merge при нарушениях                           │
│                                                                 │
│  Измеримость                                                    │
│  └─ Dashboard с метриками архитектурного здоровья               │
│                                                                 │
│  AI-native                                                      │
│  └─ Агенты интегрированы через MCP                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Фаза 1: Проактивность (1-2 дня)

> **Цель:** Сделать архитектурную проверку обязательной ДО написания кода

### 1.1. Plan.md паттерн

**Что:** Обязательный артефакт планирования перед реализацией фичи.

**Зачем:** 
- Исследование показало, что "mandatory design review before code" снижает количество переделок
- Превращает систему из реактивной в проактивную
- Создаёт точку синхронизации между сессиями

**Как:**

```markdown
# Шаблон PLAN.md

## Фича
{название и краткое описание}

## Архитектурный анализ

### Затрагиваемые модули
- [ ] backend/app/services/...
- [ ] frontend/src/components/...

### Релевантные ADR
- ADR-001: {как влияет}
- ADR-004: {как влияет}

### Результат arch-checker
{вставить вывод проверки}

## План изменений

### Код
1. ...
2. ...

### Документация (doc-sync)
- [ ] docs/api-reference.md
- [ ] docs/pipeline/XX.md

## Открытые вопросы
- ...

## Нужен новый ADR?
{да/нет, почему}
```

**Интеграция в workflow:**

```markdown
# Добавить в CLAUDE.md

## Before implementing ANY feature

1. Create PLAN.md in project root
2. Run arch-checker: "Проверь соответствие ADR для: {feature}"
3. Fill all sections
4. Only then start coding
5. Delete PLAN.md after merge (or archive)
```

**Критерий успеха:** 100% новых фич начинаются с PLAN.md

---

### 1.2. Оптимизация CLAUDE.md

**Что:** Сократить CLAUDE.md до < 200 строк, вынести детали.

**Зачем:**
- Исследование: "После ~150-200 инструкций качество следования падает"
- Context drift в длинных сессиях
- Progressive disclosure работает лучше

**Как:**

**До (текущий CLAUDE.md):**
```markdown
# Длинный документ с деталями архитектуры, командами,
# примерами, историей решений...
# 500+ строк
```

**После (оптимизированный):**
```markdown
# bz2-video-transcriber

## Quick Reference
- Dev: `docker-compose up -d`
- Test: `pytest`
- Deploy: `./scripts/deploy.sh`

## Architecture (MUST READ FIRST)
@docs/audit/architecture-summary.md

## Before ANY code changes
1. Check ADR: @docs/adr/
2. Run arch-checker for feature
3. Create PLAN.md

## Key Decisions
- Claude API only (no fallback) — ADR-007
- CamelCase in API — ADR-013
- External prompts — ADR-008

## When stuck
- Pipeline: @docs/pipeline/stages.md
- API: @docs/api-reference.md
- Config: @docs/configuration.md
```

**Критерий успеха:** CLAUDE.md < 200 строк, ссылки на детали

---

### 1.3. Subagent для архитектурного review

**Что:** Использовать subagent для изолированной проверки после реализации.

**Зачем:**
- Subagent работает в отдельном context window
- Не загрязняет основную сессию
- Свежий взгляд на код

**Как:**

```markdown
# Добавить в CLAUDE.md

## After implementing feature

Run architecture review:
"Use subagent to review changes against ADR-001, ADR-004, ADR-007"

Subagent should check:
- Stage abstraction compliance (ADR-001)
- AI client patterns (ADR-004)
- No fallback logic (ADR-007)
- CamelCase in API responses (ADR-013)
```

**Критерий успеха:** Каждая фича проходит subagent review

---

## Фаза 2: Автоматизация (3-5 дней)

> **Цель:** CI блокирует merge при архитектурных нарушениях

### 2.1. Python архитектурный линтер

**Что:** Добавить import-linter для проверки границ модулей.

**Зачем:**
- Все три исследования рекомендуют архитектурные линтеры
- Автоматическая проверка, не зависит от AI
- Ловит нарушения до merge

**Как:**

```bash
# Установка
pip install import-linter

# pyproject.toml
[tool.importlinter]
root_package = "app"

[[tool.importlinter.contracts]]
name = "Stages don't import from API"
type = "forbidden"
source_modules = ["app.services.stages"]
forbidden_modules = ["app.api"]

[[tool.importlinter.contracts]]
name = "API doesn't import from stages directly"
type = "forbidden"
source_modules = ["app.api"]
forbidden_modules = ["app.services.stages"]

[[tool.importlinter.contracts]]
name = "Services use AI clients through abstraction"
type = "layers"
layers = [
    "app.api",
    "app.services",
    "app.services.ai_clients",
]
```

```bash
# Проверка
lint-imports
```

**Критерий успеха:** `lint-imports` в CI, 0 нарушений

---

### 2.2. Pre-commit hooks

**Что:** Автоматические проверки перед коммитом.

**Зачем:**
- Ловит проблемы до push
- Быстрая обратная связь
- Не требует ручного запуска

**Как:**

```yaml
# .pre-commit-config.yaml

repos:
  - repo: local
    hooks:
      - id: import-linter
        name: Check architecture boundaries
        entry: lint-imports
        language: system
        pass_filenames: false
        
      - id: doc-sync-check
        name: Check if docs need update
        entry: python scripts/doc_sync_check.py
        language: system
        pass_filenames: true
        files: ^backend/app/.*\.py$
```

```python
# scripts/doc_sync_check.py
"""
Минимальная версия doc-sync для pre-commit.
Выводит warning если изменённые файлы требуют обновления документации.
"""
import sys
from pathlib import Path

# Упрощённый маппинг из doc-sync.md
MAPPING = {
    "backend/app/api/": ["docs/api-reference.md", "docs/pipeline/09-api.md"],
    "backend/app/models/schemas.py": ["docs/data-formats.md"],
    "backend/app/services/stages/": ["docs/pipeline/"],
    # ... остальной маппинг
}

def check_files(changed_files):
    docs_to_update = set()
    for f in changed_files:
        for pattern, docs in MAPPING.items():
            if pattern in f:
                docs_to_update.update(docs)
    
    if docs_to_update:
        print("⚠️  Documentation may need update:")
        for doc in sorted(docs_to_update):
            print(f"   - {doc}")
        print("\nRun doc-sync for details.")
    
    return 0  # Warning only, don't block

if __name__ == "__main__":
    sys.exit(check_files(sys.argv[1:]))
```

**Критерий успеха:** Pre-commit установлен, срабатывает на каждый коммит

---

### 2.3. CI pipeline gate

**Что:** GitHub Actions workflow для архитектурных проверок.

**Зачем:**
- Последний рубеж перед merge
- Нельзя обойти (в отличие от pre-commit)
- Документирует статус в PR

**Как:**

```yaml
# .github/workflows/architecture.yml

name: Architecture Check

on:
  pull_request:
    paths:
      - 'backend/**'
      - 'frontend/**'

jobs:
  architecture:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install import-linter
      
      - name: Check import boundaries
        run: lint-imports
      
      - name: Check circular dependencies
        run: |
          pip install pydeps
          pydeps backend/app --no-show --no-output || true
          # Fail if cycles detected
          
      - name: Doc sync reminder
        run: |
          python scripts/doc_sync_check.py $(git diff --name-only origin/main)
```

**Критерий успеха:** PR не мержится при нарушениях архитектуры

---

## Фаза 3: Измеримость (1-2 дня)

> **Цель:** Количественные метрики архитектурного здоровья

### 3.1. Architecture Health Dashboard

**Что:** Markdown-файл с метриками, обновляемый при аудите.

**Зачем:**
- Исследование: "Нет стандартных метрик деградации"
- Визуализация тренда
- Объективная оценка вместо субъективной

**Как:**

```markdown
# docs/audit/health-dashboard.md

---
doc_type: audit
status: active
updated: 2026-01-28
---

# Architecture Health Dashboard

## Current Status

| Metric | Value | Trend | Target |
|--------|-------|-------|--------|
| ADR Violations | 0 | ✅ | 0 |
| Import Boundary Violations | 0 | ✅ | 0 |
| Circular Dependencies | 0 | ✅ | 0 |
| Doc Currency | 74% | ⬆️ +13% | > 80% |
| Undocumented Modules | 3 | ⬇️ -2 | 0 |

## History

| Date | ADR Viol. | Import Viol. | Doc Currency |
|------|-----------|--------------|--------------|
| 2026-01-28 | 0 | 0 | 74% |
| 2026-01-23 | 0 | - | 61% |
| 2026-01-15 | 2 | - | 55% |

## Last Audit

- **Date:** 2026-01-23
- **Version:** v0.59.2
- **Result:** [baseline-2026-01-23.md](./baseline-2026-01-23.md)

## Next Actions

- [ ] Update docs/pipeline/05-longread.md
- [ ] Add frontmatter to remaining docs
- [ ] Setup import-linter
```

**Интеграция:**

```markdown
# Добавить в audit.md workflow

## После каждого аудита

Обнови docs/audit/health-dashboard.md:
1. Текущие метрики
2. История (добавь строку)
3. Next Actions
```

**Критерий успеха:** Dashboard обновляется при каждом аудите

---

### 3.2. Метрики в arch-audit

**Что:** Добавить количественные метрики в arch-audit workflow.

**Зачем:**
- Объективизация оценки
- Возможность сравнения между аудитами
- Раннее обнаружение деградации

**Как:**

Добавить в `arch-audit.md` секцию:

```markdown
## Метрики для сбора

### Автоматические (из линтеров)
- Import violations count
- Circular dependencies count
- Unused imports count

### Полуавтоматические (из анализа)
- Files with >500 LOC
- Functions with >50 LOC
- Modules with >10 dependencies

### Ручные (из findings)
- Duplicated patterns count
- Missing abstractions count
- ADR compliance issues
```

**Критерий успеха:** Каждый arch-audit содержит числовые метрики

---

## Фаза 4: AI-native интеграция (2-4 недели)

> **Цель:** Агенты интегрированы через MCP

### 4.1. MCP-сервер архитектуры (исследование)

**Что:** Оформить arch-checker и doc-sync как MCP tools.

**Зачем:**
- Все три исследования рекомендуют MCP
- Агенты обязаны обращаться к серверу
- Стандартный протокол для agentic workflows

**Как:**

```
┌─────────────────────────────────────────────────────────────────┐
│              ARCHITECT MCP SERVER (концепция)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  RESOURCES                                                      │
│  ├─ architecture://summary                                      │
│  │   → docs/audit/architecture-summary.md                       │
│  ├─ architecture://adr/{number}                                 │
│  │   → docs/adr/{number}-*.md                                   │
│  └─ architecture://health                                       │
│      → docs/audit/health-dashboard.md                           │
│                                                                 │
│  TOOLS                                                          │
│  ├─ check_adr_compliance(files: list[str])                      │
│  │   → Результат arch-checker                                   │
│  ├─ get_docs_to_update(files: list[str])                        │
│  │   → Результат doc-sync                                       │
│  ├─ validate_imports(path: str)                                 │
│  │   → Результат import-linter                                  │
│  └─ get_relevant_adrs(feature: str)                             │
│      → Список ADR по ключевым словам                            │
│                                                                 │
│  PROMPTS                                                        │
│  ├─ new_feature_plan                                            │
│  │   → Шаблон PLAN.md                                           │
│  └─ adr_template                                                │
│      → Шаблон нового ADR                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Этапы:**

1. **Исследование** — изучить MCP SDK, примеры серверов
2. **Прототип** — минимальный сервер с одним tool
3. **Интеграция** — подключение к Claude Code
4. **Расширение** — добавление остальных tools

**Критерий успеха:** MCP-сервер работает, Claude Code использует tools

---

### 4.2. Skills для Claude Code

**Что:** Вынести редко используемые знания в Skills.

**Зачем:**
- CLAUDE.md остаётся компактным
- Skills загружаются on-demand
- Лучшая организация знаний

**Как:**

```
.claude/skills/
├── add-pipeline-stage.md    # Из arch-checker чеклиста
├── add-ai-provider.md       # Из arch-checker чеклиста  
├── add-api-endpoint.md      # Из arch-checker чеклиста
├── run-arch-audit.md        # Из arch-audit workflow
└── create-adr.md            # Шаблон и процесс
```

```markdown
# .claude/skills/add-pipeline-stage.md

# How to Add a New Pipeline Stage

## Prerequisites
- Read ADR-001 (Stage Abstraction)
- Read ADR-002 (Pipeline Decomposition)

## Checklist

### 1. Create Stage Class
```python
# backend/app/services/stages/{name}_stage.py

class NewStage(BaseStage):
    name = "new_stage"
    depends_on = ["previous_stage"]
    
    async def execute(self, context: StageContext) -> Result:
        ...
```

### 2. Register Stage
- Add to `stages/__init__.py`
- Add weight to `progress_manager.py`

### 3. Create Prompts
- Add `config/prompts/{stage_name}/system.md`

### 4. Update Documentation
- Create `docs/pipeline/XX-{name}.md`
- Update `docs/pipeline/stages.md`

### 5. Verify
- Run arch-checker
- Run tests
```

**Критерий успеха:** 3+ Skills созданы и используются

---

## Сводка по фазам

| Фаза | Срок | Effort | Результат |
|------|------|--------|-----------|
| **1. Проактивность** | 1-2 дня | Low | Plan.md, slim CLAUDE.md, subagent review |
| **2. Автоматизация** | 3-5 дней | Medium | import-linter, pre-commit, CI gate |
| **3. Измеримость** | 1-2 дня | Low | Health dashboard, метрики в аудите |
| **4. AI-native** | 2-4 недели | High | MCP-сервер, Skills |

---

## Приоритизация

```
         Impact
           ▲
           │
    High   │   [2.3 CI gate]     [4.1 MCP-сервер]
           │   [2.1 Линтер]
           │
           │   [1.1 Plan.md]     [1.2 Slim CLAUDE.md]
    Medium │   [2.2 Pre-commit]
           │   [3.1 Dashboard]
           │
           │   [1.3 Subagent]    [4.2 Skills]
    Low    │   [3.2 Метрики]
           │
           └────────────────────────────────────────► Effort
               Low              Medium           High
```

**Рекомендуемый порядок:**

1. **1.1 Plan.md** — максимальный impact при минимальном effort
2. **1.2 Slim CLAUDE.md** — быстро, сразу улучшает следование правилам
3. **2.1 Линтер** — автоматизация без зависимостей
4. **3.1 Dashboard** — визуализация прогресса
5. **2.2 Pre-commit** — после настройки линтера
6. **2.3 CI gate** — после pre-commit
7. **4.2 Skills** — когда накопится опыт
8. **4.1 MCP-сервер** — когда будет время на исследование

---

## Критерии успеха (Definition of Done)

### Фаза 1 завершена когда:
- [ ] PLAN.md шаблон в репозитории
- [ ] CLAUDE.md < 200 строк
- [ ] Workflow в документации обновлён
- [ ] Одна фича реализована с Plan.md

### Фаза 2 завершена когда:
- [ ] `lint-imports` проходит без ошибок
- [ ] Pre-commit hooks установлены
- [ ] CI workflow создан и работает
- [ ] Один PR заблокирован и исправлен

### Фаза 3 завершена когда:
- [ ] health-dashboard.md создан
- [ ] arch-audit обновлён с метриками
- [ ] Проведён один аудит с новыми метриками

### Фаза 4 завершена когда:
- [ ] MCP-сервер отвечает на запросы
- [ ] Claude Code использует MCP tools
- [ ] 3+ Skills созданы

---

## Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Линтер ломает существующий код | Medium | High | Сначала warning mode, потом error |
| CLAUDE.md слишком краткий | Low | Medium | A/B тестирование, итерации |
| MCP слишком сложен | Medium | Low | Отложить до Фазы 4 |
| Overhead от Plan.md | Low | Medium | Упрощённый шаблон для мелких фич |

---

## Связь с исследованием

| Рекомендация из исследования | Пункт плана |
|------------------------------|-------------|
| Plan.md как external memory | 1.1 |
| Slim CLAUDE.md (< 200 строк) | 1.2 |
| Subagents для review | 1.3 |
| Architecture linters в CI | 2.1, 2.3 |
| Pre-commit hooks | 2.2 |
| Метрики деградации | 3.1, 3.2 |
| MCP-сервер архитектуры | 4.1 |
| Skills для редких случаев | 4.2 |

---

## Следующий шаг

**Начать с Фазы 1.1:** Создать шаблон PLAN.md и протестировать на следующей фиче.

```
Создай PLAN.md для: {описание следующей фичи}
```

---

*Документ создан: 2026-01-28*
*На основе: architecture-integrity-research.md*
