---
doc_type: reference
status: active
created: 2026-01-24
updated: 2026-01-24
audience: [developer, ai-agent]
tags:
  - architecture
  - reference
---

# Architecture Summary

Компактная карта проекта для быстрой навигации AI-агентов.

## 1. Карта компонентов

### Backend (`backend/app/`)

| Компонент | Путь | Назначение | Зависит от |
|-----------|------|------------|------------|
| **API Routes** | `api/routes.py` | Основные endpoints (inbox, archive, process) | services, models |
| **Step Routes** | `api/step_routes.py` | Пошаговые endpoints (/api/step/*) | services, models |
| **Cache Routes** | `api/cache_routes.py` | Кэш результатов pipeline | pipeline/stage_cache |
| **Models Routes** | `api/models_routes.py` | Список доступных моделей | config/models.yaml |
| **Prompts Routes** | `api/prompts_routes.py` | Варианты промптов | config/prompts/ |
| **Schemas** | `models/schemas.py` | Pydantic модели (CamelCaseModel) | — |
| **Cache Models** | `models/cache.py` | Модели кэширования | schemas |

### Backend Services (`backend/app/services/`)

| Компонент | Путь | Назначение | Зависит от |
|-----------|------|------------|------------|
| **Parser** | `parser.py` | Парсинг имени файла → metadata | config/events.yaml |
| **Transcriber** | `transcriber.py` | Whisper API обёртка | ai_clients/whisper |
| **Cleaner** | `cleaner.py` | Очистка транскрипта | ai_clients, prompts |
| **Slides Extractor** | `slides_extractor.py` | Извлечение текста со слайдов (Vision) | ai_clients/claude |
| **Longread Generator** | `longread_generator.py` | Генерация лонгрида | ai_clients, prompts |
| **Summary Generator** | `summary_generator.py` | Генерация конспекта | ai_clients, prompts |
| **Story Generator** | `story_generator.py` | Генерация истории (8 блоков) | ai_clients, prompts |
| **Saver** | `saver.py` | Сохранение в архив | models/schemas |
| **Summarizer** | `summarizer.py` | Устаревший (см. summary_generator) | — |
| **Audio Extractor** | `audio_extractor.py` | Извлечение аудио из видео | ffmpeg |
| **Outline Extractor** | `outline_extractor.py` | Извлечение структуры документа | ai_clients |
| **Text Splitter** | `text_splitter.py` | Разбиение текста на чанки | — |

### Pipeline Package (`backend/app/services/pipeline/`)

| Компонент | Путь | Назначение | Зависит от |
|-----------|------|------------|------------|
| **Orchestrator** | `orchestrator.py` | Координация этапов pipeline | stages, progress_manager |
| **Progress Manager** | `progress_manager.py` | STAGE_WEIGHTS, расчёт прогресса | — |
| **Config Resolver** | `config_resolver.py` | Override моделей для step-by-step | models.yaml |
| **Stage Cache** | `stage_cache.py` | Версионирование результатов | models/cache |
| **Processing Strategy** | `processing_strategy.py` | Выбор local/cloud провайдера | ai_clients |

### Stage Abstraction (`backend/app/services/stages/`)

| Stage | Файл | Зависит от | Условие выполнения |
|-------|------|------------|-------------------|
| `parse` | `parse_stage.py` | parser | всегда |
| `transcribe` | `transcribe_stage.py` | transcriber | всегда |
| `clean` | `clean_stage.py` | cleaner | всегда |
| `longread` | `longread_stage.py` | longread_generator | content_type = educational |
| `summarize` | `summarize_stage.py` | summary_generator | content_type = educational |
| `story` | `story_stage.py` | story_generator | content_type = leadership |
| `chunk` | `chunk_stage.py` | h2_chunker | всегда |
| `save` | `save_stage.py` | saver | всегда |

> **Note:** `slides` — отдельный API endpoint, не stage.

### AI Clients (`backend/app/services/ai_clients/`)

| Client | Файл | Провайдер | Задачи |
|--------|------|-----------|--------|
| **BaseAIClient** | `base.py` | Protocol | Интерфейс + ChatUsage |
| **OllamaClient** | `ollama_client.py` | Ollama | Локальные LLM |
| **ClaudeClient** | `claude_client.py` | Anthropic | Облачные LLM + Vision |
| **WhisperClient** | `whisper_client.py` | Whisper API | Транскрипция |

### Utils (`backend/app/utils/`)

| Утилита | Файл | Назначение |
|---------|------|------------|
| `extract_json()` | `json_utils.py` | Извлечение JSON из LLM ответа |
| `estimate_tokens()` | `token_utils.py` | Оценка количества токенов |
| `validate_cyrillic_ratio()` | `chunk_utils.py` | Проверка кириллицы в тексте |
| `get_media_duration()` | `media_utils.py` | Длительность медиафайла (ffprobe) |
| `calculate_cost()` | `pricing_utils.py` | Расчёт стоимости по токенам |
| `chunk_by_h2()` | `h2_chunker.py` | Детерминистическое чанкирование |
| `pdf_to_images()` | `pdf_utils.py` | Конвертация PDF в изображения |

### Frontend (`frontend/src/`)

| Область | Путь | Компоненты |
|---------|------|------------|
| **Entry** | `main.tsx`, `App.tsx` | Точка входа, роутинг |
| **API** | `api/` | `client.ts`, `sse.ts`, `types.ts` |
| **Hooks** | `api/hooks/` | useInbox, useArchive, useSteps, useModels, usePrompts |
| **Processing** | `components/processing/` | ProcessingModal, StepByStep, AutoProcessingCompact |
| **Results** | `components/results/` | TranscriptView, LongreadView, SummaryView, StatisticsView |
| **Settings** | `components/settings/` | SettingsModal, ModelSelector, ComponentPromptSelector |
| **Slides** | `components/slides/` | SlidesAttachment, SlidesModal |
| **Utils** | `utils/` | formatUtils, modelUtils, fileUtils |
| **Shared Hook** | `hooks/usePipelineProcessor.ts` | Логика pipeline для обоих режимов |

### Config (`config/`)

| Файл | Назначение | Используется в |
|------|------------|----------------|
| `models.yaml` | Модели, pricing, context profiles | ProcessingStrategy, pricing_utils |
| `events.yaml` | Типы событий (ПШ, Форум) | parser.py |
| `glossary.yaml` | Терминология для коррекции | cleaner.py |
| `prompts/{stage}/` | LLM промпты по этапам | все LLM сервисы |

---

## 2. Сводка ADR

| ADR | Суть решения | Затронутые компоненты |
|-----|--------------|----------------------|
| [001](../decisions/001-stage-abstraction.md) | Stage абстракция с BaseStage, StageContext, StageRegistry | stages/, orchestrator |
| [002](../decisions/002-pipeline-decomposition.md) | Декомпозиция pipeline.py на pipeline/ пакет | pipeline/ |
| [003](../decisions/003-shared-utils.md) | Shared utils для LLM сервисов | utils/ |
| [004](../decisions/004-ai-client-abstraction.md) | AI клиенты с Context Profiles | ai_clients/, models.yaml |
| [005](../decisions/005-result-caching.md) | Версионирование промежуточных результатов | stage_cache, .cache/ |
| [006](../decisions/006-cloud-model-integration.md) | Интеграция Claude API | ClaudeClient, ProcessingStrategy |
| [007](../decisions/007-remove-fallback-use-claude.md) | Удаление fallback, Claude по умолчанию | orchestrator, stages |
| [008](../decisions/008-external-prompts.md) | Внешние промпты с приоритетом загрузки | config/prompts/, PROMPTS_DIR |
| [009](../decisions/009-extended-metrics.md) | Расширенные метрики (tokens, cost, time) | schemas, ai_clients |
| [010](../decisions/010-slides-integration.md) | Интеграция слайдов презентаций | slides_extractor, SlidesAttachment |
| [011](../decisions/011-processing-mode-separation.md) | Разделение auto/step-by-step режимов | AutoProcessingCompact, StepByStep |
| [012](../decisions/012-statistics-tab.md) | Вкладка "Статистика" для метрик | StatisticsView |
| [013](../decisions/013-api-camelcase-serialization.md) | CamelCase сериализация в API | CamelCaseModel, все endpoints |

---

## 3. Pipeline

### Граф обработки

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PIPELINE FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   INPUT                                                                      │
│     │                                                                        │
│     ▼                                                                        │
│   [Parse] ─────────────────────────────────────────────────────────────┐     │
│     │                                                                  │     │
│     ▼                                                                  │     │
│   [Transcribe] ──► Whisper API ──► RawTranscript                      │     │
│     │                                                                  │     │
│     ▼                                                                  │     │
│   [Clean] ──► Claude/Ollama ──► CleanedTranscript                     │     │
│     │                                                                  │     │
│     ├──────────────────── (if slides attached) ────────────────────┐  │     │
│     │                                                              │  │     │
│     │                    [Slides] ──► Claude Vision                │  │     │
│     │                        │                                     │  │     │
│     │                        ▼                                     │  │     │
│     │                  SlidesExtractionResult                      │  │     │
│     │                        │                                     │  │     │
│     └────────────────────────┼─────────────────────────────────────┘  │     │
│                              │                                        │     │
│     ┌────────────────────────┴────────────────────────────┐           │     │
│     │                                                     │           │     │
│     ▼                                                     ▼           │     │
│   content_type = EDUCATIONAL                   content_type = LEADERSHIP    │
│     │                                                     │                 │
│     ▼                                                     ▼                 │
│   [Longread] ──► Claude                        [Story] ──► Claude           │
│     │                                                     │                 │
│     ▼                                                     │                 │
│   [Summary] ──► Claude                                    │                 │
│     │                                                     │                 │
│     └─────────────────────────────────────────────────────┘                 │
│                              │                                              │
│                              ▼                                              │
│                           [Chunk] ──► H2 parsing (детерминистический)       │
│                              │                                              │
│                              ▼                                              │
│                           [Save] ──► Archive                                │
│                              │                                              │
│                              ▼                                              │
│                           OUTPUT                                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Выходные файлы

| ContentType | Файлы в архиве |
|-------------|----------------|
| `educational` | `longread.md`, `summary.md`, `transcript_*.txt`, `pipeline_results.json` |
| `leadership` | `story.md`, `transcript_*.txt`, `pipeline_results.json` |

### Структура архива

```
archive/{year}/
├── {event_type}/{MM.DD}/{Title}/     # regular events (ПШ)
└── Выездные/{event_name}/{Title}/    # offsite events (Форум)
```

---

## 4. Точки расширения

### Новый этап pipeline

1. Создать `backend/app/services/stages/{name}_stage.py`:
   ```python
   class NewStage(BaseStage):
       name = "new_stage"
       depends_on = ["clean"]  # зависимости
       optional = True

       def should_skip(self, context: StageContext) -> bool:
           # условие пропуска

       async def execute(self, context: StageContext) -> NewResult:
           # логика
   ```
2. Добавить в `stages/__init__.py`
3. Добавить weight в `pipeline/progress_manager.py`
4. Создать промпты в `config/prompts/{stage}/`

### Новый AI провайдер

1. Создать `backend/app/services/ai_clients/{provider}_client.py`:
   ```python
   class ProviderClient(BaseAIClientImpl):
       async def generate(...) -> tuple[str, ChatUsage]:
           # реализация
   ```
2. Добавить в `ai_clients/__init__.py`
3. Обновить `ProcessingStrategy.create_client()`
4. Добавить модели в `config/models.yaml`

### Новый формат вывода

1. Добавить Pydantic модель в `models/schemas.py`:
   ```python
   class NewFormat(CamelCaseModel):
       content: str
       # поля
   ```
2. Создать генератор в `services/{format}_generator.py`
3. Добавить stage (см. выше) или endpoint в `api/step_routes.py`
4. Добавить TypeScript типы в `frontend/src/api/types.ts`
5. Создать view компонент в `frontend/src/components/results/`

### Новый тип контента

1. Добавить в `ContentType` enum (`models/schemas.py`)
2. Обновить `parser.py` — логика определения типа
3. Создать stages с `should_skip()` по типу
4. Обновить Saver для новых выходных файлов

### Новый вариант промпта

1. Добавить файл в `config/prompts/{stage}/{variant}.md`
2. API `/api/prompts/{stage}` автоматически найдёт вариант
3. Передать в запросе `prompt_overrides: {"system": "variant"}`

---

## 5. Навигация

| Что искать | Где смотреть |
|------------|--------------|
| Схемы данных API | `backend/app/models/schemas.py` |
| Типы TypeScript | `frontend/src/api/types.ts` |
| Параметры моделей | `config/models.yaml` |
| Промпты LLM | `config/prompts/{stage}/` |
| Логика парсинга имён | `backend/app/services/parser.py` |
| Pipeline этапы | `backend/app/services/stages/` |
| Координация pipeline | `backend/app/services/pipeline/orchestrator.py` |
| AI клиенты | `backend/app/services/ai_clients/` |
| Кэширование | `backend/app/services/pipeline/stage_cache.py` |
| Утилиты форматирования | `frontend/src/utils/formatUtils.ts` |
| Логика обработки UI | `frontend/src/hooks/usePipelineProcessor.ts` |
| Настройки деплоя | `docker-compose.yml`, `scripts/deploy.sh` |
| Архитектурные решения | `docs/decisions/` |
| Документация pipeline | `docs/pipeline/` |
| API reference | `docs/api-reference.md` |

### Быстрые команды

```bash
# Проверить AI сервисы
curl http://100.64.0.1:11434/api/version  # Ollama
curl http://100.64.0.1:9000/health        # Whisper

# Web UI
http://100.64.0.1:8802  # Frontend
http://100.64.0.1:8801  # Backend API

# Деплой
./scripts/deploy.sh
```

---

## 6. Ключевые концепции

### Content Types

| Тип | Определение | Pipeline |
|-----|-------------|----------|
| `educational` | Обучающие темы | longread → summary → chunk |
| `leadership` | Лидерские истории | story → chunk |

### Event Categories

| Категория | Структура архива | Примеры |
|-----------|------------------|---------|
| `regular` | `{year}/{event_type}/{MM.DD}/` | ПШ (еженедельные) |
| `offsite` | `{year}/Выездные/{event_name}/` | Форумы, выездные |

### Processing Modes

| Режим | Компонент | Описание |
|-------|-----------|----------|
| `auto` | AutoProcessingCompact | Минимальный UI, только прогресс |
| `step` | StepByStep | Split view, настройки моделей/промптов |

### API Serialization

| Слой | Формат |
|------|--------|
| Python | snake_case |
| JSON API | camelCase |
| TypeScript | camelCase |

---

*Документ обновлён: 2026-01-24*
