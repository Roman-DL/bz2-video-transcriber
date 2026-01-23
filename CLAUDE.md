# bz2-video-transcriber

Система автоматической транскрипции и саммаризации видеозаписей для БЗ 2.0.

## Инструкции для Claude

- **Язык общения:** Русский
- **Язык кода:** Английский (имена переменных, функций, комментарии в коде)
- **Язык документации:** Русский
- **Версионирование:** После коммита новых фич — ОБЯЗАТЕЛЬНО предложи обновить версию в `frontend/package.json`

## Документирование кода

При реализации функций следуй [гайдлайнам по документированию](docs/DOCUMENTATION_GUIDELINES.md):
- **Docstrings в коде** — обязательны для публичных методов (Google-style)
- **Внешняя документация** — только архитектура, интеграция, решения
- **Не дублируй код в docs** — ИИ читает код напрямую

## Quick Start

```bash
# Проверить AI сервисы
curl http://100.64.0.1:11434/api/version  # Ollama
curl http://100.64.0.1:9000/health        # Whisper

# Деплой на сервер (локальный docker-compose не работает!)
./scripts/deploy.sh

# Web UI
http://100.64.0.1:8802      # Frontend
http://100.64.0.1:8801      # Backend API
```

## Архитектура

```
Video + [Slides] → Parse → Whisper → Clean ─┬─→ [Slides] → Longread → Summary → Chunk (H2) → Save (educational)
                                            └─→ [Slides] → Story → Chunk (H2) → Save (leadership)
```

> **v0.25+:** Chunk теперь детерминированный (парсинг H2 заголовков), выполняется ПОСЛЕ longread/story.
> **v0.51+:** Опциональный шаг Slides появляется перед Longread/Story если пользователь прикрепил слайды.

## Документация

| Тема | Документ |
|------|----------|
| Обзор системы | [docs/overview.md](docs/overview.md) |
| Архитектура | [docs/architecture.md](docs/architecture.md) |
| **Конфигурация** | [docs/configuration.md](docs/configuration.md) |
| Pipeline (этапы) | [docs/pipeline/](docs/pipeline/) |
| **Stage абстракция** | [docs/pipeline/stages.md](docs/pipeline/stages.md) |
| Форматы данных | [docs/data-formats.md](docs/data-formats.md) |
| API сервисов | [docs/api-reference.md](docs/api-reference.md) |
| Развёртывание | [docs/deployment.md](docs/deployment.md) |
| Логирование | [docs/logging.md](docs/logging.md) |
| Тестирование | [docs/testing.md](docs/testing.md) |
| Тестирование моделей | [docs/model-testing.md](docs/model-testing.md) |
| **Прокси для Claude** | [docs/Прокси для Docker-приложений.md](docs/Прокси%20для%20Docker-приложений.md) |
| ADR (решения) | [docs/adr/](docs/adr/) |

## Структура проекта

```
backend/app/services/             # Сервисы pipeline
backend/app/services/ai_clients/  # AI клиенты (v0.17+)
backend/app/services/pipeline/    # Pipeline package (v0.15+)
backend/app/services/stages/      # Stage абстракция (v0.14+)
backend/app/utils/                # Shared utilities (v0.16+)
backend/app/models/               # Pydantic models (schemas.py, cache.py)
backend/app/api/                  # FastAPI endpoints
frontend/src/                     # React + Vite + Tailwind
frontend/src/utils/               # Shared utilities (modelUtils.ts, v0.35+)
config/prompts/                   # LLM промпты
config/glossary.yaml              # Терминология
docs/adr/                         # Architecture Decision Records
```

## Pipeline Package (v0.15+, updated v0.29)

Декомпозированный pipeline с чёткими обязанностями:

```
backend/app/services/pipeline/
├── __init__.py              # Экспорт PipelineOrchestrator
├── orchestrator.py          # Координация этапов
├── progress_manager.py      # STAGE_WEIGHTS, расчёт прогресса
├── config_resolver.py       # Override моделей для step-by-step
├── stage_cache.py           # Версионирование результатов (v0.18+)
└── processing_strategy.py   # Выбор local/cloud провайдера (v0.19+)
```

