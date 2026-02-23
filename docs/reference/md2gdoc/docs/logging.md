# Логирование

Стратегия логирования md2gdoc.

## Два уровня логирования

### 1. Application Logs (Python logging)

Стандартный structured logging для отладки и мониторинга.

```bash
# Environment variable
LOG_LEVEL=INFO  # DEBUG/INFO/WARNING/ERROR
```

#### Что логируется

| Компонент | INFO | WARNING | ERROR |
|-----------|------|---------|-------|
| **Converter** | Начало/завершение конвертации, размер | Placeholder для изображений | Ошибка парсинга MD |
| **Sync Manager** | Polling cycle, найдены N файлов | Файл пропущен (дедупликация) | Ошибка сканирования директории |
| **Google Drive** | Upload/update документа | Rate limit (429), retry | Auth error (403), upload failed |
| **Rules Engine** | CRUD операции | Невалидный path | — |

#### Использование в модулях

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Converting: %s (%d bytes)", filename, size)
logger.error("Google API error: %s", err, exc_info=True)
```

### 2. Conversion Log (SQLite таблица)

Персистентная история операций для UI и аудита. Таблица `conversion_log` в SQLite.

| Поле | Описание |
|------|----------|
| `rule_id` | Связь с правилом (или NULL для ручных) |
| `source_path` | Исходный файл |
| `document_id` | ID Google Doc |
| `status` | `success` / `error` |
| `conversion_time_ms` | Длительность конвертации |
| `error_message` | Текст ошибки (если есть) |

**API:** `GET /api/logs` с фильтрацией по правилу, статусу, пагинацией. См. [api-reference.md](api-reference.md).

## Диагностика

### Google API ошибки

| Код | Причина | Действие |
|-----|---------|----------|
| 403 | Нет доступа к папке | Расшарить папку на Service Account |
| 404 | Документ удалён | Пересоздать file_mapping |
| 429 | Rate limit | Автоматический retry с backoff |

### Просмотр логов

```bash
# Docker
docker logs md2gdoc --tail 100
docker logs md2gdoc 2>&1 | grep 'ERROR'

# Фильтр по компоненту
docker logs md2gdoc 2>&1 | grep 'google'
```

## Связанные документы

- [configuration.md](configuration.md) — переменные окружения
- [api-reference.md](api-reference.md) — `GET /api/logs` endpoint
- [architecture/02-rules-engine.md](architecture/02-rules-engine.md) — таблица `conversion_log`
