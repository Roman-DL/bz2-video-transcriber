# Pipeline Orchestrator

[< Назад: Save](06-save.md) | [Обзор Pipeline](README.md)

---

## Назначение

Координация всех этапов обработки видео с поддержкой двух режимов:
1. **Полный pipeline** — автоматическое выполнение всех этапов
2. **Пошаговый режим** — независимое выполнение каждого этапа для тестирования

## Класс PipelineOrchestrator

```python
from app.services.pipeline import PipelineOrchestrator, PipelineError

orchestrator = PipelineOrchestrator(settings)

# Полный pipeline
result = await orchestrator.process(Path("inbox/video.mp4"))

# Или пошагово
metadata = orchestrator.parse(video_path)
raw = await orchestrator.transcribe(video_path)
cleaned = await orchestrator.clean(raw, metadata)
chunks = await orchestrator.chunk(cleaned, metadata)
summary = await orchestrator.summarize(cleaned, metadata, "summarizer_v2")
files = await orchestrator.save(metadata, raw, chunks, summary)
```

---

## Два режима работы

### Режим 1: Полный Pipeline

```
process(video_path, progress_callback)
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  Parse → Transcribe → Clean → [Chunk + Summarize] → Save   │
│                                 └─── параллельно ───┘       │
└─────────────────────────────────────────────────────────────┘
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
┌──────────────────────────────────────────────────────────────┐
│  Каждый метод независим — можно повторять любой этап        │
│                                                              │
│  parse()      → VideoMetadata                                │
│  transcribe() → RawTranscript                                │
│  clean()      → CleanedTranscript   ◄── тестировать глоссарий│
│  chunk()      → TranscriptChunks                             │
│  summarize()  → VideoSummary        ◄── тестировать промпты  │
│  save()       → list[str]                                    │
└──────────────────────────────────────────────────────────────┘
```

**Использование для тестирования промптов:**
```python
orchestrator = PipelineOrchestrator()
video_path = Path("inbox/video.mp4")

# Выполняем тяжёлые этапы один раз
metadata = orchestrator.parse(video_path)
raw = await orchestrator.transcribe(video_path)
cleaned = await orchestrator.clean(raw, metadata)
chunks = await orchestrator.chunk(cleaned, metadata)

# Тестируем разные промпты
summary_v1 = await orchestrator.summarize(cleaned, metadata, "summarizer")
summary_v2 = await orchestrator.summarize(cleaned, metadata, "summarizer_v2")
summary_v3 = await orchestrator.summarize(cleaned, metadata, "summarizer_detailed")

# Сохраняем лучший вариант
files = await orchestrator.save(metadata, raw, chunks, summary_v2)
```

---

## API методов

### process()

```python
async def process(
    video_path: Path,
    progress_callback: ProgressCallback | None = None,
) -> ProcessingResult
```

Полный pipeline с параллельным выполнением Chunk и Summarize.

**Progress callback signature:**
```python
async def callback(
    status: ProcessingStatus,  # Текущий этап
    progress: float,           # 0-100%
    message: str,              # Человекочитаемое сообщение
) -> None
```

### Пошаговые методы

| Метод | Async | Вход | Выход |
|-------|-------|------|-------|
| `parse(video_path)` | Нет | `Path` | `VideoMetadata` |
| `transcribe(video_path)` | Да | `Path` | `RawTranscript` |
| `clean(raw, metadata)` | Да | `RawTranscript`, `VideoMetadata` | `CleanedTranscript` |
| `chunk(cleaned, metadata)` | Да | `CleanedTranscript`, `VideoMetadata` | `TranscriptChunks` |
| `summarize(cleaned, metadata, prompt_name)` | Да | `CleanedTranscript`, `VideoMetadata`, `str` | `VideoSummary` |
| `save(metadata, raw, chunks, summary)` | Да | Все результаты | `list[str]` |

---

## Progress Callback

### Распределение прогресса по этапам

| Этап | Вес | Накопительный % | Обоснование |
|------|-----|-----------------|-------------|
| PARSING | 2% | 0-2% | Синхронный regex |
| TRANSCRIBING | 50% | 2-52% | Whisper (самый долгий, ~77% времени) |
| CLEANING | 13% | 52-65% | Один LLM вызов |
| CHUNKING | 16% | 65-81% | Параллельно с SUMMARIZING |
| SUMMARIZING | 16% | 65-97% | Параллельно с CHUNKING |
| SAVING | 3% | 97-100% | Мгновенно (<1s) |

