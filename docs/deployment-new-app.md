# Развёртывание нового приложения на TrueNAS сервере

Пошаговое руководство для развёртывания нового проекта (backend + frontend) на домашнем сервере.
Основано на опыте деплоя bz2-video-transcribe.

---

## 1. Сервер — обзор инфраструктуры

| Параметр | Значение |
|----------|----------|
| Платформа | TrueNAS SCALE 25.10 |
| IP локальный | 192.168.1.152 |
| IP Tailscale | 100.64.0.1 |
| SSH | `truenas_admin@192.168.1.152` |
| Управление контейнерами | Dockge (http://100.64.0.1:5001) |
| Диапазон dev-портов | 8800-8899 |
| Пользователь для файлов | `roman:family` (uid/gid **3000:3000**) |

### Сетевая топология

```
[Mac разработчика] ──Tailscale──▶ [TrueNAS 100.64.0.1]
                                       │
                       ┌───────────────┼───────────────┐
                       ▼               ▼               ▼
                   frontend        backend         AI сервисы
                   (Nginx)         (Uvicorn)       (Ollama, Whisper)
                                       │
                                       ▼  Claude/OpenAI запросы
                                   Mihomo (7890) ──▶ VPN ──▶ API
```

### Карта портов сервера

| Сервис | Порт | HTTPS домен |
|--------|------|-------------|
| TrueNAS UI | 80/443 | nas.home |
| Immich | 2283 | photos.home |
| Grafana | 3000 | grafana.home |
| MCP Gateway | 3010 | — |
| Open WebUI | 3080 | chat.home |
| Dockge | 5001 | — |
| Mihomo (прокси) | 7890 | — |
| qBittorrent | 8081 | torrent.home |
| Radarr | 7878 | radarr.home |
| Nextcloud | 8080 | cloud.home |
| Jellyfin | 8096 | media.home |
| ComfyUI | 8188 | comfyui.home |
| **bz2-transcriber** (backend) | **8801** | — |
| **bz2-frontend** | **8802** | — |
| Whisper | 9000 | whisper.home |
| Mihomo dashboard | 9091 | — |
| Ollama | 11434 | — |

### Свободные диапазоны

| Диапазон | Назначение |
|----------|------------|
| 3011–3079 | MCP-серверы |
| 8800, 8803–8899 | Веб-приложения (backend + frontend) |

Универсальный доступ ко всем сервисам — через `http://100.64.0.1:порт` по Tailscale.

---

## 2. Подготовка на сервере (один раз)

```bash
# SSH на сервер
source .env.local
sshpass -p "$DEPLOY_PASSWORD" ssh truenas_admin@192.168.1.152

# Создать директорию проекта
sudo mkdir -p /mnt/apps-pool/dev/projects/MY-PROJECT

# Создать директорию данных (если нужна)
sudo mkdir -p /mnt/main/work/bz2/MY-PROJECT-DATA
sudo chown -R roman:family /mnt/main/work/bz2/MY-PROJECT-DATA
sudo chmod -R 775 /mnt/main/work/bz2/MY-PROJECT-DATA
```

---

## 3. Структура проекта

```
my-project/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       └── main.py
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── src/
├── config/                  # Опционально: конфиги, промпты
├── scripts/
│   └── deploy.sh
├── docker-compose.yml
├── .env.local               # Секреты (НЕ коммитить!)
├── .env.example             # Шаблон секретов
└── .gitignore
```

---

## 4. Docker Compose — шаблон

```yaml
services:
  my-backend:
    build: ./backend
    container_name: my-backend
    restart: unless-stopped
    ports:
      - "XXXX:80"                    # ← выбрать свободный порт
    volumes:
      # Данные приложения (если нужны)
      - /mnt/main/work/bz2/MY-DATA:/data:rw
      # Конфигурация (если есть)
      - ./config:/app/config:ro
    environment:
      # --- AI API ключи ---
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
      # - OPENAI_API_KEY=${OPENAI_API_KEY:-}

      # --- Прокси для AI API (обязательно из России) ---
      - HTTP_PROXY=http://192.168.1.152:7890
      - HTTPS_PROXY=http://192.168.1.152:7890
      - NO_PROXY=localhost,127.0.0.1,192.168.1.0/24,100.64.0.0/10

      # --- Telegram (если бот) ---
      # - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-}

      # --- Логирование ---
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  my-frontend:
    build: ./frontend
    container_name: my-frontend
    restart: unless-stopped
    ports:
      - "YYYY:80"                    # ← выбрать свободный порт
    depends_on:
      - my-backend
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Важно: `.env` для docker compose

Docker Compose автоматически читает файл `.env` рядом с `docker-compose.yml`.
API ключи передаются через `${ANTHROPIC_API_KEY:-}` — значение берётся из `.env` на сервере.

Файл `.env` создаётся на сервере скриптом деплоя (не коммитится):
```
ANTHROPIC_API_KEY=sk-ant-api03-...
TELEGRAM_BOT_TOKEN=123456:ABC-...
```

---

## 5. Dockerfile backend (Python)

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# curl для healthcheck, другие зависимости по необходимости
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код приложения
COPY app/ ./app/

# ВАЖНО: uid/gid 3000:3000 — совпадает с roman:family на TrueNAS
# Это нужно для корректных прав при записи в примонтированные volumes
RUN groupadd -g 3000 appgroup && \
    useradd -m -u 3000 -g 3000 appuser && \
    chown -R appuser:appgroup /app
USER appuser

EXPOSE 80

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
```

### Зачем uid/gid 3000:3000?

На TrueNAS данные лежат в пулах ZFS, владелец — `roman:family` (3000:3000).
Если контейнер запущен от другого пользователя, он не сможет писать в примонтированные volumes.

```
Хост:      roman:family     = 3000:3000  ← владелец /mnt/main/work/...
Контейнер: appuser:appgroup = 3000:3000  ← совпадает → запись работает
```

**Если приложение не пишет на диск** (только API без volumes) — можно пропустить.

---

## 6. Dockerfile frontend (Node.js + Nginx)

```dockerfile
# Этап 1: сборка
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Этап 2: продакшн — только статика + Nginx
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Multi-stage build: финальный образ ~30MB (Alpine + Nginx + статика).

---

## 7. Nginx — конфиг фронтенда

Файл `frontend/nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # Сжатие
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 1000;

    # SPA routing — все неизвестные маршруты → index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Проксирование API на backend
    # "my-backend" — имя сервиса из docker-compose.yml
    location /api {
        proxy_pass http://my-backend:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Таймауты — увеличить если есть длинные операции
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;

        # Максимальный размер тела запроса
        client_max_body_size 50M;
    }

    # WebSocket (если используется)
    location /ws {
        proxy_pass http://my-backend:80;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;    # 24 часа для persistent WS
    }

    # Health endpoint
    location /health {
        proxy_pass http://my-backend:80;
        proxy_set_header Host $host;
    }

    # Кэширование статики
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Ключевые настройки

| Параметр | Значение | Пояснение |
|----------|----------|-----------|
| `proxy_pass` | `http://my-backend:80` | Имя сервиса Docker Compose = DNS имя в сети контейнеров |
| `proxy_read_timeout` | `300s` | Увеличить если backend долго обрабатывает (у нас 7200s для видео) |
| `client_max_body_size` | `50M` | Увеличить если принимаете файлы |
| `try_files` | `$uri /index.html` | Обязательно для SPA (React Router, Vue Router) |
| WS `proxy_read_timeout` | `86400` | 24 часа для постоянных WebSocket-соединений |

---

## 8. Прокси для AI API (обязательно из России)

На сервере работает **Mihomo** — прокси с VPN-маршрутизацией.

```
Docker-контейнер → Mihomo (192.168.1.152:7890) → WireGuard VPN → VPS Германия → AI API ✅
```

### Конфигурация в docker-compose.yml

```yaml
environment:
  - HTTP_PROXY=http://192.168.1.152:7890
  - HTTPS_PROXY=http://192.168.1.152:7890
  - NO_PROXY=localhost,127.0.0.1,192.168.1.0/24,100.64.0.0/10
```

### NO_PROXY — что исключено

| Паттерн | Что покрывает |
|---------|---------------|
| `localhost` | Loopback контейнера |
| `127.0.0.1` | Loopback |
| `192.168.1.0/24` | Локальная сеть (Ollama, Whisper, TrueNAS) |
| `100.64.0.0/10` | Tailscale сеть |

### Какие API требуют прокси

| Сервис | Домен |
|--------|-------|
| Anthropic Claude | `api.anthropic.com` |
| OpenAI | `api.openai.com` |
| Perplexity | `api.perplexity.ai` |
| Google AI | `generativelanguage.googleapis.com` |
| DeepL | `api.deepl.com` |

### Какие НЕ требуют (Telegram)

Telegram API (`api.telegram.org`) **не заблокирован** в России с 2020 года.
Если бот обращается только к Telegram — прокси не нужен.
Но если бот вызывает Claude/OpenAI — прокси обязателен для этих вызовов.

Рекомендация: **всегда добавлять прокси** в docker-compose, а через `NO_PROXY` исключить то, что не нужно проксировать.

### Совместимость библиотек

Переменные `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` — стандарт. Работают автоматически:

| Библиотека | Поддержка |
|------------|-----------|
| Python: `requests`, `httpx`, `aiohttp` | ✅ |
| Python: `anthropic`, `openai` SDK | ✅ (через httpx) |
| Python: `python-telegram-bot`, `aiogram` | ✅ (через aiohttp/httpx) |
| Node.js: `node-fetch`, `axios` | ⚠️ Может потребовать `https-proxy-agent` |
| Go: `net/http` | ✅ |
| curl, wget | ✅ |

### Проверка работы прокси

```bash
# Из контейнера:
docker exec -it my-backend sh
curl -x $HTTPS_PROXY https://ifconfig.me
# Должен показать IP VPN (185.21.8.147), а НЕ IP провайдера

# Dashboard Mihomo — посмотреть активные соединения:
# http://192.168.1.152:9091/ui → Connections
```

---

## 9. Скрипт деплоя

Файл `scripts/deploy.sh`:

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 1. Загрузить креды
if [ -f "$PROJECT_DIR/.env.local" ]; then
    source "$PROJECT_DIR/.env.local"
else
    echo "Error: .env.local not found"
    echo "Required: DEPLOY_HOST, DEPLOY_USER, DEPLOY_PASSWORD, DEPLOY_PATH"
    exit 1
fi

# 2. Валидация
for var in DEPLOY_HOST DEPLOY_USER DEPLOY_PASSWORD DEPLOY_PATH; do
    if [ -z "${!var}" ]; then
        echo "Error: $var not set in .env.local"
        exit 1
    fi
done

SSH_CMD="sshpass -p $DEPLOY_PASSWORD ssh -o StrictHostKeyChecking=no ${DEPLOY_USER}@${DEPLOY_HOST}"
RSYNC_CMD="sshpass -p $DEPLOY_PASSWORD rsync"

echo "Deploying to ${DEPLOY_HOST}:${DEPLOY_PATH}..."

# 3. Синхронизировать файлы (без мусора)
$RSYNC_CMD -avz --delete \
    --exclude 'node_modules' \
    --exclude 'frontend/dist' \
    --exclude '.git' \
    --exclude '.env.local' \
    --exclude '.env' \
    --exclude '__pycache__' \
    --exclude '.venv' \
    --exclude '.vscode' \
    --exclude '.idea' \
    --exclude '*.pyc' \
    "$PROJECT_DIR/" "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}/"

# 4. Создать .env с секретами на сервере
ENV_CONTENT=""
[ -n "$ANTHROPIC_API_KEY" ]    && ENV_CONTENT+="ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY\n"
[ -n "$OPENAI_API_KEY" ]       && ENV_CONTENT+="OPENAI_API_KEY=$OPENAI_API_KEY\n"
[ -n "$TELEGRAM_BOT_TOKEN" ]   && ENV_CONTENT+="TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN\n"

if [ -n "$ENV_CONTENT" ]; then
    echo "Creating .env on server..."
    $SSH_CMD "echo '$DEPLOY_PASSWORD' | sudo -S bash -c 'printf \"$ENV_CONTENT\" > ${DEPLOY_PATH}/.env'"
fi

# 5. Собрать и запустить
echo "Building and starting containers..."
$SSH_CMD "cd ${DEPLOY_PATH} && echo '$DEPLOY_PASSWORD' | sudo -S docker compose build --no-cache && echo '$DEPLOY_PASSWORD' | sudo -S docker compose up -d"

echo ""
echo "Deployed successfully!"
echo "Backend:  http://100.64.0.1:XXXX"
echo "Frontend: http://100.64.0.1:YYYY"
```

```bash
chmod +x scripts/deploy.sh
```

---

## 10. Файл .env.local

Хранится **только на Mac разработчика**, никогда не коммитится.

```bash
# Deploy
DEPLOY_HOST=192.168.1.152
DEPLOY_USER=truenas_admin
DEPLOY_PASSWORD=<пароль_от_sudo_на_TrueNAS>
DEPLOY_PATH=/mnt/apps-pool/dev/projects/MY-PROJECT

# API ключи (пробрасываются на сервер через deploy.sh)
ANTHROPIC_API_KEY=sk-ant-api03-...
# OPENAI_API_KEY=sk-...
# TELEGRAM_BOT_TOKEN=123456:ABC-...
```

`.gitignore`:
```
.env.local
.env
```

### Почему sshpass, а не SSH-ключи?

TrueNAS SCALE ограничивает настройку `authorized_keys` для системных пользователей.
`sshpass` — рабочий обходной путь. Пароль хранится только в `.env.local`.

---

## 11. Чеклист деплоя нового приложения

```
□ 1. Выбрать свободные порты (не из таблицы занятых)
□ 2. Создать директорию на сервере:
       /mnt/apps-pool/dev/projects/MY-PROJECT/
□ 3. Создать директорию данных (если нужна):
       /mnt/main/work/bz2/MY-DATA/  (chown roman:family, chmod 775)
□ 4. Подготовить файлы:
       docker-compose.yml
       backend/Dockerfile
       frontend/Dockerfile + nginx.conf
       scripts/deploy.sh
       .env.local
       .gitignore (включить .env.local, .env)
□ 5. uid/gid 3000:3000 в Dockerfile backend (если пишет в volumes)
□ 6. Добавить прокси в docker-compose.yml (HTTP_PROXY, HTTPS_PROXY, NO_PROXY)
□ 7. Запустить deploy.sh
□ 8. Проверить:
       curl http://100.64.0.1:XXXX/health     # backend
       curl http://100.64.0.1:YYYY             # frontend
       docker logs my-backend --tail 20        # логи
□ 9. (Опционально) Добавить в Dockge для UI-управления
```

---

## 12. Диагностика

### Контейнер не стартует

```bash
# Логи
sshpass -p "$DEPLOY_PASSWORD" ssh truenas_admin@192.168.1.152 \
    "echo '$DEPLOY_PASSWORD' | sudo -S docker logs my-backend --tail 50"

# Статус
sshpass -p "$DEPLOY_PASSWORD" ssh truenas_admin@192.168.1.152 \
    "echo '$DEPLOY_PASSWORD' | sudo -S docker ps -a | grep my-"
```

### Нет доступа к AI API (403 / timeout)

1. Проверить что `HTTP_PROXY`/`HTTPS_PROXY` указаны в docker-compose
2. Проверить что Mihomo работает: `curl -x http://192.168.1.152:7890 https://ifconfig.me`
3. Проверить dashboard: http://192.168.1.152:9091/ui → Connections

### Нет прав на запись в volume

```bash
# Внутри контейнера
docker exec -it my-backend id
# uid=3000(appuser) gid=3000(appgroup) — должно быть 3000:3000

# Снаружи
ls -la /mnt/main/work/bz2/MY-DATA/
# Владелец должен быть roman:family (3000:3000)
```

### Фронтенд не видит API

1. Проверить что `proxy_pass` в nginx.conf указывает на правильное имя сервиса
2. Имя сервиса в `docker-compose.yml` = DNS-имя в сети Docker Compose
3. Проверить через `docker exec -it my-frontend curl http://my-backend:80/health`

---

## 13. Опционально: HTTPS через Tailscale + mkcert

Если нужен доступ по домену `myapp.home`:

1. **DNS в Headscale** (VPS):
   ```bash
   ssh root@83.222.22.23
   nano /opt/beget/headscale/config/config.yaml
   # dns.extra_records:
   #   - name: "myapp.home"
   #     type: "A"
   #     value: "100.64.0.1"
   docker compose restart headscale
   ```

2. **Сертификат** (Mac):
   ```bash
   cd ~/Documents/Certificates/home-lab
   mkcert -cert-file cert.pem -key-file key.pem \
       myapp.home ...другие.домены...
   ```

3. **Traefik роутер** — добавить конфигурацию для нового домена

Результат: `https://myapp.home` → `http://100.64.0.1:YYYY`
