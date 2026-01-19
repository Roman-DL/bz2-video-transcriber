# Этап 7: Save Files

[< Назад: Summarize](06-summarize.md) | [Обзор Pipeline](README.md) | [Далее: Orchestrator >](08-orchestrator.md)

---

## Назначение

Сохранение результатов обработки в структурированный архив.

## Структура архива

```
/archive/
└── {год}/
    └── {месяц}/
        └── {тип}.{поток}/
            └── {тема} ({спикер})/
                ├── {original_filename}.mp4      # Видео (перемещённое)
                ├── audio.mp3                    # Извлечённое аудио
                ├── transcript_chunks.json       # Для RAG
                ├── longread.md                  # Развёрнутый текст
                ├── summary.md                   # Конспект (File Search)
                ├── transcript_raw.txt           # Backup оригинала
                ├── transcript_cleaned.txt       # Очищенный текст
                └── pipeline_results.json        # Для просмотра в UI
```

## Выходные файлы

| Файл | Назначение | Описание |
|------|------------|----------|
| `{название}.mp4` | Видео | Оригинальный файл |
| `audio.mp3` | Аудио | Извлечённая дорожка |
| `transcript_chunks.json` | RAG | Семантические чанки для индексации |
| `longread.md` | БЗ 2.0 | Развёрнутый текст (5-10 страниц) |
| `summary.md` | File Search | Конспект с callouts (2-4 страницы) |
| `transcript_raw.txt` | Backup | Текст с таймкодами |
| `transcript_cleaned.txt` | Чтение | Очищенный текст |
| `pipeline_results.json` | UI | Полные результаты для просмотра |

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

## Формат transcript_chunks.json

JSON для RAG-индексации:
- `video_id` — уникальный идентификатор
- `metadata` — информация о видео
- `statistics` — статистика по чанкам
- `chunks[]` — массив с id, topic, text

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

## Операции

| Метод | Описание |
|-------|----------|
| `save()` | Основной метод — создаёт папку и все файлы |
| `_save_chunks_json()` | Генерация JSON для RAG |
| `_save_longread_md()` | Сохранение лонгрида |
| `_save_summary_md()` | Сохранение конспекта |
| `_save_raw_transcript()` | Сохранение текста с таймкодами |
| `_save_cleaned_transcript()` | Сохранение очищенного текста |
| `_save_pipeline_results()` | Сохранение полных результатов для UI |
| `_copy_audio()` | Копирование аудио |
| `_move_video()` | Перемещение видео в archive |

## Параметры save()

Метод `save()` принимает:
- `metadata` — VideoMetadata с путями
- `raw_transcript` — сырая транскрипция
- `cleaned_transcript` — очищенная транскрипция
- `chunks` — семантические чанки
- `longread` — развёрнутый текст
- `summary` — конспект
- `audio_path` — путь к аудио (опционально)

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

- **Сервис:** `backend/app/services/saver.py`
- **Форматы:** [data-formats.md](../data-formats.md)
- **Конфигурация потоков:** `config/events.yaml`
