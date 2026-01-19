# Конфигурация системы

Настройки системы задаются через переменные окружения и YAML-файлы.

## Переменные окружения

Определены в `backend/app/config.py`, передаются через `docker-compose.yml`.

### AI сервисы

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `OLLAMA_URL` | `http://192.168.1.152:11434` | URL Ollama API |
| `WHISPER_URL` | `http://192.168.1.152:9000` | URL Whisper API |
| `SUMMARIZER_MODEL` | `qwen2.5:14b` | Модель для суммаризации |
| `CLEANER_MODEL` | `gemma2:9b` | Модель для очистки транскрипта |
| `CHUNKER_MODEL` | `gemma2:9b` | Модель для семантического чанкирования |
| `WHISPER_MODEL` | `large-v3-turbo` | Имя модели Whisper (для отображения в UI) |
| `WHISPER_LANGUAGE` | `ru` | Язык транскрипции |
| `WHISPER_INCLUDE_TIMESTAMPS` | `false` | Включать таймкоды `[HH:MM:SS]` в транскрипт |
| `LLM_TIMEOUT` | `300` | Таймаут LLM запросов (секунды) |

### Пути

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `DATA_ROOT` | `/data` | Корневая директория данных |
| `INBOX_DIR` | `/data/inbox` | Папка входящих видео |
| `ARCHIVE_DIR` | `/data/archive` | Папка архива |
| `TEMP_DIR` | `/data/temp` | Временные файлы |
| `CONFIG_DIR` | `/app/config` | Конфигурационные файлы |

### Логирование

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `LOG_LEVEL` | `INFO` | Общий уровень логов |
| `LOG_FORMAT` | `structured` | Формат: `simple` или `structured` |
| `LOG_LEVEL_AI_CLIENT` | — | Override для ai_client |
| `LOG_LEVEL_PIPELINE` | — | Override для pipeline |
| `LOG_LEVEL_TRANSCRIBER` | — | Override для transcriber |
| `LOG_LEVEL_CLEANER` | — | Override для cleaner |
| `LOG_LEVEL_CHUNKER` | — | Override для chunker |
| `LOG_LEVEL_SUMMARIZER` | — | Override для summarizer |

## Конфигурационные файлы

Расположены в `config/`, монтируются в контейнер как `/app/config`.

### models.yaml

Параметры обработки для каждой модели и список доступных Whisper моделей.

#### Секция whisper_models

Список установленных моделей транскрипции. Только эти модели показываются в UI.

```yaml
whisper_models:
  - id: "Systran/faster-whisper-large-v3"      # Полный ID модели HuggingFace
    name: "large-v3"                            # Короткое имя для отображения
    description: "Высокое качество, медленнее"  # Описание для UI
  - id: "deepdml/faster-whisper-large-v3-turbo-ct2"
    name: "large-v3-turbo"
    description: "Быстрее, хорошее качество"
```

Для добавления новой whisper модели:
1. Загрузить модель на whisper сервер (первый запрос с этой моделью)
2. Добавить запись в `whisper_models`

#### Секция models

Параметры обработки для каждой LLM модели:

```yaml
models:
  gemma2:
    context_tokens: 8192      # Размер контекстного окна модели
    cleaner:
      chunk_size: 3000        # Размер чанка для очистки
      chunk_overlap: 200      # Перекрытие между чанками
      small_text_threshold: 3500
    chunker:
      large_text_threshold: 10000
      min_chunk_words: 100
      target_chunk_words: 250
    text_splitter:
      part_size: 6000
      overlap_size: 1500
      min_part_size: 2000

  qwen2:
    context_tokens: 32768     # Большее окно → большие чанки
    cleaner:
      chunk_size: 12000
    # ...

defaults:
  # Fallback значения если модель не найдена
```

| Параметр | Описание |
|----------|----------|
| `context_tokens` | Размер контекстного окна модели (отображается в UI) |
| `cleaner.chunk_size` | Размер чанка текста для очистки |
| `chunker.large_text_threshold` | Порог для Map-Reduce режима |

### glossary.yaml

Словарь терминов для коррекции ошибок Whisper.

```yaml
categories:
  - name: "Названия"
    terms:
      - correct: "БЗ 2.0"
        wrong: ["БЗ два ноль", "бз2"]
```

### events.yaml

Типы событий для парсинга имён файлов.

```yaml
event_types:
  - code: "ПШ"
    name: "Пленарная Школа"
  - code: "СГ"
    name: "Семинар Глобальный"
```

### performance.yaml

Коэффициенты для оценки времени обработки.

```yaml
stages:
  transcribe:
    base_coefficient: 0.15
    min_seconds: 30
```

### prompts/

Промпты для LLM. Поддерживается fallback:
1. `{name}_{model_family}.md` — специфичный для модели
2. `{name}.md` — общий

Примеры:
- `cleaner_system.md` — системный промпт для очистки
- `cleaner_system_gemma2.md` — версия для gemma2
- `chunker.md` — промпт для чанкирования
- `summarizer_system.md` — промпт для суммаризации

## Где что менять

| Задача | Что менять |
|--------|------------|
| Сменить модель суммаризации | `docker-compose.yml` → `SUMMARIZER_MODEL` |
| Настроить формат транскрипта | `docker-compose.yml` → `WHISPER_INCLUDE_TIMESTAMPS` |
| Изменить параметры chunking | `config/models.yaml` |
| Добавить термин в глоссарий | `config/glossary.yaml` |
| Изменить промпт LLM | `config/prompts/*.md` |
| Добавить тип события | `config/events.yaml` |

## Override моделей через UI

Пользователь может временно переопределить модели для обработки через веб-интерфейс:

1. Нажать иконку настроек (шестерёнка) в Header
2. Выбрать модели для каждого этапа pipeline
3. Сохранить — настройки сохраняются в localStorage браузера

**Приоритет:** UI override > переменные окружения > defaults

Настройки из UI передаются в API как параметр `model` в запросах `/step/clean`, `/step/chunk`, `/step/summarize`.

## Применение изменений

**Переменные окружения:** требуют пересборки контейнера
```bash
./scripts/deploy.sh
```

**YAML-файлы:** применяются при перезапуске (без пересборки)
```bash
# На сервере
docker compose restart bz2-transcriber
```

**UI настройки:** применяются сразу (localStorage)
