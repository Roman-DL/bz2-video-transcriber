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
updated: 2025-01-09
status: mvp-ready
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
| [pipeline/](pipeline/) | Детальный pipeline (6 этапов) |
| [web-ui.md](web-ui.md) | Web интерфейс |
| [deployment.md](deployment.md) | Развёртывание, Docker, доступ |
| [data-formats.md](data-formats.md) | Форматы файлов, конфигурация |
| [api-reference.md](api-reference.md) | HTTP API для Ollama и Whisper |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Процесс разработки |

---

## Архитектура системы

### Общая схема

```
┌─────────────────────────────────────────────────────────────────┐
│  Клиенты                                                        │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │   Браузер    │  │  Mac (Ollama)│                             │
│  │   Web UI     │  │   клиент     │                             │
│  └──────┬───────┘  └──────────────┘                             │
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
│  │  bz2-video-transcriber (:8801)                          │    │
│  │                                                         │    │
│  │  ┌─────────┐  ┌────────────┐  ┌────────────┐            │    │
│  │  │ Web UI  │  │  FastAPI   │  │  Pipeline  │            │    │
│  │  │ (React) │◄─┤  Backend   │◄─┤            │            │    │
│  │  └─────────┘  └─────┬──────┘  │ 1.Parser   │            │    │
│  │                     │         │ 2.Whisper ─┼──► API     │    │
│  │                     │         │ 3.Cleaner ─┼──► API     │    │
│  │                     │         │ 4.Chunker ─┼──► API     │    │
│  │                     │         │ 5.Summary ─┼──► API     │    │
│  │                     │         │ 6.Saver    │            │    │
│  │                     │         └──────┬─────┘            │    │
│  └─────────────────────┼────────────────┼──────────────────┘    │
│                        │                │                       │
│            ┌───────────┴────────────────┴───────────┐           │
│            │                                        │           │
│            ▼                                        ▼           │
│  ┌──────────────────────────┐    ┌──────────────────────────┐   │
│  │  ollama (:11434)         │    │  faster-whisper (:9000)  │   │
│  │                          │    │                          │   │
│  │  ┌────────────────────┐  │    │  ┌────────────────────┐  │   │
│  │  │  qwen2.5:14b       │  │    │  │  large-v3          │  │   │
│  │  │  ~9 GB VRAM        │  │    │  │  ~3 GB VRAM        │  │   │
│  │  └────────────────────┘  │    │  └────────────────────┘  │   │
│  │                          │    │                          │   │
│  │  Задачи:                 │    │  Задачи:                 │   │
│  │  • Cleaner               │    │  • Транскрипция          │   │
│  │  • Chunker               │    │                          │   │
│  │  • Summarizer            │    │                          │   │
│  └──────────────────────────┘    └──────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Файловая система                                        │   │
│  │                                                          │   │
│  │  /mnt/main/work/bz2/video/                               │   │
│  │  ├── inbox/      ← Входящие видео (watcher мониторит)    │   │
│  │  ├── archive/    ← Обработанные (структура по датам)     │   │
│  │  └── temp/       ← Временные файлы обработки             │   │
│  │                                                          │   │
│  │  /mnt/apps-pool/dev/projects/bz2-video-transcriber/      │   │
│  │  └── config/     ← Промпты, глоссарий, настройки         │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  GPU: RTX 5070 Ti 16GB (shared: Whisper + Ollama)               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Компоненты

| Компонент | Технология | Назначение |
|-----------|------------|------------|
| **Web UI** | React + Vite + TanStack Query + Tailwind | Интерфейс управления |
| **Backend** | FastAPI + WebSocket | API, оркестрация |
| **Transcriber** | HTTP → faster-whisper API | Вызов внешнего сервиса |
| **Cleaner** | HTTP → Ollama API | Очистка транскрипта |
| **Chunker** | HTTP → Ollama API | Смысловое разбиение |
| **Summarizer** | HTTP → Ollama API | Саммаризация + классификация |

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
│   ├── pipeline/                # Детальный pipeline (6 этапов)
│   ├── data-formats.md          # Форматы файлов
│   ├── deployment.md            # Развёртывание
│   └── CONTRIBUTING.md          # Процесс разработки
│
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Настройки
│   │   ├── routers/
│   │   │   ├── files.py         # API для файлов
│   │   │   ├── jobs.py          # API для задач
│   │   │   ├── settings.py      # API настроек
│   │   │   └── websocket.py     # WebSocket прогресс
│   │   ├── services/
│   │   │   ├── parser.py        # Парсинг имени файла
│   │   │   ├── watcher.py       # Мониторинг inbox
│   │   │   ├── transcriber.py   # HTTP → Whisper API
│   │   │   ├── cleaner.py       # HTTP → Ollama API
│   │   │   ├── chunker.py       # HTTP → Ollama API
│   │   │   ├── summarizer.py    # HTTP → Ollama API
│   │   │   └── pipeline.py      # Оркестрация
│   │   └── models/
│   │       └── schemas.py       # Pydantic модели
│   └── requirements.txt
│
├── frontend/
│   ├── Dockerfile               # Docker образ (node build → nginx)
│   ├── nginx.conf               # Proxy для API и WebSocket
│   ├── package.json
│   ├── vite.config.ts           # Vite + proxy + path alias
│   ├── tailwind.config.js
│   └── src/
│       ├── App.tsx              # Главный компонент
│       ├── main.tsx
│       ├── index.css            # Tailwind imports
│       ├── api/
│       │   ├── types.ts         # TypeScript типы (из backend schemas)
│       │   ├── client.ts        # Axios instance
│       │   ├── websocket.ts     # WebSocket hook
│       │   └── hooks/           # TanStack Query hooks
│       └── components/
│           ├── layout/          # Header, Layout
│           ├── common/          # Button, Card, Badge, ProgressBar
│           ├── services/        # ServiceStatus (Whisper/Ollama)
│           ├── inbox/           # InboxList, VideoItem
│           ├── jobs/            # JobList, JobCard
│           ├── processing/      # ProcessingModal, FullPipeline, StepByStep
│           └── results/         # MetadataView, TranscriptView, etc.
│
├── config/
│   ├── prompts/
│   │   ├── cleaner.md
│   │   ├── chunker.md
│   │   └── summarizer.md
│   ├── glossary.yaml
│   └── events.yaml
│
├── docker-compose.yml
├── Dockerfile
├── nginx.conf
└── scripts/
    └── deploy.sh
```

