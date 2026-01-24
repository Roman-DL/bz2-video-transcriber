---
doc_type: reference
status: active
updated: 2026-01-24
audience: [developer, ai-agent]
tags:
  - pipeline
  - stage
---

# Этап 5: Longread (Генерация лонгрида)

[< Назад: Slides](04-slides.md) | [Обзор Pipeline](README.md) | [Далее: Summarize >](06-summarize.md)

---

## Назначение

Создание развёрнутого структурированного текста (5-10 страниц) из очищенного транскрипта.

Лонгрид — это переработанная версия транскрипта, где:
- Устранены устные обороты и повторы
- Текст организован по смысловым секциям
- Сохранены все ключевые идеи и примеры
- Добавлены введение и заключение

> **v0.25+:** Longread теперь зависит от `clean`, а не от `chunk`. Pipeline order изменён.

## Input / Output

### Input (из StageContext)

| Источник | Тип | Описание |
|----------|-----|----------|
| `parse` | `VideoMetadata` | Метаданные видео |
| `clean` | `CleanedTranscript` | Очищенный транскрипт |

### Output

| Тип | Описание |
|-----|----------|
| `Longread` | Лонгрид с секциями, intro/conclusion и классификацией |

### Условное выполнение

Stage пропускается для `ContentType.LEADERSHIP` — вместо него выполняется `StoryStage`.

```python
def should_skip(self, context: StageContext) -> bool:
    metadata = context.get_result("parse")
    return metadata.content_type == ContentType.LEADERSHIP
```

## Архитектура: Map-Reduce

Генерация выполняется в несколько фаз:

```
CleanedTranscript
       │
       ▼
┌─────────────────────────────┐
│   SPLIT: TextSplitter       │  → Разбиение на TextParts
└────────────┬────────────────┘
             │ list[TextPart]
             ▼
┌─────────────────────────────┐
│   OUTLINE (optional)        │  → Только для текстов > 10K chars
│   OutlineExtractor          │
└────────────┬────────────────┘
             │ TranscriptOutline | None
             ▼
┌─────────────────────────────┐
│   MAP: Section Generation   │  → Параллельная обработка групп parts
│   (system + instructions)   │     (max 2 параллельно)
└────────────┬────────────────┘
             │ list[LongreadSection]
             ▼
┌─────────────────────────────┐
│  REDUCE: Frame Generation   │  → Intro, Conclusion, Classification
│  (system + instructions +   │
│   template)                 │
└────────────┬────────────────┘
             │
             ▼
         Longread
```

### SPLIT: Разбиение текста

Текст разбивается на части через `TextSplitter`:

```python
text_parts = self.text_splitter.split(cleaned_transcript.text)
```

### OUTLINE: Извлечение структуры (условно)

Outline извлекается только для больших текстов:

| Параметр | Значение | Описание |
|----------|----------|----------|
| `large_text_threshold` | 10000 | Порог в символах для извлечения outline |

### MAP: Генерация секций

Parts группируются и обрабатываются параллельно:

| Параметр | Default | Описание |
|----------|---------|----------|
| `parts_per_section` | 2 | TextParts на одну секцию |
| `max_parallel_sections` | 2 | Одновременных LLM-запросов |

Каждый запрос получает:
- Группу TextParts с текстом
- Outline контекст (если извлечён)
- Информацию о позиции (1/N, 2/N, ...)

### REDUCE: Генерация рамки

После генерации всех секций выполняется финальный запрос:
- Создание введения (без спойлеров содержания)
- Создание заключения (ключевые выводы)
- Классификация (`topic_area`, `tags`, `access_level`)

## Slides интеграция (v0.50+)

Если предоставлен `slides_text`, он добавляется к транскрипту:

