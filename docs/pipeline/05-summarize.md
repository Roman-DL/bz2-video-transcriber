# Этап 5: Summarize (+ Classification)

[< Назад: Chunk](04-chunk.md) | [Обзор Pipeline](README.md) | [Далее: Save >](06-save.md)

---

## Назначение

Создание структурированного саммари для File Search в БЗ 2.0.

## Класс VideoSummarizer

```python
from app.services.summarizer import VideoSummarizer, VALID_SECTIONS

class VideoSummarizer:
    """
    Сервис саммаризации видео через Ollama LLM.

    Создаёт структурированные саммари с ключевыми тезисами,
    рекомендациями и классификацией для БЗ 2.0.

    Поддерживает динамический выбор промпта для итеративной настройки формата.
    """

    def __init__(
        self,
        ai_client: AIClient,
        settings: Settings,
        prompt_name: str = "summarizer",  # Имя файла промпта
    ):
        ...

    async def summarize(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
    ) -> VideoSummary:
        """Создаёт саммари из очищенного транскрипта."""
        ...

    def set_prompt(self, prompt_name: str) -> None:
        """Смена промпта на лету без пересоздания объекта."""
        ...
```

## Использование

```python
from app.config import get_settings
from app.services.ai_client import AIClient
from app.services.summarizer import VideoSummarizer

settings = get_settings()

async with AIClient(settings) as client:
    # Стандартное использование
    summarizer = VideoSummarizer(client, settings)
    summary = await summarizer.summarize(cleaned_transcript, metadata)

    # С альтернативным промптом
    summarizer = VideoSummarizer(client, settings, prompt_name="summarizer_v2")

    # Смена промпта на лету
    summarizer.set_prompt("summarizer_test")
    summary = await summarizer.summarize(cleaned_transcript, metadata)
```

## Динамический выбор промпта

Для итеративной настройки формата саммари можно создавать разные версии промптов:

| Файл | Назначение |
|------|------------|
| `config/prompts/summarizer.md` | Основной промпт (по умолчанию) |
| `config/prompts/summarizer_v2.md` | Тестовая версия |
| `config/prompts/summarizer_compact.md` | Компактный формат |

После подбора лучшего варианта — переименовать его в `summarizer.md`.

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

## Структура ответа LLM

```json
{
  "summary": "2-3 абзаца: о чём видео и какую проблему решает",

  "key_points": [
    "Ключевой тезис 1",
    "Ключевой тезис 2",
    "Ключевой тезис 3",
    "Ключевой тезис 4",
    "Ключевой тезис 5"
  ],

  "recommendations": [
    "Практическая рекомендация 1",
    "Практическая рекомендация 2",
    "Практическая рекомендация 3"
  ],

  "target_audience": "Для кого полезно это видео",

  "questions_answered": [
    "На какой вопрос отвечает видео 1?",
    "На какой вопрос отвечает видео 2?",
    "На какой вопрос отвечает видео 3?"
  ],

  "classification": {
    "section": "Обучение|Продукты|Бизнес|Мотивация",
    "subsection": "Подкатегория внутри секции",
    "tags": ["тег1", "тег2", "тег3", "тег4", "тег5"],
    "access_level": 1
  }
}
```

## Модель данных

```python
from pydantic import BaseModel, Field

class VideoSummary(BaseModel):
    """Саммари видео для БЗ 2.0."""

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

## Валидация

### Секции (VALID_SECTIONS)

```python
VALID_SECTIONS = ["Обучение", "Продукты", "Бизнес", "Мотивация"]
```

Если LLM вернёт невалидную секцию — автоматически подставляется "Обучение" с предупреждением в лог.

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

## Обработка ответа LLM

1. **Извлечение JSON** — поддержка markdown-обёрток (` ```json ... ``` `)
2. **Сглаживание структуры** — поля из `classification` перемещаются на верхний уровень
3. **Валидация секции** — проверка на допустимые значения
4. **Создание VideoSummary** — Pydantic модель с валидацией access_level

## Тестирование

```bash
cd backend && .venv/bin/python -m app.services.summarizer
```

Тесты:
1. Загрузка промпта
2. Извлечение JSON (plain)
3. Извлечение JSON (markdown)
4. Парсинг полей саммари
5. Валидация секций (valid/invalid)
6. Полная саммаризация с LLM

---

## Связанные документы

- **Код:** [`backend/app/services/summarizer.py`](../../backend/app/services/summarizer.py)
- **Промпт:** [`config/prompts/summarizer.md`](../../config/prompts/summarizer.md)
- **Модели:** [`backend/app/models/schemas.py`](../../backend/app/models/schemas.py)
- **API:** [api-reference.md](../api-reference.md#ollama-api)
