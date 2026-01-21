# Конфигурация системы

Настройки системы задаются через переменные окружения и YAML-файлы.

## Переменные окружения

Определены в `backend/app/config.py`, передаются через `docker-compose.yml`.

### AI сервисы (v0.29+)

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `OLLAMA_URL` | `http://192.168.1.152:11434` | URL Ollama API |
| `WHISPER_URL` | `http://192.168.1.152:9000` | URL Whisper API |
| `SUMMARIZER_MODEL` | `claude-sonnet-4-5` | Модель для суммаризации |
| `CLEANER_MODEL` | `claude-sonnet-4-5` | Модель для очистки транскрипта |
| `LONGREAD_MODEL` | `claude-sonnet-4-5` | Модель для генерации лонгрида |
| `WHISPER_MODEL` | `large-v3-turbo` | Имя модели Whisper (для отображения в UI) |
| `WHISPER_LANGUAGE` | `ru` | Язык транскрипции |
| `WHISPER_INCLUDE_TIMESTAMPS` | `false` | Включать таймкоды `[HH:MM:SS]` в транскрипт |
| `LLM_TIMEOUT` | `300` | Таймаут LLM запросов (секунды) |

> **v0.29+:** По умолчанию все LLM операции используют Claude Sonnet. Требуется `ANTHROPIC_API_KEY`.

### AI сервисы — облачные (Claude API)

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `ANTHROPIC_API_KEY` | — | API ключ Anthropic (обязателен для Claude) |

**Получение ключа:** [console.anthropic.com](https://console.anthropic.com/)

**Формат:** `sk-ant-api03-...`

**Использование:** Модели с префиксом `claude` автоматически используют Claude API:
- `claude-sonnet-4-5` — Sonnet 4.5 (рекомендуется, $3/$15)
- `claude-haiku-4-5` — Haiku 4.5 (быстрая, $1/$5)
- `claude-opus-4-5` — Opus 4.5 (мощная, $5/$25)

**Стоимость:** Цены за 1M токенов (вход/выход)

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

Конфигурация моделей и параметров обработки. Включает:
- Список Whisper моделей
- Context Profiles (параметры по размеру контекста)
- Провайдеры AI (Ollama, Claude)
- Конфигурации отдельных моделей

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

#### Секция context_profiles (v0.17+)

Context Profiles — параметры обработки, сгруппированные по размеру контекстного окна.
Это избавляет от дублирования параметров для каждой модели.

```yaml
context_profiles:
  # Малый контекст (< 16K tokens) — локальные модели
  small:
    context_tokens: 8192
    cleaner:
      chunk_size: 3000          # Небольшие чанки
      chunk_overlap: 200
      small_text_threshold: 3500
    chunker:
      large_text_threshold: 10000
      min_chunk_words: 100
      target_chunk_words: 250
    # ...

  # Средний контекст (16K - 64K tokens) — продвинутые локальные модели
  medium:
    context_tokens: 32768
    cleaner:
      chunk_size: 8000          # Большие чанки
    # ...

  # Большой контекст (> 100K tokens) — облачные модели
  large:
    context_tokens: 200000
    cleaner:
      chunk_size: 100000        # Минимум чанков
      small_text_threshold: 150000  # Почти весь текст обрабатывается целиком
    # ...
```

| Профиль | Контекст | Модели |
|---------|----------|--------|
| `small` | < 16K tokens | gemma2:9b |
| `medium` | 16K - 64K tokens | qwen2.5:14b, llama3.2:8b |
| `large` | > 100K tokens | Claude Sonnet, Claude Opus |

#### Секция providers (v0.17+)

Конфигурация AI провайдеров:

```yaml
providers:
  ollama:
    type: "local"              # Локальный сервер
    default_profile: small     # Профиль по умолчанию
    base_url_env: "OLLAMA_URL" # Переменная окружения с URL

  claude:
    type: "cloud"              # Облачный API
    default_profile: large
    api_key_env: "ANTHROPIC_API_KEY"  # Переменная с API ключом
```

#### Секция models

Конфигурация отдельных моделей. Каждая модель ссылается на `context_profile`:

```yaml
models:
  gemma2:
    provider: ollama
    context_profile: small     # Параметры из профиля 'small'
    context_tokens: 8192

  qwen2.5:
    provider: ollama
    context_profile: medium
    context_tokens: 32768

  claude-sonnet:
    provider: claude
    context_profile: large
    context_tokens: 200000
```

**Claude модели (v0.19+):**

С версии 0.19 поддерживаются облачные модели Claude API:

```yaml
  claude-sonnet:
    provider: claude           # Использует ClaudeClient
    context_profile: large     # 200K context — без чанкирования
    context_tokens: 200000
```

Для использования Claude:
1. Установить `ANTHROPIC_API_KEY` в docker-compose.yml
2. Выбрать модель в настройках (например `claude-sonnet-4-5`)

**Переопределение параметров:** Модель может override параметры профиля:

```yaml
models:
  qwen3:
    provider: ollama
    context_profile: medium     # Базовые параметры из 'medium'
    context_tokens: 40960       # Но контекст больше
    # Override отдельных параметров
    cleaner:
      chunk_size: 10000         # Переопределяем только chunk_size
```

| Параметр | Описание |
|----------|----------|
| `provider` | Провайдер AI (ollama, claude) |
| `context_profile` | Ссылка на профиль параметров |
| `context_tokens` | Размер контекстного окна модели |
| `cleaner.*` | Override параметров очистки |
| `chunker.*` | Override параметров чанкирования |

#### Добавление новой модели

1. Выбрать подходящий `context_profile`
2. Добавить запись в `models`:

```yaml
models:
  my-new-model:
    provider: ollama
    context_profile: medium     # Выбираем профиль по размеру контекста
    context_tokens: 32000       # Указываем точный размер
```

Дополнительно см.:
- [ADR-004: Абстракция AI клиентов](adr/004-ai-client-abstraction.md)
- [ADR-006: Интеграция облачных моделей](adr/006-cloud-model-integration.md)

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
| Включить Claude API | `docker-compose.yml` → `ANTHROPIC_API_KEY` |
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