```python
longread = await generator.generate(
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

## Модель данных

### LongreadSection

Одна секция лонгрида:

| Поле | Тип | Описание |
|------|-----|----------|
| `index` | `int` | Номер секции (1-based) |
| `title` | `str` | Заголовок секции |
| `content` | `str` | Текст секции в Markdown |
| `source_chunks` | `list[int]` | Индексы исходных TextParts |
| `word_count` | `int` | Количество слов |

### Longread

Полный лонгрид с метаданными:

| Поле | Тип | Описание |
|------|-----|----------|
| `video_id` | `str` | Уникальный ID видео |
| `title` | `str` | Название видео |
| `speaker` | `str` | Спикер |
| `speaker_status` | `str` | Статус спикера (v0.23+) |
| `date` | `date` | Дата записи |
| `event_type` | `str` | Тип события (ПШ, etc.) |
| `stream` | `str` | Поток (SV, etc.) |
| `introduction` | `str` | Вступление |
| `sections` | `list[LongreadSection]` | Секции |
| `conclusion` | `str` | Заключение |
| `topic_area` | `list[str]` | Тематика (v0.23+) |
| `tags` | `list[str]` | Теги для поиска |
| `access_level` | `str` | Уровень доступа |
| `model_name` | `str` | Использованная модель |
| `tokens_used` | `TokensUsed \| None` | Токены (v0.42+) |
| `cost` | `float \| None` | Стоимость USD (v0.42+) |
| `processing_time_sec` | `float \| None` | Время обработки (v0.42+) |
| `total_word_count` | `int` | Общее кол-во слов (computed) |
| `total_sections` | `int` | Кол-во секций (computed) |

**Классификация:**

| Поле | Допустимые значения |
|------|---------------------|
| `topic_area` | `продажи`, `спонсорство`, `лидерство`, `мотивация`, `инструменты`, `маркетинг-план` |
| `access_level` | `consultant`, `leader`, `personal` |

## Формат выходного файла

Лонгрид сохраняется как `longread.md` в папке архива:

```markdown
---
title: Мастер-класс по питанию
speaker: Иван Петров
speaker_status: GET
date: 2025-01-15
event_type: ПШ
stream: SV
topic_area: [инструменты, продажи]
tags: [белки, жиры, углеводы]
access_level: consultant
word_count: 3500
---

# Мастер-класс по питанию

> Спикер: Иван Петров (GET) | Дата: 15 января 2025 | ПШ SV

## Введение

Краткое введение в тему...

## 1. Белки и их роль

Содержание первой секции...

## 2. Жиры в питании

Содержание второй секции...

## Заключение

Ключевые выводы и рекомендации...
```

## Конфигурация

Параметры настраиваются в `config/models.yaml`:

```yaml
defaults:
  longread:
    parts_per_section: 2
    max_parallel_sections: 2
    large_text_threshold: 10000

models:
  claude-sonnet-4-5:
    longread:
      parts_per_section: 3
      max_parallel_sections: 2
```

## Промпты

Промпты организованы в `config/prompts/longread/` (v0.30+):

| Файл | Назначение |
|------|------------|
| `system.md` | Роль и общие инструкции |
| `instructions.md` | Принципы генерации |
| `template.md` | Шаблон JSON для frame |
| `section.md` | (legacy) Генерация секции |
| `combine.md` | (legacy) Объединение |

Архитектура промптов (v0.23+):
```
system.md + instructions.md → Section generation
system.md + instructions.md + template.md → Frame generation
```

## Step-by-step режим

В режиме `POST /api/step/longread`:

```python
{
    "cleaned_transcript": {...},
    "metadata": {...},
    "slides_text": "...",           # опционально (v0.50+)
    "model": "claude-sonnet-4-5",   # опционально
    "prompt_overrides": {           # опционально (v0.32+)
        "system": "system",
        "instructions": "instructions",
        "template": "template"
    }
}
```

Возвращает `Longread` без сохранения в файл.

## Метрики (v0.42+)

Результат содержит метрики для отладки:

```python
longread.tokens_used      # TokensUsed(input=5000, output=2000)
longread.cost             # 0.0255 (USD)
longread.processing_time_sec  # 45.3
```

---

## Связанные файлы

- **Stage:** [backend/app/services/stages/longread_stage.py](../../backend/app/services/stages/longread_stage.py)
- **Сервис:** [backend/app/services/longread_generator.py](../../backend/app/services/longread_generator.py)
- **Модели:** [backend/app/models/schemas.py](../../backend/app/models/schemas.py) → `Longread`, `LongreadSection`
- **Промпты:** [config/prompts/longread/](../../config/prompts/longread/)
- **Конфигурация:** [config/models.yaml](../../config/models.yaml) → `longread`
