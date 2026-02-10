---
doc_type: audit
status: active
created: 2026-01-24
updated: 2026-01-24
last_analyzed: docs/adr/
tags: [documentation, analysis, diataxis]
---

# Анализ документации проекта

> Классификация документов по Diátaxis+ Framework

## docs/ (корневые файлы)

| Документ                                                                     | Тип         | Аудитория                | Frontmatter | Проблемы             | Рекомендация      |
| ---------------------------------------------------------------------------- | ----------- | ------------------------ | ----------- | -------------------- | ----------------- |
| [README.md](../../README.md)                                                 | reference   | developer, ai-agent      | Нет         | Навигационный хаб    | ✅ Add frontmatter |
| [overview.md](../../overview.md)                                             | explanation | developer, ai-agent      | Нет         | —                    | ✅ Add frontmatter |
| [architecture.md](../../architecture.md)                                     | explanation | developer, ai-agent      | Да          | Obsidian-style links | ⏳ Leave as-is     |
| [configuration.md](../../configuration.md)                                   | reference   | developer, ai-agent, ops | Нет         | —                    | ✅ Add frontmatter |
| [deployment.md](../../deployment.md)                                         | how-to      | ops, developer           | Нет         | —                    | ✅ Add frontmatter |
| [api-reference.md](../../api-reference.md)                                   | reference   | developer, ai-agent      | Нет         | —                    | ✅ Add frontmatter |
| [data-formats.md](../../data-formats.md)                                     | reference   | developer, ai-agent      | Нет         | —                    | ✅ Add frontmatter |
| [logging.md](../../logging.md)                                               | reference   | developer, ops           | Нет         | —                    | ✅ Add frontmatter |
| [testing.md](../../testing.md)                                               | how-to      | developer, ai-agent      | Нет         | —                    | ✅ Add frontmatter |
| [model-testing.md](../../model-testing.md)                                   | how-to      | developer                | Нет         | —                    | ✅ Add frontmatter |
| [web-ui.md](../../web-ui.md)                                                 | reference   | developer                | Нет         | —                    | ✅ Add frontmatter |
| [CONTRIBUTING.md](../../CONTRIBUTING.md)                                     | how-to      | developer                | Нет         | —                    | ✅ Add frontmatter |
| [DOCUMENTATION_GUIDELINES.md](../../DOCUMENTATION_GUIDELINES.md)             | how-to      | developer, ai-agent      | Нет         | —                    | ✅ Add frontmatter |
| [Прокси для Docker-приложений.md](../../Прокси%20для%20Docker-приложений.md) | how-to      | ops                      | Нет         | Инфра-специфичный    | ✅ Add frontmatter |

### Наблюдения по docs/ (корень)

**Сильные стороны:**
- Полное покрытие ключевых тем (архитектура, API, деплой, конфигурация)
- DOCUMENTATION_GUIDELINES — чёткие правила для AI и разработчиков
- Хорошие таблицы для быстрого поиска

**Области улучшения:**
- 13 из 14 документов без frontmatter
- architecture.md использует Obsidian [[wikilinks]] — могут не работать в GitHub

---

## docs/pipeline/

