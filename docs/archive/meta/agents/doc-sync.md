---
doc_type: reference
ai_scope: none
status: active
created: 2026-01-24
updated: 2026-01-24
tags:
  - documentation
  - meta
  - agent
---

# Agent: doc-sync

> Определяет документы, требующие обновления после изменений в коде.

---

## Назначение

**doc-sync** анализирует изменения в коде и определяет какие документы нужно обновить. Запускается после PR или при подозрении на рассинхронизацию.

**Когда использовать:**
- После merge PR с изменениями в backend/frontend
- После рефакторинга модулей
- Перед релизом — проверка актуальности документации
- При добавлении новых endpoints, моделей, этапов pipeline

---

## Маппинг: Код → Документация

### Backend API

| Изменённый файл | Документы для обновления |
|-----------------|--------------------------|
| `backend/app/api/routes.py` | [api-reference.md](../../api-reference.md), [pipeline/09-api.md](../../pipeline/09-api.md) |
| `backend/app/api/step_routes.py` | [api-reference.md](../../api-reference.md), [pipeline/09-api.md](../../pipeline/09-api.md) |
| `backend/app/api/cache_routes.py` | [api-reference.md](../../api-reference.md) |
| `backend/app/api/models_routes.py` | [api-reference.md](../../api-reference.md), [configuration.md](../../configuration.md) |
| `backend/app/api/prompts_routes.py` | [api-reference.md](../../api-reference.md) |

### Backend Models & Schemas

| Изменённый файл | Документы для обновления |
|-----------------|--------------------------|
| `backend/app/models/schemas.py` | [data-formats.md](../../data-formats.md), [api-reference.md](../../api-reference.md) |
| `backend/app/models/cache.py` | [pipeline/08-orchestrator.md](../../pipeline/08-orchestrator.md) |
| `backend/app/config.py` | [configuration.md](../../configuration.md), [deployment.md](../../deployment.md) |

### Pipeline Stages

| Изменённый файл | Документы для обновления |
|-----------------|--------------------------|
| `backend/app/services/stages/parse_stage.py` | [pipeline/01-parse.md](../../pipeline/01-parse.md), [pipeline/stages.md](../../pipeline/stages.md) |
| `backend/app/services/stages/transcribe_stage.py` | [pipeline/02-transcribe.md](../../pipeline/02-transcribe.md), [pipeline/stages.md](../../pipeline/stages.md) |
| `backend/app/services/stages/clean_stage.py` | [pipeline/03-clean.md](../../pipeline/03-clean.md), [pipeline/stages.md](../../pipeline/stages.md) |
| `backend/app/services/stages/slides_stage.py` | [pipeline/03a-slides.md](../../pipeline/03a-slides.md), [pipeline/stages.md](../../pipeline/stages.md) |
| `backend/app/services/stages/chunk_stage.py` | [pipeline/04-chunk.md](../../pipeline/04-chunk.md), [pipeline/stages.md](../../pipeline/stages.md) |
| `backend/app/services/stages/longread_stage.py` | [pipeline/05-longread.md](../../pipeline/05-longread.md), [pipeline/stages.md](../../pipeline/stages.md) |
| `backend/app/services/stages/story_stage.py` | [pipeline/05b-story.md](../../pipeline/05b-story.md), [pipeline/stages.md](../../pipeline/stages.md) |
| `backend/app/services/stages/summarize_stage.py` | [pipeline/06-summarize.md](../../pipeline/06-summarize.md), [pipeline/stages.md](../../pipeline/stages.md) |
| `backend/app/services/stages/save_stage.py` | [pipeline/07-save.md](../../pipeline/07-save.md), [pipeline/stages.md](../../pipeline/stages.md) |

### Pipeline Infrastructure

| Изменённый файл | Документы для обновления |
|-----------------|--------------------------|
| `backend/app/services/pipeline/orchestrator.py` | [pipeline/08-orchestrator.md](../../pipeline/08-orchestrator.md), [architecture.md](../../architecture.md) |
| `backend/app/services/pipeline/progress_manager.py` | [pipeline/08-orchestrator.md](../../pipeline/08-orchestrator.md) |
| `backend/app/services/pipeline/stage_cache.py` | [pipeline/08-orchestrator.md](../../pipeline/08-orchestrator.md) |
| `backend/app/services/pipeline/processing_strategy.py` | [architecture.md](../../architecture.md) |

