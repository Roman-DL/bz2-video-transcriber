# Прокси для Docker-приложений

## Контекст

На домашнем сервере TrueNAS работает **Mihomo** — прокси-сервер с VPN-маршрутизацией. Он направляет трафик к заблокированным сервисам (AI API, стриминг и др.) через VPN-сервер в Германии.

**Проблема:** Docker-контейнеры по умолчанию выходят в интернет напрямую, минуя Mihomo. Запросы к API (например, Anthropic) блокируются по IP.

**Решение:** Указать переменные окружения `HTTP_PROXY` / `HTTPS_PROXY`, чтобы HTTP-клиенты внутри контейнера использовали Mihomo.

---

## Конфигурация

### Адрес прокси

```
http://192.168.1.152:7890
```

| Параметр | Значение |
|----------|----------|
| Хост | 192.168.1.152 (TrueNAS) |
| Порт | 7890 (HTTP прокси Mihomo) |
| Протокол | HTTP (даже для HTTPS-запросов) |

### Переменные окружения

Добавить в секцию `environment` сервиса в `docker-compose.yml`:

```yaml
environment:
  # Proxy for external APIs
  - HTTP_PROXY=http://192.168.1.152:7890
  - HTTPS_PROXY=http://192.168.1.152:7890
  - NO_PROXY=localhost,127.0.0.1,192.168.1.0/24,100.64.0.0/10
```

### Описание переменных

| Переменная | Назначение |
|------------|------------|
| `HTTP_PROXY` | Прокси для HTTP-запросов |
| `HTTPS_PROXY` | Прокси для HTTPS-запросов (значение то же — `http://...`) |
| `NO_PROXY` | Адреса, которые идут напрямую без прокси |

### NO_PROXY — исключения

```
NO_PROXY=localhost,127.0.0.1,192.168.1.0/24,100.64.0.0/10
```

| Исключение | Что покрывает |
|------------|---------------|
| `localhost` | Локальный хост контейнера |
| `127.0.0.1` | Loopback-адрес |
| `192.168.1.0/24` | Локальная сеть (Ollama, Whisper, TrueNAS) |
| `100.64.0.0/10` | Tailscale сеть |

**Важно:** `NO_PROXY` обеспечивает работу локальных сервисов даже при недоступности Mihomo.

---

## Пример docker-compose.yml

```yaml
services:
  my-app:
    build: ./backend
    container_name: my-app
    restart: unless-stopped
    ports:
      - "8801:80"
    environment:
      # Local AI services (direct connection)
      - OLLAMA_URL=http://192.168.1.152:11434
      - WHISPER_URL=http://192.168.1.152:9000
      
      # Cloud AI API keys
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      
      # Proxy for external APIs (required for blocked services)
      - HTTP_PROXY=http://192.168.1.152:7890
      - HTTPS_PROXY=http://192.168.1.152:7890
      - NO_PROXY=localhost,127.0.0.1,192.168.1.0/24,100.64.0.0/10
```

---

## Сервисы, требующие VPN

Трафик к этим сервисам должен идти через прокси:

| Сервис | Домены |
|--------|--------|
| **Anthropic / Claude** | `api.anthropic.com`, `claude.ai`, `claude.com` |
| **OpenAI / ChatGPT** | `api.openai.com`, `chatgpt.com` |
| **Perplexity** | `api.perplexity.ai` |
| **Google AI** | `generativelanguage.googleapis.com` |
| **DeepL** | `api.deepl.com` |

Mihomo автоматически направляет эти домены через VPN согласно правилам маршрутизации.

---

## Как это работает

```
┌─────────────────────────────────────────────────────────────────┐
│  Docker-контейнер                                               │
│                                                                 │
│  Запрос к api.anthropic.com                                     │
│       │                                                         │
│       ▼                                                         │
│  HTTP-клиент видит HTTPS_PROXY                                  │
│       │                                                         │
└───────┼─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  Mihomo (192.168.1.152:7890)                                    │
│                                                                 │
│  Правило: api.anthropic.com → AI → WireGuard-Fornex (VPN)       │
│                                                                 │
└───────┼─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  VPS Германия (185.21.8.147) → Интернет → Anthropic API ✅      │
└─────────────────────────────────────────────────────────────────┘
```

**Локальные сервисы (NO_PROXY):**

```
Запрос к 192.168.1.152:11434 (Ollama)
       │
       ▼ NO_PROXY — не через прокси
       │
       ▼
Ollama напрямую ✅
```

---

## Совместимость

Переменные `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` — стандартное соглашение. Поддерживаются:

| Язык / Библиотека | Поддержка |
|-------------------|-----------|
| Python: `requests`, `httpx`, `aiohttp` | ✅ Автоматически |
| Python: `anthropic`, `openai` SDK | ✅ Автоматически (через httpx) |
| Node.js: `node-fetch`, `axios` | ⚠️ Может требовать настройки |
| Go: `net/http` | ✅ Автоматически |
| curl, wget | ✅ Автоматически |

---

## Проверка работы

### 1. Dashboard Mihomo

Открыть http://192.168.1.152:9091/ui → **Connections**

Искать запросы к `api.anthropic.com` с цепочкой:
```
RuleSet: claude → AI → WireGuard-Fornex
```

### 2. Тест из контейнера

```bash
# Зайти в контейнер
docker exec -it my-app /bin/sh

# Проверить IP (должен быть IP VPN: 185.21.8.147)
curl -x $HTTPS_PROXY https://ifconfig.me

# Проверить доступ к API
curl -x $HTTPS_PROXY -sI https://api.anthropic.com | head -3
```

---

## Частые ошибки

### 403 Forbidden от API

**Причина:** Запросы идут напрямую, минуя VPN.

**Решение:** Проверить что переменные `HTTP_PROXY` / `HTTPS_PROXY` добавлены в docker-compose.yml и контейнер перезапущен.

### Локальные сервисы недоступны

**Причина:** Отсутствует или неправильный `NO_PROXY`.

**Решение:** Убедиться что `NO_PROXY` включает `192.168.1.0/24`.

### Прокси недоступен

**Причина:** Mihomo не запущен или порт неверный.

**Проверка:**
```bash
curl -x http://192.168.1.152:7890 https://ifconfig.me
```

---

## Ссылки

- Конфигурация Mihomo: `[[Установка Mihomo на TrueNAS]]`
- Правила маршрутизации: `[[Правила маршрутизации Mihomo]]`
- Dashboard: http://192.168.1.152:9091/ui
