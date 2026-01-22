# Stage Abstraction

Система абстракций для этапов обработки видео. Позволяет легко добавлять новые шаги в pipeline без изменения оркестратора.

## Обзор

```
backend/app/services/stages/
├── __init__.py              # Экспорты и create_default_stages()
├── base.py                  # BaseStage, StageContext, StageRegistry
├── parse_stage.py           # Парсинг имени файла
├── transcribe_stage.py      # Транскрипция через Whisper
├── clean_stage.py           # Очистка транскрипта
├── chunk_stage.py           # H2-based чанкирование (детерминистический)
├── longread_stage.py        # Генерация лонгрида (EDUCATIONAL)
├── summarize_stage.py       # Генерация конспекта (EDUCATIONAL)
├── story_stage.py           # Генерация истории 8 блоков (LEADERSHIP, v0.23+)
└── save_stage.py            # Сохранение результатов

backend/app/services/
└── slides_extractor.py      # Извлечение текста со слайдов (v0.51+, отдельный сервис)
```

## Основные классы

### StageContext

Иммутабельный контекст, передаваемый между стадиями. Хранит результаты предыдущих стадий.

```python
from app.services.stages import StageContext

# Создание контекста
context = StageContext()
context = context.with_metadata("video_path", Path("video.mp4"))

# Добавление результатов (возвращает новый контекст)
context = context.with_result("parse", metadata)
context = context.with_result("transcribe", (raw_transcript, audio_path))

# Получение результатов
metadata = context.get_result("parse")
raw, audio = context.get_result("transcribe")

# Проверка наличия
if context.has_result("clean"):
    cleaned = context.get_result("clean")
```

### BaseStage

Абстрактный базовый класс для всех стадий.

```python
from app.services.stages import BaseStage, StageContext

class MyStage(BaseStage):
    name = "my_stage"              # Уникальный идентификатор
    depends_on = ["longread"]      # Зависимости
    optional = True                # Опциональная стадия?
    status = ProcessingStatus.SUMMARIZING  # Для прогресса

    async def execute(self, context: StageContext) -> MyResult:
        # Получаем данные из контекста
        longread = context.get_result("longread")

        # Обрабатываем
        result = await self.process(longread)

        return result

    def estimate_time(self, input_size: int) -> float:
        """Оценка времени выполнения в секундах."""
        return 10.0 + input_size / 1000
```

### StageRegistry

Реестр для управления стадиями и построения pipeline. Автоматически разрешает зависимости через топологическую сортировку (алгоритм Кана).

```python
from app.services.stages import StageRegistry, create_default_stages
from app.services.ai_clients import WhisperClient
from app.services.pipeline import ProcessingStrategy

# v0.29+: Whisper для транскрипции, ProcessingStrategy для LLM
async with WhisperClient.from_settings(settings) as whisper:
    strategy = ProcessingStrategy(settings)
    async with strategy.create_client("claude-sonnet-4-5") as llm:
        registry = create_default_stages(whisper, llm, settings)

# Построение pipeline (автоматически добавляет зависимости)
stages = registry.build_pipeline(["parse", "transcribe", "clean"])

# Выполнение
context = StageContext().with_metadata("video_path", video_path)
for stage in stages:
    result = await stage.execute(context)
    context = context.with_result(stage.name, result)
```

> **API классов:** См. docstrings в `backend/app/services/stages/base.py`

---

## Добавление нового шага

### Пример: TelegramSummaryStage

Допустим, нужно генерировать короткое превью для Telegram (~150 символов).

**1. Создать файл `stages/telegram_summary_stage.py`:**