| Документ | Тип | Аудитория | Frontmatter | Проблемы | Рекомендация |
|----------|-----|-----------|-------------|----------|--------------|
| [README.md](../../pipeline/README.md) | reference | developer, ai-agent | Нет | — | ✅ Add frontmatter |
| [stages.md](../../pipeline/stages.md) | reference | developer, ai-agent | Нет | Большой объём, много примеров кода | ✅ Add frontmatter |
| [01-parse.md](../../pipeline/01-parse.md) | reference | developer, ai-agent | Нет | — | ✅ Add frontmatter |
| [02-transcribe.md](../../pipeline/02-transcribe.md) | reference | developer, ai-agent | Нет | — | ✅ Add frontmatter |
| [03-clean.md](../../pipeline/03-clean.md) | reference + explanation | developer, ai-agent | Нет | Содержит explanation (почему LLM вместо Regex) | ✅ Add frontmatter |
| [03a-slides.md](../../pipeline/03a-slides.md) | reference | developer, ai-agent | Нет | — | ✅ Add frontmatter |
| [04-chunk.md](../../pipeline/04-chunk.md) | reference | developer, ai-agent | Нет | — | ✅ Add frontmatter |
| [05-longread.md](../../pipeline/05-longread.md) | reference | developer, ai-agent | Нет | — | ✅ Add frontmatter |
| [05b-story.md](../../pipeline/05b-story.md) | reference | developer, ai-agent | Нет | — | ✅ Add frontmatter |
| [06-summarize.md](../../pipeline/06-summarize.md) | reference | developer, ai-agent | Нет | Содержит историю изменений | ✅ Add frontmatter |
| [07-save.md](../../pipeline/07-save.md) | reference | developer, ai-agent | Нет | Содержит историю изменений | ✅ Add frontmatter |
| [08-orchestrator.md](../../pipeline/08-orchestrator.md) | reference | developer, ai-agent | Нет | Содержит историю изменений | ✅ Add frontmatter |
| [09-api.md](../../pipeline/09-api.md) | reference | developer | Нет | Длинный, много примеров API | ✅ Add frontmatter |
| [error-handling.md](../../pipeline/error-handling.md) | reference | developer | Нет | — | ✅ Add frontmatter |

### Наблюдения по docs/pipeline/

**Сильные стороны:**
- Единая структура: Input/Output таблицы, связанные файлы
- Хорошая навигация: ссылки "Назад / Обзор / Далее"
- Актуальная информация с версионированием (v0.XX+)
- Примеры кода для интеграции

**Области улучшения:**
- Ни один документ не имеет frontmatter
- Некоторые документы содержат explanation контент внутри reference (03-clean.md)
- История изменений в конце документов (06, 07, 08) — можно вынести в CHANGELOG или ADR

---

## docs/adr/

| Документ | Тип | Аудитория | Frontmatter | Проблемы | Рекомендация |
|----------|-----|-----------|-------------|----------|--------------|
| [001-stage-abstraction.md](../../adr/001-stage-abstraction.md) | adr | developer | Нет | Метаданные как bold text | ✅ Add frontmatter |
| [002-pipeline-decomposition.md](../../adr/002-pipeline-decomposition.md) | adr | developer | Нет | Метаданные как H2 + text | ✅ Add frontmatter |
| [003-shared-utils.md](../../adr/003-shared-utils.md) | adr | developer | Нет | Метаданные как H2 + text | ✅ Add frontmatter |
| [004-ai-client-abstraction.md](../../adr/004-ai-client-abstraction.md) | adr | developer | Нет | Метаданные как H2 + text | ✅ Add frontmatter |
| [005-result-caching.md](../../adr/005-result-caching.md) | adr | developer | Нет | Метаданные как H2 + text | ✅ Add frontmatter |
| [006-cloud-model-integration.md](../../adr/006-cloud-model-integration.md) | adr | developer | Нет | Метаданные как H2 + text | ✅ Add frontmatter |
| [007-remove-fallback-use-claude.md](../../adr/007-remove-fallback-use-claude.md) | adr | developer | Нет | Метаданные как bold text + версия | ✅ Add frontmatter |
| [008-external-prompts.md](../../adr/008-external-prompts.md) | adr | developer | Нет | Метаданные как H2 + text | ✅ Add frontmatter |
| [009-extended-metrics.md](../../adr/009-extended-metrics.md) | adr | developer | Нет | Метаданные как H2 + text | ✅ Add frontmatter |
| [010-slides-integration.md](../../adr/010-slides-integration.md) | adr | developer | Нет | Метаданные как H2 + text | ✅ Add frontmatter |
| [011-processing-mode-separation.md](../../adr/011-processing-mode-separation.md) | adr | developer | Нет | Метаданные как markdown list | ✅ Add frontmatter |
| [012-statistics-tab.md](../../adr/012-statistics-tab.md) | adr | developer | Нет | Метаданные как H2 + version | ✅ Add frontmatter |
| [013-api-camelcase-serialization.md](../../adr/013-api-camelcase-serialization.md) | adr | developer | Нет | Метаданные как H2 + version | ✅ Add frontmatter |