### AI Clients

| Изменённый файл | Документы для обновления |
|-----------------|--------------------------|
| `backend/app/services/ai_clients/base.py` | [architecture.md](../../architecture.md) |
| `backend/app/services/ai_clients/claude_client.py` | [architecture.md](../../architecture.md), [configuration.md](../../configuration.md) |
| `backend/app/services/ai_clients/ollama_client.py` | [architecture.md](../../architecture.md), [configuration.md](../../configuration.md) |
| `backend/app/services/ai_clients/whisper_client.py` | [pipeline/02-transcribe.md](../../pipeline/02-transcribe.md), [configuration.md](../../configuration.md) |

### Services

| Изменённый файл | Документы для обновления |
|-----------------|--------------------------|
| `backend/app/services/parser.py` | [pipeline/01-parse.md](../../pipeline/01-parse.md) |
| `backend/app/services/transcriber.py` | [pipeline/02-transcribe.md](../../pipeline/02-transcribe.md) |
| `backend/app/services/cleaner.py` | [pipeline/03-clean.md](../../pipeline/03-clean.md) |
| `backend/app/services/slides_extractor.py` | [pipeline/03a-slides.md](../../pipeline/03a-slides.md) |
| `backend/app/services/longread_generator.py` | [pipeline/05-longread.md](../../pipeline/05-longread.md) |
| `backend/app/services/summary_generator.py` | [pipeline/06-summarize.md](../../pipeline/06-summarize.md) |
| `backend/app/services/story_generator.py` | [pipeline/05b-story.md](../../pipeline/05b-story.md) |
| `backend/app/services/saver.py` | [pipeline/07-save.md](../../pipeline/07-save.md) |

### Configuration Files