```python
"""Telegram summary stage for generating short previews."""

from app.config import Settings
from app.models.schemas import Longread
from app.services.ai_clients import BaseAIClient
from app.services.stages.base import BaseStage, StageContext, StageError
from pydantic import BaseModel


class TelegramSummary(BaseModel):
    """Short summary for Telegram preview."""
    text: str  # ~150 chars
    hashtags: list[str]


class TelegramSummaryStage(BaseStage):
    """Generate short preview for Telegram.

    Input: longread
    Output: TelegramSummary
    """

    name = "telegram_summary"
    depends_on = ["longread"]
    optional = True  # Не обязательный шаг

    def __init__(self, ai_client: BaseAIClient, settings: Settings):
        self.ai_client = ai_client
        self.settings = settings

    async def execute(self, context: StageContext) -> TelegramSummary:
        self.validate_context(context)

        longread: Longread = context.get_result("longread")

        # Генерируем превью
        prompt = f"""
        Создай короткое превью для Telegram (150 символов) на основе лонгрида.

        Заголовок: {longread.title}
        Введение: {longread.introduction}

        Формат ответа:
        - text: краткое описание
        - hashtags: список хэштегов (3-5)
        """

        response = await self.ai_client.generate(
            prompt=prompt,
            model=self.settings.summarizer_model,
        )

        # Парсинг ответа...
        return TelegramSummary(
            text=response[:150],
            hashtags=["#видео", "#обучение"],
        )

    def estimate_time(self, input_size: int) -> float:
        return 5.0
```

**2. Зарегистрировать в `stages/__init__.py`:**

```python
from app.services.stages.telegram_summary_stage import TelegramSummaryStage

__all__ = [
    # ...existing exports...
    "TelegramSummaryStage",
]

def create_default_stages(ai_client, settings, registry=None):
    # ...existing registrations...

    # Добавить новую стадию
    registry.register(TelegramSummaryStage(ai_client, settings))

    return registry
```

**3. Использование:**

```python
# Включить в pipeline
stages = registry.build_pipeline([
    "parse", "transcribe", "clean", "chunk",
    "longread", "telegram_summary", "save"
])

# Результат будет в context.get_result("telegram_summary")
```

> **Выбор AI провайдера:** Для автоматического выбора между local (Ollama) и cloud (Claude) используйте `ProcessingStrategy`. См. [ADR-004](../adr/004-ai-client-abstraction.md).

---

## Генераторы и PromptOverrides (v0.32+)

Генераторы (`TranscriptCleaner`, `LongreadGenerator`, `SummaryGenerator`, `StoryGenerator`) поддерживают выбор вариантов промптов через `PromptOverrides`:

```python
from app.models.schemas import PromptOverrides
from app.services.cleaner import TranscriptCleaner

# Использование с override промптов
overrides = PromptOverrides(system="system_v2")
cleaner = TranscriptCleaner(ai_client, settings, prompt_overrides=overrides)
result = await cleaner.clean(raw_transcript, metadata)
```

**Доступные компоненты по этапам:**

| Генератор | Компоненты |
|-----------|------------|
| `TranscriptCleaner` | `system`, `user` |
| `LongreadGenerator` | `system`, `instructions`, `template` |
| `SummaryGenerator` | `system`, `instructions`, `template` |
| `StoryGenerator` | `system`, `instructions`, `template` |

**Логика:**
- `prompt_overrides=None` → используются default промпты
- `prompt_overrides.system="system_v2"` → загружается `config/prompts/{stage}/system_v2.md`

---

## Граф зависимостей

```
parse ─────┬──────────────────────────────────────────────→ save
           │                                                  ↑
           ↓                                                  │
       transcribe (Whisper)                                   │
           │                                                  │
           ↓                                                  │
         clean (Claude) ──────────────────────────────────────┤
           │                                                  │
           ├────────────────────────────┐                     │
           ↓                            ↓                     │
       longread (Claude)           story (Claude)             │
      [EDUCATIONAL]               [LEADERSHIP]                │
           │                            │                     │
           ↓                            │                     │
       summarize (Claude)               │                     │
           │                            │                     │
           └────────────┬───────────────┘                     │
                        ↓                                     │
                  chunk (H2) ─────────────────────────────────┘
```

**Ветвление по content_type:**
- `EDUCATIONAL` → longread → summarize → chunk → save
- `LEADERSHIP` → story → chunk → save

---

## Slides Extraction (v0.51+)

Извлечение текста со слайдов презентаций реализовано как отдельный сервис, а не как stage. Это связано с тем, что:

1. Шаг выполняется **условно** — только если пользователь прикрепил слайды
2. Работает только в **step-by-step режиме** (не в автоматическом pipeline)
3. Требует **multimodal API** (Claude Vision) — отличается от текстовых LLM операций

