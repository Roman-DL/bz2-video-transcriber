# RFC: Рефакторинг конфигурации моделей

## Статус
- [x] Планирование
- [x] Реализация: таймкоды в транскрипции
- [x] Реализация: переименование llm_model → summarizer_model
- [x] Реализация: привязка промптов к моделям
- [x] Реализация: параметры чанкования per-model
- [ ] Тестирование (деплой и проверка)
- [ ] Архивация RFC

## Цель

Сделать систему более гибкой для тестирования разных моделей:
1. Возможность отключить таймкоды при транскрипции
2. Привязка промптов к выбранной модели
3. Настройка параметров чанкования для каждой модели

## Мотивация

По результатам тестирования qwen3:14b (см. [qwen3-model-testing.md](qwen3-model-testing.md)):
- Контекст 8K у gemma2:9b ограничивает возможности
- Разные модели требуют разных промптов
- Таймкоды в транскрипте мешают LLM (снижают cyrillic ratio с 90% до 52%)

## Текущее состояние

### Конфигурация моделей (`backend/app/config.py`)

```python
class Settings:
    llm_model: str = "qwen2.5:14b"        # Summarizer (неявно)
    cleaner_model: str = "gemma2:9b"
    chunker_model: str = "gemma2:9b"
    # summarizer_model - НЕТ! Используется llm_model
```

### Промпты (`config/prompts/`)

```
config/prompts/
├── cleaner.md      # Общий для всех моделей
├── chunker.md      # Общий для всех моделей
└── summarizer.md   # Общий для всех моделей
```

### Параметры чанкования (захардкожены)

```python
# backend/app/services/cleaner.py
CHUNK_SIZE_CHARS = 3000      # Max characters per chunk
CHUNK_OVERLAP_CHARS = 200    # Overlap between chunks

# backend/app/services/text_splitter.py
MAX_PART_SIZE = 8000         # Max characters per part
OVERLAP_SIZE = 1500          # Overlap between parts
MIN_PART_SIZE = 2000         # Minimum size for last part

# backend/app/services/chunker.py
MIN_CHUNK_WORDS = 100        # Minimum words per chunk
```

### Таймкоды

- Whisper всегда возвращает таймкоды
- Нет настройки для их отключения

---

## Предлагаемые изменения

### 1. Таймкоды в транскрипции

**Файл:** `backend/app/config.py`

```python
class Settings:
    # Transcription
    whisper_include_timestamps: bool = False  # По умолчанию БЕЗ таймкодов
```

**Файл:** `backend/app/services/transcriber.py`

```python
def _format_transcript(self, segments: list, include_timestamps: bool) -> str:
    if include_timestamps:
        return "\n".join(f"[{seg['start']:.2f}] {seg['text']}" for seg in segments)
    else:
        return " ".join(seg['text'].strip() for seg in segments)
```

### 2. Переименование llm_model → summarizer_model

`llm_model` используется ТОЛЬКО для summarizer и outline_extractor.
Переименовываем для ясности.

**Файл:** `backend/app/config.py`

```python
class Settings:
    cleaner_model: str = "gemma2:9b"
    chunker_model: str = "gemma2:9b"
    summarizer_model: str = "qwen2.5:14b"  # Было: llm_model
```

**Файлы для обновления:**
- `backend/app/services/summarizer.py` — использовать `summarizer_model`
- `backend/app/services/outline_extractor.py` — использовать `summarizer_model`
- `backend/app/services/ai_client.py` — fallback на `summarizer_model`
- `backend/app/services/saver.py` — записывать `summarizer_model`
- `backend/app/services/pipeline.py` — `model_name=summarizer_model`

### 3. Привязка промптов к моделям

**Вариант A: Именование файлов**

```
config/prompts/
├── cleaner_gemma2.md       # Для gemma2:*
├── cleaner_qwen2.md        # Для qwen2.5:*
├── cleaner_qwen3.md        # Для qwen3:* с /no_think
├── chunker_gemma2.md
├── chunker_qwen3.md
└── summarizer_qwen2.md
```

**Логика загрузки:**

