---
doc_type: explanation
status: active
updated: 2026-02-11
audience: [developer, ai-agent, ops]
tags:
  - architecture
  - deployment
  - infrastructure
---

# Архитектура развёртывания

Описание инфраструктуры, сетевой архитектуры и процесса развёртывания приложения на домашнем сервере.

---

## Обзор инфраструктуры

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Клиент (MacBook / iPhone / любое устройство с Tailscale)                │
│  https://transcriber.home                                                │
└────────────────────────┬─────────────────────────────────────────────────┘
                         │ Tailscale VPN (WireGuard)
                         │ DNS: Headscale Magic DNS (VPS 83.222.22.23)
                         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  TrueNAS SCALE (192.168.1.152 / 100.64.0.1)                              │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Traefik (:443)                                                    │  │
│  │  • TLS termination (mkcert сертификаты)                            │  │
│  │  • Host(`transcriber.home`) → http://192.168.1.152:8802            │  │
│  └──────────────────────────┬─────────────────────────────────────────┘  │
│                              │ HTTP                                      │
│                              ▼                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  bz2-frontend (nginx :8802)                                        │  │
│  │  • SPA (React + Vite)                                              │  │
│  │  • Проксирует /api, /ws, /health → bz2-transcriber                 │  │
│  │  • X-Forwarded-Proto: сохраняет значение от Traefik                │  │
│  └──────────────────────────┬─────────────────────────────────────────┘  │
│                              │ Docker network (внутренняя)               │
│                              ▼                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  bz2-transcriber (FastAPI :80, expose only)                        │  │
│  │  • REST API + WebSocket (SSE прогресс)                             │  │
│  │  • Pipeline orchestration                                          │  │
│  │  • Нет прямого порта — доступен только через nginx                 │  │
│  └──────────┬──────────────────┬──────────────────┬───────────────────┘  │
│             │                  │                  │                      │
│             ▼                  ▼                  ▼                      │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                  │
│  │ Whisper      │   │ Claude API   │   │ Ollama       │                  │
│  │ :9000        │   │ (via proxy)  │   │ :11434       │                  │
│  │ GPU: RTX5070 │   │ Mihomo:7890  │   │ (fallback)   │                  │
│  └──────────────┘   └──────────────┘   └──────────────┘                  │
│                                                                          │
│  Данные: /mnt/main/work/bz2/video/ (inbox, archive, temp)                │
│  Проект: /mnt/apps-pool/dev/projects/bz2-video-transcribe/               │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Сетевая архитектура

### Уровни доступа

| Уровень | Протокол | Кто → Кто | Порт |
|---------|----------|-----------|------|
| Клиент → Traefik | HTTPS (TLS) | Браузер → Traefik | 443 |
| Traefik → Frontend | HTTP | Traefik → nginx | 8802 |
| Frontend → Backend | HTTP | nginx → FastAPI | 80 (Docker internal) |
| Backend → AI сервисы | HTTP | FastAPI → Whisper/Ollama | 9000, 11434 |
| Backend → Claude | HTTPS (via proxy) | FastAPI → Mihomo → Claude API | 7890 → 443 |

### HTTPS (v0.63+)

**Принцип:** Приложение не настраивает HTTPS. Traefik терминирует TLS.

```
Браузер ──HTTPS──► Traefik ──HTTP──► nginx ──HTTP──► FastAPI
         (TLS)            (plain)          (Docker net)
```

- **Traefik** — reverse proxy на TrueNAS, обслуживает все `*.home` домены
- **mkcert** — локальный CA для сертификатов, установлен на всех клиентских устройствах
- **Headscale** — DNS через Magic DNS (VPS), резолвит `transcriber.home` → `100.64.0.1`

### Проброс заголовков

```
Traefik добавляет:
  X-Forwarded-Proto: https
  X-Forwarded-For: <client-ip>

nginx (map директива):
  Если X-Forwarded-Proto пришёл от Traefik → сохраняет его
  Если прямой доступ (нет заголовка) → подставляет $scheme

FastAPI получает:
  X-Forwarded-Proto: https  (корректный протокол)
  X-Forwarded-Host: transcriber.home
```

---

## Docker Compose

### Контейнеры

| Контейнер | Образ | Сеть | Описание |
|-----------|-------|------|----------|
| `bz2-transcriber` | `./backend` | `expose: 80` | FastAPI backend, нет внешнего порта |
| `bz2-frontend` | `./frontend` | `ports: 8802:80` | nginx + React SPA, единственная точка входа |

### Зависимости

