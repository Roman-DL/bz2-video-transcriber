# Этап 5: Longread (Генерация лонгрида)

[< Назад: Chunk](04-chunk.md) | [Обзор Pipeline](README.md) | [Далее: Summarize >](06-summarize.md)

---

## Назначение

Создание развёрнутого структурированного текста (5-10 страниц) из семантических чанков транскрипта.

Лонгрид — это переработанная версия транскрипта, где:
- Устранены устные обороты и повторы
- Текст организован по смысловым секциям
- Сохранены все ключевые идеи и примеры
- Добавлены введение и заключение

## Архитектура: Map-Reduce

Генерация выполняется в два этапа для обеспечения качества на больших объёмах.

```
TranscriptChunks
       │
       ▼
┌─────────────────────────────┐
│   MAP: Section Generation   │  → Параллельная обработка групп чанков
│   (longread_section.md)     │     (max 3 параллельно)
└────────────┬────────────────┘
             │ list[LongreadSection]
             ▼
┌─────────────────────────────┐
│  REDUCE: Combine + Classify │  → Intro, Conclusion, Classification
│  (longread_combine.md)      │
└────────────┬────────────────┘
             │
             ▼
         Longread
```

### MAP: Генерация секций

Чанки группируются (по умолчанию 3-4 на секцию) и обрабатываются параллельно:

| Параметр | Значение | Описание |
|----------|----------|----------|
| chunks_per_section | 3 | Чанков на одну секцию |
| max_parallel_sections | 3 | Одновременных LLM-запросов |

Каждый запрос получает:
- Группу чанков с текстом
- Глобальный outline транскрипта (контекст)
- Информацию о позиции (1/5, 2/5, ...)

### REDUCE: Объединение

После генерации всех секций выполняется финальный запрос:
- Создание введения (без спойлеров содержания)
- Создание заключения (ключевые выводы)
- Классификация (section, subsection, tags, access_level)

## Модель данных

### LongreadSection

Одна секция лонгрида:

| Поле | Тип | Описание |
|------|-----|----------|
| index | int | Номер секции (1-based) |
| title | str | Заголовок секции |
| content | str | Текст секции в Markdown |
| source_chunks | list[int] | Индексы исходных чанков |
| word_count | int | Количество слов |

### Longread

Полный лонгрид с метаданными:

| Поле | Тип | Описание |
|------|-----|----------|
| video_id | str | Уникальный ID видео |
| title | str | Название видео |
| speaker | str | Спикер |
| date | date | Дата записи |
| duration | str | Длительность (HH:MM:SS) |
| introduction | str | Вступление |
| conclusion | str | Заключение |
| sections | list[LongreadSection] | Секции |
| classification | dict | section, subsection, tags, access_level |
| total_word_count | int | Общее количество слов (computed) |

## Использование Outline

Лонгрид использует **TranscriptOutline** (тот же, что и Chunker) для:

1. **Глобального контекста** — LLM знает общую структуру видео
2. **Консистентности** — секции связаны единой логикой
3. **Эффективности** — outline не генерируется повторно

```
TranscriptOutline (shared)
       │
       ├──────────────────┬────────────────────┐
       ▼                  ▼                    ▼
   Chunker           LongreadGenerator    (будущее)
       │                  │
       ▼                  ▼
TranscriptChunks      Longread
```

## Формат выходного файла

Лонгрид сохраняется как `longread.md` в папке архива:

```markdown
---
title: Мастер-класс по питанию
speaker: Иван Петров
date: 2025-01-15
duration: "01:23:45"
section: Обучение
subsection: Питание
tags: [белки, жиры, углеводы]
access_level: 1
word_count: 3500
---

# Мастер-класс по питанию

> Спикер: Иван Петров | Дата: 15 января 2025 | Длительность: 1:23:45

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
    chunks_per_section: 3
    max_parallel_sections: 3

models:
  qwen2.5:14b:
    longread:
      chunks_per_section: 4
      max_parallel_sections: 3
```

## Промпты

| Файл | Назначение |
|------|------------|
| `config/prompts/longread_section.md` | Генерация одной секции |
| `config/prompts/longread_combine.md` | Intro, conclusion, classification |

Поддерживаются версии для конкретных моделей:
- `longread_section_qwen2.5:14b.md`
- `longread_combine_gemma2:9b.md`

## Step-by-step режим

В режиме `/api/steps/longread`:
1. Принимает готовые чанки и outline
2. Генерирует лонгрид автономно
3. Возвращает результат без сохранения

## Оценка времени

Для 2-часового видео (~30 чанков, ~10 секций):

| Этап | Время |
|------|-------|
| MAP (секции) | ~3-5 мин |
| REDUCE (combine) | ~30 сек |
| **Итого** | **~4-6 мин** |

---

## Связанные файлы

- **Сервис:** `backend/app/services/longread_generator.py`
- **Модели:** `backend/app/models/schemas.py` → `Longread`, `LongreadSection`
- **Промпты:** `config/prompts/longread_section.md`, `config/prompts/longread_combine.md`
- **Конфигурация:** `config/models.yaml` → `longread`