> **v0.29+:** Fallback механизмы удалены. При ошибках LLM выбрасывается `PipelineError`.

Подробнее: [docs/adr/002-pipeline-decomposition.md](docs/adr/002-pipeline-decomposition.md)

## Stage Result Cache (v0.18+)

Версионированное кэширование промежуточных результатов pipeline:

```
backend/app/models/cache.py           # CacheManifest, CacheEntry, API models
backend/app/services/pipeline/stage_cache.py  # StageResultCache
backend/app/api/cache_routes.py       # Cache API endpoints
```

**Структура кэша:**
```
archive/2025/ПШ/01.09/Video Title/
├── pipeline_results.json    # Текущие результаты
└── .cache/
    ├── manifest.json        # Версии и метаданные
    ├── cleaning/v1.json     # Версия 1
    ├── cleaning/v2.json     # Re-run с другой моделью
    └── ...
```

**Использование:**
```python
from app.services.pipeline import StageResultCache
from app.models.cache import CacheStageName

cache = StageResultCache(settings)

# Сохранить результат
entry = await cache.save(
    archive_path=Path("/data/archive/2025/..."),
    stage=CacheStageName.CLEANING,
    result=cleaned_transcript,
    model_name="gemma2:9b",
)

# Загрузить текущую версию
result = await cache.load(archive_path, CacheStageName.CLEANING)

# Загрузить конкретную версию
result = await cache.load(archive_path, CacheStageName.CLEANING, version=1)
```

**API endpoints:**
- `GET /api/cache/{video_id}` — информация о кэше
- `POST /api/cache/rerun` — перезапуск этапа
- `POST /api/cache/version` — установка текущей версии

Подробнее: [docs/adr/005-result-caching.md](docs/adr/005-result-caching.md)

## Prompts API (v0.31+)

API для получения доступных вариантов промптов и их использования при обработке.

**Endpoints:**
- `GET /api/prompts/{stage}` — список вариантов промптов для этапа

**Step API с prompt_overrides (v0.32+):**
```python
# POST /api/step/clean, /api/step/longread, /api/step/summarize, /api/step/story
{
    "raw_transcript": {...},
    "metadata": {...},
    "model": "claude-sonnet-4-5",       # опционально
    "prompt_overrides": {                # опционально
        "system": "system_v2",           # использовать system_v2.md
        "user": "user"                   # default
    }
}
```

**UI (v0.33+):** В пошаговом режиме (step-by-step) показываются селекторы промптов, если для компонента есть несколько вариантов.

Подробнее: [docs/api-reference.md](docs/api-reference.md)

## Slides Extraction (v0.51+)

Опциональный шаг для извлечения текста со слайдов презентаций с использованием Claude Vision API.

**Pipeline со слайдами:**
```
Video + Slides → Parse → Transcribe → Clean → [SLIDES] → Longread/Story → Summary → Chunk → Save
```

Шаг `slides` появляется условно между `clean` и `longread/story` если пользователь прикрепил слайды.

**Модели данных:**
```python
from app.models.schemas import SlideInput, SlidesExtractionResult

# SlideInput — входные данные (base64 encoded)
class SlideInput(BaseModel):
    filename: str
    content_type: str  # image/jpeg, image/png, application/pdf
    data: str          # base64 encoded

# SlidesExtractionResult — результат извлечения
class SlidesExtractionResult(BaseModel):
    extracted_text: str      # markdown формат
    slides_count: int        # количество слайдов
    chars_count: int
    words_count: int
    tables_count: int        # обнаруженные таблицы
    model: str               # claude-haiku-4-5 / claude-sonnet-4-5
    tokens_used: TokensUsed | None
    cost: float | None
    processing_time_sec: float | None
```

**API endpoint:**
```python
# POST /api/step/slides
{
    "slides": [
        {"filename": "slide1.jpg", "content_type": "image/jpeg", "data": "base64..."},
        {"filename": "presentation.pdf", "content_type": "application/pdf", "data": "base64..."}
    ],
    "model": "claude-haiku-4-5",  # опционально
    "prompt_overrides": {...}      # опционально
}
```

