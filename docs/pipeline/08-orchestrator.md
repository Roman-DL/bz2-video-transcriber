# Pipeline Orchestrator

[< Назад: Save](07-save.md) | [Обзор Pipeline](README.md)

---

## Назначение

Координация всех этапов обработки видео с поддержкой двух режимов:
1. **Полный pipeline** — автоматическое выполнение всех этапов
2. **Пошаговый режим** — независимое выполнение каждого этапа для тестирования

## Использование

```python
from app.services.pipeline import PipelineOrchestrator

orchestrator = PipelineOrchestrator(settings)

# Полный pipeline
result = await orchestrator.process(Path("inbox/video.mp4"))

# Или пошагово
metadata = orchestrator.parse(video_path)
raw = await orchestrator.transcribe(video_path)
cleaned = await orchestrator.clean(raw, metadata)
chunks = await orchestrator.chunk(cleaned, metadata)
longread = await orchestrator.longread(chunks, metadata)
summary = await orchestrator.summarize_from_longread(longread, metadata)
files = await orchestrator.save(metadata, raw, cleaned, chunks, longread, summary)
```

> **API методов:** См. docstrings в `backend/app/services/pipeline/orchestrator.py`

---

## Декомпозиция pipeline (v0.15+)

С версии 0.15 pipeline декомпозирован на отдельные модули с чёткими обязанностями:

```
backend/app/services/pipeline/
├── __init__.py              # Экспорт публичного API
├── orchestrator.py          # Координация этапов, PipelineError
├── progress_manager.py      # Веса этапов, расчёт прогресса
├── fallback_factory.py      # Создание fallback объектов при ошибках
├── config_resolver.py       # Override моделей для пошагового режима
├── stage_cache.py           # Версионирование результатов (v0.18+)
└── processing_strategy.py   # Выбор local/cloud провайдера (v0.19+)
```

| Модуль | Назначение |
|--------|------------|
| **orchestrator** | Координация stages, управление потоком выполнения |
| **progress_manager** | Калиброванные веса STAGE_WEIGHTS, расчёт % прогресса |
| **fallback_factory** | Создание fallback chunks/longread/summary при ошибках |
| **config_resolver** | Подмена модели для конкретного этапа (model override) |
| **stage_cache** | Сохранение/загрузка версионированных результатов этапов |
| **processing_strategy** | Выбор между local (Ollama) и cloud (Claude) провайдером |

> **Архитектурные решения:** [ADR-002](../adr/002-pipeline-decomposition.md)

---

## Два режима работы

### Режим 1: Полный Pipeline

```
process(video_path, progress_callback)
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│  Parse → Transcribe → Clean → Chunk → Longread → Summarize → Save │
│                                 └───────── последовательно ───────┘ │
└────────────────────────────────────────────────────────────────────┘
         │
         ▼
   ProcessingResult
```

**Использование:**
```python
async def on_progress(status, progress, message):
    print(f"[{status.value}] {progress:.0f}% - {message}")

result = await orchestrator.process(
    video_path=Path("inbox/video.mp4"),
    progress_callback=on_progress,
)

print(f"Video ID: {result.video_id}")
print(f"Chunks: {result.chunks_count}")
print(f"Files: {result.files_created}")
```

### Режим 2: Пошаговый

```
┌───────────────────────────────────────────────────────────────────┐
│  Каждый метод независим — можно повторять любой этап             │
│                                                                   │
│  parse()                  → VideoMetadata                         │
│  transcribe()             → RawTranscript                         │
│  clean()                  → CleanedTranscript   ◄── глоссарий     │
│  chunk()                  → TranscriptChunks                      │
│  longread()               → Longread            ◄── промпты       │
│  summarize_from_longread()→ Summary             ◄── промпты       │
│  save()                   → list[str]                             │
└───────────────────────────────────────────────────────────────────┘
```

**Использование для тестирования промптов:**
```python
orchestrator = PipelineOrchestrator(settings)
video_path = Path("inbox/video.mp4")

# Выполняем тяжёлые этапы один раз
metadata = orchestrator.parse(video_path)
raw = await orchestrator.transcribe(video_path)
cleaned = await orchestrator.clean(raw, metadata)
chunks = await orchestrator.chunk(cleaned, metadata)

# Тестируем разные модели для longread
longread_qwen = await orchestrator.longread(chunks, metadata, model="qwen2.5:14b")
longread_gemma = await orchestrator.longread(chunks, metadata, model="gemma2:9b")

# Генерируем summary из лучшего longread
summary = await orchestrator.summarize_from_longread(longread_qwen, metadata)

# Сохраняем результат
files = await orchestrator.save(metadata, raw, cleaned, chunks, longread_qwen, summary)
```

---

## Progress Callback

### Распределение прогресса по этапам

| Этап | Вес | Накопительный % | Обоснование |
|------|-----|-----------------|-------------|
| PARSING | 2% | 0-2% | Синхронный regex |
| TRANSCRIBING | 45% | 2-47% | Whisper (доминирующий этап) |
| CLEANING | 10% | 47-57% | Один LLM вызов |
| CHUNKING | 12% | 57-69% | Map-Reduce разбиение |
| LONGREAD | 18% | 69-87% | Map-Reduce генерация секций |
| SUMMARIZING | 10% | 87-97% | Один LLM вызов из longread |
| SAVING | 3% | 97-100% | Мгновенно (<1s) |

