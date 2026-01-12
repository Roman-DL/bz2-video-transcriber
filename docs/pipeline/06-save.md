# Этап 6: Save Files

[< Назад: Summarize](05-summarize.md) | [Обзор Pipeline](README.md) | [Далее: Orchestrator >](07-orchestrator.md)

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
                ├── summary.md                   # Для File Search
                ├── transcript_raw.txt           # Backup оригинала
                ├── transcript_cleaned.txt       # Очищенный текст
                └── pipeline_results.json        # Для просмотра в UI
```

## Выходные файлы

| Файл | Назначение | Имя |
|------|------------|-----|
| Видео | Оригинальный файл | `{оригинальное_название}.mp4` |
| Аудио | Извлечённая дорожка | `audio.mp3` |
| Chunks | RAG-индексация в БЗ 2.0 | `transcript_chunks.json` |
| Summary | File Search в БЗ 2.0 | `summary.md` |
| Raw transcript | Backup с таймкодами | `transcript_raw.txt` |
| Cleaned transcript | Чистый текст для чтения | `transcript_cleaned.txt` |
| Pipeline results | Просмотр результатов в UI | `pipeline_results.json` |

## Формат transcript_chunks.json

JSON файл для RAG-индексации содержит:
- `video_id` — уникальный идентификатор
- `metadata` — информация о видео (спикер, дата, длительность)
- `statistics` — статистика по чанкам
- `chunks[]` — массив семантических блоков с id, topic, text

Подробная структура: [data-formats.md](../data-formats.md#1-transcript_chunksjson)

## Формат summary.md

Markdown с YAML frontmatter для File Search:
- Frontmatter — метаданные для фильтрации (section, tags, access_level)
- Body — структурированное саммари для пользователя

Подробная структура: [data-formats.md](../data-formats.md#2-summarymd)

## Формат transcript_raw.txt

Текстовый файл с таймкодами:
```
[00:00:00] Первый сегмент текста.
[00:00:08] Второй сегмент текста.
```

## Формат pipeline_results.json

JSON файл для просмотра результатов в веб-интерфейсе:
- `version` — версия формата для совместимости
- `created_at` — дата/время обработки
- `metadata`, `raw_transcript`, `cleaned_transcript`, `chunks`, `summary` — полные данные pipeline
- `display_text` — текст транскрипции для отображения (с/без таймкодов)

Подробная структура: [data-formats.md](../data-formats.md#5-pipeline_resultsjson)

## Операции

| Метод | Описание |
|-------|----------|
| `save()` | Основной метод — создаёт папку и все файлы |
| `_save_chunks_json()` | Генерация JSON для RAG |
| `_save_summary_md()` | Генерация Markdown с frontmatter |
| `_save_raw_transcript()` | Сохранение текста с таймкодами |
| `_save_cleaned_transcript()` | Сохранение очищенного текста |
| `_save_pipeline_results()` | Сохранение полных результатов для UI |
| `_copy_audio()` | Копирование аудио как `audio.mp3` |
| `_move_video()` | Перемещение видео в archive |

## Параметры save()

Метод `save()` принимает:
- `metadata` — VideoMetadata с путями
- `raw_transcript` — сырая транскрипция
- `cleaned_transcript` — очищенная транскрипция
- `chunks` — семантические чанки
- `summary` — структурированное саммари
- `audio_path` — путь к извлечённому аудио (опционально)

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

- [`backend/app/services/saver.py`](../../backend/app/services/saver.py) — код сохранения
- [data-formats.md](../data-formats.md) — детальные форматы файлов
- [`config/events.yaml`](../../config/events.yaml) — конфигурация потоков
