# Architecture Decision Records

> Архитектурные решения проекта {PROJECT_NAME}

## Что такое ADR

ADR (Architecture Decision Record) — документ, фиксирующий значимое архитектурное решение:
- **Почему** выбран этот подход, а не другой
- **Контекст** — какая проблема решалась
- **Последствия** — плюсы и минусы решения

## Индекс решений

| ADR | Статус | Описание |
|-----|--------|----------|
| [001](001-stage-abstraction.md) | accepted | Stage абстракция |
| [002](002-pipeline-decomposition.md) | accepted | Декомпозиция pipeline |
| [003](003-shared-utils.md) | accepted | Shared utilities |
| [004](004-ai-client-abstraction.md) | accepted | AI client абстракция |
| [005](005-result-caching.md) | accepted | Stage result cache |
| [006](006-cloud-model-integration.md) | accepted | Cloud model integration (Claude) |
| [007](007-remove-fallback-use-claude.md) | accepted | Remove fallback, use Claude |
| [008](008-external-prompts.md) | accepted | External prompts |
| [009](009-extended-metrics.md) | accepted | Extended metrics (v0.42+) |
| [010](010-slides-integration.md) | accepted | Slides integration (v0.51+) |
| [011](011-processing-mode-separation.md) | accepted | Processing mode separation |
| [012](012-statistics-tab.md) | accepted | Statistics tab (v0.58+) |
| [013](013-api-camelcase-serialization.md) | accepted | API camelCase serialization (v0.59+) |

## Статусы

- **Принято** — решение действует
- **Заменено** — заменено другим ADR (указать каким)
- **Отклонено** — рассмотрено, но не принято

## Когда создавать ADR

- Выбор между несколькими архитектурными подходами
- Добавление новой абстракции или паттерна
- Интеграция внешнего сервиса или библиотеки
- Изменение, затрагивающее несколько компонентов
- Решение, которое будет сложно отменить

## Когда НЕ нужен ADR

- Рефакторинг без изменения интерфейсов
- Исправление багов
- Обновление зависимостей (minor/patch)
- Изменения в одном файле

---

## Шаблон ADR

```markdown
# ADR-{NNN}: {Название решения}

**Статус:** Принято | Заменено | Отклонено
**Дата:** {YYYY-MM-DD}

## Контекст

{Какая проблема решается? Какие ограничения существуют?}

## Решение

{Что решили сделать? Краткое описание подхода.}

## Последствия

### Положительные
- {Плюс 1}
- {Плюс 2}

### Отрицательные
- {Минус 1}

## Альтернативы

### 1. {Альтернатива A}
- ✗ {Почему не подошло}
- ✓ {Что было бы хорошо}

### 2. {Альтернатива B}
...

## Связанные документы

- [ARCHITECTURE.md](../ARCHITECTURE.md) — общая архитектура
```

---

_Индекс обновлять при создании нового ADR._