> **Калибровка:** Веса основаны на замерах: transcribe ~87s, clean ~7.5s, chunk+longread+summary ~25s. См. константу `STAGE_WEIGHTS` в `progress_manager.py`.

### Пример вывода

```
[parsing] 0% - Parsing: 2025.01.09 ПШ.SV Video Title (Speaker).mp4
[parsing] 100% - Parsed: 2025-01-09_ПШ-SV_video-title
[transcribing] 2% - Transcribing: 2025.01.09 ПШ.SV Video Title (Speaker).mp4
[transcribing] 47% - Transcribed: 156 segments, 3600s
[cleaning] 47% - Cleaning transcript with glossary and LLM
[cleaning] 57% - Cleaned: 45000 -> 42000 chars
[chunking] 57% - Starting semantic chunking
[chunking] 69% - Completed: 12 chunks
[longread] 69% - Generating longread sections
[longread] 87% - Generated 5 sections, 3500 words
[summarizing] 87% - Generating summary from longread
[summarizing] 97% - Summary ready
[saving] 97% - Saving to: /archive/2025/01/ПШ.SV/Video Title (Speaker)
[saving] 100% - Saved 6 files
```

---

## ProgressManager

Сервис расчёта прогресса выполнения pipeline.

### Архитектура

```
PipelineOrchestrator._do_*()
    │
    ├─ manager.calculate_overall_progress(stage, stage_progress)
    │       ↓
    │   float (0-100%)
    │
    └─ manager.update_progress(callback, status, stage_progress, message)
            ↓
        await callback(status, overall_progress, message)
```

**Ключевой метод:**
```python
# Пример: TRANSCRIBING на 50% → 2 + (45 * 0.5) = 24.5%
overall = manager.calculate_overall_progress(ProcessingStatus.TRANSCRIBING, 50)
```

> **API:** См. docstrings в `backend/app/services/pipeline/progress_manager.py`

---

## ProcessingStrategy (v0.19+)

Автоматический выбор AI провайдера по имени модели:

```python
from app.services.pipeline import ProcessingStrategy

strategy = ProcessingStrategy(settings)

# Автоматический выбор: "claude-*" → cloud, остальное → local
async with strategy.create_client("claude-sonnet") as client:
    response = await client.generate("...")

# С fallback на локальную модель
client, model = await strategy.get_client_with_fallback(
    "claude-sonnet",   # Предпочтительная
    "qwen2.5:14b"      # Fallback если Claude недоступен
)
```

| Модель | Провайдер |
|--------|-----------|
| `claude-*` | Cloud (Anthropic API) |
| Всё остальное | Local (Ollama) |

> **Подробнее:** [ADR-006](../adr/006-cloud-model-integration.md)

---

## Stage Result Cache (v0.18+)

Версионированное сохранение результатов каждого этапа для повторных запусков:

```python
from app.services.pipeline import StageResultCache
from app.models.cache import CacheStageName

cache = StageResultCache(settings)

# Сохранить результат (автоматически создаёт новую версию)
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

**Структура кэша:**
```
archive/2025/01.09 ПШ/Video Title/
├── pipeline_results.json    # Текущие результаты
└── .cache/
    ├── manifest.json        # Версии и метаданные
    ├── cleaning/v1.json     # Версия 1
    ├── cleaning/v2.json     # Re-run с другой моделью
    └── ...
```

> **Подробнее:** [ADR-005](../adr/005-result-caching.md)

---

## Error Handling

### PipelineError

```python
from app.services.pipeline import PipelineError

try:
    result = await orchestrator.process(video_path)
except PipelineError as e:
    print(f"Pipeline failed at {e.stage.value}: {e.message}")
    if e.cause:
        print(f"Cause: {e.cause}")
```

### Graceful Degradation

При ошибках в некритичных этапах pipeline продолжает работу:

| Ситуация | Поведение |
|----------|-----------|
| Chunker упал | Fallback на разбиение по ~300 слов |
| Longread упал | Fallback — минимальный longread |
| Summarizer упал | Fallback на минимальный конспект |
| Все три упали | PipelineError |
| Parse/Transcribe/Save упал | Немедленный PipelineError |

Fallback объекты создаются через `FallbackFactory`. См. docstrings в `backend/app/services/pipeline/fallback_factory.py`.

---

## Сериализация результатов

Все модели — Pydantic, поддерживают JSON сериализацию:

```python
# Сохранить для повторного использования
raw_json = raw.model_dump_json()
with open("raw_transcript.json", "w") as f:
    f.write(raw_json)

# Загрузить обратно
from app.models.schemas import RawTranscript
raw = RawTranscript.model_validate_json(raw_json)
```

---

## Связанные документы

- [Stage Abstraction](stages.md) — система этапов обработки
- [ADR-002: Pipeline Decomposition](../adr/002-pipeline-decomposition.md)
- [ADR-005: Result Caching](../adr/005-result-caching.md)
- [ADR-006: Cloud Model Integration](../adr/006-cloud-model-integration.md)