**Ограничения:**

| Параметр | Лимит | Причина |
|----------|-------|---------|
| Макс. файлов | 50 | Контекст модели |
| Макс. размер файла | 10 MB | API ограничение |
| Общий размер | 100 MB | Память браузера |
| Batch size | 5 слайдов | Управление контекстом |

**Конфигурация** (`config/models.yaml`):
```yaml
slides:
  default: claude-haiku-4-5
  batch_size: 5
  available:
    - claude-haiku-4-5   # быстро, дешево
    - claude-sonnet-4-5  # баланс
    - claude-opus-4-5    # качество
```

**Промпты** (`config/prompts/slides/`):
- `system.md` — роль и правила извлечения
- `user.md` — инструкции по обработке изображений

Подробнее: [docs/adr/010-slides-integration.md](docs/adr/010-slides-integration.md)

## Content Types и Archive Structure (v0.21+, updated v0.23)

Система поддерживает два типа контента с разными pipeline и выходными документами:

| ContentType | Выходные файлы | Описание |
|-------------|----------------|----------|
| `educational` | `longread.md` + `summary.md` | Обучающие темы |
| `leadership` | `story.md` | Лидерские истории (8 блоков) |

**Категории мероприятий:**

| EventCategory | Структура архива | Примеры |
|---------------|------------------|---------|
| `regular` | `archive/{year}/{event_type}/{MM.DD}/{Title}/` | ПШ (еженедельные школы) |
| `offsite` | `archive/{year}/Выездные/{event_name}/{Title}/` | Форумы, выездные |

**Определение типа по имени файла:**

```python
# Regular events (ПШ): дата + тип в имени → content_type = educational
"2025.01.13 ПШ.SV Закрытие ПО (Кухаренко).mp4"

# Dated offsite leadership (v0.28+): маркер # → content_type = leadership
"2026.01 Форум Табтим. # Антоновы (Дмитрий и Юлия).mp3"

# Dated offsite educational (v0.28+): без # → content_type = educational
"2026.01 Форум Табтим. Тестовая тема (Светлана Дмитрук).mp3"

# Offsite folder leadership: Фамилия (Имя) → content_type = leadership
"Антоновы (Дмитрий и Юлия).mp4"

# Offsite folder educational: Фамилия — Название → content_type = educational
"Мекибель — Модели работы с МП.mp4"
```

**Модели:**
```python
from app.models.schemas import ContentType, EventCategory, VideoMetadata

# VideoMetadata теперь содержит:
metadata.content_type   # ContentType.EDUCATIONAL | LEADERSHIP
metadata.event_category # EventCategory.REGULAR | OFFSITE
metadata.event_name     # Для offsite: "Форум TABTeam (Москва)"
metadata.is_offsite     # computed: True если event_category == OFFSITE
```

## Расширенные метрики (v0.42+, updated v0.58)

API response содержит метрики для отладки промптов и отслеживания стоимости:

```python
from app.models.schemas import TokensUsed, CleanedTranscript

# TokensUsed — статистика токенов
class TokensUsed(CamelCaseModel):  # v0.58+: camelCase сериализация
    input: int   # входные токены
    output: int  # выходные токены
    total: int   # computed: input + output

# Метрики в моделях результатов:
# RawTranscript: confidence, processing_time_sec, chars, words
# CleanedTranscript: tokens_used, cost, processing_time_sec, words, change_percent
# Longread: tokens_used, cost, processing_time_sec, chars
# Summary: tokens_used, cost, processing_time_sec, chars, words
# Story: tokens_used, cost, processing_time_sec, chars
# TranscriptChunks: total_tokens
```

### API Serialization Rules (v0.59+)

**Правило:** Все API endpoints должны возвращать Pydantic модели, не `dict`.

| Слой | Формат | Пример |
|------|--------|--------|
| Python код | snake_case | `raw_transcript`, `tokens_used` |
| API JSON | camelCase | `rawTranscript`, `tokensUsed` |
| TypeScript | camelCase | `rawTranscript`, `tokensUsed` |

