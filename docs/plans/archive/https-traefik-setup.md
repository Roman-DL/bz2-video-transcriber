# План: Подключение приложения через HTTPS

## Контекст

Приложение сейчас доступно только по HTTP на портах 8801/8802. На сервере TrueNAS уже работает **Traefik** как reverse proxy с TLS termination (mkcert сертификаты). Нужно подключить приложение к этой инфраструктуре: `https://transcriber.home` через Tailscale VPN.

**Принцип:** Приложение НЕ настраивает HTTPS. Traefik терминирует TLS. Прямой HTTP-доступ по портам убираем.

**Проблема:** `frontend/nginx.conf:24` — `X-Forwarded-Proto $scheme` перезаписывает заголовок от Traefik на `http`.

---

## Часть A — Доработки в приложении (делаем в этой беседе)

Все изменения небольшие, укладываются в одну сессию.

### A1. Исправить nginx.conf — проброс заголовков от Traefik

**Файл:** `frontend/nginx.conf`

Добавить `map` директиву ДО блока `server`:
```nginx
map $http_x_forwarded_proto $x_forwarded_proto {
    default $http_x_forwarded_proto;
    ""      $scheme;
}
```

В location `/api` заменить:
- `proxy_set_header X-Forwarded-Proto $scheme` → `$x_forwarded_proto`
- Добавить `proxy_set_header X-Forwarded-Host $host;`

### A2. Убрать прямой порт бэкенда

**Файл:** `docker-compose.yml`

Заменить `ports: ["8801:80"]` на `expose: ["80"]` у `bz2-transcriber`. Бэкенд доступен только через nginx внутри Docker-сети. Frontend остаётся на `8802:80` (для Traefik).

### A3. Обновить deploy.sh

**Файл:** `scripts/deploy.sh`

Финальное сообщение: `https://transcriber.home` вместо `http://100.64.0.1:8801`.

### A4. Добавить APP_DOMAIN в .env.example

**Файл:** `.env.example`

```bash
# Application domain (HTTPS via Traefik)
APP_DOMAIN=transcriber.home
```

### A5. Создать скрипт setup-https.sh

**Файл:** `scripts/setup-https.sh` (новый)

Скрипт автоматизации серверной настройки, запускается с Mac:
1. Генерация сертификата mkcert (все домены + `transcriber.home`)
2. Копирование cert на TrueNAS через scp
3. Добавление router/service в Traefik dynamic.yml через SSH
4. (Опционально) DNS-запись в Headscale через SSH на VPS
5. Перезапуск Traefik и проверка `curl -I https://transcriber.home`

### A6. Обновить документацию

**Файлы:** `docs/deployment.md`, `CLAUDE.md`

- Основной URL: `https://transcriber.home`
- Убрать/обновить HTTP-порты в таблицах
- HTTPS — основной способ доступа (не опциональный)

---

## Часть B — Ручная настройка сервера (после деплоя приложения)

Эти шаги выполняются вручную на инфраструктуре. Скрипт из A5 автоматизирует большую часть, но можно и вручную.

### B1. DNS-запись в Headscale (на VPS)
```bash
ssh root@83.222.22.23
# В /opt/beget/headscale/config/config.yaml → dns.extra_records:
#   - name: "transcriber.home"
#     type: "A"
#     value: "100.64.0.1"
cd /opt/beget/headscale && docker compose restart headscale
```

### B2. Сертификат mkcert (на Mac)
```bash
cd ~/Documents/Certificates/home-lab
mkcert -cert-file cert.pem -key-file key.pem \
  media.home cloud.home nas.home radarr.home prowlarr.home \
  torrent.home comfyui.home grafana.home prometheus.home \
  photos.home chat.home whisper.home \
  transcriber.home \
  home
```

### B3. Копирование сертификата на TrueNAS (с Mac)
```bash
scp cert.pem key.pem truenas_admin@192.168.1.152:/tmp/
ssh truenas_admin@192.168.1.152
sudo cp /tmp/{cert.pem,key.pem} /mnt/apps-pool/docker/traefik/certs/
sudo chmod 644 /mnt/apps-pool/docker/traefik/certs/*.pem
```

### B4. Роутер в Traefik (на TrueNAS)
В `/mnt/apps-pool/docker/traefik/config/dynamic.yml`:
```yaml
# routers:
    transcriber:
      rule: "Host(`transcriber.home`)"
      entryPoints: [websecure]
      service: transcriber
      tls: {}

# services:
    transcriber:
      loadBalancer:
        servers:
          - url: "http://192.168.1.152:8802"
```
```bash
sudo docker restart traefik
```

### B5. Проверка
```bash
curl -I https://transcriber.home   # → HTTP/2 200
```

---

## Файлы для изменения (Часть A)

| Файл | Изменение |
|------|-----------|
| `frontend/nginx.conf` | Fix X-Forwarded-Proto, добавить X-Forwarded-Host |
| `docker-compose.yml` | ports → expose для бэкенда |
| `scripts/deploy.sh` | URL в сообщениях |
| `.env.example` | Добавить APP_DOMAIN |
| `scripts/setup-https.sh` | **Новый** — скрипт настройки сервера |
| `docs/deployment.md` | Обновить URL, секция HTTPS |
| `CLAUDE.md` | Quick Start URL |

---

## Верификация

1. `docker compose config` — валидация конфигурации
2. Деплой: `./scripts/deploy.sh`
3. Настройка: `./scripts/setup-https.sh` (или вручную по Части B)
4. `curl -I https://transcriber.home` → HTTP/2 200
5. WebSocket: запустить обработку видео в UI — прогресс через WSS
6. `curl https://transcriber.home/health` → `{"status":"ok"}`
7. `curl http://100.64.0.1:8801` → недоступен (порт закрыт)
