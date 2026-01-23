# 05b. Story (Генерация лидерских историй)

[< Назад: Longread](05-longread.md) | [Обзор Pipeline](README.md) | [Далее: Summarize >](06-summarize.md)

---

> Альтернатива longread+summarize для content_type=LEADERSHIP

## Обзор

Story Stage генерирует структурированную 8-блочную историю из транскрипта для лидерского контента. Вместо longread.md и summary.md создаётся единый story.md.

## Input / Output

### Input (из StageContext)

| Источник | Тип | Описание |
|----------|-----|----------|
| `parse` | `VideoMetadata` | Метаданные (content_type, speaker, event_name) |
| `clean` | `CleanedTranscript` | Очищенный транскрипт |

### Output

| Тип | Описание |
|-----|----------|
| `Story` | 8-блочная история с метаданными и метриками |

### Условное выполнение

Stage пропускается для `ContentType.EDUCATIONAL` — вместо него выполняются `LongreadStage` + `SummarizeStage`.

```python
def should_skip(self, context: StageContext) -> bool:
    metadata = context.get_result("parse")
    return metadata.content_type != ContentType.LEADERSHIP
```

## Pipeline

| content_type | Этапы |
|--------------|-------|
| `educational` | clean → longread + summarize → chunk → save |
| `leadership` | clean → **story** → chunk → save |

> **v0.25+:** `chunk` выполняется ПОСЛЕ story (H2 парсинг из story.md)

## Модель данных

### StoryBlock

Один блок истории (1 из 8):

| Поле | Тип | Описание |
|------|-----|----------|
| `block_number` | `int` | Номер блока (1-8) |
| `block_name` | `str` | Название блока |
| `content` | `str` | Текст блока в Markdown |

### Story

Полная история с метаданными:

| Поле | Тип | Описание |
|------|-----|----------|
| `video_id` | `str` | ID видео |
| `names` | `str` | "Дмитрий и Юлия Антоновы" |
| `current_status` | `str` | "GET Team" |
| `event_name` | `str` | "Форум TABTeam (Москва)" |
| `date` | `date` | Дата события |
| `main_insight` | `str` | Главный инсайт (1 предложение) |
| `blocks` | `list[StoryBlock]` | 8 блоков |
| `time_in_business` | `str` | "12 лет" |
| `time_to_status` | `str` | "8 лет" |
| `speed` | `str` | быстро / средне / долго / очень долго |
| `business_format` | `str` | клуб / онлайн / гибрид |
| `is_family` | `bool` | Семейный бизнес |
| `had_stagnation` | `bool` | Была стагнация |
| `stagnation_years` | `int` | Лет стагнации |
| `had_restart` | `bool` | Был рестарт |
| `key_pattern` | `str` | Ключевой паттерн |
| `mentor` | `str` | Имя ментора |
| `tags` | `list[str]` | Теги для поиска |
| `access_level` | `str` | consultant / leader / personal |
| `related` | `list[str]` | Связанные истории |
| `model_name` | `str` | Использованная модель |
| `tokens_used` | `TokensUsed \| None` | Токены (v0.42+) |
| `cost` | `float \| None` | Стоимость USD (v0.42+) |
| `processing_time_sec` | `float \| None` | Время обработки (v0.42+) |
| `total_blocks` | `int` | Количество блоков (computed) |

## 8 блоков Story

| № | Название | Содержание |
|---|----------|------------|
| 1 | Кто они | Предыстория: образование, семья, чем занимались до |
| 2 | Путь в бизнес | Как пришли в Herbalife, первый опыт |
| 3 | Рост и вызовы | Этапы развития, трудности, преодоление |
| 4 | Ключ к статусу | Переломный момент, что изменило траекторию |
| 5 | Как устроен бизнес | Формат работы, география, команда |
| 6 | Принципы и советы | Ключевые рекомендации от лидеров |
| 7 | Итоги | Текущие результаты, достижения |
| 8 | Заметки аналитика | Аналитические наблюдения, паттерны |

## Slides интеграция (v0.53+)

Если предоставлен `slides_text`, он добавляется к транскрипту:

```python
story = await generator.generate(
    cleaned_transcript,
    metadata,
    slides_text=slides_extraction.extracted_text,  # optional
)
```

