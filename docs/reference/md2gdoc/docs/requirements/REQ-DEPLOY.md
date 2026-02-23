# REQ-DEPLOY: Развёртывание на TrueNAS

> Требование для настройки автоматического деплоя md2gdoc на сервер TrueNAS.

**Статус:** Ожидает реализации
**Приоритет:** Средний (после реализации Converter MVP + Rules Engine)

---

## Контекст

md2gdoc разворачивается рядом с bz2-video-transcriber на том же сервере TrueNAS. Инфраструктура (Docker, Traefik, Tailscale) уже настроена. Нужно: создать скрипт деплоя, Dockerfile'ы, настроить HTTPS через Traefik.

**Референс:** деплой bz2-video-transcriber проверен в production, паттерн переиспользуется.

---

## Сервер TrueNAS

| Параметр | Значение |
|----------|----------|
| Платформа | TrueNAS SCALE 25.10 |
| IP локальный | 192.168.1.152 |
| IP Tailscale | 100.64.0.1 |
| SSH | `ssh truenas_admin@192.168.1.152` |
| Dockge UI | http://100.64.0.1:5001 |

### Соседние приложения

| Приложение | Порт | Домен |
|-----------|------|-------|
| bz2-transcriber (frontend) | 8802 | transcriber.home |
| Ollama | 11434 | — |
| Whisper | 9000 | — |
| Open WebUI | 3080 | — |
| Grafana | 3000 | — |

**Диапазон свободных портов:** 8800–8899. Выбрать свободный порт для md2gdoc (например 8803 или 8810).

---

## Что реализовать

### 1. `.env.local` и `.env.local.example`

```bash
# .env.local.example (коммитится в репозиторий)
DEPLOY_HOST=192.168.1.152
DEPLOY_USER=truenas_admin
DEPLOY_PASSWORD=<пароль сервера>
DEPLOY_PATH=/mnt/apps-pool/dev/projects/md2gdoc
# Google Service Account JSON ключ копируется отдельно
```

**Правила:**
- `.env.local` — в `.gitignore`, НИКОГДА не коммитить
- Пароль — тот же, что у bz2-video-transcriber (один сервер)
- `DEPLOY_PATH` — отдельная папка от bz2

### 2. `scripts/deploy.sh`

Адаптировать скрипт bz2-video-transcriber:

```
rsync → docker compose build → docker compose up -d → health check
```

**Отличия от bz2:**
- Нет `ANTHROPIC_API_KEY` (md2gdoc не использует LLM)
- Нет build number (не нужен для MVP)
- Нет прокси (Google API доступен напрямую)
- Базовые образы: `python:3.12-slim`, `node:20-alpine`, `nginx:alpine`
- Health URL: `https://md2gdoc.home/health` (или `http://192.168.1.152:<порт>/health` до настройки Traefik)

**SSH паттерн (обязательно):**
```bash
SSH_OPTS="-o StrictHostKeyChecking=no -o PubkeyAuthentication=no -o PreferredAuthentications=password"
sshpass -p "$DEPLOY_PASSWORD" ssh $SSH_OPTS "$DEPLOY_USER@$DEPLOY_HOST" "COMMAND"
```

> Без `PubkeyAuthentication=no` — SSH падает с "Too many auth failures" из-за множества ключей в agent.

### 3. `backend/Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 4. `frontend/Dockerfile`

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### 5. `frontend/nginx.conf`

Проксирование API запросов к backend:

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /health {
        proxy_pass http://backend:8000;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### 6. `docker-compose.yml`

```yaml
services:
  backend:
    build: ./backend
    container_name: md2gdoc-backend
    restart: unless-stopped
    expose:
      - "8000"
    volumes:
      - ./config/service-account.json:/app/config/service-account.json:ro
      - ./data:/app/data
      - /mnt/main/work/bz2/video:/mnt/source:ro  # Архив bz2-transcriber (для режима once)
      # Добавить дополнительные source paths по необходимости:
      # - /mnt/obsidian-vault:/mnt/obsidian:ro  # Obsidian vault (для one-way/two-way)
    environment:
      - GOOGLE_SERVICE_ACCOUNT_PATH=/app/config/service-account.json
      - DB_PATH=/app/data/md2gdoc.db
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build: ./frontend
    container_name: md2gdoc-frontend
    restart: unless-stopped
    ports:
      - "8810:80"  # Внешний порт для Traefik
    depends_on:
      - backend
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Volume для source files:**
- `/mnt/main/work/bz2/video` — архив bz2-transcriber (серверная папка, для режима `once`)
- `/mnt/obsidian-vault/` — Obsidian vault через SMB/NFS mount (для `one-way`/`two-way`, настраивается позже)

### 7. HTTPS через Traefik (отдельный шаг)

Traefik уже работает на сервере для `transcriber.home`. Нужно добавить роут для `md2gdoc.home`:

1. **DNS (локальный):** добавить `md2gdoc.home → 192.168.1.152` в роутер/hosts
2. **Сертификат:** `mkcert md2gdoc.home` → установить в Traefik
3. **Traefik конфиг:** роут `md2gdoc.home` → `http://192.168.1.152:8810`

> Это настраивается вручную, аналогично transcriber.home. Можно создать `scripts/setup-https.sh` по образцу bz2.

---

## Правило для `.claude/rules/infrastructure.md`

После реализации деплоя добавить:

```markdown
## Деплой
- ВСЕГДА деплой через `/bin/bash scripts/deploy.sh`
- sshpass + SSH_OPTS (PubkeyAuthentication=no) — обязательно
- docker-compose НЕ работает локально — volume paths только на сервере
- HTTPS через Traefik: `https://md2gdoc.home`
- Бэкенд — `expose: 8000`, НЕ `ports` — доступен только через nginx
```

---

## Чеклист

- [ ] `.env.local.example` создан и закоммичен
- [ ] `.env.local` добавлен в `.gitignore`
- [ ] `scripts/deploy.sh` создан и протестирован
- [ ] `backend/Dockerfile` собирается
- [ ] `frontend/Dockerfile` + `nginx.conf` собирается
- [ ] `docker-compose.yml` — контейнеры стартуют
- [ ] Health check проходит: `curl http://192.168.1.152:8810/health`
- [ ] Volumes: Service Account доступен, SQLite база создаётся
- [ ] Source volume: `/mnt/main/work/bz2/video` доступна из контейнера
- [ ] (Позже) HTTPS: `https://md2gdoc.home` работает через Traefik
- [ ] `.claude/rules/infrastructure.md` обновлён
- [ ] `docs/deployment.md` обновлён конкретными значениями

---

## Запрос для Claude Code

```
/preflight docs/requirements/REQ-DEPLOY.md
```

Или сокращённо:

```
Реализуй деплой на TrueNAS сервер по требованию docs/requirements/REQ-DEPLOY.md.
Создай deploy.sh, Dockerfile'ы, docker-compose.yml, .env.local.example.
```

---

_Референс: bz2-video-transcribe/scripts/deploy.sh, bz2-video-transcribe/docs/deployment.md_
