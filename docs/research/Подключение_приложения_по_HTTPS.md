# Подключение приложения по HTTPS

## Назначение документа

Инструкция для подключения нового приложения, развёрнутого на домашнем сервере TrueNAS, к инфраструктуре HTTPS-доступа через Traefik reverse proxy. Документ служит двойной цели:

1. **Руководство для администратора** — пошаговая настройка серверной инфраструктуры
2. **Контекст для ИИ-ассистента** — техническая спецификация для корректной реализации настроек на стороне приложения

---

## Архитектура доступа

```
┌─────────────────────────────────────────────────────────────────┐
│  Клиент (iPhone / MacBook / любое устройство с Tailscale)       │
│  Запрос: https://myapp.home                                     │
└────────────────────────────┬────────────────────────────────────┘
                             │ Tailscale VPN (WireGuard)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  TrueNAS (100.64.0.1)                                          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Traefik (порты 80/443)                                 │    │
│  │  • TLS termination (mkcert сертификаты)                 │    │
│  │  • Роутинг по Host header → backend сервис              │    │
│  └────────────────────────────┬────────────────────────────┘    │
│                               │ HTTP (без TLS)                  │
│                               ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Приложение (http://192.168.1.152:PORT)                 │    │
│  │  • Слушает только HTTP                                  │    │
│  │  • TLS НЕ нужен на уровне приложения                    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Ключевой принцип

Приложение **не настраивает HTTPS самостоятельно**. Traefik выступает reverse proxy и терминирует TLS. Приложение работает по обычному HTTP на выделенном порту. Весь стек доступен **только через Tailscale VPN** — порты не проброшены в интернет.

---

## Параметры инфраструктуры (для ИИ-контекста)

Этот раздел содержит техническую спецификацию, необходимую ИИ-ассистенту для корректной настройки приложения.

### Сервер

| Параметр | Значение |
|----------|----------|
| ОС | TrueNAS SCALE 25.10 |
| IP (локальный) | 192.168.1.152 |
| IP (Tailscale) | 100.64.0.1 |
| Reverse proxy | Traefik (TLS termination) |
| Сертификаты | mkcert (локальный CA) |
| Доменная зона | *.home |
| DNS | Headscale Magic DNS |

### Развёртывание приложений

| Параметр | Значение |
|----------|----------|
| Контейнеризация | Docker (через TrueNAS Apps → Install via YAML) |
| Данные стабильных сервисов | `/mnt/apps-pool/docker/<service-name>/` |
| Данные экспериментов | `/mnt/apps-pool/dev/projects/<project-name>/` |
| AI-сервисы | `/mnt/apps-pool/ai/<service-name>/` |
| Часовой пояс | `Europe/Moscow` |

### Занятые порты

| Порт | Сервис |
|------|--------|
| 80, 443 | TrueNAS UI / Traefik |
| 2283 | Immich |
| 3000 | Grafana |
| 3010–3011 | MCP Gateway |
| 3080 | Open WebUI |
| 5001 | Dockge |
| 7878 | Radarr |
| 8080 | Nextcloud |
| 8081 | qBittorrent |
| 8096 | Jellyfin |
| 8188 | ComfyUI |
| 9000 | Whisper |
| 9091 | Mihomo API |
| 11434 | Ollama |

### Свободные диапазоны для новых сервисов

| Диапазон | Назначение |
|----------|------------|
| 3011–3079 | MCP-серверы |
| 8800–8899 | Веб-приложения |

### Существующие домены в сертификате

```
media.home cloud.home nas.home radarr.home prowlarr.home
torrent.home comfyui.home grafana.home prometheus.home
photos.home chat.home whisper.home home
```

---

## Что нужно от приложения (для ИИ-контекста)

### Обязательные требования

1. **Слушать HTTP** на выделенном порту (например, `8850`). Без TLS.
2. **Не привязываться к localhost** — слушать `0.0.0.0` для доступа извне контейнера.
3. **Корректно работать за reverse proxy** — Traefik проксирует запросы, клиент приходит по HTTPS.

### Рекомендуемые настройки приложения

Если приложение генерирует абсолютные URL (ссылки, редиректы, API-ответы), оно должно знать свой внешний адрес:

```
# Типичные переменные окружения (зависят от фреймворка)
BASE_URL=https://myapp.home
TRUSTED_PROXIES=192.168.1.152,172.16.0.0/12
```

Если приложение использует WebSocket, Traefik пробрасывает их автоматически — дополнительная настройка не требуется.

### Шаблон Docker Compose (для TrueNAS Apps)

```yaml
services:
  myapp:
    image: author/image:tag
    container_name: myapp
    restart: unless-stopped
    ports:
      - "8850:8850"          # HOST_PORT:CONTAINER_PORT
    volumes:
      - /mnt/apps-pool/docker/myapp/config:/config
      - /mnt/apps-pool/docker/myapp/data:/data
    environment:
      - TZ=Europe/Moscow
      - BASE_URL=https://myapp.home    # если приложение поддерживает