**Базовая модель:**
```python
from app.models.schemas import CamelCaseModel

class CamelCaseModel(BaseModel):
    """Python: snake_case, JSON: camelCase."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # принимает оба формата на входе
    )

# Все модели результатов наследуют от CamelCaseModel
# API возвращает camelCase: {"rawTranscript": {...}, "cleanedTranscript": {...}}
```

**Как добавить новый endpoint:**
1. Создать response модель наследующую от `CamelCaseModel` в `schemas.py`:
   ```python
   class MyNewResponse(CamelCaseModel):
       some_field: str
       another_field: int
   ```
2. Указать return type в endpoint:
   ```python
   @router.get("/my-endpoint")
   async def my_endpoint() -> MyNewResponse:
       return MyNewResponse(some_field="value", another_field=42)
   ```
3. Добавить импорт модели в файл routes

Подробнее: [docs/adr/013-api-camelcase-serialization.md](docs/adr/013-api-camelcase-serialization.md)

### Вкладка "Статистика" (v0.58+)

Централизованное отображение метрик обработки:

```typescript
// frontend/src/components/results/StatisticsView.tsx
<StatisticsView
  data={{
    rawTranscript: data.rawTranscript,
    cleanedTranscript: data.cleanedTranscript,
    slidesExtraction: data.slidesExtraction,
    longread: data.longread,
    summary: data.summary,
    story: data.story,
    chunks: data.chunks,
    savedFiles: data.savedFiles,
    contentType: data.metadata?.content_type,
  }}
/>
```

Появляется:
- В StepByStep после сохранения (автопереключение)
- В ArchiveResultsModal при наличии данных

Подробнее: [docs/adr/012-statistics-tab.md](docs/adr/012-statistics-tab.md)

**Frontend утилиты (v0.44+):**
```typescript
import { formatTime, formatCost, formatTokens } from '@/utils/formatUtils';

formatTime(6.2)        // → "6с"
formatTime(125.5)      // → "2м 6с"
formatCost(0.0314)     // → "~$0.03"
formatCost(0)          // → "бесплатно"
formatTokens(3570)     // → "3 570"
```

Подробнее: [docs/data-formats.md](docs/data-formats.md)

## Stage Abstraction (v0.14+, updated v0.51)

Система абстракций для этапов обработки. Позволяет добавлять новые шаги без изменения оркестратора.

```
backend/app/services/stages/
├── base.py              # BaseStage, StageContext, StageRegistry
├── parse_stage.py       # Парсинг имени файла
├── transcribe_stage.py  # Транскрипция через Whisper
├── clean_stage.py       # Очистка транскрипта
├── chunk_stage.py       # Семантическое чанкирование
├── longread_stage.py    # Генерация лонгрида (EDUCATIONAL)
├── summarize_stage.py   # Генерация конспекта (EDUCATIONAL)
├── story_stage.py       # Генерация истории 8 блоков (LEADERSHIP, v0.23+)
└── save_stage.py        # Сохранение результатов
```

**Примечание:** Шаг `slides` реализован как отдельный API endpoint (`/api/step/slides`) и не является частью stage абстракции. Выполняется условно при наличии прикреплённых слайдов (работает в обоих режимах: пошаговом и автоматическом).

**Условное выполнение (v0.23+):**
```python
class StoryStage(BaseStage):
    name = "story"
    depends_on = ["clean", "parse"]

    def should_skip(self, context: StageContext) -> bool:
        metadata = context.get_result("parse")
        return metadata.content_type != ContentType.LEADERSHIP
```

**Добавление нового этапа:**
```python
class TelegramSummaryStage(BaseStage):
    name = "telegram_summary"
    depends_on = ["longread"]
    optional = True

    async def execute(self, context: StageContext) -> TelegramSummary:
        longread = context.get_result("longread")
        # ...
```

Подробнее: [docs/pipeline/stages.md](docs/pipeline/stages.md)

## Shared Utils (v0.16+, updated v0.28)

Общие утилиты для LLM сервисов, извлечённые из дублированного кода:

