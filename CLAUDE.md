# bz2-video-transcriber

Система автоматической транскрипции и саммаризации видеозаписей для БЗ 2.0.

## Инструкции для Claude

- **Язык общения:** Русский
- **Язык кода:** Английский (имена переменных, функций, комментарии в коде)
- **Язык документации:** Русский
- **Версионирование:** После коммита новых фич — ОБЯЗАТЕЛЬНО предложи обновить версию в `frontend/package.json`

## Документирование кода

При реализации функций следуй [гайдлайнам по документированию](docs/DOCUMENTATION_GUIDELINES.md):
- **Docstrings в коде** — обязательны для публичных методов (Google-style)
- **Внешняя документация** — только архитектура, интеграция, решения
- **Не дублируй код в docs** — ИИ читает код напрямую

## Quick Start

```bash
# Проверить AI сервисы
curl http://100.64.0.1:11434/api/version  # Ollama
curl http://100.64.0.1:9000/health        # Whisper

# Деплой на сервер (локальный docker-compose не работает!)
./scripts/deploy.sh

# Web UI
http://100.64.0.1:8802      # Frontend
http://100.64.0.1:8801      # Backend API
```

## Архитектура

```
Video → Parse → Whisper → Clean → Chunk → Summarize → Save
```

## Документация

| Тема | Документ |
|------|----------|
| Обзор системы | [docs/overview.md](docs/overview.md) |
| Архитектура | [docs/architecture.md](docs/architecture.md) |
| Pipeline (этапы) | [docs/pipeline/](docs/pipeline/) |
| Форматы данных | [docs/data-formats.md](docs/data-formats.md) |
| API сервисов | [docs/api-reference.md](docs/api-reference.md) |
| Развёртывание | [docs/deployment.md](docs/deployment.md) |
| Логирование | [docs/logging.md](docs/logging.md) |

## Структура проекта

```
backend/app/services/   # Сервисы pipeline
backend/app/api/        # FastAPI endpoints
frontend/src/           # React + Vite + Tailwind
config/prompts/         # LLM промпты
config/glossary.yaml    # Терминология
```

## AI сервисы

| Сервис | URL | Модель |
|--------|-----|--------|
| Ollama | http://100.64.0.1:11434 | qwen2.5:14b |
| Whisper | http://100.64.0.1:9000 | large-v3 |

## Разработка

### Особенности macOS

На macOS используй `python3` вместо `python`:

```bash
# Проверка синтаксиса Python
python3 -m py_compile backend/app/api/step_routes.py

# Установка зависимостей
cd backend && pip3 install -r requirements.txt

# Запуск сервера
python3 -m uvicorn app.main:app --reload --port 8801
```

### Backend

```bash
cd backend && pip3 install -r requirements.txt
python3 -m uvicorn app.main:app --reload --port 8801
```

### Frontend

```bash
cd frontend && npm install && npm run dev
```

## Деплой

**Локальный docker-compose не работает** — пути к данным (`/mnt/main/work/bz2/video`) существуют только на сервере.

```bash
./scripts/deploy.sh   # Единственный способ деплоя
```

Подробнее: [docs/deployment.md](docs/deployment.md)

## Версионирование

Версия отображается в веб-интерфейсе (`v0.1.0 • 10.01.26 15:30`). Дата/время обновляются автоматически при сборке.

**При значимых изменениях** предлагай обновить версию в `frontend/package.json`:
- **patch** (0.1.x) — баг-фиксы, мелкие правки
- **minor** (0.x.0) — новые фичи, заметные улучшения
- **major** (x.0.0) — ломающие изменения, крупные переработки

## Логирование

Система логирования с управлением через переменные окружения.

### Конфигурация

```bash
LOG_LEVEL=INFO                    # Общий уровень (DEBUG/INFO/WARNING/ERROR)
LOG_FORMAT=structured             # Формат: simple | structured
LOG_LEVEL_AI_CLIENT=DEBUG         # Per-module override
LOG_LEVEL_PIPELINE=INFO
LOG_LEVEL_TRANSCRIBER=INFO
LOG_LEVEL_CLEANER=INFO
LOG_LEVEL_CHUNKER=INFO
LOG_LEVEL_SUMMARIZER=INFO
```

### Формат structured логов

```
2025-01-09 10:30:15 | INFO     | ai_client       | Transcribing: video.mp4 (156.3 MB)
2025-01-09 10:32:18 | ERROR    | ai_client       | Transcription timeout after 123.4s
```

### Просмотр логов на сервере

```bash
# Последние 50 строк
ssh truenas_admin@192.168.1.152 'sudo docker logs bz2-transcriber --tail 50'

# В реальном времени
ssh truenas_admin@192.168.1.152 'sudo docker logs -f bz2-transcriber'
```

Подробнее: [docs/logging.md](docs/logging.md)

## Тестирование на сервере

Claude может автоматически тестировать приложение на сервере без веб-интерфейса.

### Доступные операции

```bash
# Через SSH (используя .env.local credentials)
source .env.local && sshpass -p "$DEPLOY_PASSWORD" ssh "${DEPLOY_USER}@${DEPLOY_HOST}" "команда"

# Health check
curl -s http://localhost:8801/health
curl -s http://localhost:8801/health/services

# Список файлов в inbox и архиве
curl -s http://localhost:8801/api/inbox
curl -s http://localhost:8801/api/archive

# Логи контейнера
sudo docker logs bz2-transcriber --tail 50

# Вызов API транскрипции
curl -X POST http://localhost:8801/api/step/transcribe \
  -H "Content-Type: application/json" \
  -d '{"video_filename": "test.mp4"}'
```

### Цикл отладки

1. Внести изменения в код локально
2. Задеплоить: `./scripts/deploy.sh`
3. Запустить тест через API/SSH
4. Проверить логи
5. Повторить при необходимости
