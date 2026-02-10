---
doc_type: explanation
status: active
updated: 2026-02-10
audience: [developer, ai-agent]
tags:
  - architecture
  - pipeline
---

# БЗ2: Транскрибатор видео — архитектура

Техническая архитектура системы автоматической транскрипции и саммаризации видеозаписей.

> **Обзор системы:** [overview.md](overview.md) — цели, AI сервисы, быстрый старт
> **Детали:** [architecture/](architecture/) | [pipeline/](pipeline/) | [decisions/](decisions/)

---

## Архитектура системы

```
┌─────────────────────────────────────────────────────────────────┐
│  Клиенты                                                        │
│  ┌──────────────┐                                               │
│  │   Браузер    │                                               │
│  │   Web UI     │                                               │
│  └──────┬───────┘                                               │
└─────────┼───────────────────────────────────────────────────────┘
          │ HTTP / WebSocket
          │ Tailscale (100.64.0.1)
┌─────────┼───────────────────────────────────────────────────────┐
│  TrueNAS│SCALE                                                  │
│         ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  bz2-video-transcriber (:8801/:8802)                    │    │
│  │                                                         │    │
│  │  ┌─────────┐  ┌────────────┐  ┌────────────┐            │    │
│  │  │ Web UI  │  │  FastAPI   │  │  Pipeline  │            │    │
│  │  │ (React) │◄─┤  Backend   │◄─┤  (v0.47+)  │            │    │
│  │  └─────────┘  └─────┬──────┘  │            │            │    │
│  │                     │         │ 1.Parse    │            │    │
│  │                     │         │ 2.Transcribe─► Whisper  │    │
│  │                     │         │ 3.Clean ────► Claude    │    │
│  │                     │         │ 3.5.Slides ─► Claude V. │    │
│  │                     │         │ 4.Longread ─► Claude    │    │
│  │                     │         │ 5.Summary ──► Claude    │    │
│  │                     │         │ 6.Chunk (H2)            │    │
│  │                     │         │ 7.Save      │            │    │
│  │                     │         └──────┬─────┘            │    │
│  └─────────────────────┼────────────────┼──────────────────┘    │
│            ┌───────────┴────────────────┼───────────┐           │
│            ▼                            ▼           ▼           │
│  ┌──────────────────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │  faster-whisper (:9000)  │  │ Claude API  │  │ Ollama      │ │
│  │  large-v3-turbo          │  │ (через прокси)│  │ (:11434)    │ │
│  │  Задачи: транскрипция    │  │ sonnet/haiku│  │ (fallback)  │ │
│  └──────────────────────────┘  └─────────────┘  └─────────────┘ │
│                                                                 │
│  /mnt/main/work/bz2/video/ — inbox/, archive/, temp/, prompts/ │
│  GPU: RTX 5070 Ti 16GB (Whisper only, LLM → облако)             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Компоненты

| Компонент | Технология | Назначение |
|-----------|------------|------------|
| **Web UI** | React + Vite + TanStack Query + Tailwind | Интерфейс управления |
| **Backend** | FastAPI + SSE | API, оркестрация |
| **ClaudeClient** | Anthropic SDK | Основной LLM провайдер |
| **OllamaClient** | HTTP → Ollama API | Резервный LLM провайдер |
| **WhisperClient** | HTTP → faster-whisper API | Транскрипция видео |
| **ProcessingStrategy** | Автовыбор провайдера | Выбор LLM по имени модели |
| **PipelineOrchestrator** | Stage registry + DAG | Координация этапов |
| **StageResultCache** | Файловая система | Версионирование результатов |

---

## Pipeline

```
Video + [Slides] → Parse → Whisper → Clean ─┬─→ [Slides] → Longread → Summary → Chunk (H2) → Save (educational)
                                            └─→ [Slides] → Story → Chunk (H2) → Save (leadership)
```

- **EDUCATIONAL** → longread.md + summary.md
- **LEADERSHIP** → story.md (8 блоков)
- **Chunk** — детерминистический (H2 парсинг, без LLM), выполняется ПОСЛЕ longread/story
- **Slides** — опционально, между clean и longread/story

> Детали: [pipeline/](pipeline/) (14 документов) | [pipeline/stages.md](pipeline/stages.md) — stage абстракция

---

## Режимы обработки (v0.56+)

| Режим | Компонент | Описание |
|-------|-----------|----------|
| **auto** | `AutoProcessingCompact` | Компактный UI, автоматическое выполнение |
| **step** | `StepByStep` | Split view, ручное управление шагами |

Общая логика: `usePipelineProcessor` hook (`frontend/src/hooks/usePipelineProcessor.ts`).

---

## Ключевые решения

- **v0.29+:** Claude — default для всех LLM операций, fallback удалён ([ADR-007](decisions/007-remove-fallback-use-claude.md))
- **v0.25+:** Chunk детерминистический (H2 парсинг), без LLM
- **v0.14+:** Stage абстракция — новые этапы без изменения оркестратора ([ADR-001](decisions/001-stage-abstraction.md))
- **v0.42+:** Расширенные метрики (tokens, cost, time) ([ADR-009](decisions/009-extended-metrics.md))

---

## Связанные документы

| Документ | Описание |
|----------|----------|
| [architecture/](architecture/) | Индекс архитектурной документации |
| [pipeline/](pipeline/) | Детальный pipeline (14 документов) |
| [decisions/](decisions/) | Architecture Decision Records (13 ADR) |
| [api-reference.md](api-reference.md) | HTTP API endpoints |
| [configuration.md](configuration.md) | Конфигурация моделей, промптов, pricing |
| [deployment.md](deployment.md) | Развёртывание и Docker |
| [data-formats.md](data-formats.md) | Форматы файлов и метрик |
