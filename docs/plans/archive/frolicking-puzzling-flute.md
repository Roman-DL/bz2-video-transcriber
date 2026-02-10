# План исправления: Backend не запускается после v0.58

## Диагностика

**Ошибка**: `NameError: name 'SlidesExtractionResult' is not defined`

**Причина**: В [schemas.py:952](backend/app/models/schemas.py#L952) класс `PipelineResults` ссылается на `SlidesExtractionResult`, который определён позже в файле (строка 1105).

**Файл**: `backend/app/models/schemas.py`

## Анализ архитектуры

### Текущая структура schemas.py

```
1. Base models + Enums (строки 24-98)
2. Core data models (VideoMetadata, Transcript, Chunks) (строки 100-402)
3. Content result models (Story, Longread, Summary) (строки 444-889)
4. Processing models (ProcessingResult, ProcessingJob) (строки 891-913)
5. PipelineResults (АГРЕГАТОР) (строка 920) ← ссылается на Slides
6. API Request models (строки 960-1089)
7. Slides models (строки 1091-1147) ← ПРОБЛЕМА: определены ПОСЛЕ агрегатора
8. Prompt models (строки 1189-1219)
```

### Проблема архитектуры

`SlidesExtractionResult` — это модель результата этапа (как `Longread`, `Summary`, `Story`), но она находится в секции API Request моделей вместе с `StepSlidesRequest`.

### Принцип чистой архитектуры

**Все модели данных определяются ДО агрегатора.**

## План исправления

### Шаг 1: Переместить Slides data models в секцию результатов

Переместить `SlideInput` и `SlidesExtractionResult` из строк 1091-1131 в секцию "Content result models" — **перед `ProcessingResult`** (перед строкой 891).

**Новая структура:**

```
...
3. Content result models:
   - Story (строка 455)
   - Longread (строка 597)
   - Summary (строка 728)
   - SlideInput (ПЕРЕМЕСТИТЬ СЮДА)      ← NEW
   - SlidesExtractionResult (ПЕРЕМЕСТИТЬ СЮДА)  ← NEW
4. Processing models (ProcessingResult, ProcessingJob)
5. PipelineResults (агрегатор) — теперь все зависимости выше ✓
6. API Request models
7. Step Request models (включая StepSlidesRequest — остаётся на месте)
8. Prompt models
```

### Шаг 2: Обновить комментарии-разделители

Добавить секцию `# Slides Extraction Models` перед перемещёнными классами.

## Файлы для изменения

| Файл | Изменение |
|------|-----------|
| `backend/app/models/schemas.py` | Переместить SlideInput, SlidesExtractionResult выше PipelineResults |

## Верификация

1. Проверить синтаксис локально:
   ```bash
   cd backend && python3 -m py_compile app/models/schemas.py
   ```

2. Деплой на сервер:
   ```bash
   ./scripts/deploy.sh
   ```

3. Проверить health endpoint:
   ```bash
   curl http://100.64.0.1:8801/health
   ```

4. Проверить frontend загружает inbox/archive без ошибок

## Оценка риска

**Низкий** — перемещение классов внутри файла, импорты не меняются, логика не затрагивается.
