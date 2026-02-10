---
doc_type: reference
status: active
updated: 2026-01-24
audience: [developer, ai-agent]
tags:
  - pipeline
  - stage
---

# Этап 7: Save Files

[< Назад: Summarize](06-summarize.md) | [Обзор Pipeline](README.md) | [Далее: Orchestrator >](08-orchestrator.md)

---

## Назначение

Сохранение результатов обработки в структурированный архив.

**Важно:** Сохраняемые файлы зависят от `content_type`:
- **EDUCATIONAL** → `longread.md` + `summary.md`
- **LEADERSHIP** → `story.md`

## SaveStage (v0.23+)

Stage-обёртка для интеграции с pipeline orchestrator.

```python
class SaveStage(BaseStage):
    name = "save"
    depends_on = ["parse", "transcribe", "clean", "chunk"]
    status = ProcessingStatus.SAVING
```

**Input (from context):**
- `parse` → VideoMetadata
- `transcribe` → Tuple[RawTranscript, audio_path]
- `clean` → CleanedTranscript
- `chunk` → Tuple[TranscriptChunks, outline, text_parts]
- `longread` + `summarize` (EDUCATIONAL) или `story` (LEADERSHIP)

**Output:** `list[str]` — список созданных файлов

## Структура архива

### EDUCATIONAL контент

```
/archive/{год}/{месяц}/{тип}.{поток}/{тема} ({спикер})/
├── {original_filename}.mp4      # Видео (перемещённое)
├── audio.mp3                    # Извлечённое аудио
├── transcript_chunks.json       # Для RAG
├── longread.md                  # Развёрнутый текст
├── summary.md                   # Конспект (File Search)
├── transcript_raw.txt           # Backup оригинала
├── transcript_cleaned.txt       # Очищенный текст
└── pipeline_results.json        # Для просмотра в UI (camelCase, v0.58+)
```

### LEADERSHIP контент (v0.23+)

```
/archive/{год}/Выездные/{event_name}/{Title}/
├── {original_filename}.mp4
├── audio.mp3
├── transcript_chunks.json
├── story.md                     # История 8 блоков (вместо longread + summary)
├── transcript_raw.txt
├── transcript_cleaned.txt
└── pipeline_results.json
```

## Выходные файлы

| Файл | Назначение | Content Type | Описание |
|------|------------|--------------|----------|
| `{название}.mp4` | Видео | Оба | Оригинальный файл |
| `audio.mp3` | Аудио | Оба | Извлечённая дорожка |
| `transcript_chunks.json` | RAG | Оба | Семантические чанки для индексации |
| `longread.md` | БЗ 2.0 | EDUCATIONAL | Развёрнутый текст (5-10 страниц) |
| `summary.md` | File Search | EDUCATIONAL | Конспект с callouts (2-4 страницы) |
| `story.md` | БЗ 2.0 | LEADERSHIP | История 8 блоков (v0.23+) |
| `transcript_raw.txt` | Backup | Оба | Текст с таймкодами |
| `transcript_cleaned.txt` | Чтение | Оба | Очищенный текст |
| `pipeline_results.json` | UI | Оба | Полные результаты (camelCase, v0.58+) |

## Формат longread.md

Markdown с YAML frontmatter — развёрнутое изложение:

```markdown
---
title: Название видео
speaker: Спикер
date: 2025-01-15
duration: "01:23:45"
section: Обучение
subsection: Питание
tags: [тег1, тег2]
access_level: 1
word_count: 3500
---

# Название

> Спикер: ... | Дата: ... | Длительность: ...

## Введение
...

## 1. Секция первая
...

## Заключение
...
```

