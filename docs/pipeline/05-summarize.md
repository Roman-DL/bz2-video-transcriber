# Этап 5: Summarize (+ Classification)

[< Назад: Chunk](04-chunk.md) | [Обзор Pipeline](README.md) | [Далее: Save >](06-save.md)

---

## Назначение

Создание структурированного саммари для File Search в БЗ 2.0.

## Класс VideoSummarizer

```python
class VideoSummarizer:
    """
    Video summarization service using Ollama LLM.

    Creates structured summaries with key points, recommendations,
    target audience, and classification for BZ 2.0 knowledge base.

    Supports dynamic prompt selection for iterative format tuning.
    """

    def __init__(
        self,
        ai_client: AIClient,
        settings: Settings,
        prompt_name: str = "summarizer",  # Имя файла промпта
    ):
        """
        Initialize summarizer.

        Args:
            ai_client: AI client for LLM calls
            settings: Application settings
            prompt_name: Name of prompt template file (without .md extension)
        """

    async def summarize(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
    ) -> VideoSummary:
        """Create structured summary from cleaned transcript."""

    def set_prompt(self, prompt_name: str) -> None:
        """Change prompt template on the fly."""
```

## Пример использования

```python
async with AIClient(settings) as client:
    # Стандартное использование
    summarizer = VideoSummarizer(client, settings)
    summary = await summarizer.summarize(cleaned_transcript, metadata)

    print(f"Section: {summary.section}")
    print(f"Tags: {summary.tags}")
    print(f"Access level: {summary.access_level}")

    # С альтернативным промптом
    summarizer = VideoSummarizer(client, settings, prompt_name="summarizer_v2")

    # Смена промпта на лету
    summarizer.set_prompt("summarizer_test")
    summary = await summarizer.summarize(cleaned_transcript, metadata)
```

## Формат промпта

Промпт использует плейсхолдеры (подстановка через `.replace()`):

| Плейсхолдер | Источник |
|-------------|----------|
| `{title}` | `metadata.title` |
| `{speaker}` | `metadata.speaker` |
| `{date}` | `metadata.date` в формате "8 января 2025" |
| `{event_type}` | `metadata.event_type` |
| `{stream_name}` | `metadata.stream_full` |
| `{transcript}` | `cleaned_transcript.text` |

> **Почему `.replace()` вместо f-string?** Промпт содержит примеры JSON с фигурными скобками `{}`, которые конфликтуют с форматированием `str.format()`.

**Русские названия месяцев:**
```python
RUSSIAN_MONTHS = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]
```

## Динамический выбор промпта

Для итеративной настройки формата саммари можно создавать разные версии промптов:

| Файл | Назначение |
|------|------------|
| `config/prompts/summarizer.md` | Основной промпт (по умолчанию) |
| `config/prompts/summarizer_v2.md` | Тестовая версия |
| `config/prompts/summarizer_compact.md` | Компактный формат |

После подбора лучшего варианта — переименовать его в `summarizer.md`.

## Структура ответа LLM

```json
{
  "summary": "2-3 абзаца: о чём видео и какую проблему решает",

  "key_points": [
    "Ключевой тезис 1",
    "Ключевой тезис 2",
    "Ключевой тезис 3"
  ],

  "recommendations": [
    "Практическая рекомендация 1",
    "Практическая рекомендация 2"
  ],

  "target_audience": "Для кого полезно это видео",

  "questions_answered": [
    "На какой вопрос отвечает видео 1?",
    "На какой вопрос отвечает видео 2?"
  ],

  "classification": {
    "section": "Обучение|Продукты|Бизнес|Мотивация",
    "subsection": "Подкатегория внутри секции",
    "tags": ["тег1", "тег2", "тег3"],
    "access_level": 1
  }
}
```

## Модель данных

```python
class VideoSummary(BaseModel):
    """Video summary for BZ 2.0."""

    # Контент
    summary: str                      # Краткое содержание (2-3 абзаца)
    key_points: list[str]             # Ключевые тезисы (5-7)
    recommendations: list[str]        # Практические рекомендации (3-5)
    target_audience: str              # Для кого полезно (1-2 предложения)
    questions_answered: list[str]     # Вопросы, на которые отвечает (3-5)

    # Классификация (из вложенного classification)
    section: str                      # Обучение / Продукты / Бизнес / Мотивация
    subsection: str                   # Подкатегория
    tags: list[str]                   # Теги для поиска (5-7)
    access_level: int = Field(ge=1, le=4, default=1)  # Уровень доступа
```