| Изменённый файл | Документы для обновления |
|-----------------|--------------------------|
| `config/models.yaml` | [configuration.md](../../configuration.md), [architecture.md](../../architecture.md) |
| `config/events.yaml` | [pipeline/01-parse.md](../../pipeline/01-parse.md), [configuration.md](../../configuration.md) |
| `config/glossary.yaml` | [pipeline/03-clean.md](../../pipeline/03-clean.md), [configuration.md](../../configuration.md) |
| `config/prompts/**` | Соответствующий pipeline/*.md |
| `docker-compose.yml` | [deployment.md](../../deployment.md), [configuration.md](../../configuration.md) |

### Frontend

| Изменённый файл | Документы для обновления |
|-----------------|--------------------------|
| `frontend/src/api/types.ts` | [data-formats.md](../../data-formats.md) |
| `frontend/src/api/client.ts` | [api-reference.md](../../api-reference.md) |
| `frontend/src/components/**` | [web-ui.md](../../web-ui.md) |

---

## Использование

### Вариант 1: После PR (автоматический)

```
Проанализируй изменения в PR и определи документы для обновления.

## Контекст
PR #XXX: {краткое описание}

## Изменённые файлы
{список файлов из git diff --name-only}

## Задача
1. Используй маппинг из docs/meta/agents/doc-sync.md
2. Для каждого изменённого файла найди связанные документы
3. Сгруппируй по приоритету (API/config → high, pipeline → medium, остальное → low)
4. Выведи список документов для обновления с кратким описанием что проверить
```

### Вариант 2: Полный аудит (ручной)

```
Проведи аудит синхронизации кода и документации.

## Задача
1. Прочитай docs/meta/agents/doc-sync.md
2. Для каждой категории в маппинге:
   - Проверь существование файлов кода
   - Сравни с содержимым документов
   - Найди расхождения
3. Создай отчёт с приоритизированным списком обновлений
```

### Вариант 3: Точечная проверка

```
Проверь синхронизацию документации для {модуль/область}.

Например: "Проверь синхронизацию для pipeline stages"

## Задача
1. Найди все файлы в backend/app/services/stages/
2. Найди соответствующие документы в docs/pipeline/
3. Сравни Input/Output, методы, зависимости
4. Выведи расхождения
```

---

## Алгоритм работы

```
┌─────────────────────────────────────────────────────┐
│                    doc-sync                          │
├─────────────────────────────────────────────────────┤
│                                                      │
│  INPUT: Список изменённых файлов                    │
│     │                                                │
│     ▼                                                │
│  ┌─────────────────────────────────────────────┐    │
│  │ 1. Категоризация файлов                     │    │
│  │    - API routes → api-reference.md          │    │
│  │    - Schemas → data-formats.md              │    │
│  │    - Stages → pipeline/*.md                 │    │
│  │    - Config → configuration.md              │    │
│  └─────────────────────────────────────────────┘    │
│     │                                                │
│     ▼                                                │
│  ┌─────────────────────────────────────────────┐    │
│  │ 2. Маппинг к документам                     │    │
│  │    Используем таблицы выше                  │    │
│  └─────────────────────────────────────────────┘    │
│     │                                                │
│     ▼                                                │
│  ┌─────────────────────────────────────────────┐    │
│  │ 3. Приоритизация                            │    │
│  │    HIGH: API, config, schemas               │    │
│  │    MEDIUM: pipeline stages                  │    │
│  │    LOW: frontend, utils                     │    │
│  └─────────────────────────────────────────────┘    │
│     │                                                │
│     ▼                                                │
│  OUTPUT: Приоритизированный список документов       │
│          + что именно проверить                     │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## Приоритеты обновления

| Приоритет | Категория | Почему |
|-----------|-----------|--------|
| 🔴 HIGH | API endpoints, Response schemas | Внешний контракт, breaking changes |
| 🔴 HIGH | Configuration (ENV, Settings) | Влияет на деплой |
| 🟡 MEDIUM | Pipeline stages | Внутренняя логика, но важна для понимания |
| 🟡 MEDIUM | AI clients | Влияет на качество результатов |
| 🟢 LOW | Frontend components | UI, не влияет на API |
| 🟢 LOW | Utils, helpers | Внутренняя реализация |

---

## Примеры результатов

### Пример 1: Изменение в step_routes.py

**Input:**
```
backend/app/api/step_routes.py
```

**Output:**
```
## Документы для обновления

### 🔴 HIGH
- **docs/api-reference.md**
  - Проверить: endpoints в разделе Step-by-Step API
  - Что искать: новые/изменённые параметры, response schema

- **docs/pipeline/09-api.md**
  - Проверить: раздел Step Routes
  - Что искать: соответствие примеров запросов
```

### Пример 2: Новый stage

**Input:**
```
backend/app/services/stages/new_stage.py
backend/app/services/new_generator.py
```

**Output:**
```
## Документы для обновления

### 🔴 HIGH
- **docs/pipeline/stages.md**
  - Добавить: новый этап в таблицу stages
  - Обновить: граф зависимостей

### 🟡 MEDIUM
- **Создать: docs/pipeline/XX-new.md**
  - Использовать шаблон существующих stage документов
  - Включить: Input/Output, зависимости, промпты

### 🟢 LOW
- **docs/architecture.md**
  - Добавить: новый сервис в карту компонентов
```

---

## Интеграция

### В CLAUDE.md

```markdown
## При изменениях кода

После внесения изменений в код запусти doc-sync:

\`\`\`
Используй docs/meta/agents/doc-sync.md для определения 
документов, требующих обновления после изменений в:
{список файлов}
\`\`\`
```

### В CI/CD (будущее)

```yaml
# .github/workflows/docs-check.yml
- name: Check docs sync
  run: |
    # Получить изменённые файлы
    # Вызвать Claude API с промптом doc-sync
    # Создать issue если есть расхождения
```

---

## Связанные документы

- [Update Workflow](../workflows/update.md) — как обновлять документы
- [Audit Process](../workflows/audit.md) — полный аудит документации
- [Architecture Summary](../../audit/architecture-summary.md) — карта компонентов

---

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-01-24 | Создан документ |
