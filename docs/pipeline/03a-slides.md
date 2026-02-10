---
doc_type: reference
status: active
updated: 2026-01-24
audience: [developer, ai-agent]
tags:
  - pipeline
  - stage
---

# Этап 3a: Slides (Опциональный)

[< Назад: Clean](03-clean.md) | [Обзор Pipeline](README.md) | [Далее: Chunk >](04-chunk.md)

---

## Назначение

Извлечение структурированного текста со слайдов презентаций с использованием Claude Vision API.

> **Примечание:** Этап опциональный — выполняется только при наличии прикреплённых слайдов.

## Input / Output

| Направление | Тип | Описание |
|-------------|-----|----------|
| **Input** | `list[SlideInput]` | Список слайдов (base64 encoded) |
| **Output** | `SlidesExtractionResult` | Извлечённый текст с метриками |

**Особенность:** Реализован как API endpoint `/api/step/slides`, а не как stage-абстракция.

### Поля SlideInput

| Поле | Тип | Описание |
|------|-----|----------|
| `filename` | `str` | Имя файла |
| `content_type` | `str` | MIME тип |
| `data` | `str` | Base64 encoded контент |

### Поля SlidesExtractionResult

| Поле | Тип | Описание |
|------|-----|----------|
| `extracted_text` | `str` | Текст в markdown формате |
| `slides_count` | `int` | Количество обработанных слайдов |
| `chars_count` | `int` | Количество символов |
| `words_count` | `int` | Количество слов |
| `tables_count` | `int` | Обнаруженные таблицы |
| `model` | `str` | Использованная модель |
| `tokens_used` | `TokensUsed \| None` | Статистика токенов |
| `cost` | `float \| None` | Стоимость в USD |
| `processing_time_sec` | `float \| None` | Время обработки |

## Архитектура

```
SlideInput[] (images/PDF)
       │
       ▼
┌─────────────────┐
│ PDF → Images    │  PyMuPDF (fitz)
│ (если PDF)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Batch Processing│  По 5 слайдов
│ (Claude Vision) │  (claude-haiku-4-5)
└────────┬────────┘
         │
         ▼
  SlidesExtractionResult
  (markdown с таблицами)
```

### Поддерживаемые форматы

| Формат | MIME Type | Обработка |
|--------|-----------|-----------|
| JPEG | `image/jpeg` | Напрямую |
| PNG | `image/png` | Напрямую |
| WebP | `image/webp` | Напрямую |
| GIF | `image/gif` | Напрямую |
| PDF | `application/pdf` | Конвертация в PNG |

## Место в Pipeline

```
Parse → Transcribe → Clean → [SLIDES] → Longread/Story → Summary → Chunk → Save
                              ↑
                     Условно, если есть слайды
```

Извлечённый текст передаётся в longread/story как дополнительный контекст для обогащения материала.

## Конфигурация

| Параметр | Значение | Описание |
|----------|----------|----------|
| `DEFAULT_SLIDES_MODEL` | `claude-haiku-4-5` | Модель по умолчанию |
| `DEFAULT_BATCH_SIZE` | 5 | Слайдов за один API вызов |
| `temperature` | 0.3 | Для структурированного извлечения |
| `num_predict` | 4096 | Максимум токенов на батч |

## Лимиты (из CLAUDE.md)

| Параметр | Лимит | Причина |
|----------|-------|---------|
| Макс. файлов | 50 | Контекст модели |
| Макс. размер файла | 10 MB | API ограничение |
| Общий размер | 100 MB | Память браузера |

## Промпты

Промпты находятся в `config/prompts/slides/`:
- `system.md` — роль и правила извлечения
- `user.md` — инструкции по обработке изображений

## API Endpoint

```python
# POST /api/step/slides
{
    "slides": [
        {
            "filename": "slide1.jpg",
            "content_type": "image/jpeg",
            "data": "base64..."
        },
        {
            "filename": "presentation.pdf",
            "content_type": "application/pdf",
            "data": "base64..."
        }
    ],
    "model": "claude-haiku-4-5",      # опционально
    "prompt_overrides": {...}          # опционально
}
```

## Доступные модели

| Модель | Скорость | Стоимость | Качество |
|--------|----------|-----------|----------|
| `claude-haiku-4-5` | Быстро | Дёшево | Хорошее (default) |
| `claude-sonnet-4-5` | Средне | Средне | Отличное |
| `claude-opus-4-5` | Медленно | Дорого | Максимальное |

## Логирование

```
INFO: Extracting text from 10 slides using claude-haiku-4-5
DEBUG: Processing batch 1-5/10
DEBUG: Processing batch 6-10/10
INFO: Slides extraction complete: 10 slides, 5432 chars, 2 tables, 8.3s
PERF | slides | slides=10 | chars=5432 | tables=2 | tokens=12000+1500 | cost=$0.0156 | time=8.3s
```

## Тестирование

```bash
cd backend
source .venv/bin/activate
python -m app.services.slides_extractor
```

**Требования для тестов:**
- `ANTHROPIC_API_KEY` — API ключ Claude
- `PyMuPDF` (fitz) — для работы с PDF

---

## Связанные файлы

- **Сервис:** [`backend/app/services/slides_extractor.py`](../../backend/app/services/slides_extractor.py)
- **API:** [`backend/app/api/step_routes.py`](../../backend/app/api/step_routes.py) — endpoint `/api/step/slides`
- **Промпты:**
  - [`config/prompts/slides/system.md`](../../config/prompts/slides/system.md)
  - [`config/prompts/slides/user.md`](../../config/prompts/slides/user.md)
- **Модели:** [`backend/app/models/schemas.py`](../../backend/app/models/schemas.py) — `SlideInput`, `SlidesExtractionResult`
- **Утилиты:** [`backend/app/utils/pdf_utils.py`](../../backend/app/utils/pdf_utils.py) — `pdf_to_images()`
- **ADR:** [`docs/decisions/010-slides-integration.md`](../decisions/010-slides-integration.md)