```
bz2-frontend ──depends_on──► bz2-transcriber
```

Frontend (nginx) проксирует запросы к backend по Docker DNS имени `bz2-transcriber`.

### Volumes

| Host | Container | Mode | Назначение |
|------|-----------|------|------------|
| `/mnt/main/work/bz2/video` | `/data` | rw | inbox, archive, temp |
| `./config` | `/app/config` | ro | Промпты, глоссарий, конфиг |
| `.../video/prompts` | `/data/prompts` | ro | Внешние промпты (override) |

---

## Процесс развёртывания

### deploy.sh

```
Mac (разработка)                    TrueNAS (продакшн)
     │                                    │
     │  1. rsync (исходники)              │
     ├───────────────────────────────────►│
     │                                    │
     │  2. .env (API keys)                │
     ├───────────────────────────────────►│
     │                                    │
     │  3. docker compose build           │
     │     --no-cache                     │
     │  4. docker compose up -d           │
     │                                    │
     │  ◄── Deployed: https://transcriber.home
```

**Ключевые особенности:**
- Все операции через `sshpass` (credentials из `.env.local`)
- `rsync --delete` — полная синхронизация, исключая node_modules, .git, .venv
- `--no-cache` — гарантия актуальности кода в образе
- API ключи передаются через `.env` файл на сервере

### setup-https.sh

Одноразовая настройка HTTPS инфраструктуры:

```
Mac                     TrueNAS                 VPS (Headscale)
 │                        │                        │
 │ 1. mkcert              │                        │
 │    (генерация cert)    │                        │
 │                        │                        │
 │ 2. scp cert.pem ──────►│                        │
 │                        │ 3. cp → traefik/certs  │
 │                        │                        │
 │ 4. Traefik config ────►│                        │
 │    (router + service)  │                        │
 │                        │                        │
 │ 5. DNS record ─────────┼───────────────────────►│
 │    (transcriber.home)  │                        │ → 100.64.0.1
 │                        │                        │
 │ 6. docker restart ────►│ traefik                │
 │                        │                        │
 │ 7. curl verify         │                        │
 │    https://transcriber.home ✓                   │
```

---

## Прокси для Claude API

Docker-контейнеры выходят в интернет напрямую, но доступ к AI API заблокирован по IP. Mihomo (прокси на TrueNAS) маршрутизирует трафик через VPN.

```
Контейнер                Mihomo              VPN (Германия)         Claude API
    │                      │                      │                      │
    │ HTTPS_PROXY ────────►│                      │                      │
    │ api.anthropic.com    │ WireGuard ──────────►│                      │
    │                      │                      │ ────────────────────►│
    │                      │                      │                      │ ✓
```

**Переменные окружения:**
- `HTTP_PROXY=http://192.168.1.152:7890`
- `HTTPS_PROXY=http://192.168.1.152:7890`
- `NO_PROXY=localhost,127.0.0.1,192.168.1.0/24,100.64.0.0/10`

Локальные сервисы (Whisper, Ollama) обходят прокси через `NO_PROXY`.

---

## Файловая структура на сервере

```
/mnt/apps-pool/dev/projects/bz2-video-transcribe/   ← Исходный код
├── backend/                                          ← FastAPI
├── frontend/                                         ← React + nginx
├── config/                                           ← Промпты, глоссарий
├── scripts/                                          ← deploy.sh, setup-https.sh
├── docker-compose.yml
└── .env                                              ← API keys (на сервере)

/mnt/main/work/bz2/video/                             ← Данные приложения
├── inbox/                                            ← Входящие видео
├── archive/{year}/{type}/{date}/{title}/              ← Результаты
│   ├── *.mp4
│   ├── transcript_chunks.json
│   ├── summary.md / story.md
│   └── .cache/{stage}/v{N}.json
├── temp/                                             ← Временные файлы
└── prompts/                                          ← Внешние промпты (override)

/mnt/apps-pool/docker/traefik/                        ← Traefik
├── config/dynamic.yml                                ← Роутеры и сервисы
└── certs/cert.pem, key.pem                           ← mkcert сертификаты
```

---

## Связанные документы

| Документ | Описание |
|----------|----------|
| [deployment.md](../deployment.md) | How-to руководство по развёртыванию |
| [Подключение по HTTPS](../research/Подключение_приложения_по_HTTPS.md) | Инфраструктура HTTPS (Traefik, mkcert, Headscale) |
| [ARCHITECTURE.md](../ARCHITECTURE.md) | Обзор архитектуры системы |