```
backend/app/utils/
├── __init__.py          # Экспорт публичных функций
├── json_utils.py        # extract_json(), parse_json_safe()
├── token_utils.py       # estimate_tokens(), calculate_num_predict()
├── chunk_utils.py       # validate_cyrillic_ratio(), generate_chunk_id()
└── media_utils.py       # get_media_duration(), is_audio_file() (v0.28+)
```

**Использование:**
```python
from app.utils import extract_json, get_media_duration, is_audio_file

json_str = extract_json(response, json_type="array")
duration = get_media_duration(Path("video.mp4"))  # via ffprobe
is_audio = is_audio_file(Path("recording.mp3"))   # True
```

Подробнее: [docs/adr/003-shared-utils.md](docs/adr/003-shared-utils.md)

## AI Clients (v0.17+, updated v0.27)

Абстракция для AI провайдеров с разделением ответственности:

```
backend/app/services/ai_clients/
├── __init__.py          # Экспорт OllamaClient, ClaudeClient, WhisperClient
├── base.py              # BaseAIClient (Protocol), AIClientConfig, исключения
├── ollama_client.py     # OllamaClient — только LLM (generate, chat)
├── claude_client.py     # ClaudeClient — Anthropic Claude API (v0.19+)
└── whisper_client.py    # WhisperClient — транскрибация (v0.27+)
```

**Использование:**
```python
from app.services.ai_clients import OllamaClient, ClaudeClient, WhisperClient

# Транскрибация (WhisperClient)
async with WhisperClient.from_settings(settings) as whisper:
    result = await whisper.transcribe(audio_path)

# Локальная LLM (Ollama)
async with OllamaClient.from_settings(settings) as client:
    response = await client.generate("Hello!")

# Облачная LLM (Claude) — требует ANTHROPIC_API_KEY
async with ClaudeClient.from_settings(settings) as client:
    response = await client.generate("Analyze this document...")
```

**ProcessingStrategy (v0.19+, updated v0.29):**
```python
from app.services.pipeline import ProcessingStrategy

strategy = ProcessingStrategy(settings)

# Автоматический выбор провайдера по имени модели
async with strategy.create_client("claude-sonnet-4-5") as client:
    response = await client.generate("...")
```

> **v0.29+:** Метод `get_client_with_fallback()` удалён. Ошибки теперь пробрасываются вызывающему коду.

**Context Profiles** (в `config/models.yaml`):
- `small` — для gemma2:9b (< 16K tokens)
- `medium` — для qwen2.5:14b (16K-64K tokens)
- `large` — для Claude (> 100K tokens)

Подробнее:
- [docs/adr/004-ai-client-abstraction.md](docs/adr/004-ai-client-abstraction.md)
- [docs/adr/006-cloud-model-integration.md](docs/adr/006-cloud-model-integration.md)

## AI сервисы

| Сервис | URL | Модель |
|--------|-----|--------|
| Ollama | http://100.64.0.1:11434 | см. ниже |
| Whisper | http://100.64.0.1:9000 | large-v3 |

### Конфигурация моделей (v0.29+, updated v0.51)

| Задача | Модель по умолчанию | Почему |
|--------|---------------------|--------|
| Очистка | claude-sonnet-4-5 | Высокое качество очистки текста |
| Слайды | claude-haiku-4-5 | Быстро и дёшево для извлечения текста (v0.51+) |
| Лонгрид | claude-sonnet-4-5 | Отличное качество длинного текста |
| Конспект | claude-sonnet-4-5 | Структурированный вывод, глубокий анализ |
| Чанкирование | — | Детерминистический (H2 парсинг, v0.26+) |

> **v0.29+:** По умолчанию все LLM операции используют Claude. Требуется `ANTHROPIC_API_KEY`.

Подробнее: [docs/model-testing.md](docs/model-testing.md)

### Ключевые настройки (env)

