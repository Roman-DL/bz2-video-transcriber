# Конфигурация

Настройки приложения md2gdoc.

## Environment Variables

| Переменная | Описание | Default |
|-----------|----------|---------|
| `GOOGLE_SERVICE_ACCOUNT_PATH` | Путь к JSON-ключу Service Account | `config/service-account.json` |
| `POLL_INTERVAL_DEFAULT` | Интервал polling (минуты) | `5` |
| `MAX_CONCURRENT_CONVERSIONS` | Макс. одновременных конвертаций | `3` |
| `DB_PATH` | Путь к SQLite базе | `data/md2gdoc.db` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |

## Google Service Account

### Создание

1. Перейти в [Google Cloud Console](https://console.cloud.google.com/)
2. Создать проект или выбрать существующий
3. Включить Google Drive API (`APIs & Services → Library → Google Drive API`)
4. Создать Service Account (`IAM & Admin → Service Accounts → Create`)
5. Создать JSON-ключ (`Keys → Add Key → Create new key → JSON`)
6. Сохранить файл как `config/service-account.json`

### Настройка доступа

Service Account нужен доступ к целевым папкам Google Drive:
- Скопировать email Service Account (формат: `name@project.iam.gserviceaccount.com`)
- Расшарить целевую папку Google Drive на этот email (Editor)

### Безопасность

- `config/service-account.json` добавлен в `.gitignore` — **НИКОГДА не коммитить**
- В Docker — пробрасывать через volume или Docker secret

## SQLite Database

- Файл: `data/md2gdoc.db`
- Создаётся автоматически при первом запуске
- 3 таблицы: `rules`, `file_mappings`, `conversion_log` (см. [architecture/02-rules-engine.md](architecture/02-rules-engine.md))
- Бэкап: копирование файла `.db` при остановленном приложении

## Frontend

| Переменная | Описание | Default |
|-----------|----------|---------|
| `VITE_API_BASE_URL` | URL backend API | `http://localhost:8000` |

## Docker

При деплое через Docker Compose все переменные задаются в `docker-compose.yml` или `.env` файле:

```yaml
services:
  backend:
    environment:
      - GOOGLE_SERVICE_ACCOUNT_PATH=/app/config/service-account.json
      - DB_PATH=/app/data/md2gdoc.db
      - POLL_INTERVAL_DEFAULT=5
      - MAX_CONCURRENT_CONVERSIONS=3
    volumes:
      - ./config/service-account.json:/app/config/service-account.json:ro
      - ./data:/app/data
      - /mnt/source:/mnt/source:ro  # Исходные MD файлы
```

## Инструменты разработки

### Pencil (дизайн UI)

Для проектирования интерфейса используется Pencil (pencil.dev) — визуальный редактор через MCP-сервер в Claude Code. См. [ADR-001](decisions/ADR-001-pencil-design-workflow.md).

**Установка:**

1. В VSCode: Extensions (Cmd+Shift+X) → поиск "Pencil" → Install
2. MCP-сервер запускается автоматически при открытии `.pen` файла в Pencil

**Проверка:** в Claude Code выполни `/mcp` — Pencil должен появиться в списке серверов. Инструменты `mcp__pencil__*` станут доступны.

**Требования:** Claude Code CLI установлен и аутентифицирован (`claude --version`).

## Подробнее

- Полный список настроек: [PROJECT-SPEC.md](PROJECT-SPEC.md) (Appendix)
- Service Account детали: [architecture/03-google-drive.md](architecture/03-google-drive.md)
