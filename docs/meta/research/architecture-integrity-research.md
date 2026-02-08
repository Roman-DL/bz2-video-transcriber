---
doc_type: research
status: active
created: 2026-01-28
sources: [Claude, ChatGPT, Perplexity]
tags:
  - architecture
  - ai-assisted-development
  - research
---

# Управление архитектурной целостностью при AI-assisted разработке

> Синтез исследований: Claude, ChatGPT, Perplexity  
> Дата: 2026-01-28

---

## Executive Summary

Проблема архитектурной деградации при AI-assisted разработке **признана индустрией**, но **не решена системно**. Все три источника сходятся в следующем:

| Консенсус | Статус |
|-----------|--------|
| Проблема реальна и усугубляется с ростом AI-adoption | ✅ Подтверждено |
| Полностью автоматического решения не существует | ✅ Подтверждено |
| Комбинация подходов работает лучше, чем любой один | ✅ Подтверждено |
| Роль человека-архитектора остаётся критической | ✅ Подтверждено |

**Ключевой инсайт:** Система bz2-video-transcriber (ADR + arch-checker + architecture-summary + doc-sync) реализует **~70-80% найденных паттернов** и опережает большинство практик индустрии. Главный gap — **проактивное enforcement** и **интеграция в CI/CD**.

---

## 1. Таксономия подходов

Все три исследования выделяют **6 основных классов решений**:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LANDSCAPE РЕШЕНИЙ                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ПРОАКТИВНЫЕ (до генерации кода)                                    │
│  ├─ IDE Rules (.cursorrules, CLAUDE.md)                             │
│  ├─ MCP-сервер архитектуры                                          │
│  └─ Spec-Driven Development                                         │
│                                                                     │
│  РЕАКТИВНЫЕ (после генерации)                                       │
│  ├─ Архитектурные линтеры (ArchUnit, dependency-cruiser)            │
│  ├─ Human review (AI-architect роль)                                │
│  └─ Периодический аудит                                             │
│                                                                     │
│  КООРДИНАЦИОННЫЕ (multi-agent)                                      │
│  ├─ Orchestrator + specialized agents                               │
│  └─ Architect Task → Coder Task паттерн                             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Детальный анализ по категориям

### 2.1. IDE Rules (Cursor / CLAUDE.md)

**Консенсус всех источников:**

| Аспект | Находка |
|--------|---------|
| Формат | Модульные правила по доменам, а не монолит |
| Размер | < 500 строк (после ~150-200 качество падает) |
| Структура | Core CLAUDE.md → ссылки на детальные файлы |
| Проблема | Context drift — правила "забываются" в длинных сессиях |
| Решение | Periodic Rule Reinforcement — явные напоминания |

**Best practices из всех источников:**

```markdown
# CLAUDE.md (минимальный)

## Architecture
See @docs/audit/architecture-summary.md

## Before implementing
1. Check relevant ADR: @docs/adr/
2. Run arch-checker for changes

## Commands
npm run dev | test | build
```

**Иерархия правил (Claude Code):**

```
~/.claude/CLAUDE.md          # глобальные
project/CLAUDE.md            # проектные  
project/.claude/rules/*.md   # модульные (path-scoped)
project/subdir/CLAUDE.md     # директорные (on-demand)
```

### 2.2. MCP-сервер архитектуры

**Самая перспективная рекомендация** (упоминается во всех трёх источниках):

```
┌─────────────────────────────────────────────────────────────────┐
│                 ARCHITECT MCP SERVER                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  RESOURCES (экспортирует данные)                                │
│  ├─ architecture-summary.md                                     │
│  ├─ ADR list by domain                                          │
│  └─ allowed dependencies matrix                                 │
│                                                                 │
│  TOOLS (предоставляет инструменты)                              │
│  ├─ check_change_against_adr(diff)    # arch-checker            │
│  ├─ suggest_adr_for_change(diff)      # генерация ADR           │
│  ├─ list_docs_to_update(diff)         # doc-sync                │
│  └─ architectural_smell_scan(path)    # arch-audit              │
│                                                                 │
│  PROMPTS (шаблоны)                                              │
│  └─ architectural decision template                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Преимущество:** Агенты **обязаны** обращаться к серверу перед генерацией — это превращает систему из реактивной в проактивную.

### 2.3. Архитектурные линтеры

**Единодушная рекомендация** как "последний рубеж":

| Инструмент | Язык | Возможности |
|------------|------|-------------|
| **ArchUnit** | Java | Unit-тесты архитектуры |
| **dependency-cruiser** | JS/TS | Правила импортов, циклы |
| **import-linter** | Python | Слои, границы модулей |
| **pydeps** | Python | Визуализация зависимостей |

**Интеграция:**

```yaml
# CI/CD gate
- name: Architecture check
  run: |
    dependency-cruiser --validate .dependency-cruiser.json src/
    # или для Python:
    lint-imports
