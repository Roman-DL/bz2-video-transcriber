---
related:
  - "[[Среда разработки — MOC]]"
  - "[[Архитектура среды разработки]]"
  - "[[Архитектура локальных AI сервисов]]"
  - "[[Локальные AI сервисы — MOC]]"
  - "[[Домашний сервер — MOC]]"
  - "[[Конфигурация сервера]]"
created: 2025-01-08
tags:
  - homelab
  - development
  - video
  - transcription
  - ai
  - whisper
  - ollama
  - knowledge-base
updated: 2025-01-23
status: production
priority: high
---

# БЗ2: Транскрибатор видео — архитектура

Техническая архитектура системы автоматической транскрипции и саммаризации видеозаписей.

> **Обзор системы:** [overview.md](overview.md) — цели, AI сервисы, быстрый старт

---

## Документация

| Документ | Описание |
|----------|----------|
| [overview.md](overview.md) | Обзор системы, цели, AI сервисы |
| [pipeline/](pipeline/) | Детальный pipeline (7 этапов) |
| [configuration.md](configuration.md) | Конфигурация моделей, промптов, pricing |
| [data-formats.md](data-formats.md) | Форматы файлов, метрики (v0.42+) |
| [api-reference.md](api-reference.md) | HTTP API |
| [deployment.md](deployment.md) | Развёртывание, Docker, доступ |
| [adr/](adr/) | Architecture Decision Records |

---

## Архитектура системы

### Общая схема

