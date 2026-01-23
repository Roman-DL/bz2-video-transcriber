# Этап 6: Summarize (Генерация конспекта)

[< Назад: Longread](05-longread.md) | [Обзор Pipeline](README.md) | [Далее: Save >](07-save.md)

---

## Назначение

Создание структурированного конспекта (2-4 страницы) из **очищенного транскрипта** для быстрого ознакомления с содержанием видео.

Конспект — это выжимка ключевой информации для тех, кто УЖЕ слушал тему:
- Суть видео в 2-3 предложениях
- Основные концепции и термины
- Практические инструменты и техники
- Цитаты спикера (дословно из транскрипта)
- Инсайты и рекомендации к действию

**Важно:** Генерируется только для `content_type=educational`.

## Архитектура (v0.24+)

```
CleanedTranscript (~50K chars)
       │
       ▼
┌───────────────────────────┐
│    SummaryGenerator       │  → 3-компонентная архитектура промптов
│  system + instructions +  │
│       template            │
└───────────┬───────────────┘
            │
            ▼
        Summary
 (с topic_area, access_level)
```

**Почему из cleaned, а не из longread (v0.24+):**
- Видит ВСЕ детали оригинала — не "копия копии"
- Цитаты дословные из транскрипта
- LLM сама классифицирует тему (topic_area, access_level)
- Не ограничен редактурой лонгрида

**3-компонентная архитектура промптов:**
- `summary_system.md` — роль и назначение
- `summary_instructions.md` — правила извлечения по типам тем
- `summary_template.md` — JSON-структура ответа

## Модель данных: Summary

| Поле | Тип | Описание |
|------|-----|----------|
| video_id | str | ID видео |
| title | str | Название |
| speaker | str | Спикер |
| date | date | Дата |
| essence | str | Суть видео (2-3 абзаца) |
| key_concepts | list[str] | Ключевые концепции (3-5) |
| practical_tools | list[str] | Практические инструменты (2-4) |
| quotes | list[str] | Дословные цитаты спикера (2-4) |
| insight | str | Главный инсайт (1 предложение) |
| actions | list[str] | Рекомендации к действию (2-3) |
| topic_area | list[str] | Тематические области (LLM) |
| tags | list[str] | Теги для поиска (LLM) |
| access_level | str | Уровень доступа (LLM) |
| related | list[str] | Связанные документы |
| model_name | str | Используемая LLM модель |
| tokens_used | TokensUsed \| None | Статистика токенов (v0.42+) |
| cost | float \| None | Стоимость в USD (v0.42+) |
| processing_time_sec | float \| None | Время обработки в секундах (v0.42+) |

## Классификация (генерируется LLM)

### Допустимые topic_area

| Значение | Описание |
|----------|----------|
| `продажи` | Работа с клиентами, первички, продажи программ |
| `спонсорство` | Работа с командой, планирование, 3D-чаты |
| `лидерство` | Построение организации, первое поколение |
| `мотивация` | Философия, мышление, преодоление кризисов |
| `инструменты` | Конкретные методики (дом-магазин, солнышко) |
| `маркетинг-план` | Статусы, квалификации, роялти |

### Уровни доступа (access_level)

| Значение | Аудитория |
|----------|-----------|
| `consultant` | Все консультанты (по умолчанию) |
| `leader` | Лидеры уровня СТ+ |
| `personal` | Только для личного пользования |

## Формат выходного файла

Конспект сохраняется как `summary.md` в формате Obsidian с callouts:

```markdown
---
title: Мастер-класс по питанию
speaker: Иван Петров
date: 2025-01-15
duration: "01:23:45"
topic_area: ["продажи", "инструменты"]
tags: [дом-магазин, клиенты, первички]
access_level: consultant
type: summary
---

# Мастер-класс по питанию

> Спикер: Иван Петров | Дата: 15 января 2025 | Длительность: 1:23:45

> [!abstract] Суть
> Краткое описание содержания видео в 2-3 абзацах.
> Какую проблему решает, для кого полезна.

> [!info] Ключевые концепции
> - Концепция 1 — описание
> - Концепция 2 — описание

> [!tip] Практические инструменты
> - **Дом-магазин:** краткое описание
> - **3D-чат:** краткое описание

> [!quote] Цитаты
> - "Дословная цитата спикера 1"
> - "Дословная цитата спикера 2"

> [!success] Главный инсайт
> Одна мысль которую человек унесёт с собой.

> [!todo] К действию
> - [ ] Действие 1
> - [ ] Действие 2
```

## Конфигурация

Параметры в `config/models.yaml`:

```yaml
defaults:
  summary:
    max_input_chars: 50000

models:
  qwen2.5:14b:
    summary:
      max_input_chars: 60000
```

## Промпты (3-компонентная архитектура)

Файлы в `config/prompts/summary/` (v0.30+ иерархическая структура):
- `system.md` — системный промпт (роль, назначение)
- `instructions.md` — инструкции по извлечению
- `template.md` — JSON-формат ответа

Поддерживаются варианты промптов через API (v0.32+):
```python
prompt_overrides={"system": "system_v2", "instructions": "instructions"}
```

## Step-by-step режим

В режиме `/api/step/summarize`:
1. **Вход:** CleanedTranscript + VideoMetadata (v0.24+)
2. Генерирует конспект с topic_area, access_level
3. Возвращает без сохранения

**Breaking change в v0.24:** API `/step/summarize` принимает `cleaned_transcript` вместо `longread`.

## Условное выполнение

SummarizeStage использует `should_skip()`:

```python
def should_skip(self, context: StageContext) -> bool:
    metadata = context.get_result("parse")
    return metadata.content_type == ContentType.LEADERSHIP
```

Для leadership контента используется StoryStage вместо Summarize.

## Оценка времени

| Входные данные | Время |
|----------------|-------|
| Транскрипт ~20K chars | ~30-60 сек |
| Транскрипт ~50K chars | ~1-2 мин |

---

## Связанные файлы

- **Сервис:** `backend/app/services/summary_generator.py`
- **Stage:** `backend/app/services/stages/summarize_stage.py`
- **Модели:** `backend/app/models/schemas.py` → `Summary`
- **Промпты:** `config/prompts/summary/` (system.md, instructions.md, template.md)
- **Конфигурация:** `config/models.yaml` → `summary`

## История изменений

- **v0.42:** Добавлены метрики tokens_used, cost, processing_time_sec.
- **v0.30:** Иерархическая структура промптов (`config/prompts/summary/`).
- **v0.29:** Удалён fallback механизм — при ошибке выбрасывается StageError.
- **v0.24:** Генерация из CleanedTranscript вместо Longread. 3-компонентная архитектура промптов. LLM генерирует topic_area, tags, access_level.
- **v0.13:** Генерация из Longread (заменено в v0.24)
