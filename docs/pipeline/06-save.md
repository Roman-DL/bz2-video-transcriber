# Этап 6: Save Files

[< Назад: Summarize](05-summarize.md) | [Обзор Pipeline](README.md)

---

## Назначение

Сохранение результатов обработки в структурированный архив.

## Класс FileSaver

```python
from app.services.saver import FileSaver

saver = FileSaver(settings)
files = await saver.save(metadata, raw_transcript, chunks, summary)
# ['transcript_chunks.json', 'summary.md', 'transcript_raw.txt', 'video.mp4']
```

## Структура архива

```
/archive/
└── {год}/
    └── {месяц}/
        └── {тип}.{поток}/
            └── {тема} ({спикер})/
                ├── {original_filename}.mp4      # Видео (перемещённое)
                ├── transcript_chunks.json       # Для RAG
                ├── summary.md                   # Для File Search
                └── transcript_raw.txt           # Backup оригинала
```

## Методы класса

| Метод | Описание |
|-------|----------|
| `__init__(settings)` | Инициализация, загрузка events_config |
| `save(metadata, raw_transcript, chunks, summary)` | Основной метод сохранения |
| `_save_chunks_json(...)` | Генерация JSON для RAG |
| `_save_summary_md(...)` | Генерация Markdown с YAML frontmatter |
| `_save_raw_transcript(...)` | Сохранение текста с таймкодами |
| `_move_video(source, dest_dir)` | Перемещение видео в archive |
| `_get_stream_name(event_type, stream)` | Получение полного имени потока |
| `_format_duration(seconds)` | Форматирование HH:MM:SS |

---

## Генерация transcript_chunks.json

```python
def _save_chunks_json(
    self,
    archive_path: Path,
    metadata: VideoMetadata,
    raw_transcript: RawTranscript,
    chunks: TranscriptChunks,
) -> Path:
    """Сохраняет chunks в JSON для RAG-индексации."""

    total_words = sum(c.word_count for c in chunks.chunks)
    stream_name = self._get_stream_name(metadata.event_type, metadata.stream)

    data = {
        "video_id": metadata.video_id,
        "metadata": {
            "title": metadata.title,
            "speaker": metadata.speaker,
            "date": metadata.date.isoformat(),
            "event_type": metadata.event_type,
            "stream": metadata.stream,
            "stream_name": stream_name,
            "duration_seconds": raw_transcript.duration_seconds,
            "duration_formatted": self._format_duration(raw_transcript.duration_seconds),
            "language": raw_transcript.language,
            "whisper_model": raw_transcript.whisper_model,
            "processed_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "statistics": {
            "total_chunks": chunks.total_chunks,
            "avg_chunk_words": chunks.avg_chunk_size,
            "total_words": total_words,
        },
        "chunks": [
            {
                "id": chunk.id,
                "index": chunk.index,
                "topic": chunk.topic,
                "text": chunk.text,
                "word_count": chunk.word_count,
            }
            for chunk in chunks.chunks
        ],
    }

    file_path = archive_path / "transcript_chunks.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return file_path
```

---

## Генерация summary.md

YAML frontmatter содержит полные метаданные для File Search в БЗ 2.0:

```python
def _save_summary_md(
    self,
    archive_path: Path,
    metadata: VideoMetadata,
    raw_transcript: RawTranscript,
    summary: VideoSummary,
) -> Path:
    """Генерирует summary.md с YAML frontmatter."""

    stream_name = self._get_stream_name(metadata.event_type, metadata.stream)
    date_formatted = self._format_date_russian(metadata.date)  # "7 апреля 2025"
    duration_formatted = self._format_duration(raw_transcript.duration_seconds)

    # YAML frontmatter
    frontmatter = f'''---
# === Identification ===
video_id: "{metadata.video_id}"
title: "{metadata.title}"
type: "video_summary"

# === Source ===
speaker: "{metadata.speaker}"
date: "{metadata.date.isoformat()}"
event_type: "{metadata.event_type}"
stream: "{metadata.stream}"
stream_name: "{stream_name}"
duration: "{duration_formatted}"

# === Classification for BZ 2.0 ===
section: "{summary.section}"
subsection: "{summary.subsection}"
access_level: {summary.access_level}
tags:
  - "tag1"
  - "tag2"

# === Files ===
video_file: "{metadata.original_filename}"
transcript_file: "transcript_chunks.json"

# === Service ===
created: "{datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")}"
llm_model: "{self.settings.llm_model}"
pipeline_version: "1.0.0"
---'''

    # Markdown body
    body = f'''
# {metadata.title}

**Спикер:** {metadata.speaker}
**Дата:** {date_formatted}
**Поток:** {stream_name}

---

## Краткое содержание

{summary.summary}

## Ключевые тезисы

- Point 1
- Point 2

## Практические рекомендации

1. Recommendation 1
2. Recommendation 2

## Для кого полезно

{summary.target_audience}

## Вопросы, на которые отвечает видео

- Question 1?
- Question 2?
'''

    file_path = archive_path / "summary.md"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(frontmatter + body)

    return file_path
```

---

## Сохранение raw транскрипта

```python
def _save_raw_transcript(
    self,
    archive_path: Path,
    raw_transcript: RawTranscript,
) -> Path:
    """
    Сохраняет оригинальный транскрипт с тайм-кодами.
    Использует готовое свойство raw_transcript.text_with_timestamps.
    """

    file_path = archive_path / "transcript_raw.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(raw_transcript.text_with_timestamps)

    return file_path
```

Формат файла:
```
[00:00:00] Первый сегмент текста.
[00:00:08] Второй сегмент текста.
[00:00:15] Третий сегмент текста.
```

---

## Перемещение видео

```python
def _move_video(self, source: Path, dest_dir: Path) -> Path:
    """Перемещает видео из inbox в archive."""

    dest_path = dest_dir / source.name
    shutil.move(str(source), str(dest_path))

    return dest_path
```

---

## Вспомогательные методы

### Получение полного имени потока

```python
def _get_stream_name(self, event_type: str, stream: str) -> str:
    """
    Получает полное имя потока из events.yaml.

    Пример: ("ПШ", "SV") -> "Понедельничная Школа — Супервайзеры"
    """
    event_types = self.events_config.get("event_types", {})
    event_info = event_types.get(event_type, {})
    event_name = event_info.get("name", event_type)

    streams = event_info.get("streams", {})
    stream_desc = streams.get(stream, stream)

    return f"{event_name} — {stream_desc}"
```

### Форматирование времени

```python
@staticmethod
def _format_duration(seconds: float) -> str:
    """Форматирует секунды в HH:MM:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
```

---

## Связанные документы

- **Код:** [`backend/app/services/saver.py`](../../backend/app/services/saver.py)
- **Форматы:** [data-formats.md](../data-formats.md)
- **Конфигурация потоков:** [`config/events.yaml`](../../config/events.yaml)