```

**Ограничение:** Это **не AI-специфичный** инструмент — он не понимает намерений, только проверяет правила.

### 2.4. Multi-Agent Coordination

**ChatGPT подробно описывает Claude-Flow:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLAUDE-FLOW (64 agents)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PM Agent (orchestrator)                                        │
│      │                                                          │
│      ├── Backend Engineer                                       │
│      ├── Frontend Engineer                                      │
│      ├── Database Specialist                                    │
│      ├── QA Engineer                                            │
│      │                                                          │
│      ├── Standards Agent ←──── Читает .claude/standards/*.md    │
│      │   (проверяет паттерны)   Выявляет нарушения              │
│      │                          Генерирует план исправления     │
│      │                                                          │
│      └── Workflow Agent ←───── Читает ERD, sequence diagrams    │
│          (проверяет бизнес)     Сверяет с документацией         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Результат эксперимента:** 5 архитектурных нарушений обнаружены и исправлены автоматически.

**Проблемы:**
- Сложность настройки и отладки
- Конфликты между агентами
- Overkill для solo-разработчика

### 2.5. Spec-Driven Development

**Claude выделяет как emerging подход:**

```
Intent Layer      →  Бизнес-намерение
Contract Layer    →  OpenAPI, спецификации
Validation Layer  →  Drift detection
Generation Layer  →  AI создаёт код по спеке
Governance Layer  →  Compliance, audit
```

**Ключевая идея: Bidirectional Sync**

> Amazon Kiro (2025): "Developers can update code and request specification changes, OR update specs to trigger implementation tasks."

**Типы drift detection:**

| Тип | Пример |
|-----|--------|
| Structural | API возвращает поля, не описанные в спеке |
| Behavioral | Сервис игнорирует required поля |
| Semantic | Error handling отличается от контракта |
| Security | Scopes деградировали относительно политики |

### 2.6. Практики команд

**Все источники сходятся:**

| Практика | Описание |
|----------|----------|
| AI как "джуниор" | Обязательный human review |
| AI-architect роль | Владеет CLAUDE.md, обновляет ADR |
| Mandatory design review | План до кода, а не после |
| Регулярный аудит | Еженедельный arch-review |
| Единый ассистент | Один context-aware agent на весь репо |

---

## 3. Сравнительная матрица

| Подход | Проактивность | Интеграция | Overhead | Solo | Team | AI-native |
|--------|---------------|------------|----------|------|------|-----------|
| **IDE Rules** | ⚠️ Средняя | ✅ Встроено | ✅ Низкий | ✅ | ✅ | ✅ |
| **MCP-сервер** | ✅ Высокая | ⚠️ Требует настройки | ⚠️ Средний | ✅ | ✅ | ✅ |
| **Архитектурные линтеры** | ❌ Постфактум | ✅ CI/CD | ✅ Низкий | ✅ | ✅ | ❌ |
| **Multi-Agent** | ✅ Высокая | ❌ Сложная | ❌ Высокий | ❌ | ✅ | ✅ |
| **Spec-Driven** | ✅ Высокая | ❌ Emerging | ❌ Высокий | ⚠️ | ✅ | ✅ |
| **Human review** | ⚠️ Средняя | ✅ Процесс | ⚠️ Средний | N/A | ✅ | ❌ |
| **Твоя система** | ⚠️ Средняя | ⚠️ Ручная | ⚠️ Средний | ✅ | ✅ | ⚠️ Частично |

---

## 4. Оценка системы bz2-video-transcriber

### Что уже реализовано

| Компонент | Аналог в индустрии | Статус |
|-----------|-------------------|--------|
| **ADR** | Architecture Decision Records | ✅ Лучше среднего (13 ADR, структурированы) |
| **arch-checker** | Standards Agent (Claude-Flow) | ✅ Уникально (нет в Cursor/Claude по умолчанию) |
| **architecture-summary** | MCP Resources | ✅ Опережает (progressive disclosure) |
| **doc-sync** | Drift Detection lite | ✅ Есть |
| **arch-audit** | Periodic review | ✅ Есть |
| **Diátaxis+ Framework** | — | ✅ Уникально |

### Позиция относительно индустрии

```
┌─────────────────────────────────────────────────────────────────┐
│              MATURITY SPECTRUM                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Базовый ──────────────────────────────────────────► Продвинутый│
│                                                                 │
│  [Нет системы]                                                  │
│       ↓                                                         │
│  [Только CLAUDE.md] ← Большинство проектов                      │
│       ↓                                                         │
│  [CLAUDE.md + линтеры]                                          │
│       ↓                                                         │
│  [ADR + arch-checker + doc-sync] ← ★ ТЫ ЗДЕСЬ                   │
│       ↓                                                         │
│  [+ MCP-сервер + CI gates]                                      │
│       ↓                                                         │
│  [Multi-Agent с Architect Agent]                                │
│       ↓                                                         │
│  [Spec-Driven + Bidirectional Sync] ← Frontier                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Вывод:** Система находится в **верхних 10-20%** по зрелости среди AI-assisted проектов.

