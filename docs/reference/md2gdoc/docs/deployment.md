# Развёртывание

Инструкции по деплою md2gdoc.

## Целевая среда

- **Сервер:** TrueNAS (Docker)
- **Сетевой доступ:** локальная сеть (Traefik для HTTPS)
- **Исходные файлы:** локальная FS сервера или SMB/NFS mount (Obsidian vault с Mac)

## Docker Compose

### Сервисы

| Сервис | Назначение | Порт |
|--------|-----------|------|
| `backend` | FastAPI + Sync Manager + Worker | 8000 (internal) |
| `frontend` | React SPA (Nginx) | 80 (internal) |
| `traefik` | Reverse proxy, HTTPS | 443 |

### docker-compose.yml

```yaml
services:
  backend:
    build: ./backend
    environment:
      - GOOGLE_SERVICE_ACCOUNT_PATH=/app/config/service-account.json
      - DB_PATH=/app/data/md2gdoc.db
      - POLL_INTERVAL_DEFAULT=5
      - MAX_CONCURRENT_CONVERSIONS=3
    volumes:
      - ./config/service-account.json:/app/config/service-account.json:ro
      - ./data:/app/data
      - /mnt/source:/mnt/source:ro
    expose:
      - "8000"

  frontend:
    build: ./frontend
    expose:
      - "80"
    depends_on:
      - backend

  traefik:
    image: traefik:v3
    ports:
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./config/traefik:/etc/traefik
```

## Volumes

| Host path | Container path | Описание |
|-----------|---------------|----------|
| `./config/service-account.json` | `/app/config/service-account.json` | Google API credentials (read-only) |
| `./data/` | `/app/data/` | SQLite database |
| `/mnt/source/` | `/mnt/source/` | Исходные MD файлы (read-only для `once`/`one-way`) |

## Первый деплой

### Prerequisites

1. Docker и Docker Compose установлены на сервере
2. Google Service Account JSON-ключ готов (см. [configuration.md](configuration.md))
3. Целевая папка Google Drive расшарена на Service Account email

### Шаги

1. **Клонировать репозиторий:**
   ```bash
   git clone <repo-url> md2gdoc
   cd md2gdoc
   ```

2. **Разместить Service Account ключ:**
   ```bash
   cp ~/service-account.json config/service-account.json
   ```

3. **Настроить источники файлов:**
   - Проверить что SMB/NFS mount доступен: `ls /mnt/source/`
   - Убедиться что путь совпадает с volume в docker-compose.yml

4. **Запустить:**
   ```bash
   docker-compose up -d
   ```

5. **Проверить:**
   ```bash
   curl http://localhost:8000/health
   # {"status": "ok", "version": "0.0.0"}
   ```

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "ok",
  "version": "0.0.0",
  "google_connected": true,
  "active_rules": 0,
  "db_size_mb": 0.1
}
```

## Обновление

```bash
git pull
docker-compose up -d --build
```

## Подробнее

- Конфигурация: [configuration.md](configuration.md)
- API endpoints: [api-reference.md](api-reference.md)