Подробная структура: [data-formats.md](../data-formats.md#3-longreadmd)

## Формат summary.md

Markdown с Obsidian callouts — конспект для быстрого ознакомления:

```markdown
---
title: Название
speaker: Спикер
section: Обучение
tags: [тег1, тег2]
type: summary
---

# Название

> [!abstract] Суть
> ...

> [!info] Ключевые концепции
> - Концепция 1
> - Концепция 2

> [!tip] Практические инструменты
> ...
```

Подробная структура: [data-formats.md](../data-formats.md#4-summarymd)

## Формат story.md (v0.23+)

Markdown с YAML frontmatter — лидерская история из 8 блоков:

```markdown
---
title: Название истории
speaker: Спикер
date: 2025-01-15
duration: "01:23:45"
type: story
tags: [лидерство, история]
---

# Название истории

> Спикер: ... | Дата: ... | Длительность: ...

## 1. Жизнь до
...

## 2. Момент истины
...

## 3-8. Остальные блоки
...
```

Подробная структура: [data-formats.md](../data-formats.md#5-storymd)

## Формат transcript_chunks.json (BZ2-Bot v1.0, v0.60+)

JSON для импорта в BZ2-Bot:
- `version` — версия контракта (`"1.0"`)
- `materials[].description` — семантический индекс (Claude-generated)
- `materials[].short_description` — краткое описание для Telegram
- `materials[].metadata` — информация о видео
- `materials[].chunks[]` — массив с контекстной шапкой и метаданными

Генерация description: `_generate_description()` вызывает Claude (`describe_model`) до сохранения chunks. При ошибке — сохраняется с пустыми описаниями.

Подробная структура: [data-formats.md](../data-formats.md#1-transcript_chunksjson)

## Формат transcript_raw.txt

Текстовый файл с таймкодами:
```
[00:00:00] Первый сегмент текста.
[00:00:08] Второй сегмент текста.
```

## Формат pipeline_results.json

JSON для веб-интерфейса:
- `version` — версия формата
- `created_at` — дата/время обработки
- `metadata`, `raw_transcript`, `cleaned_transcript`
- `chunks`, `longread`, `summary`
- `display_text` — текст для отображения

Подробная структура: [data-formats.md](../data-formats.md#6-pipeline_resultsjson)

## Операции FileSaver

### Публичные методы (v0.23+)

| Метод | Content Type | Описание |
|-------|--------------|----------|
| `save()` | — | Backward compat → вызывает `save_educational()` |
| `save_educational()` | EDUCATIONAL | Сохраняет longread + summary |
| `save_leadership()` | LEADERSHIP | Сохраняет story |

### Приватные методы

| Метод | Описание |
|-------|----------|
| `_generate_description()` | Генерация description/short_description через Claude (v0.60+) |
| `_save_chunks_json()` | Генерация JSON в формате BZ2-Bot v1.0 (v0.60+) |
| `_save_longread_md()` | Сохранение лонгрида |
| `_save_summary_md()` | Сохранение конспекта |
| `_save_story_md()` | Сохранение истории (v0.23+) |
| `_save_raw_transcript()` | Сохранение текста с таймкодами |
| `_save_cleaned_transcript()` | Сохранение очищенного текста |
| `_save_pipeline_results_educational()` | Pipeline JSON для educational |
| `_save_pipeline_results_leadership()` | Pipeline JSON для leadership |
| `_copy_audio()` | Копирование аудио |
| `_move_video()` | Перемещение видео в archive |
| `_get_stream_name()` | Полное имя потока из events.yaml |
| `_format_duration()` | Форматирование HH:MM:SS |
| `_format_date_russian()` | Дата на русском |

## Параметры save_educational()

```python
async def save_educational(
    metadata: VideoMetadata,
    raw_transcript: RawTranscript,
    cleaned_transcript: CleanedTranscript,
    chunks: TranscriptChunks,
    longread: Longread,
    summary: Summary,
    audio_path: Path | None = None,
    slides_extraction: SlidesExtractionResult | None = None,  # v0.51+
) -> list[str]
```

## Параметры save_leadership()

```python
async def save_leadership(
    metadata: VideoMetadata,
    raw_transcript: RawTranscript,
    cleaned_transcript: CleanedTranscript,
    chunks: TranscriptChunks,
    story: Story,
    audio_path: Path | None = None,
    slides_extraction: SlidesExtractionResult | None = None,  # v0.51+
) -> list[str]
```

## Тестирование

```bash
python -m backend.app.services.saver
```

**Тесты:**
1. Форматирование времени (`_format_duration`)
2. Форматирование даты на русском (`_format_date_russian`)
3. Получение полного имени потока (`_get_stream_name`)
4. Полный цикл сохранения в temp директорию

---

## Связанные файлы

- **Stage:** `backend/app/services/stages/save_stage.py`
- **Сервис:** `backend/app/services/saver.py`
- **Модели:** `backend/app/models/schemas.py` → `PipelineResults`
- **Форматы:** [data-formats.md](../data-formats.md)
- **Конфигурация потоков:** `config/events.yaml`

## История изменений

- **v0.60:** BZ2-Bot v1.0 формат transcript_chunks.json. Генерация description через Claude (`describe_model`). Контекстная шапка в каждом chunk. Разбиение >600 слов с суффиксом (N/M).
- **v0.58:** camelCase сериализация в pipeline_results.json (`by_alias=True`).
- **v0.51:** Поддержка `slides_extraction` в методах save.
- **v0.23:** Разделение на `save_educational()` и `save_leadership()`. Добавлен `story.md` для leadership контента.