**Файл модели:** [`backend/app/models/schemas.py`](../../backend/app/models/schemas.py)

## Обработка ответа LLM

### Извлечение JSON

Метод `_extract_json()` обрабатывает различные форматы ответа:

1. **Markdown-wrapped JSON:** ` ```json {...} ``` `
2. **Plain JSON object:** `{...}`
3. **JSON с окружающим текстом:** находит границы `{...}` через bracket counting

```python
def _extract_json(self, text: str) -> str:
    """
    Extract JSON from LLM response.

    Handles markdown code blocks and embedded JSON objects.
    """
```

### Сглаживание структуры (flatten)

Метод `_flatten_response()` извлекает поля classification на верхний уровень:

```python
def _flatten_response(self, data: dict) -> dict:
    """
    Flatten nested classification into top-level fields.

    Fallback логика для полей classification:
    1. Сначала проверяет data["classification"]["field"]
    2. Затем data["field"] (если LLM вернул плоскую структуру)
    3. Значение по умолчанию (пустая строка, [], 1 для access_level)
    """
```

### Валидация секции

```python
VALID_SECTIONS = ["Обучение", "Продукты", "Бизнес", "Мотивация"]

# При невалидной секции — автоматическая замена на "Обучение"
if section not in VALID_SECTIONS:
    logger.warning(f"Invalid section value: '{section}', using default 'Обучение'")
    summary_data["section"] = "Обучение"
```

### Создание VideoSummary

Pydantic модель с валидацией `access_level: int = Field(ge=1, le=4, default=1)`.

## Валидация

### Секции (VALID_SECTIONS)

| Секция | Описание |
|--------|----------|
| Обучение | Методики, техники, навыки, тренинги |
| Продукты | Продукция Herbalife, применение, результаты |
| Бизнес | Построение бизнеса, рекрутинг, продажи |
| Мотивация | Истории успеха, вдохновение, личностный рост |

### Уровни доступа

| Уровень | Аудитория |
|---------|-----------|
| 1 | Все консультанты (базовая информация) |
| 2 | Спонсоры (продвинутые темы) |
| 3 | TAB Team (управленческие темы) |
| 4 | Администраторы (внутренняя информация) |

## Логирование

Сервис логирует ключевые события:

```
INFO: Summarizing transcript: 2500 chars, prompt=summarizer
INFO: Summarization complete: section=Продукты, tags=5, access_level=1
INFO: Prompt changed to: summarizer_v2
WARNING: Invalid section value: 'НеверныйРаздел', using default 'Обучение'
ERROR: Failed to parse JSON: ...
DEBUG: Response was: ...
```

## Обработка ошибок

При невалидном JSON выбрасывается `ValueError`:

```python
try:
    data = json.loads(json_str)
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse JSON: {e}")
    raise ValueError(f"Invalid JSON in LLM response: {e}")
```

## Конфигурация

Timeout для LLM запросов: `llm_timeout: 300` секунд (5 минут) в `backend/app/config.py`.

## Тестирование

Встроенные тесты запускаются командой:

```bash
python -m backend.app.services.summarizer
```

**Тесты:**
1. **Загрузка промпта** — проверка плейсхолдеров `{title}`, `{speaker}`, `{transcript}`
2. **Извлечение JSON (plain)** — парсинг чистого JSON
3. **Извлечение JSON (markdown)** — удаление ` ```json ``` ` обёртки
4. **Парсинг полей саммари** — проверка всех полей включая вложенный classification
5. **Валидация секций** — проверка valid/invalid значений, fallback на "Обучение"
6. **Полная саммаризация с LLM** — интеграционный тест (если Ollama доступен)

---

## Связанные документы

- **Код:** [`backend/app/services/summarizer.py`](../../backend/app/services/summarizer.py)
- **Модели:** [`backend/app/models/schemas.py`](../../backend/app/models/schemas.py)
- **Промпт:** [`config/prompts/summarizer.md`](../../config/prompts/summarizer.md)