Текст слайдов добавляется в конец с разделителем:

```markdown
{transcript_text}

---

## Дополнительная информация со слайдов презентации

{slides_text}
```

## Промпт-архитектура (v0.30+)

Промпты организованы в `config/prompts/story/`:

| Файл | Назначение |
|------|------------|
| `system.md` | Роль и правила |
| `instructions.md` | Детальные инструкции по блокам |
| `template.md` | JSON-структура для ответа |

### Сборка промпта

```python
# В StoryGenerator
system_prompt = load_prompt("story", "system", settings)
instructions = load_prompt("story", "instructions", settings)
template = load_prompt("story", "template", settings)

# Объединяется в единый prompt:
prompt = f"""
{system_prompt}

---

{instructions}

---

## Задание

Создай конспект лидерской истории по шаблону 8 блоков.

**Имена:** {metadata.speaker}
**Событие:** {metadata.event_name}
**Дата:** {metadata.date.isoformat()}

### Транскрипт

{cleaned_transcript.text}

### Формат ответа

{template}
"""

response, usage = await ai_client.generate(prompt, model=settings.summarizer_model)
```

## Классификация speed

| speed | Критерий |
|-------|----------|
| `быстро` | До статуса < 3 лет |
| `средне` | 3-7 лет |
| `долго` | 7-15 лет |
| `очень долго` | > 15 лет |

## Классификация business_format

| format | Описание |
|--------|----------|
| `клуб` | Физический клуб здорового питания |
| `онлайн` | Только онлайн-консультации |
| `гибрид` | Сочетание офлайн и онлайн |

## Выходной файл

### story.md

```markdown
---
type: "leadership-story"
names: "Дмитрий и Юлия Антоновы"
current_status: "GET Team"
event_name: "Форум TABTeam"
date: 2025-01-20
main_insight: "Стагнация — не приговор, если есть команда"
time_in_business: "12 лет"
time_to_status: "8 лет"
speed: "долго"
business_format: "гибрид"
is_family: true
had_stagnation: true
stagnation_years: 5
tags: [стагнация, семейная-пара, клуб]
access_level: "leader"
---

# История Антоновых: от консультантов до GET Team

## Главный инсайт

Стагнация — не приговор, если есть команда...

## 1. Кто они

Дмитрий — инженер, Юлия — врач...

## 8. Заметки аналитика

Классический пример преодоления стагнации...
```

## Метрики (v0.42+)

Результат содержит метрики для отладки:

```python
story.tokens_used      # TokensUsed(input=8000, output=3000)
story.cost             # 0.0345 (USD)
story.processing_time_sec  # 62.5
```

## Step-by-step режим

В режиме `POST /api/step/story`:

```python
{
    "cleaned_transcript": {...},
    "metadata": {...},
    "slides_text": "...",           # опционально (v0.53+)
    "model": "claude-sonnet-4-5",   # опционально
    "prompt_overrides": {           # опционально (v0.32+)
        "system": "system",
        "instructions": "instructions",
        "template": "template"
    }
}
```

Возвращает `Story` без сохранения в файл.

## Отличия от Longread

| Аспект | Longread | Story |
|--------|----------|-------|
| Контент | Обучающие темы | Лидерские истории |
| Структура | Динамическое кол-во секций | Фиксированно 8 блоков |
| Фокус | Передача знаний | Путь и паттерны лидера |
| Дополнение | + summary.md | Только story.md |
| access_level | consultant / leader / personal | consultant / leader / personal |

---

## Связанные файлы

- **Stage:** [backend/app/services/stages/story_stage.py](../../backend/app/services/stages/story_stage.py)
- **Сервис:** [backend/app/services/story_generator.py](../../backend/app/services/story_generator.py)
- **Модели:** [backend/app/models/schemas.py](../../backend/app/models/schemas.py) → `Story`, `StoryBlock`
- **Промпты:** [config/prompts/story/](../../config/prompts/story/)

## См. также

- [05-longread.md](05-longread.md) — для educational контента
- [06-summarize.md](06-summarize.md) — summary для educational
- [01-parse.md](01-parse.md) — определение content_type
