# Этап 5: Summarize (+ Classification)

[< Назад: Chunk](04-chunk.md) | [Обзор Pipeline](README.md) | [Далее: Save >](06-save.md)

---

## Назначение

Создание структурированного саммари для File Search в БЗ 2.0.

## LLM Summarization

```python
async def summarize_transcript(
    cleaned_text: str,
    metadata: VideoMetadata,
    client: AsyncClient
) -> dict:
    """
    Создаёт саммари и классификацию для БЗ 2.0.

    Returns:
        {
            "summary": "...",
            "key_points": [...],
            "recommendations": [...],
            "target_audience": "...",
            "classification": {
                "section": "...",
                "subsection": "...",
                "tags": [...]
            }
        }
    """

    prompt = load_prompt("config/prompts/summarizer.md")
    prompt = prompt.format(
        title=metadata.title,
        speaker=metadata.speaker,
        date=metadata.date.strftime("%d %B %Y"),
        stream=metadata.stream_full,
        transcript=cleaned_text
    )

    response = await client.chat(
        model="qwen2.5:14b",
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.5},
        format="json"
    )

    return json.loads(response["message"]["content"])
```

## Структура ответа

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

  "classification": {
    "section": "Один из: Обучение | Продукты | Бизнес | Мотивация",
    "subsection": "Подкатегория внутри секции",
    "tags": ["тег1", "тег2", "тег3"],
    "access_level": 1
  },

  "questions_answered": [
    "На какой вопрос отвечает видео 1?",
    "На какой вопрос отвечает видео 2?"
  ]
}
```

## Модель данных

```python
@dataclass
class VideoSummary:
    """Саммари видео для БЗ 2.0."""

    # Контент
    summary: str                      # Краткое содержание
    key_points: list[str]             # Ключевые тезисы
    recommendations: list[str]        # Практические рекомендации
    target_audience: str              # Для кого полезно
    questions_answered: list[str]     # Вопросы, на которые отвечает

    # Классификация
    section: str                      # Обучение / Продукты / Бизнес / Мотивация
    subsection: str                   # Подкатегория
    tags: list[str]                   # Теги для поиска
    access_level: int                 # Уровень доступа (1-4)
```

## Классификация

### Секции

| Секция | Описание |
|--------|----------|
| Обучение | Методики, техники, навыки |
| Продукты | Продукция Herbalife |
| Бизнес | Построение бизнеса, рекрутинг |
| Мотивация | Истории успеха, вдохновение |

### Уровни доступа

| Уровень | Аудитория |
|---------|-----------|
| 1 | Все консультанты |
| 2 | Супервайзеры и выше |
| 3 | ГЕТ и выше |
| 4 | Президентская Команда |

---

## Связанные документы

- **Код:** [`backend/app/services/summarizer.py`](../../backend/app/services/summarizer.py)
- **Промпт:** [`config/prompts/summarizer.md`](../../config/prompts/summarizer.md)
- **API:** [api-reference.md](../api-reference.md#ollama-api)
