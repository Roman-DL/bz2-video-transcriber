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
| **Конфигурация** | [docs/configuration.md](docs/configuration.md) |
| Pipeline (этапы) | [docs/pipeline/](docs/pipeline/) |
| Форматы данных | [docs/data-formats.md](docs/data-formats.md) |
| API сервисов | [docs/api-reference.md](docs/api-reference.md) |
| Развёртывание | [docs/deployment.md](docs/deployment.md) |
| Логирование | [docs/logging.md](docs/logging.md) |
| Тестирование | [docs/testing.md](docs/testing.md) |
| Тестирование моделей | [docs/model-testing.md](docs/model-testing.md) |

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
| Ollama | http://100.64.0.1:11434 | см. ниже |
| Whisper | http://100.64.0.1:9000 | large-v3 |

### Конфигурация моделей

| Задача | Модель | Почему |
|--------|--------|--------|
| Суммаризация | qwen2.5:14b | Лучшее качество текста |
| Очистка | gemma2:9b | Стабильный JSON, умеренное сжатие |
| Чанкирование | gemma2:9b | Оптимальное количество чанков |

Подробнее: [docs/model-testing.md](docs/model-testing.md)

### Ключевые настройки (env)

| Настройка | Где менять | Эффект |
|-----------|------------|--------|
| `SUMMARIZER_MODEL` | docker-compose.yml | Модель для суммаризации |
| `CLEANER_MODEL` | docker-compose.yml | Модель для очистки транскрипта |
| `CHUNKER_MODEL` | docker-compose.yml | Модель для чанкирования |
| `WHISPER_INCLUDE_TIMESTAMPS` | docker-compose.yml | `true` — таймкоды в транскрипте и файле |

### Конфигурационные файлы

| Файл | Назначение |
|------|------------|
| `config/models.yaml` | Параметры моделей (chunk_size, thresholds) |
| `config/glossary.yaml` | Глоссарий терминов для коррекции |
| `config/prompts/*.md` | Промпты для LLM (поддержка {name}_{model}.md) |
| `config/events.yaml` | Типы событий для парсинга имён |

Подробнее: [docs/configuration.md](docs/configuration.md)

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

### Подключение к серверу (для Claude)

**ВАЖНО:** Используй `sshpass` с паролем из `.env.local` для выполнения команд на сервере:

```bash
# Загрузить credentials
source .env.local

# Выполнить команду на сервере
sshpass -p "$DEPLOY_PASSWORD" ssh -o StrictHostKeyChecking=no "$DEPLOY_USER@$DEPLOY_HOST" "COMMAND"

# Пример: получить логи контейнера
sshpass -p "$DEPLOY_PASSWORD" ssh -o StrictHostKeyChecking=no "$DEPLOY_USER@$DEPLOY_HOST" \
  "echo '$DEPLOY_PASSWORD' | sudo -S docker logs bz2-transcriber --tail 50" 2>&1

# Пример: прочитать файл из архива (путь на хосте!)
sshpass -p "$DEPLOY_PASSWORD" ssh -o StrictHostKeyChecking=no "$DEPLOY_USER@$DEPLOY_HOST" \
  "echo '$DEPLOY_PASSWORD' | sudo -S cat '/mnt/main/work/bz2/video/archive/2025/...'" 2>&1
```

**Пути:**
- На хосте: `/mnt/main/work/bz2/video/archive/...`
- В контейнере: `/data/archive/...`

### Просмотр логов на сервере

```bash
# Через sshpass (рекомендуется для Claude)
source .env.local && sshpass -p "$DEPLOY_PASSWORD" ssh -o StrictHostKeyChecking=no "$DEPLOY_USER@$DEPLOY_HOST" \
  "echo '$DEPLOY_PASSWORD' | sudo -S docker logs bz2-transcriber --tail 50" 2>&1

# Интерактивно (для пользователя)
ssh truenas_admin@192.168.1.152 'sudo docker logs bz2-transcriber --tail 50'
```

Подробнее: [docs/logging.md](docs/logging.md)

## Тестирование на сервере

Claude может тестировать pipeline-шаги на сервере через inline Python в контейнере.

**Ключевое:** пути в контейнере отличаются от хоста (`/data/` вместо `/mnt/main/work/bz2/video/`).

Подробнее: [docs/testing.md](docs/testing.md) — примеры тестов, классы сервисов, Pydantic-модели.
