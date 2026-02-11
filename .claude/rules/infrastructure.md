---
globs: backend/app/utils/**,backend/app/config.py,config/**,docker-compose.yml,scripts/**,backend/app/services/text_splitter.py
---

# Rules: Infrastructure

## Логирование
- Формат: structured (`LOG_FORMAT=structured`)
- Per-module override: `LOG_LEVEL_AI_CLIENT=DEBUG`, `LOG_LEVEL_PIPELINE=INFO`, etc.
- ВСЕГДА использовать structured logging: `logger.info("event", key=value)` — НЕ f-строки
- Формат вывода: `2025-01-09 10:30:15 | INFO | ai_client | Event message`

## Промпты
- Загрузка: `load_prompt(stage, name, settings)` из `app.config`
- Структура: `config/prompts/{stage}/{name}.md`
- Внешние промпты: `PROMPTS_DIR=/data/prompts` (приоритет: внешние → встроенные)
- НЕ хардкодить промпты в Python-коде — ВСЕГДА через файлы

## Деплой
- docker-compose НЕ работает локально — пути `/mnt/main/work/bz2/video` только на сервере
- ВСЕГДА деплой через `./scripts/deploy.sh`
- Пути: хост `/mnt/main/work/bz2/video/archive/`, контейнер `/data/archive/`
- HTTPS через Traefik (v0.63+): `https://transcriber.home` — основной способ доступа
- Бэкенд (`bz2-transcriber`) — `expose: 80`, НЕ `ports` — доступен только через nginx
- Настройка HTTPS инфраструктуры: `./scripts/setup-https.sh` (mkcert, Traefik, DNS)

## SSH к серверу
- ВСЕГДА использовать `sshpass` с credentials из `.env.local`:
  ```bash
  source .env.local
  sshpass -p "$DEPLOY_PASSWORD" ssh -o StrictHostKeyChecking=no "$DEPLOY_USER@$DEPLOY_HOST" "COMMAND"
  ```
- Для логов контейнера: `docker logs bz2-transcriber --tail 50` (через sudo)
- Для файлов архива: пути на хосте (`/mnt/main/work/bz2/video/archive/...`)

## Конфигурация
- Модели: `config/models.yaml` (параметры, pricing, chunk_size, context profiles)
- Глоссарий: `config/glossary.yaml`
- События: `config/events.yaml`
- ENV для моделей: `CLEANER_MODEL`, `LONGREAD_MODEL`, `SUMMARY_MODEL`
- `ANTHROPIC_API_KEY` — обязателен для Claude
- `HTTP_PROXY`/`HTTPS_PROXY` — для Claude API через прокси

## macOS разработка
- Системный Python защищён — ВСЕГДА использовать venv: `python3 -m venv .venv`
- Проверка синтаксиса без venv: `python3 -m py_compile backend/app/...`

## Документация
- Стандарты именования и frontmatter: `docs/reference/`