| Настройка | Где менять | Эффект |
|-----------|------------|--------|
| `CLEANER_MODEL` | docker-compose.yml | Модель для очистки транскрипта |
| `LONGREAD_MODEL` | docker-compose.yml | Модель для генерации лонгрида |
| `SUMMARY_MODEL` | docker-compose.yml | Модель для генерации конспекта |
| `WHISPER_INCLUDE_TIMESTAMPS` | docker-compose.yml | `true` — таймкоды в транскрипте и файле |
| `ANTHROPIC_API_KEY` | docker-compose.yml | API ключ для Claude (v0.19+) |
| `HTTP_PROXY` / `HTTPS_PROXY` | docker-compose.yml | Прокси для Claude API (v0.20+) |
| `PROMPTS_DIR` | docker-compose.yml | Внешние промпты без деплоя (v0.30+) |

### Конфигурационные файлы

| Файл | Назначение |
|------|------------|
| `config/models.yaml` | Параметры моделей (chunk_size, thresholds, **pricing**) |
| `config/glossary.yaml` | Глоссарий терминов для коррекции |
| `config/prompts/{stage}/` | Промпты для LLM (v0.30+: иерархическая структура) |
| `config/events.yaml` | Типы событий для парсинга имён |

### Pricing моделей (v0.42+)

Цены моделей хранятся в `config/models.yaml` и используются для расчёта стоимости:

```yaml
claude_models:
  - id: "claude-sonnet-4-5"
    pricing:
      input: 3.00   # $ за 1M токенов
      output: 15.00
  - id: "claude-haiku-4-5"
    pricing:
      input: 1.00
      output: 5.00
  - id: "claude-opus-4-5"
    pricing:
      input: 15.00
      output: 75.00
```

Локальные модели (Ollama) — бесплатны, pricing не указывается.

**Утилиты расчёта:**
```python
from app.utils import pricing_utils

cost = pricing_utils.calculate_cost("claude-sonnet-4-5", input_tokens=1000, output_tokens=500)
# → 0.0105 USD
```

### Структура промптов (v0.31+)

Промпты организованы по этапам pipeline:

```
config/prompts/
├── cleaning/            # Очистка транскрипта
│   ├── system.md        # default
│   ├── system_v2.md     # вариант (опционально)
│   └── user.md
├── slides/              # Извлечение текста со слайдов (v0.51+)
│   ├── system.md
│   └── user.md
├── longread/            # Генерация лонгрида
│   ├── system.md
│   ├── instructions.md
│   └── template.md
├── summary/             # Генерация конспекта
├── story/               # Генерация истории
└── outline/             # Извлечение outline
    └── map.md
```

**Загрузка промптов:**
```python
from app.config import load_prompt

# Сигнатура: load_prompt(stage, name, settings)
system = load_prompt("cleaning", "system", settings)         # default
system_v2 = load_prompt("cleaning", "system_v2", settings)   # вариант
```

**API промптов (v0.31+):**
```bash
# Получить доступные варианты для этапа
curl http://100.64.0.1:8801/api/prompts/cleaning

# Response: {"stage":"cleaning","components":[
#   {"component":"system","default":"system","variants":[...]},
#   {"component":"user",...}
# ]}
```

**Внешние промпты (без деплоя):**
- Монтируется через `PROMPTS_DIR=/data/prompts`
- Приоритет: внешние → встроенные
- Редактирование через SMB

Подробнее: [docs/configuration.md](docs/configuration.md)

## Разработка

### Особенности macOS

На macOS системный Python защищён от установки пакетов. Используй виртуальное окружение:

```bash
# Проверка синтаксиса (работает без venv)
python3 -m py_compile backend/app/api/step_routes.py

# Для запуска кода — создай venv
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Запуск сервера
python -m uvicorn app.main:app --reload --port 8801
```

### Локальное тестирование

> **ВАЖНО:** Перед запуском тестов читай [docs/testing.md](docs/testing.md) — там описаны изолированные тесты без Settings для локальной разработки.

Многие модули содержат встроенные тесты в `if __name__ == "__main__"`:

```bash
cd backend
source .venv/bin/activate

# Тесты парсера (проверка паттернов, archive_path)
python -m app.services.parser

# Тесты saver
python -m app.services.saver
```

**Если нет `.env`** — используй изолированные тесты (без `get_settings()`):