### Наблюдения по docs/adr/

**Сильные стороны:**
- Чёткая нумерация и именование (001–013)
- Единая структура контента: Контекст → Решение → Последствия → Связанные документы
- Хорошие ссылки между ADR (граф зависимостей)
- Примеры кода с объяснениями
- Альтернативы с обоснованием отклонения

**Области улучшения:**
- **Ни один ADR не имеет YAML frontmatter**
- **3+ форматов метаданных:**
  - Bold text: `**Статус:** Принято` (001, 007)
  - H2 + text: `## Статус\n\nПринято (2025-01-20)` (002–006, 008–010)
  - Markdown list: `- **Статус:** Принято` (011)
  - H2 + version: `## Статус\n\nПринято (v0.XX)` (012, 013)
- Нет поля `deciders` (кто принял решение)
- Нет поля `supersedes` / `superseded_by` для эволюции решений

**Рекомендуемый шаблон frontmatter:**
```yaml
---
doc_type: adr
status: accepted | proposed | deprecated | superseded
created: YYYY-MM-DD
updated: YYYY-MM-DD
version: vX.XX  # optional, version of implementation
deciders: [Claude Opus 4.5]
supersedes: adr-00X  # optional
tags: [pipeline, architecture, ...]
---
```

---

## docs/template prompts/

| Документ | Тип | Аудитория | Frontmatter | Проблемы | Рекомендация |
|----------|-----|-----------|-------------|----------|--------------|
| Educational_Longread_Instructions.md | reference | ai-agent | Нет | Шаблон промпта | ✅ Add frontmatter |
| Educational_Longread_Template.md | reference | ai-agent | Нет | Шаблон промпта | ✅ Add frontmatter |
| Educational_Summary_Instructions.md | reference | ai-agent | Нет | Шаблон промпта | ✅ Add frontmatter |
| Educational_Summary_Template.md | reference | ai-agent | Нет | Шаблон промпта | ✅ Add frontmatter |
| Slides_Extraction_Instructions.md | reference | ai-agent | Нет | Шаблон промпта | ✅ Add frontmatter |
| Leadership_Story_Instructions.md | reference | ai-agent | Нет | Шаблон промпта | ✅ Add frontmatter |
| Leadership_Story_Template.md | reference | ai-agent | Нет | Шаблон промпта | ✅ Add frontmatter |
| System_Prompts_Examples.md | reference | ai-agent | Нет | Шаблон промпта | ✅ Add frontmatter |

### Наблюдения по docs/template prompts/

**Назначение:** Эталонные версии промптов для документации (config/prompts/ — рабочие версии)

**Области улучшения:**
- Нет frontmatter
- Возможно дублирование с config/prompts/ — проверить синхронизацию

---

## Сводка

| Папка | Всего | С frontmatter | Без frontmatter |
|-------|-------|---------------|-----------------|
| docs/ (корень) | 14 | 1 | 13 |
| docs/pipeline/ | 14 | 0 | 14 |
| docs/adr/ | 13 | 0 | 13 |
| docs/template prompts/ | 8 | 0 | 8 |
| **Итого** | **49** | **1** | **48** |

### Распределение по типам

| Тип | Количество |
|-----|------------|
| reference | 31 |
| adr | 13 |
| how-to | 7 |
| explanation | 3 |

### Распределение по аудитории

| Аудитория | Документов |
|-----------|------------|
| developer | 49 |
| ai-agent | 40 |
| ops | 4 |

### Приоритетные действия

1. **Добавить frontmatter** — 48 документов без метаданных
2. **architecture.md** — единственный с frontmatter, использовать как образец
3. **ADR шаблон** — стандартизировать с полями status, date, deciders
4. **template prompts** — проверить синхронизацию с config/prompts/