```python
def load_prompt(stage: str, model: str, settings: Settings) -> str:
    """
    Load prompt for stage+model combination.

    Fallback order:
    1. prompts/{stage}_{model_family}.md  (e.g., cleaner_gemma2.md)
    2. prompts/{stage}.md                  (e.g., cleaner.md)

    Model family extracted from model name:
    - "gemma2:9b" -> "gemma2"
    - "qwen2.5:14b" -> "qwen2"
    - "qwen3:14b" -> "qwen3"
    """
    model_family = model.split(":")[0].rstrip("0123456789.")

    # Try model-specific prompt first
    specific_path = settings.config_dir / "prompts" / f"{stage}_{model_family}.md"
    if specific_path.exists():
        return specific_path.read_text()

    # Fallback to generic prompt
    generic_path = settings.config_dir / "prompts" / f"{stage}.md"
    return generic_path.read_text()
```

### 4. Параметры чанкования per-model

**Файл:** `config/models.yaml` (новый)

```yaml
# Model-specific configurations
models:
  gemma2:
    # Context: 8K tokens
    cleaner:
      chunk_size: 3000
      chunk_overlap: 200
    chunker:
      max_part_size: 8000
      overlap_size: 1500
      min_part_size: 2000
      min_chunk_words: 100

  qwen2:
    # Context: 32K tokens
    cleaner:
      chunk_size: 8000
      chunk_overlap: 500
    chunker:
      max_part_size: 20000
      overlap_size: 3000
      min_part_size: 5000
      min_chunk_words: 100

  qwen3:
    # Context: 40K tokens
    cleaner:
      chunk_size: 10000
      chunk_overlap: 600
    chunker:
      max_part_size: 25000
      overlap_size: 4000
      min_part_size: 6000
      min_chunk_words: 100

# Default fallback
defaults:
  cleaner:
    chunk_size: 3000
    chunk_overlap: 200
  chunker:
    max_part_size: 8000
    overlap_size: 1500
    min_part_size: 2000
    min_chunk_words: 100
```

**Функция загрузки:**

```python
def load_model_config(model: str, stage: str, settings: Settings) -> dict:
    """
    Load model-specific configuration for a stage.

    Returns config dict with chunk sizes, overlaps etc.
    Falls back to defaults if model not found.
    """
    config = load_models_yaml(settings)
    model_family = model.split(":")[0].rstrip("0123456789.")

    if model_family in config["models"]:
        model_config = config["models"][model_family]
        if stage in model_config:
            return model_config[stage]

    return config["defaults"].get(stage, {})
```

---

## План реализации

### Этап 1: Таймкоды (низкий риск)

1. Добавить `whisper_include_timestamps` в Settings
2. Обновить `transcriber.py` для использования настройки
3. По умолчанию = False (без таймкодов)

### Этап 2: llm_model → summarizer_model (низкий риск)

1. Переименовать `llm_model` → `summarizer_model` в Settings
2. Обновить все файлы где используется `llm_model`
3. Обновить `.env` / docker-compose если есть

### Этап 3: Промпты per-model (средний риск)

1. Создать `load_prompt()` с fallback логикой
2. Скопировать текущие промпты как `*_gemma2.md`
3. Обновить сервисы для использования новой функции
4. Тестирование на gemma2 (должно работать как раньше)

### Этап 4: Параметры чанкования (высокий риск)

1. Создать `config/models.yaml`
2. Создать `load_model_config()` функцию
3. Рефакторинг сервисов для использования конфига вместо констант
4. Полное тестирование pipeline

---

## Затрагиваемые файлы

| Файл | Изменения |
|------|-----------|
| `backend/app/config.py` | Новые поля, функции загрузки |
| `backend/app/services/transcriber.py` | Настройка таймкодов |
| `backend/app/services/cleaner.py` | Конфиг вместо констант |
| `backend/app/services/chunker.py` | Конфиг вместо констант |
| `backend/app/services/text_splitter.py` | Конфиг вместо констант |
| `backend/app/services/summarizer.py` | summarizer_model |
| `config/models.yaml` | Новый файл |
| `config/prompts/*_gemma2.md` | Новые файлы |

---

## Риски и митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Сломать текущий pipeline | Средняя | Fallback к defaults, поэтапное внедрение |
| Неправильные параметры для модели | Низкая | Начать с текущих значений как defaults |
| Сложность поддержки промптов | Низкая | Минимум промптов (только tested models) |

---

## Критерии успеха

1. Pipeline работает как раньше с gemma2:9b / qwen2.5:14b
2. Можно переключить модель в .env и получить правильные промпты/параметры
3. Тесты моделей проходят быстрее (меньше чанков для моделей с большим контекстом)

---

## История изменений

| Дата | Изменение |
|------|-----------|
| 2026-01-12 | RFC создан |