### Архитектура

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Step-by-step Pipeline (Frontend)                 │
│                                                                      │
│   Transcribe → Clean ─┬─→ [SLIDES] → Longread → Summary → Save      │
│                       └─→ [SLIDES] → Story → Save                   │
│                               ↓                                      │
│                       (только если есть                              │
│                        прикреплённые слайды)                         │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        SlidesExtractor                               │
│                                                                      │
│   SlideInput[] ─→ PDF→Images ─→ Batch(5) ─→ Claude Vision ─→ Result │
│                                                                      │
│   Input:  list[SlideInput]  (base64 images/PDFs)                    │
│   Output: SlidesExtractionResult (markdown text + metrics)          │
└─────────────────────────────────────────────────────────────────────┘
```

### Использование

```python
from app.services.slides_extractor import SlidesExtractor
from app.services.ai_clients import ClaudeClient
from app.models.schemas import SlideInput, PromptOverrides

async with ClaudeClient.from_settings(settings) as client:
    extractor = SlidesExtractor(client, settings)

    slides = [
        SlideInput(
            filename="slide1.jpg",
            content_type="image/jpeg",
            data="base64_encoded_data"
        ),
        SlideInput(
            filename="presentation.pdf",
            content_type="application/pdf",
            data="base64_encoded_data"
        )
    ]

    result = await extractor.extract(
        slides=slides,
        model="claude-haiku-4-5",  # опционально
        prompt_overrides=PromptOverrides(system="system"),  # опционально
    )

    print(f"Extracted {result.slides_count} slides")
    print(f"Text: {result.extracted_text[:200]}...")
    print(f"Cost: ${result.cost:.4f}")
```

### Интеграция в Longread/Story

Извлечённый текст передаётся как параметр `slides_text`:

```python
# LongreadGenerator
result = await generator.generate(
    cleaned_transcript=cleaned,
    metadata=metadata,
    slides_text=slides_result.extracted_text,  # опционально
)

# StoryGenerator
result = await generator.generate(
    cleaned_transcript=cleaned,
    metadata=metadata,
    slides_text=slides_result.extracted_text,  # опционально
)
```

### Конфигурация

См. `config/models.yaml`:

```yaml
slides:
  default: claude-haiku-4-5
  batch_size: 5
  available:
    - id: "claude-haiku-4-5"
      description: "Быстрый и дешёвый"
    - id: "claude-sonnet-4-5"
      description: "Баланс качества и скорости"
    - id: "claude-opus-4-5"
      description: "Максимальное качество"
```

### API Endpoint

```python
POST /api/step/slides

# Request
{
    "slides": [{"filename": "...", "content_type": "...", "data": "base64..."}],
    "model": "claude-haiku-4-5",
    "prompt_overrides": {"system": "system"}
}

# Response (SSE)
{"type": "progress", "progress": 33.3, "message": "Processing batch 1/3..."}
{"type": "result", "data": {...SlidesExtractionResult...}}
```

Подробнее: [ADR-010: Slides Integration](../adr/010-slides-integration.md)

---

## Обработка ошибок (v0.29+)

Стадии выбрасывают `StageError` при ошибках. Fallback механизмы удалены — ошибки пробрасываются вызывающему коду:

```python
from app.services.stages import StageError

async def execute(self, context: StageContext) -> Result:
    try:
        result = await self.process(data)
        return result
    except ValueError as e:
        raise StageError(self.name, f"Validation failed: {e}", e)
```

> **v0.29+:** Fallback логика удалена. При ошибках LLM генерации (longread, summary) выбрасывается `PipelineError`, пользователь видит явное сообщение об ошибке.

См. [ADR-007: Remove Fallback](../adr/007-remove-fallback-use-claude.md)

---

## Встроенные тесты

```bash
PYTHONPATH=backend python3 backend/app/services/stages/base.py
```

---

## Связанные документы

- [Pipeline Orchestrator](08-orchestrator.md) — координация stages
- [ADR-004: AI Client Abstraction](../adr/004-ai-client-abstraction.md) — OllamaClient, ClaudeClient
- [ADR-006: Cloud Model Integration](../adr/006-cloud-model-integration.md) — ProcessingStrategy