```
┌─────────────────────────────────────────────────────────────────┐
│  Клиенты                                                        │
│                                                                 │
│  ┌──────────────┐                                               │
│  │   Браузер    │                                               │
│  │   Web UI     │                                               │
│  └──────┬───────┘                                               │
│         │                                                       │
└─────────┼───────────────────────────────────────────────────────┘
          │ HTTP / WebSocket
          │ Tailscale (100.64.0.1)
          │
┌─────────┼───────────────────────────────────────────────────────┐
│  TrueNAS│SCALE                                                  │
│         │                                                       │
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
│                        │                │                       │
│            ┌───────────┴────────────────┼───────────┐           │
│            │                            │           │           │
│            ▼                            ▼           ▼           │
│  ┌──────────────────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │  faster-whisper (:9000)  │  │ Claude API  │  │ Ollama      │ │
│  │                          │  │ (через прокси)│  │ (:11434)    │ │
│  │  ┌────────────────────┐  │  │             │  │ (fallback)  │ │
│  │  │  large-v3-turbo    │  │  │ Модели:     │  │             │ │
│  │  │  ~3 GB VRAM        │  │  │ • sonnet-4.5│  │ Модели:     │ │
│  │  └────────────────────┘  │  │ • haiku-4.5 │  │ • qwen2.5   │ │
│  │                          │  │ • opus-4.5  │  │ • gemma2    │ │
│  │  Задачи:                 │  │             │  │             │ │
│  │  • Транскрипция          │  │ Задачи:     │  │ Задачи:     │ │
│  │  • Confidence/duration   │  │ • Clean     │  │ (опц.)      │ │
│  │                          │  │ • Longread  │  │             │ │
│  └──────────────────────────┘  │ • Summary   │  └─────────────┘ │
│                                │ • Story     │                  │
│                                └─────────────┘                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Файловая система                                        │   │
│  │                                                          │   │
│  │  /mnt/main/work/bz2/video/                               │   │
│  │  ├── inbox/      ← Входящие видео                        │   │
│  │  ├── archive/    ← Обработанные (по датам/событиям)      │   │
│  │  │   └── .cache/ ← Stage cache (версионирование)         │   │
│  │  ├── temp/       ← Временные файлы                       │   │
│  │  └── prompts/    ← Внешние промпты (v0.30+)              │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  GPU: RTX 5070 Ti 16GB (Whisper only, LLM → облако)             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Компоненты

| Компонент | Технология | Назначение |
|-----------|------------|------------|
| **Web UI** | React + Vite + TanStack Query + Tailwind | Интерфейс управления |
| **Backend** | FastAPI + SSE | API, оркестрация |
| **WhisperClient** | HTTP → faster-whisper API (v0.27+) | Транскрипция видео |
| **ClaudeClient** | Anthropic SDK (v0.19+) | Основной LLM провайдер |
| **OllamaClient** | HTTP → Ollama API | Резервный LLM провайдер |
| **ProcessingStrategy** | Автовыбор провайдера (v0.19+) | Выбор LLM по имени модели |
| **TranscriptCleaner** | ClaudeClient (v0.29+) | Очистка транскрипта |
| **SlidesExtractor** | ClaudeClient Vision (v0.51+) | Извлечение текста со слайдов |
| **LongreadGenerator** | ClaudeClient | Генерация развёрнутого текста |
| **SummaryGenerator** | ClaudeClient | Генерация конспекта |
| **StoryGenerator** | ClaudeClient (v0.23+) | Генерация лидерских историй |
| **H2Chunker** | Deterministic (v0.25+) | Разбиение по H2 заголовкам |
| **StageResultCache** | Файловая система (v0.18+) | Версионирование результатов |

---

## Структура проекта

```
bz2-video-transcriber/
├── CLAUDE.md                    # Entry point для Claude Code
├── docs/
│   ├── README.md                # Навигация по документации
│   ├── overview.md              # Обзор системы
│   ├── architecture.md          # Этот документ
│   ├── web-ui.md                # Документация Web UI
│   ├── pipeline/                # Детальный pipeline
│   ├── data-formats.md          # Форматы файлов, метрики (v0.42+)
│   ├── configuration.md         # Конфигурация моделей и промптов
│   ├── deployment.md            # Развёртывание
│   ├── adr/                     # Architecture Decision Records
│   └── CONTRIBUTING.md          # Процесс разработки
│
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings (Pydantic)
│   │   ├── api/
│   │   │   ├── routes.py        # API: inbox, archive
│   │   │   ├── step_routes.py   # Step API с SSE прогрессом
│   │   │   ├── cache_routes.py  # Cache API (v0.18+)
│   │   │   └── prompt_routes.py # Prompts API (v0.31+)
│   │   ├── services/
│   │   │   ├── ai_clients/      # AI клиенты (v0.17+)
│   │   │   │   ├── base.py      # BaseAIClient, ChatUsage, исключения
│   │   │   │   ├── claude_client.py   # ClaudeClient (v0.19+)
│   │   │   │   ├── ollama_client.py   # OllamaClient
│   │   │   │   └── whisper_client.py  # WhisperClient (v0.27+)
│   │   │   ├── parser.py              # Парсинг имени файла
│   │   │   ├── cleaner.py             # TranscriptCleaner → AI client
│   │   │   ├── slides_extractor.py    # SlidesExtractor → Claude Vision (v0.51+)
│   │   │   ├── longread_generator.py  # LongreadGenerator → AI client
│   │   │   ├── summary_generator.py   # SummaryGenerator → AI client
│   │   │   ├── story_generator.py     # StoryGenerator (v0.23+)
│   │   │   ├── saver.py               # Сохранение в архив
│   │   │   ├── pipeline/              # Pipeline package (v0.15+)
│   │   │   │   ├── orchestrator.py    # PipelineOrchestrator
│   │   │   │   ├── progress_manager.py # STAGE_WEIGHTS
│   │   │   │   ├── config_resolver.py # Override моделей
│   │   │   │   ├── stage_cache.py     # StageResultCache (v0.18+)
│   │   │   │   └── processing_strategy.py # ProcessingStrategy (v0.19+)
│   │   │   └── stages/                # Stage абстракция (v0.14+)
│   │   │       ├── base.py            # BaseStage, StageContext, Registry
│   │   │       ├── parse_stage.py
│   │   │       ├── transcribe_stage.py
│   │   │       ├── clean_stage.py
│   │   │       ├── chunk_stage.py     # H2Chunker (deterministic)
│   │   │       ├── longread_stage.py
│   │   │       ├── summarize_stage.py
│   │   │       ├── story_stage.py     # StoryStage (v0.23+)
│   │   │       └── save_stage.py
│   │   ├── utils/                     # Shared utilities (v0.16+)
│   │   │   ├── json_utils.py          # extract_json(), parse_json_safe()
│   │   │   ├── token_utils.py         # estimate_tokens()
│   │   │   ├── chunk_utils.py         # validate_cyrillic_ratio()
│   │   │   ├── media_utils.py         # get_media_duration() (v0.28+)
│   │   │   ├── pricing_utils.py       # calculate_cost() (v0.42+)
│   │   │   ├── pdf_utils.py           # pdf_to_images(), pdf_page_count() (v0.51+)
│   │   │   └── h2_chunker.py          # H2-based chunking (v0.25+)
│   │   └── models/
│   │       ├── schemas.py       # Pydantic модели, TokensUsed (v0.42+)
│   │       └── cache.py         # CacheManifest, CacheEntry (v0.18+)
│   └── requirements.txt
│
├── frontend/
│   ├── Dockerfile               # Docker образ (node build → nginx)
│   ├── nginx.conf               # Proxy для API
│   ├── package.json             # Версия (v0.47+)
│   ├── vite.config.ts           # Vite + proxy + path alias
│   ├── tailwind.config.js
│   └── src/
│       ├── App.tsx              # Главный компонент (Dashboard)
│       ├── main.tsx
│       ├── index.css            # Tailwind imports
│       ├── api/
│       │   ├── types.ts         # TypeScript типы (метрики v0.44+)
│       │   ├── client.ts        # Axios instance
│       │   └── hooks/           # TanStack Query hooks
│       ├── utils/               # Shared utilities (v0.35+)
│       │   ├── modelUtils.ts    # getDisplayModelName()
│       │   └── formatUtils.ts   # formatTime(), formatCost() (v0.44+)
│       └── components/
│           ├── layout/          # Header, Layout
│           ├── common/          # Button, Card, Modal, ProgressBar
│           │   ├── ResultFooter.tsx    # Метрики (v0.45+)
│           │   └── InlineDiffView.tsx  # Diff view (v0.46+)
│           ├── services/        # ServiceStatus (Whisper/Claude)
│           ├── inbox/           # InboxList, VideoItem
│           ├── archive/         # ArchiveCatalog
│           ├── processing/      # ProcessingModal, StepByStep
│           ├── slides/          # SlidesAttachment, SlidesModal (v0.52+)
│           └── results/         # MetadataView, TranscriptView, SlidesResultView
│
├── config/
│   ├── models.yaml              # Модели, context profiles, pricing
│   ├── glossary.yaml            # Терминология Herbalife
│   ├── events.yaml              # Типы событий
│   └── prompts/                 # Промпты по этапам (v0.31+)
│       ├── cleaning/            # system.md, user.md
│       ├── slides/              # system.md, user.md (v0.51+)
│       ├── longread/            # system.md, instructions.md, template.md
│       ├── summary/
│       ├── story/
│       └── outline/
│
├── docker-compose.yml
├── Dockerfile
├── nginx.conf
└── scripts/
    └── deploy.sh
