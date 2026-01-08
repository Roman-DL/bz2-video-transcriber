# bz2-video-transcriber

Система автоматической транскрипции и саммаризации видеозаписей обучающих мероприятий для БЗ 2.0.

## Quick Start

```bash
# Проверить что AI сервисы запущены
curl http://100.64.0.1:11434/api/version  # Ollama
curl http://100.64.0.1:9000/health         # Whisper

# Запуск
docker-compose up -d

# Web UI
http://localhost:8801
````

## Документация

|Документ|Описание|
|---|---|
|[docs/architecture.md](https://claude.ai/chat/docs/architecture.md)|Схема системы, компоненты, интеграция|
|[docs/pipeline.md](https://claude.ai/chat/docs/pipeline.md)|6-этапный pipeline обработки|
|[docs/api-reference.md](https://claude.ai/chat/docs/api-reference.md)|HTTP API для Ollama и Whisper|
|[docs/data-formats.md](https://claude.ai/chat/docs/data-formats.md)|Форматы файлов, интеграция с БЗ 2.0|
|[docs/llm-prompts.md](https://claude.ai/chat/docs/llm-prompts.md)|Промпты для Ollama|
|[DEPLOYMENT.md](https://claude.ai/chat/DEPLOYMENT.md)|Развёртывание на TrueNAS|

## Архитектура

```
Video → Parse → Whisper API → Clean → Chunk → Summarize → Save
                    ↓            ↓       ↓         ↓
               HTTP :9000    ←── Ollama API ──→ HTTP :11434
```

**Ключевые компоненты:**

- **Backend:** FastAPI (оркестрация, API)
- **Frontend:** React + Vite + Zustand
- **AI сервисы:** Ollama + Whisper (внешние, через HTTP)

## AI сервисы (внешние)

> Приложение использует AI сервисы, развёрнутые на сервере. Они должны быть запущены.

|Сервис|URL|Назначение|
|---|---|---|
|**Ollama**|http://100.64.0.1:11434|Очистка, chunking, саммаризация|
|**Whisper**|http://100.64.0.1:9000|Транскрипция видео|

**Модели:**

- Ollama: `qwen2.5:14b` (русский язык, 32K контекст)
- Whisper: `large-v3` (лучшее качество)

**Примеры вызовов:** см. [docs/api-reference.md](https://claude.ai/chat/docs/api-reference.md)

## Структура проекта

```
bz2-video-transcriber/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI
│   │   ├── services/
│   │   │   ├── parser.py        # Парсинг имени файла
│   │   │   ├── transcriber.py   # HTTP → Whisper API
│   │   │   ├── cleaner.py       # HTTP → Ollama API
│   │   │   ├── chunker.py       # HTTP → Ollama API
│   │   │   ├── summarizer.py    # HTTP → Ollama API
│   │   │   └── pipeline.py      # Оркестрация
│   │   └── models/schemas.py
│   └── requirements.txt
├── frontend/
│   └── src/
├── config/
│   ├── prompts/                 # cleaner.md, chunker.md, summarizer.md
│   ├── glossary.yaml            # Терминология Herbalife
│   └── events.yaml              # Типы мероприятий
├── docs/
├── DEPLOYMENT.md
└── docker-compose.yml
```

## Входящие файлы

**Формат имени:**

```
{дата} {тип}.{поток} {тема} ({спикер}).mp4

Пример:
2025.04.07 ПШ.SV Группа поддержки (Светлана Дмитрук).mp4
```

## Выходные файлы

```
/archive/{год}/{месяц}/{тип}.{поток}/{тема} ({спикер})/
├── {оригинал}.mp4
├── transcript_chunks.json    # → RAG Search
├── summary.md                # → File Search
└── transcript_raw.txt        # Backup
```

## Интеграция с БЗ 2.0

1. Транскрибатор создаёт файлы в `/archive/`
2. Оператор копирует в Google Drive `/БЗ2/Видео/`
3. BZ2_Indexer автоматически индексирует

## Конфигурация

**Переменные окружения:**

```bash
OLLAMA_URL=http://192.168.1.152:11434
WHISPER_URL=http://192.168.1.152:9000
LLM_MODEL=qwen2.5:14b
WHISPER_LANGUAGE=ru
```

## Разработка

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8801

# Frontend
cd frontend && npm install && npm run dev
```

## Деплой

См. [DEPLOYMENT.md](https://claude.ai/chat/DEPLOYMENT.md) для развёртывания на TrueNAS.

```bash
./scripts/deploy.sh
```

