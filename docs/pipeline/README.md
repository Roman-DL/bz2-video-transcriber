# Pipeline обработки видео

> Детальное описание этапов обработки видео от inbox до готовых файлов для БЗ 2.0.

## Схема Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                      VIDEO PROCESSING PIPELINE                  │
│                                                                 │
│           Координируется PipelineOrchestrator                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐       │
│  │ 1.PARSE │───▶│2.WHISPER│───▶│3.CLEAN  │───▶│4.CHUNK  │──┐    │
│  │ filename│    │transcr. │    │ + gloss │    │semantic │  │    │
│  └─────────┘    └─────────┘    └─────────┘    └────┬────┘  │    │
│                                                    │       │    │
│                                               параллельно  │    │
│                                                    │       │    │
│                              ┌─────────┐    ┌─────┴───┐    │    │
│                              │6.SAVE   │◀───│5.SUMMAR.│◀───┘    │
│                              │ files   │    │ + class │         │
│                              └─────────┘    └─────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Этапы

| # | Этап | Документ | Инструмент | Вход | Выход |
|---|------|----------|------------|------|-------|
| 1 | Parse Filename | [01-parse.md](01-parse.md) | Python regex | `*.mp4` filename | `VideoMetadata` |
| 2 | Transcribe | [02-transcribe.md](02-transcribe.md) | Whisper API | `*.mp4` file | `RawTranscript` |
| 3 | Clean | [03-clean.md](03-clean.md) | Ollama + Glossary | `RawTranscript` | `CleanedTranscript` |
| 4 | Chunk | [04-chunk.md](04-chunk.md) | Ollama | `CleanedTranscript` | `TranscriptChunks` |
| 5 | Summarize | [05-summarize.md](05-summarize.md) | Ollama | `CleanedTranscript` | `Summary` + classification |
| 6 | Save | [06-save.md](06-save.md) | Python | All data | Files in archive |

## Оркестрация и API

| Компонент | Документ | Описание |
|-----------|----------|----------|
| PipelineOrchestrator | [07-orchestrator.md](07-orchestrator.md) | Координация этапов, progress callback, error handling |
| FastAPI | [08-api.md](08-api.md) | HTTP API, WebSocket, пошаговый режим |

## Полный Pipeline Flow

```python
from app.services.pipeline import PipelineOrchestrator

async def process_video(video_path: Path) -> ProcessingResult:
    """Полный pipeline обработки видео."""
    orchestrator = PipelineOrchestrator()
    return await orchestrator.process(video_path)


# С отслеживанием прогресса
async def process_with_progress(video_path: Path) -> ProcessingResult:
    """Pipeline с callback для UI."""

    async def on_progress(status, progress, message):
        print(f"[{status.value}] {progress:.0f}% - {message}")

    orchestrator = PipelineOrchestrator()
    return await orchestrator.process(video_path, progress_callback=on_progress)


# Пошаговый режим (для тестирования промптов)
async def process_step_by_step(video_path: Path) -> ProcessingResult:
    """Пошаговое выполнение с возможностью повторения этапов."""
    orchestrator = PipelineOrchestrator()

    # Тяжёлые этапы — один раз
    metadata = orchestrator.parse(video_path)
    raw = await orchestrator.transcribe(video_path)
    cleaned = await orchestrator.clean(raw, metadata)
    chunks = await orchestrator.chunk(cleaned, metadata)

    # Тестируем разные промпты
    summary = await orchestrator.summarize(cleaned, metadata, "summarizer_v2")

    # Сохраняем
    files = await orchestrator.save(metadata, raw, chunks, summary)

    return ProcessingResult(
        video_id=metadata.video_id,
        archive_path=metadata.archive_path,
        chunks_count=chunks.total_chunks,
        duration_seconds=raw.duration_seconds,
        files_created=files,
    )
```

## Связанные документы

- [architecture.md](../architecture.md) — схема системы, компоненты
- [data-formats.md](../data-formats.md) — форматы файлов
- [api-reference.md](../api-reference.md) — HTTP API сервисов
- [error-handling.md](error-handling.md) — обработка ошибок
