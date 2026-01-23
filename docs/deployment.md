# БЗ2: Транскрибатор видео — Deployment Guide

Руководство по развёртыванию на домашнем сервере TrueNAS SCALE.

---

## Инфраструктура

### Сервер

| Параметр | Значение |
|----------|----------|
| Платформа | TrueNAS SCALE 25.10 |
| IP локальный | 192.168.1.152 |
| IP Tailscale | 100.64.0.1 |
| SSH | `ssh truenas_admin@192.168.1.152` |

### Среда разработки

| Параметр | Значение |
|----------|----------|
| Путь проекта | `/mnt/apps-pool/dev/projects/bz2-video-transcribe/` |
| Управление контейнерами | Dockge UI (http://100.64.0.1:5001) |
| Порт Backend (API) | 8801 |
| Порт Frontend (Web UI) | 8802 |
| Диапазон dev-портов | 8800-8899 |

---

## Зависимости: AI сервисы

> **Критично:** Приложение использует внешние AI сервисы. Требуется настроить API ключ Claude и проверить доступность Whisper.

### Claude API (v0.29+, основной)

| Параметр | Значение |
|----------|----------|
| API | Anthropic Claude API |
| Модели | claude-sonnet-4-5, claude-haiku-4-5 |
| Назначение | Очистка, лонгрид, саммаризация, слайды |

**Требуется:** `ANTHROPIC_API_KEY` и прокси (для российского IP).

### Whisper (транскрипция)

| Параметр | Значение |
|----------|----------|
| URL | http://100.64.0.1:9000 |
| Модель | large-v3 |
| Назначение | Транскрипция видео |

**Проверка:**
```bash
curl http://100.64.0.1:9000/health
# Ожидаемый ответ: OK
```

### Ollama (опционально, для локальных моделей)

| Параметр | Значение |
|----------|----------|
| URL | http://100.64.0.1:11434 |
| Модели | gemma2:9b, qwen2.5:14b |
| Назначение | Альтернатива Claude для локальной обработки |

**Проверка:**
```bash
curl http://100.64.0.1:11434/api/version
# Ожидаемый ответ: {"version":"0.x.x"}
```

### Проверка сервисов

```bash
# Whisper (обязательно)
curl -s http://100.64.0.1:9000/health && echo " ✓ Whisper"

# Ollama (опционально)
curl -s http://100.64.0.1:11434/api/version && echo " ✓ Ollama"
```

---

## Доступ к данным

### Структура хранилища

```
/mnt/main/work/bz2/video/            ← Данные приложения
├── inbox/                           ← Входящие видео (watcher мониторит)
├── archive/                         ← Обработанные (структура по датам)
│   └── {год}/{месяц}/{тип}.{поток}/{тема} ({спикер})/
│       ├── {original}.mp4
│       ├── transcript_chunks.json
│       ├── summary.md
│       └── transcript_raw.txt
└── temp/                            ← Временные файлы обработки

/mnt/apps-pool/dev/projects/bz2-video-transcriber/
├── config/                          ← Конфигурация (в репозитории)
│   ├── prompts/
│   │   ├── cleaner.md
│   │   ├── chunker.md
│   │   └── summarizer.md
│   ├── glossary.yaml
│   └── events.yaml
└── docker-compose.yml
```

### SMB доступ к данным

| Способ | Адрес |
|--------|-------|
| Локально | `smb://nas.local/Work/bz2/video` |
| Tailscale | `smb://100.64.0.1/Work/bz2/video` |

### Volumes для Docker

| Host путь | Container путь | Режим | Назначение |
|-----------|----------------|-------|------------|
| `/mnt/main/work/bz2/video` | `/data` | `rw` | inbox, archive, temp |
| `./config` | `/app/config` | `ro` | Промпты, глоссарий |

---

## Docker Compose

### docker-compose.yml

```yaml
services:
  bz2-transcriber:
    build: ./backend
    container_name: bz2-transcriber
    restart: unless-stopped
    ports:
      - "8801:80"
    volumes:
      - /mnt/main/work/bz2/video:/data:rw
      - ./config:/app/config:ro
    environment:
      # AI сервисы
      - OLLAMA_URL=http://192.168.1.152:11434
      - WHISPER_URL=http://192.168.1.152:9000
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      # Модели (v0.29+: Claude по умолчанию)
      - CLEANER_MODEL=claude-sonnet-4-5
      - LONGREAD_MODEL=claude-sonnet-4-5
      - SUMMARY_MODEL=claude-sonnet-4-5
      - SLIDES_MODEL=claude-haiku-4-5
      # Пути
      - DATA_ROOT=/data
      - INBOX_DIR=/data/inbox
      - ARCHIVE_DIR=/data/archive
      - TEMP_DIR=/data/temp
      - CONFIG_DIR=/app/config
      # Настройки
      - WHISPER_LANGUAGE=ru
      - LLM_TIMEOUT=300
      # Прокси для Claude API (если нужен)
      - HTTP_PROXY=http://192.168.1.152:7890
      - HTTPS_PROXY=http://192.168.1.152:7890
      - NO_PROXY=localhost,127.0.0.1,192.168.1.152
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  bz2-frontend:
    build: ./frontend
    container_name: bz2-frontend
    restart: unless-stopped
    ports:
      - "8802:80"
    depends_on:
      - bz2-transcriber
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

> **v0.29+:** По умолчанию все LLM-операции используют Claude. Требуется `ANTHROPIC_API_KEY`.
> Прокси необходим для доступа к Claude API с российского IP.

---

## Развёртывание

### Подготовка папок (один раз)

```bash
ssh truenas_admin@192.168.1.152

# Создать структуру данных (если ещё не создана)
sudo mkdir -p /mnt/main/work/bz2/video/{inbox,archive,temp}
sudo chown -R roman:family /mnt/main/work/bz2
sudo chmod -R 775 /mnt/main/work/bz2
```

### Через Dockge (рекомендуется)

1. Открыть Dockge: http://100.64.0.1:5001
2. **+ Compose** → имя: `bz2-transcriber`
3. Вставить docker-compose.yml
4. **Deploy**

### Через CLI

```bash
ssh truenas_admin@192.168.1.152
cd /mnt/apps-pool/dev/projects/bz2-video-transcriber
sudo docker compose up -d --build
```

---

## Сетевой доступ

### URL приложения

| Сервис | Локальная сеть | Tailscale |
|--------|----------------|-----------|
| Frontend (Web UI) | http://192.168.1.152:8802 | http://100.64.0.1:8802 |
| Backend (API) | http://192.168.1.152:8801 | http://100.64.0.1:8801 |

### HTTPS через Traefik (опционально)

Если нужен HTTPS с доменом `transcriber.home`:

1. **DNS в Headscale** (на VPS):
   ```bash
   ssh root@83.222.22.23
   nano /opt/beget/headscale/config/config.yaml
   # Добавить в dns.extra_records:
   #   - name: "transcriber.home"
   #     type: "A"  
   #     value: "100.64.0.1"
   cd /opt/beget/headscale && docker compose restart headscale
   ```

2. **Сертификат mkcert** (на Mac):
   ```bash
   cd ~/Documents/Certificates/home-lab
   mkcert -cert-file cert.pem -key-file key.pem \
     media.home cloud.home nas.home ... transcriber.home home
   ```

3. **Скопировать на сервер и добавить роутер в Traefik**

После настройки: https://transcriber.home

---

## Переменные окружения

### AI сервисы

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `ANTHROPIC_API_KEY` | — | **Обязательно.** API ключ для Claude (v0.29+) |
| `OLLAMA_URL` | `http://192.168.1.152:11434` | URL Ollama API (для локальных моделей) |
| `WHISPER_URL` | `http://192.168.1.152:9000` | URL Whisper API |
| `CLEANER_MODEL` | `claude-sonnet-4-5` | Модель для очистки транскрипта |
| `LONGREAD_MODEL` | `claude-sonnet-4-5` | Модель для генерации лонгрида |
| `SUMMARY_MODEL` | `claude-sonnet-4-5` | Модель для суммаризации |
| `SLIDES_MODEL` | `claude-haiku-4-5` | Модель для извлечения текста со слайдов (v0.51+) |
| `LLM_TIMEOUT` | `300` | Таймаут запросов к LLM (сек) |
| `WHISPER_LANGUAGE` | `ru` | Язык транскрипции |
| `HTTP_PROXY` | `http://192.168.1.152:7890` | Прокси для Claude API |
| `HTTPS_PROXY` | `http://192.168.1.152:7890` | Прокси для Claude API |
| `NO_PROXY` | `localhost,...` | Исключения (локальные сервисы) |

> **v0.29+:** Claude используется по умолчанию для всех LLM-операций. Ollama остаётся доступным для локальных моделей (gemma2, qwen2.5).

**Примечание:** Прокси необходим для доступа к Claude API с российского IP.
Подробнее: [Прокси для Docker-приложений](Прокси%20для%20Docker-приложений.md)

### Пути

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `DATA_ROOT` | `/data` | Корень данных |
| `INBOX_DIR` | `/data/inbox` | Папка входящих видео |
| `ARCHIVE_DIR` | `/data/archive` | Папка обработанных |
| `TEMP_DIR` | `/data/temp` | Временные файлы |
| `CONFIG_DIR` | `/app/config` | Промпты и глоссарий |

---

## Диагностика

### Проверка AI сервисов из контейнера

```bash
sudo docker exec -it bz2-transcriber sh

# Проверить Ollama
curl http://192.168.1.152:11434/api/version

# Проверить Whisper
curl http://192.168.1.152:9000/health

# Тест генерации
curl http://192.168.1.152:11434/api/generate -d '{
  "model": "qwen2.5:14b",
  "prompt": "Привет",
  "stream": false
}'
```

### Логи

```bash
# Через Dockge UI: bz2-transcriber → Logs

# Через CLI
sudo docker logs -f bz2-transcriber
```

### Проверка доступа к файлам

```bash
sudo docker exec -it bz2-transcriber ls -la /data/
sudo docker exec -it bz2-transcriber ls -la /app/config/
```

### Health endpoint

```bash
curl http://100.64.0.1:8801/health
# {"status":"ok"}

curl http://100.64.0.1:8801/health/services
# {"whisper":true,"ollama":true,...}
```

---

## API сериализация (v0.59+)

С версии v0.59 API использует **camelCase** для JSON-ответов:

| Слой | Формат | Пример |
|------|--------|--------|
| Python код | snake_case | `raw_transcript`, `tokens_used` |
| API JSON | camelCase | `rawTranscript`, `tokensUsed` |
| TypeScript | camelCase | `rawTranscript`, `tokensUsed` |

Подробнее: [ADR-013: API camelCase Serialization](adr/013-api-camelcase-serialization.md)

---

## Автоматический деплой

### Скрипт deploy.sh

```bash
#!/bin/bash
# scripts/deploy.sh — rsync + docker compose

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
source "$PROJECT_DIR/.env.local"

echo "Deploying bz2-video-transcriber..."

# Синхронизация файлов
sshpass -p "$DEPLOY_PASSWORD" rsync -avz --delete \
  --exclude 'node_modules' --exclude '.git' --exclude '.env.local' \
  --exclude '__pycache__' --exclude '.venv' --exclude '*.pyc' \
  "$PROJECT_DIR/" "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}/"

# Пересборка и перезапуск
sshpass -p "$DEPLOY_PASSWORD" ssh "${DEPLOY_USER}@${DEPLOY_HOST}" \
  "cd ${DEPLOY_PATH} && echo '$DEPLOY_PASSWORD' | sudo -S docker compose up -d --build"

echo "Deployed:"
echo "  Frontend: http://100.64.0.1:8802"
echo "  Backend:  http://100.64.0.1:8801"
```

### Credentials (.env.local)

```bash
DEPLOY_HOST=192.168.1.152
DEPLOY_USER=truenas_admin
DEPLOY_PASSWORD=<пароль>
DEPLOY_PATH=/mnt/apps-pool/dev/projects/bz2-video-transcribe
```

### Использование

```bash
./scripts/deploy.sh
```

Или попросить Claude: "Задеплой на сервер"

---

## Очистка временных файлов

```bash
# На хосте
rm -rf /mnt/main/work/bz2/video/temp/*

# В контейнере
sudo docker exec bz2-transcriber rm -rf /data/temp/*
```

---

## Связанные ресурсы

| Ресурс | URL |
|--------|-----|
| Frontend (Web UI) | http://100.64.0.1:8802 |
| Backend (API) | http://100.64.0.1:8801 |
| Dockge (управление) | http://100.64.0.1:5001 |
| Ollama API | http://100.64.0.1:11434 |
| Whisper API | http://100.64.0.1:9000 |
| Open WebUI (чат) | http://100.64.0.1:3080 |
| Grafana (мониторинг) | http://100.64.0.1:3000 |