```

---

## API Endpoints

### Inbox & Archive

| Method | Endpoint | Описание |
|--------|----------|----------|
| GET | `/api/inbox` | Список видео в inbox |
| GET | `/api/archive` | Дерево папок архива |

### Step API (SSE прогресс)

| Method | Endpoint | Описание |
|--------|----------|----------|
| POST | `/api/step/parse` | Парсинг метаданных |
| POST | `/api/step/transcribe` | Транскрипция (Whisper) — SSE |
| POST | `/api/step/clean` | Очистка текста — SSE |
| POST | `/api/step/slides` | Извлечение текста со слайдов (v0.51+) — SSE |
| POST | `/api/step/chunk` | Разбиение на чанки — SSE |
| POST | `/api/step/longread` | Генерация лонгрида — SSE |
| POST | `/api/step/summarize` | Генерация конспекта — SSE |
| POST | `/api/step/save` | Сохранение в архив |

### Health

| Method | Endpoint | Описание |
|--------|----------|----------|
| GET | `/health` | Статус приложения |
| GET | `/health/services` | Статус AI сервисов (Whisper, Ollama) |

---

## Связанные документы

### Локальные AI сервисы
- [[Локальные AI сервисы — MOC]] — навигация
- [[Архитектура локальных AI сервисов]] — общая архитектура
- [[Установка Ollama на TrueNAS]] — сервер LLM
- [[Установка Whisper на TrueNAS]] — сервер транскрипции

### Среда разработки
- [[Среда разработки — MOC]] — навигация по dev-среде
- [[Архитектура среды разработки]] — общая концепция
- [[Установка Dockge]] — деплой через UI

### Инфраструктура
- [[Конфигурация сервера]] — спецификация железа
- [[Справочник сервисов]] — порты и адреса

---

## Pipeline Decomposition (v0.15+, updated v0.47)

Модуль `pipeline` декомпозирован на независимые компоненты с чёткими обязанностями:

```
┌────────────────────────────────────────────────────────────────┐
│                      PipelineOrchestrator                      │
│                    (координация этапов)                        │
└────────────┬───────────────────────────────────────────────────┘
             │
    ┌────────┼────────┬─────────────┬─────────────┬─────────────┐
    ▼        ▼        ▼             ▼             ▼             ▼
