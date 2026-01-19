# Pipeline обработки видео

> Детальное описание этапов обработки видео от inbox до готовых файлов для БЗ 2.0.

## Схема Pipeline

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       VIDEO PROCESSING PIPELINE                           │
│                                                                           │
│            Координируется PipelineOrchestrator                            │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────────────┐         │
│  │ 1.PARSE │───▶│2.WHISPER│───▶│3.CLEAN  │───▶│ OUTLINE         │         │
│  │ filename│    │transcr. │    │ + gloss │    │ EXTRACTION      │         │
│  └─────────┘    └─────────┘    └─────────┘    │ (для >10K chars)│         │
│                                               └────────┬────────┘         │
│                                                        │                  │
│                                          ┌─────────────▼────────┐         │
│                                          │    TranscriptOutline │         │
│                                          │      (shared)        │         │
│                                          └─────────┬────────────┘         │
│                                                    │                      │
│                                               ┌────▼────┐                 │
│                                               │4.CHUNK  │                 │
│                                               │semantic │                 │
│                                               └────┬────┘                 │
│                                                    │                      │
│                                               ┌────▼────┐                 │
│                                               │5.LONGRD │                 │
│                                               │map-red. │                 │
│                                               └────┬────┘                 │
│                                                    │                      │
│                                               ┌────▼────┐                 │
│                                               │6.SUMMAR.│                 │
│                                               │конспект │                 │
│                                               └────┬────┘                 │
│                                                    │                      │
│                                               ┌────▼────┐                 │
│                                               │ 7.SAVE  │                 │
│                                               │  files  │                 │
│                                               └─────────┘                 │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

## Этапы

| # | Этап | Документ | Инструмент | Вход | Выход |
|---|------|----------|------------|------|-------|
| 1 | Parse Filename | [01-parse.md](01-parse.md) | Python regex | `*.mp4` filename | `VideoMetadata` |
| 2 | Transcribe | [02-transcribe.md](02-transcribe.md) | Whisper API | `*.mp4` file | `RawTranscript` |
| 3 | Clean | [03-clean.md](03-clean.md) | Ollama + Glossary | `RawTranscript` | `CleanedTranscript` |
| — | Outline | (часть pipeline) | Ollama | `CleanedTranscript` | `TranscriptOutline` |
| 4 | Chunk | [04-chunk.md](04-chunk.md) | Ollama | `CleanedTranscript` + Outline | `TranscriptChunks` |
| 5 | Longread | [05-longread.md](05-longread.md) | Ollama | Chunks + Outline | `Longread` |
| 6 | Summarize | [06-summarize.md](06-summarize.md) | Ollama | Longread | `Summary` |
| 7 | Save | [07-save.md](07-save.md) | Python | All data | Files in archive |

> **Outline Extraction:** Выполняется только для больших текстов (>10K символов). Для маленьких — longread и summary работают с полным текстом.

## Оркестрация и API

| Компонент | Документ | Описание |
|-----------|----------|----------|
| PipelineOrchestrator | [08-orchestrator.md](08-orchestrator.md) | Координация этапов, progress callback |
| FastAPI | [09-api.md](09-api.md) | HTTP API, WebSocket, пошаговый режим |

## Step-by-step режим

Для тестирования промптов доступен пошаговый режим через `/api/steps/*`. Каждый этап можно запустить отдельно:

- `/api/steps/parse` — парсинг метаданных
- `/api/steps/transcribe` — транскрипция
- `/api/steps/clean` — очистка
- `/api/steps/chunk` — чанкирование (сам извлекает outline)
- `/api/steps/longread` — генерация лонгрида из чанков
- `/api/steps/summarize` — генерация конспекта из лонгрида
- `/api/steps/save` — сохранение

## Связанные документы

- [architecture.md](../architecture.md) — схема системы, компоненты
- [data-formats.md](../data-formats.md) — форматы файлов
- [api-reference.md](../api-reference.md) — HTTP API сервисов
- [error-handling.md](error-handling.md) — обработка ошибок