```

### Шаблон с GPU

```yaml
services:
  myapp:
    image: author/image:tag
    container_name: myapp
    restart: unless-stopped
    ports:
      - "8850:8850"
    volumes:
      - /mnt/apps-pool/ai/myapp:/data
    environment:
      - TZ=Europe/Moscow
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu, video, compute]
```

### Подготовка директорий на сервере

```bash
# Для стабильного сервиса
sudo mkdir -p /mnt/apps-pool/docker/myapp/{config,data}
sudo chown -R root:root /mnt/apps-pool/docker/myapp
sudo chmod -R 755 /mnt/apps-pool/docker/myapp

# Для AI-сервиса
sudo mkdir -p /mnt/apps-pool/ai/myapp
sudo chown -R root:root /mnt/apps-pool/ai/myapp
sudo chmod -R 755 /mnt/apps-pool/ai/myapp
```

---

## Настройка серверной инфраструктуры (для администратора)

Выполняется один раз для каждого нового сервиса. Замените `myapp` на имя вашего сервиса и `PORT` на выбранный порт.

### Шаг 1. DNS-запись в Headscale (на VPS)

```bash
ssh root@83.222.22.23
nano /opt/beget/headscale/config/config.yaml
```

В секцию `dns:` → `extra_records:` добавить:

```yaml
    - name: "myapp.home"
      type: "A"
      value: "100.64.0.1"
```

Перезапустить Headscale:

```bash
cd /opt/beget/headscale && docker compose restart headscale
```

### Шаг 2. Перевыпуск сертификата mkcert (на Mac)

Важно: mkcert перезаписывает сертификат целиком, поэтому нужно перечислить **все существующие домены** плюс новый.

```bash
cd ~/Documents/Certificates/home-lab
mkcert -cert-file cert.pem -key-file key.pem \
  media.home cloud.home nas.home radarr.home prowlarr.home \
  torrent.home comfyui.home grafana.home prometheus.home \
  photos.home chat.home whisper.home \
  myapp.home \
  home
```

### Шаг 3. Копирование сертификата на TrueNAS (с Mac)

```bash
scp cert.pem key.pem truenas_admin@192.168.1.152:/tmp/
ssh truenas_admin@192.168.1.152
sudo cp /tmp/{cert.pem,key.pem} /mnt/apps-pool/docker/traefik/certs/
sudo chmod 644 /mnt/apps-pool/docker/traefik/certs/*.pem
rm /tmp/{cert.pem,key.pem}
```

### Шаг 4. Роутер в Traefik (на TrueNAS)

```bash
sudo nano /mnt/apps-pool/docker/traefik/config/dynamic.yml
```

В секцию `http:` → `routers:` добавить:

```yaml
    myapp:
      rule: "Host(`myapp.home`)"
      entryPoints:
        - websecure
      service: myapp
      tls: {}
```

В секцию `http:` → `services:` добавить:

```yaml
    myapp:
      loadBalancer:
        servers:
          - url: "http://192.168.1.152:PORT"
```

Перезапустить Traefik:

```bash
sudo docker restart traefik
```

### Шаг 5. Проверка

```bash
# С устройства в сети Tailscale
curl -I https://myapp.home
# Ожидаемый результат: HTTP/2 200
```

---

## Чеклист подключения нового сервиса

```
[ ] Выбран свободный порт (см. таблицу занятых портов)
[ ] Подготовлены директории на TrueNAS
[ ] Приложение развёрнуто и слушает HTTP на выбранном порту
[ ] DNS-запись добавлена в Headscale
[ ] Сертификат mkcert перевыпущен с новым доменом
[ ] Сертификат скопирован на TrueNAS
[ ] Роутер и сервис добавлены в Traefik dynamic.yml
[ ] Traefik перезапущен
[ ] HTTPS-доступ проверен через Tailscale
```

---

## Устранение неполадок

### Домен не резолвится

Проверить, что DNS в Headscale обновлён и клиент Tailscale получил новые записи:

```bash
# На клиенте
nslookup myapp.home 100.100.100.100
```

Если не резолвится — перезапустить Tailscale на клиенте или подождать 1–2 минуты.

### Сертификат не принимается браузером

Убедиться, что mkcert CA установлен на устройстве. Без установки корневого сертификата mkcert браузер будет показывать предупреждение.

### 502 Bad Gateway

Traefik не может подключиться к приложению. Проверить:

```bash
# Приложение запущено?
sudo docker ps | grep myapp

# Порт слушается?
curl http://192.168.1.152:PORT
```

### Приложение отдаёт HTTP-ссылки вместо HTTPS

Настроить `BASE_URL` / `TRUSTED_PROXIES` в переменных окружения приложения, чтобы оно знало, что работает за HTTPS-прокси.