Progress  Config   Stage       Processing    Stage       AI Clients
Manager   Resolver Registry    Strategy      Cache       (Claude/Ollama)
```

| Компонент | Файл | Ответственность |
|-----------|------|-----------------|
| **PipelineOrchestrator** | `orchestrator.py` | Координация этапов, основной API |
| **ProgressManager** | `progress_manager.py` | STAGE_WEIGHTS, расчёт прогресса |
| **ConfigResolver** | `config_resolver.py` | Override моделей для step-by-step |
| **ProcessingStrategy** | `processing_strategy.py` | Автовыбор AI провайдера (v0.19+) |
| **StageResultCache** | `stage_cache.py` | Версионирование результатов (v0.18+) |

> **v0.29+:** FallbackFactory удалён. При ошибках LLM выбрасывается `PipelineError`.

**Принципы:**
- Single Responsibility: каждый модуль — одна обязанность
- Open/Closed: новые stages добавляются без изменения orchestrator
- Dependency Injection: компоненты через композицию

**Документация:**
- [adr/002-pipeline-decomposition.md](adr/002-pipeline-decomposition.md) — декомпозиция pipeline
- [adr/007-remove-fallback-use-claude.md](adr/007-remove-fallback-use-claude.md) — удаление fallback
- [adr/009-extended-metrics.md](adr/009-extended-metrics.md) — расширенные метрики (v0.42+)

---

## Stage Abstraction (v0.14+, updated v0.47)

Система абстракций для этапов обработки, позволяющая добавлять новые шаги без изменения оркестратора.

```
┌────────────────────────────────────────────────────────────────┐
│                        StageRegistry                           │
│                    (управление этапами)                        │
└────────────┬───────────────────────────────────────────────────┘
             │
    ┌────────┼────────┬────────┬───────────────────┬────────┐
    ▼        ▼        ▼        ▼                   ▼        ▼
  Parse  Transcribe  Clean  ┌───┴───┐            Chunk    Save
  Stage    Stage    Stage   │       │            Stage    Stage
    │        │        │     ▼       ▼          (H2 det.)
    │        │        │  Longread  Story
    │     Whisper  Claude  Stage    Stage
    │                │       │       │
    │                │  Summarize    │
    │                │   Stage       │
    │                │       │       │
    └────────────────┴───────┴───────┴─────────────────────┐
                                                          ▼
                                                   StageContext
                                             (метрики: tokens, cost)
```

**Pipeline (v0.25+):**
- `Parse → Transcribe → Clean → Longread/Story → Summary → Chunk (H2) → Save`

**Ветвление по content_type (v0.23+):**
- `EDUCATIONAL` → LongreadStage → SummarizeStage → ChunkStage → longread.md + summary.md
- `LEADERSHIP` → StoryStage → ChunkStage → story.md (8 блоков)

**Расширенные метрики (v0.42+):**
Каждый LLM-этап возвращает метрики в результате:
- `tokens_used` (TokensUsed: input, output, total)
- `cost` (USD, рассчитывается из pricing в models.yaml)
- `processing_time_sec`

**Основные классы:**
- `BaseStage` — абстрактный базовый класс для этапов
- `BaseStage.should_skip()` — условное выполнение по content_type
- `StageContext` — immutable контекст для передачи данных между этапами
- `StageRegistry` — реестр для управления этапами и построения pipeline

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

**Документация:**
- [pipeline/stages.md](pipeline/stages.md) — детальное описание
- [adr/001-stage-abstraction.md](adr/001-stage-abstraction.md) — обоснование решения

---

## Ресурсы

- [Anthropic Claude API](https://docs.anthropic.com/claude/reference/) — основной LLM провайдер
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) — транскрипция
- [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md) — резервный LLM
- [FastAPI](https://fastapi.tiangolo.com/) — backend framework