> **Калибровка весов:** Веса сбалансированы по реальному времени выполнения, чтобы прогресс рос плавно. См. [справочник калибровки](../reference/progress-calibration.md).

### Пример вывода

```
[parsing] 0% - Parsing: 2025.01.09 ПШ.SV Video Title (Speaker).mp4
[parsing] 100% - Parsed: 2025-01-09_ПШ-SV_video-title
[transcribing] 2% - Transcribing: 2025.01.09 ПШ.SV Video Title (Speaker).mp4
[transcribing] 47% - Transcribed: 156 segments, 3600s
[cleaning] 47% - Cleaning transcript with glossary and LLM
[cleaning] 62% - Cleaned: 45000 -> 42000 chars
[chunking] 62% - Starting parallel chunking and summarization
[summarizing] 88% - Completed: 12 chunks, summary ready
[saving] 88% - Saving to: /archive/2025/01/ПШ.SV/Video Title (Speaker)
[saving] 100% - Saved 4 files
```

---

## ProgressEstimator

Сервис оценки времени выполнения каждого этапа. Используется для показа % прогресса.

### Архитектура

```
Pipeline._do_*()
    │
    ├─ estimator.estimate_*(input) → TimeEstimate
    │       ↓
    │   {estimated_seconds: 92.3, formula: "5 + 301 * 0.29"}
    │
    ├─ estimator.start_ticker(stage, estimated_seconds, callback)
    │   └─ asyncio.Task (обновляет % каждую секунду)
    │
    ├─ await operation()  ← asyncio.to_thread() для Whisper
    │
    └─ estimator.stop_ticker() → 100%
```

### Оценка времени

Время выполнения оценивается по входным данным:

| Этап | Входные данные | Формула |
|------|----------------|---------|
| transcribe | video duration (сек) | `base_time + duration * factor` |
| clean | input chars | `base_time + chars/1000 * factor` |
| chunk | input chars | `base_time + chars/1000 * factor` |
| summarize | input chars | `base_time + chars/1000 * factor` |

Коэффициенты хранятся в `config/performance.yaml`.

### Ticker

Ticker — asyncio.Task, который каждую секунду вызывает callback с обновлённым %:

```python
async def _ticker_loop(self, ...):
    while elapsed < estimated_seconds * 1.5:
        progress = min(99.0, (elapsed / estimated_seconds) * 100)
        await callback(stage, progress, message)
        await asyncio.sleep(1.0)
        elapsed += 1.0
```

**Важно:** Ticker ограничен 99% — финальные 100% устанавливает `stop_ticker()` после завершения операции.

### Ключевые файлы

| Файл | Описание |
|------|----------|
| `backend/app/services/progress_estimator.py` | ProgressEstimator сервис |
| `config/performance.yaml` | Коэффициенты оценки времени |

> **Калибровка коэффициентов:** [docs/reference/progress-calibration.md](../reference/progress-calibration.md)

---

## Error Handling

### PipelineError

```python
class PipelineError(Exception):
    stage: ProcessingStatus  # Этап, где произошла ошибка
    message: str             # Описание ошибки
    cause: Exception | None  # Оригинальное исключение
```

**Пример обработки:**
```python
try:
    result = await orchestrator.process(video_path)
except PipelineError as e:
    print(f"Pipeline failed at {e.stage.value}: {e.message}")
    if e.cause:
        print(f"Cause: {e.cause}")
```

### Graceful Degradation

При ошибках в Chunk или Summarize pipeline продолжает работу:

| Ситуация | Поведение |
|----------|-----------|
| Chunker упал | Fallback на разбиение по ~300 слов |
| Summarizer упал | Fallback на минимальное саммари |
| Оба упали | PipelineError |
| Parse/Transcribe/Save упал | Немедленный PipelineError |

**Fallback chunks:**
```python
# Простое разбиение по 300 слов
TranscriptChunk(
    id="video-id_001",
    index=1,
    topic="Часть 1",  # Вместо семантической темы
    text="...",
    word_count=300,
)
```

**Fallback summary:**
```python
VideoSummary(
    summary="Видео 'Title' от Speaker",
    key_points=["Саммари недоступно из-за технической ошибки"],
    section="Обучение",  # Default
    tags=["ПШ", "SV"],   # Из метаданных
    access_level=1,
)
```

---

## Сериализация промежуточных результатов

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

## Тестирование

```bash
cd backend
python -m app.services.pipeline
```

Тесты включают:
- PipelineError создание
- Расчёт прогресса
- Fallback chunks/summary
- Parse метод
- Интеграционный тест (если доступны AI сервисы)