---

## API Endpoints

### Inbox & Jobs

| Method | Endpoint | Описание |
|--------|----------|----------|
| GET | `/api/inbox` | Список видео в inbox |
| GET | `/api/jobs` | Список всех задач |
| GET | `/api/jobs/{id}` | Статус задачи |
| POST | `/api/process` | Запуск полного pipeline |

### Step-by-step (пошаговый режим)

| Method | Endpoint | Описание |
|--------|----------|----------|
| POST | `/api/step/parse` | Парсинг метаданных |
| POST | `/api/step/transcribe` | Транскрипция (Whisper) |
| POST | `/api/step/clean` | Очистка текста |
| POST | `/api/step/chunk` | Разбиение на чанки |
| POST | `/api/step/summarize` | Саммаризация |
| POST | `/api/step/save` | Сохранение в архив |

### Health

| Method | Endpoint | Описание |
|--------|----------|----------|
| GET | `/health` | Статус приложения |
| GET | `/health/services` | Статус AI сервисов (Whisper, Ollama) |

### WebSocket

| Endpoint | Описание |
|----------|----------|
| `/ws/{job_id}` | Прогресс задачи в реальном времени |

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

## Ресурсы

- [faster-whisper](https://github.com/guillaumekln/faster-whisper)
- [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Qwen2.5](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct)
