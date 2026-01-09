# Система логирования

Конфигурируемая система логирования с поддержкой per-module уровней.

---

## Быстрый старт

```bash
# Включить DEBUG для ai_client (транскрипция)
LOG_LEVEL_AI_CLIENT=DEBUG ./scripts/deploy.sh

# Посмотреть логи
ssh truenas_admin@192.168.1.152 'sudo docker logs bz2-transcriber --tail 100'
```

---

## Переменные окружения

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `LOG_LEVEL` | `INFO` | Общий уровень (DEBUG/INFO/WARNING/ERROR) |
| `LOG_FORMAT` | `structured` | Формат: `simple` или `structured` |
| `LOG_LEVEL_AI_CLIENT` | - | Уровень для ai_client.py |
| `LOG_LEVEL_PIPELINE` | - | Уровень для pipeline.py |
| `LOG_LEVEL_TRANSCRIBER` | - | Уровень для transcriber.py |
| `LOG_LEVEL_CLEANER` | - | Уровень для cleaner.py |
| `LOG_LEVEL_CHUNKER` | - | Уровень для chunker.py |
| `LOG_LEVEL_SUMMARIZER` | - | Уровень для summarizer.py |

Per-module переменные переопределяют `LOG_LEVEL` для конкретного модуля.

---

## Форматы логов

### Structured (по умолчанию)

```
2025-01-09 10:30:15 | INFO     | ai_client       | Transcribing: video.mp4 (156.3 MB)
2025-01-09 10:30:15 | DEBUG    | ai_client       | Whisper URL: http://192.168.1.152:9000, language: ru
2025-01-09 10:32:18 | DEBUG    | ai_client       | Whisper response: 200, elapsed: 123.4s
2025-01-09 10:32:18 | INFO     | ai_client       | Transcription complete: 45 segments, duration: 612s, elapsed: 123.4s
```

Преимущества:
- Фиксированная ширина колонок
- Легко парсить grep/awk
- Сокращённые имена модулей

### Simple

```
2025-01-09 10:30:15,123 - app.services.ai_client - INFO - Transcribing: video.mp4
```

Стандартный Python формат.

---

## Что логируется

### ai_client.py (транскрипция)

| Уровень | Событие | Пример |
|---------|---------|--------|
| INFO | Начало транскрипции | `Transcribing: video.mp4 (156.3 MB)` |
| DEBUG | URL и параметры | `Whisper URL: http://..., language: ru` |
| DEBUG | HTTP ответ | `Whisper response: 200, elapsed: 45.2s` |
| INFO | Успешное завершение | `Transcription complete: 45 segments, duration: 612s` |
| ERROR | Timeout | `Transcription timeout after 120.5s: ...` |
| ERROR | HTTP ошибка | `Transcription HTTP error after 60.2s: 504 - ...` |

### pipeline.py

| Уровень | Событие |
|---------|---------|
| INFO | Завершение pipeline |
| WARNING | Fallback на простые chunks |
| ERROR | Ошибка chunking/summarization |

### Другие модули

- **transcriber.py** — старт/завершение транскрипции
- **cleaner.py** — количество исправлений глоссария
- **chunker.py** — количество chunks
- **summarizer.py** — смена промпта, парсинг ответа

---

## Конфигурация в docker-compose.yml

```yaml
services:
  bz2-transcriber:
    environment:
      # Logging
      - LOG_LEVEL=INFO
      - LOG_FORMAT=structured
      - LOG_LEVEL_AI_CLIENT=DEBUG  # Детальные логи Whisper
```

---

## Просмотр логов

### На сервере

```bash
# Последние N строк
sudo docker logs bz2-transcriber --tail 100

# В реальном времени
sudo docker logs -f bz2-transcriber

# С временными метками Docker
sudo docker logs -t bz2-transcriber --tail 50

# Фильтрация по модулю
sudo docker logs bz2-transcriber 2>&1 | grep 'ai_client'

# Только ошибки
sudo docker logs bz2-transcriber 2>&1 | grep 'ERROR'
```

### Удалённо (через SSH)

```bash
ssh truenas_admin@192.168.1.152 'sudo docker logs bz2-transcriber --tail 50'
```

### Через Claude (автоматически)

```bash
source .env.local && sshpass -p "$DEPLOY_PASSWORD" ssh "${DEPLOY_USER}@${DEPLOY_HOST}" \
  "sudo docker logs bz2-transcriber --tail 50"
```

---

## Диагностика проблем

### Ошибка 504 при транскрипции

1. Включить DEBUG:
   ```yaml
   - LOG_LEVEL_AI_CLIENT=DEBUG
   ```

2. Посмотреть логи:
   ```bash
   sudo docker logs bz2-transcriber 2>&1 | grep -A5 'Transcribing'
   ```

3. Искать:
   - Время до ошибки (`elapsed: XXs`)
   - HTTP статус (`Whisper response: XXX`)
   - Тип ошибки (timeout, HTTP error)

### Медленная транскрипция

Логи покажут:
- Размер файла (`156.3 MB`)
- Время обработки (`elapsed: 123.4s`)
- Длительность видео (`duration: 612s`)

Норма: elapsed ≈ duration (real-time на GPU).

---

## Архитектура

### Файлы

| Файл | Назначение |
|------|------------|
| [backend/app/logging_config.py](../backend/app/logging_config.py) | Конфигурация и форматтер |
| [backend/app/config.py](../backend/app/config.py) | Settings с log_level полями |
| [backend/app/main.py](../backend/app/main.py) | Инициализация при старте |

### Инициализация

```python
# main.py
from app.logging_config import setup_logging
from app.config import get_settings

settings = get_settings()
setup_logging(settings)  # До импорта других модулей
```

### Использование в модулях

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Message")
logger.debug("Debug info")
logger.error("Error occurred")
```

Модули используют стандартный `logging.getLogger(__name__)` — конфигурация применяется автоматически.

---

## Расширение

### Добавить новый модуль

1. В `logging_config.py` добавить маппинг:
   ```python
   MODULE_LOGGERS = {
       ...
       "new_module": "app.services.new_module",
   }
   ```

2. В `config.py` добавить поле:
   ```python
   log_level_new_module: str | None = None
   ```

3. Использовать в модуле:
   ```python
   import logging
   logger = logging.getLogger(__name__)
   ```