```bash
python3 -c "
from app.services.parser import parse_dated_offsite_filename
result = parse_dated_offsite_filename('2026.01 Event. # Title (Name).mp3')
print('OK' if result else 'FAIL')
"
```

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8801
```

### Frontend

```bash
cd frontend && npm install && npm run dev
```

## Деплой

**Локальный docker-compose не работает** — пути к данным (`/mnt/main/work/bz2/video`) существуют только на сервере.

```bash
./scripts/deploy.sh   # Единственный способ деплоя
```

Подробнее: [docs/deployment.md](docs/deployment.md)

## Версионирование

Версия отображается в веб-интерфейсе (`v0.1.0 • 10.01.26 15:30`). Дата/время обновляются автоматически при сборке.

**При значимых изменениях** предлагай обновить версию в `frontend/package.json`:
- **patch** (0.1.x) — баг-фиксы, мелкие правки
- **minor** (0.x.0) — новые фичи, заметные улучшения
- **major** (x.0.0) — ломающие изменения, крупные переработки

## Логирование

Система логирования с управлением через переменные окружения.

### Конфигурация

```bash
LOG_LEVEL=INFO                    # Общий уровень (DEBUG/INFO/WARNING/ERROR)
LOG_FORMAT=structured             # Формат: simple | structured
LOG_LEVEL_AI_CLIENT=DEBUG         # Per-module override
LOG_LEVEL_PIPELINE=INFO
LOG_LEVEL_TRANSCRIBER=INFO
LOG_LEVEL_CLEANER=INFO
LOG_LEVEL_CHUNKER=INFO
LOG_LEVEL_SUMMARIZER=INFO
```

### Формат structured логов

```
2025-01-09 10:30:15 | INFO     | ai_client       | Transcribing: video.mp4 (156.3 MB)
2025-01-09 10:32:18 | ERROR    | ai_client       | Transcription timeout after 123.4s
```

### Подключение к серверу (для Claude)

**ВАЖНО:** Используй `sshpass` с паролем из `.env.local` для выполнения команд на сервере:

```bash
# Загрузить credentials
source .env.local

# Выполнить команду на сервере
sshpass -p "$DEPLOY_PASSWORD" ssh -o StrictHostKeyChecking=no "$DEPLOY_USER@$DEPLOY_HOST" "COMMAND"

# Пример: получить логи контейнера
sshpass -p "$DEPLOY_PASSWORD" ssh -o StrictHostKeyChecking=no "$DEPLOY_USER@$DEPLOY_HOST" \
  "echo '$DEPLOY_PASSWORD' | sudo -S docker logs bz2-transcriber --tail 50" 2>&1

# Пример: прочитать файл из архива (путь на хосте!)
sshpass -p "$DEPLOY_PASSWORD" ssh -o StrictHostKeyChecking=no "$DEPLOY_USER@$DEPLOY_HOST" \
  "echo '$DEPLOY_PASSWORD' | sudo -S cat '/mnt/main/work/bz2/video/archive/2025/...'" 2>&1
```

**Пути:**
- На хосте: `/mnt/main/work/bz2/video/archive/...`
- В контейнере: `/data/archive/...`

### Просмотр логов на сервере

```bash
# Через sshpass (рекомендуется для Claude)
source .env.local && sshpass -p "$DEPLOY_PASSWORD" ssh -o StrictHostKeyChecking=no "$DEPLOY_USER@$DEPLOY_HOST" \
  "echo '$DEPLOY_PASSWORD' | sudo -S docker logs bz2-transcriber --tail 50" 2>&1

# Интерактивно (для пользователя)
ssh truenas_admin@192.168.1.152 'sudo docker logs bz2-transcriber --tail 50'
```

Подробнее: [docs/logging.md](docs/logging.md)

## Тестирование на сервере

Claude может тестировать pipeline-шаги на сервере через inline Python в контейнере.

**Ключевое:** пути в контейнере отличаются от хоста (`/data/` вместо `/mnt/main/work/bz2/video/`).

Подробнее: [docs/testing.md](docs/testing.md) — примеры тестов, классы сервисов, Pydantic-модели.