### Gaps относительно frontier

| Gap | Что нужно | Effort |
|-----|-----------|--------|
| Проактивность | Plan.md перед кодом, обязательный arch-checker | Low |
| CI интеграция | Линтеры + doc-sync в pipeline | Medium |
| MCP-сервер | Оформить агентов как MCP tools | Medium-High |
| Метрики | Количественные показатели деградации | Medium |

---

## 5. Нерешённые проблемы индустрии

**Консенсус всех трёх источников:**

| Проблема | Статус |
|----------|--------|
| **AI "забывает" архитектуру между сессиями** | Частично решается CLAUDE.md, MCP, но не полностью |
| **Проактивное enforcement до генерации** | Spec-Driven (emerging), MCP (experimental) |
| **Метрики архитектурной деградации** | Нет стандартов, только proxy-метрики |
| **Multi-agent consistency** | Исследовательская стадия |
| **Человек как bottleneck ревью** | Не решена |
| **Полная зависимость от качества документации** | Фундаментальное ограничение |

**Цитата из ChatGPT:**

> "Полностью проактивной системы, которая **сама выводит архитектурные правила из кода** и затем за ними следит, ещё не существует."

**Цитата из Perplexity:**

> "Лучшее, что сейчас есть — это комбинация архитектурного MCP-сервера, IDE-rules, архитектурных линтеров в CI и явной роли агента-архитектора."

---

## 6. Рекомендации для развития системы

### Immediate (эта неделя)

| Действие | Источник рекомендации |
|----------|----------------------|
| Оптимизировать CLAUDE.md (< 200 строк) | Claude, ChatGPT |
| Добавить Plan.md паттерн в workflow | Claude |
| Subagents для архитектурного review | Claude |

### Short-term (месяц)

| Действие | Источник рекомендации |
|----------|----------------------|
| Python архитектурный линтер (import-linter) | Все три |
| Pre-commit hooks | Все три |
| Skills для редких случаев | Claude |

### Medium-term (квартал)

| Действие | Источник рекомендации |
|----------|----------------------|
| MCP-сервер архитектуры | Perplexity, ChatGPT |
| CI gate: arch-checker + doc-sync | Все три |
| Метрики деградации | Perplexity |

### Long-term (когда появятся инструменты)

| Действие | Источник рекомендации |
|----------|----------------------|
| Spec-Driven для API | Claude |
| Architect Agent в multi-agent setup | ChatGPT |
| Bidirectional sync (code ↔ spec) | Claude |

---

## 7. Возможные метрики

**Из Perplexity (на основе академических работ):**

| Метрика | Что измеряет |
|---------|--------------|
| Нарушения / 1k строк | Плотность архитектурных проблем |
| % модулей с аномальными зависимостями | Размывание границ |
| Среднее кол-во типов зависимостей на модуль | "Энтропия" структуры |
| ADR compliance rate | % фич, соответствующих ADR |
| Doc freshness | % актуальных документов |

**Практический набор для твоего проекта:**

```markdown
## Arch Health Dashboard

- [ ] ADR violations (arch-checker): 0
- [ ] Doc currency (baseline audit): > 70%
- [ ] Circular dependencies: 0
- [ ] Import rule violations: 0
- [ ] Undocumented modules: < 5%
```

---

## 8. Итоговая оценка

### Твоя система vs Industry

| Критерий | Индустрия (среднее) | Твоя система | Delta |
|----------|---------------------|--------------|-------|
| ADR практика | Редко | 13 ADR | ✅ +++ |
| Архитектурные агенты | Нет | arch-checker, doc-sync | ✅ ++ |
| Architecture summary | Нет | Есть | ✅ + |
| CI интеграция | Линтеры | Нет | ⚠️ Gap |
| MCP-сервер | Emerging | Нет | ⚠️ Gap |
| Метрики | Нет | Нет | ⚠️ Gap |
| Проактивность | Низкая | Средняя | ⚠️ Gap |

### Вердикт

> Система bz2-video-transcriber **опережает 80% практик индустрии** по архитектурному управлению. Основные gaps — CI интеграция и проактивное enforcement — закрываются относительно простыми шагами.

> Главный вывод исследования: **комбинация человеческого архитектурного мышления + AI-инструментов контроля** — единственный работающий подход. Полностью автоматического решения нет и в ближайшее время не появится.

---

## Источники

### Claude
- Cursor Docs, awesome-cursorrules, Anthropic Engineering Blog
- InfoQ: Spec Driven Development
- dependency-cruiser, ACM DIS 2025

### ChatGPT  
- Claude-Flow (ruvnet/github), ArchUnit documentation
- MCP specification, Azure Architecture Center

### Perplexity
- Lambda Curry: Cursor Rules Best Practices
- PMC: Entropy as a Measure of Consistency
- Augment Code: AI Coding Assistants Guide
- HuggingFace: MCP Course

---

*Документ создан: 2026-01-28*
