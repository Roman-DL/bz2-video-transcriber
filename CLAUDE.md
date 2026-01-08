# bz2-video-transcriber

Система автоматической транскрипции и саммаризации видеозаписей для БЗ 2.0.

## Инструкции для Claude

- **Язык общения:** Русский
- **Язык кода:** Английский (имена переменных, функций, комментарии в коде)
- **Язык документации:** Русский

## Quick Start

```bash
# Проверить AI сервисы
curl http://100.64.0.1:11434/api/version  # Ollama
curl http://100.64.0.1:9000/health        # Whisper

# Запуск
docker-compose up -d

# Web UI
http://localhost:8801
```

## Архитектура

```
Video → Parse → Whisper → Clean → Chunk → Summarize → Save
```

## Документация

| Тема | Документ |
|------|----------|
| Обзор системы | [docs/architecture.md](docs/architecture.md) |
| Pipeline (этапы) | [docs/pipeline/](docs/pipeline/) |
| Форматы данных | [docs/data-formats.md](docs/data-formats.md) |
| API сервисов | [docs/api-reference.md](docs/api-reference.md) |
| Развёртывание | [docs/deployment.md](docs/deployment.md) |

## Структура проекта

```
backend/app/services/   # Сервисы pipeline
config/prompts/         # LLM промпты
config/glossary.yaml    # Терминология
```

## AI сервисы

| Сервис | URL | Модель |
|--------|-----|--------|
| Ollama | http://100.64.0.1:11434 | qwen2.5:14b |
| Whisper | http://100.64.0.1:9000 | large-v3 |

## Разработка

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8801

# Frontend
cd frontend && npm install && npm run dev
```

## Деплой

См. [docs/deployment.md](docs/deployment.md)
