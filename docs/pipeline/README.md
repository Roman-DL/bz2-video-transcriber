---
doc_type: reference
status: active
updated: 2026-02-20
audience: [developer, ai-agent]
tags:
  - pipeline
---

# Pipeline обработки видео

> Детальное описание этапов обработки видео от inbox до готовых файлов для БЗ 2.0.

## Схема Pipeline

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                       VIDEO PROCESSING PIPELINE (v0.51+)                      │
│                                                                               │
│            Координируется PipelineOrchestrator                                │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐                     │
│  │ 1.PARSE │───▶│2.WHISPER│───▶│3.CLEAN  │───▶│4.SLIDES │ (опционально)      │
│  │ filename│    │transcr. │    │ + gloss │    │ extract │                     │
│  └─────────┘    └─────────┘    └─────────┘    └────┬────┘                     │
│                                                    │                          │
│            ┌───────────────────────────────────────┼───────────────────┐      │
│            │                                       │                   │      │
│            │ EDUCATIONAL                           │ LEADERSHIP        │      │
│            │ (content_type)                        │ (content_type)    │      │
│            │                                       │                   │      │
│            │     ┌────▼────┐                  ┌────▼────┐              │      │
│            │     │5.LONGRD │                  │5b.STORY │              │      │
│            │     │ + слайды│                  │8 blocks │              │      │
│            │     └────┬────┘                  └────┬────┘              │      │
│            │          │                            │                   │      │
│            │     ┌────▼────┐                  ┌────▼────┐              │      │
│            │     │6.SUMMAR.│                  │6.CHUNK  │              │      │
│            │     │конспект │                  │ H2 parse│              │      │
│            │     └────┬────┘                  └────┬────┘              │      │
│            │          │                            │                   │      │
│            │     ┌────▼────┐                       │                   │      │
│            │     │7.CHUNK  │                       │                   │      │
│            │     │ H2 parse│                       │                   │      │
│            │     └────┬────┘                       │                   │      │
│            │          │                            │                   │      │
│            └──────────┼────────────────────────────┼───────────────────┘      │
│                       │                            │                          │
│                       └────────────┬───────────────┘                          │
│                                    │                                          │
│                               ┌────▼────┐                                     │
│                               │ 8.SAVE  │                                     │
│                               │  files  │                                     │
│                               └─────────┘                                     │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

> **v0.25+:** Chunk — детерминированный (парсинг H2 заголовков), выполняется ПОСЛЕ Longread/Story.
> **v0.51+:** Slides — опциональный шаг извлечения текста со слайдов (если пользователь прикрепил файлы).
> **v0.64+:** MD-файлы — готовые транскрипты из MacWhisper, Whisper пропускается, текст загружается напрямую.

## Этапы

| # | Этап | Документ | Инструмент | Вход | Выход |
|---|------|----------|------------|------|-------|
| 1 | Parse Filename | [01-parse.md](01-parse.md) | Python regex | `video_path` (Path) | `VideoMetadata` |
| 2 | Transcribe | [02-transcribe.md](02-transcribe.md) | Whisper API / File Load | `VideoMetadata`, `video_path` | `Tuple[RawTranscript, Path \| None]` |
| 3 | Clean | [03-clean.md](03-clean.md) | Claude + Glossary | `RawTranscript`, `VideoMetadata` | `CleanedTranscript` |
| 4 | **Slides** | (опционально, API) | Claude Vision | Изображения/PDF | `SlidesExtractionResult` |
| 5 | Longread | [05-longread.md](05-longread.md) | Claude | `CleanedTranscript`, `VideoMetadata` | `Longread` (EDUCATIONAL) |
| 5b | **Story** | [05b-story.md](05b-story.md) | Claude | `CleanedTranscript`, `VideoMetadata` | `Story` (LEADERSHIP) |
| 6 | Summarize | [06-summarize.md](06-summarize.md) | Claude | `CleanedTranscript`, `VideoMetadata` | `Summary` (EDUCATIONAL) |
| 7 | Chunk | [04-chunk.md](04-chunk.md) | Python (H2 parse) | `Longread` / `Story`, `VideoMetadata` | `TranscriptChunks` |
| 8 | Save | [07-save.md](07-save.md) | Python | All stage results | `list[str]` (filenames) |

> **v0.24+:** Summarize генерирует из `CleanedTranscript` (не из Longread) для доступа к полному контексту.
> **v0.29+:** Все LLM-этапы по умолчанию используют Claude (требуется `ANTHROPIC_API_KEY`).
> **Slides:** Опциональный шаг через отдельный API endpoint (`/api/step/slides`), не входит в stage abstraction.
> **Chunk:** Детерминированный парсинг H2-заголовков (без LLM).

## Оркестрация и API

| Компонент | Документ | Описание |
|-----------|----------|----------|
| Stage Abstraction | [stages.md](stages.md) | Базовые классы, StageContext, StageRegistry |
| PipelineOrchestrator | [08-orchestrator.md](08-orchestrator.md) | Координация этапов, progress callback |
| FastAPI | [09-api.md](09-api.md) | HTTP API, WebSocket, пошаговый режим |

## Step-by-step режим

Для тестирования промптов доступен пошаговый режим через `/api/step/*`. Каждый этап можно запустить отдельно:

- `/api/step/parse` — парсинг метаданных
- `/api/step/transcribe` — транскрипция
- `/api/step/clean` — очистка
- `/api/step/slides` — извлечение текста со слайдов (опционально)
- `/api/step/longread` — генерация лонгрида (EDUCATIONAL)
- `/api/step/story` — генерация истории (LEADERSHIP)
- `/api/step/summarize` — генерация конспекта из лонгрида
- `/api/step/chunk` — детерминированное чанкирование (H2 parse)
- `/api/step/save` — сохранение

## Связанные документы

- [ARCHITECTURE.md](../ARCHITECTURE.md) — схема системы, компоненты
- [data-formats.md](../data-formats.md) — форматы файлов
- [api-reference.md](../api-reference.md) — HTTP API сервисов
- [error-handling.md](error-handling.md) — обработка ошибок

### Architecture Decision Records

- [ADR-002: Pipeline Decomposition](../decisions/002-pipeline-decomposition.md) — декомпозиция на модули
- [ADR-004: AI Client Abstraction](../decisions/004-ai-client-abstraction.md) — OllamaClient, ClaudeClient
- [ADR-005: Result Caching](../decisions/005-result-caching.md) — версионирование результатов
- [ADR-006: Cloud Model Integration](../decisions/006-cloud-model-integration.md) — ProcessingStrategy
- [ADR-007: Remove Fallback, Use Claude](../decisions/007-remove-fallback-use-claude.md) — Claude по умолчанию (v0.29+)
- [ADR-010: Slides Integration](../decisions/010-slides-integration.md) — извлечение текста со слайдов (v0.51+)
