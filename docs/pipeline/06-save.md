# Этап 6: Save Files

[< Назад: Summarize](05-summarize.md) | [Обзор Pipeline](README.md)

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
                ├── {original_filename}.mp4      # Видео
                ├── transcript_chunks.json       # Для RAG
                ├── summary.md                   # Для File Search
                └── transcript_raw.txt           # Backup оригинала
```

## Генерация transcript_chunks.json

```python
def save_transcript_chunks(
    video_id: str,
    metadata: VideoMetadata,
    raw_transcript: RawTranscript,
    chunks: TranscriptChunks,
    archive_path: Path
) -> Path:
    """Сохраняет chunks в JSON для RAG-индексации."""

    data = {
        "video_id": video_id,
        "metadata": {
            "title": metadata.title,
            "speaker": metadata.speaker,
            "date": metadata.date.isoformat(),
            "stream": metadata.stream,
            "stream_name": metadata.stream_full,
            "duration_seconds": raw_transcript.duration_seconds,
            "language": raw_transcript.language,
            "whisper_model": raw_transcript.whisper_model,
            "processed_at": datetime.now().isoformat(),
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
        "statistics": {
            "total_chunks": chunks.total_chunks,
            "avg_chunk_size": chunks.avg_chunk_size,
        }
    }

    output_path = archive_path / "transcript_chunks.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return output_path
```

## Генерация summary.md

```python
def save_summary_md(
    video_id: str,
    metadata: VideoMetadata,
    raw_transcript: RawTranscript,
    summary: VideoSummary,
    archive_path: Path
) -> Path:
    """Генерирует summary.md с YAML frontmatter для БЗ 2.0."""

    duration = format_duration(raw_transcript.duration_seconds)

    content = f'''---
# === Идентификация ===
video_id: "{video_id}"
title: "{metadata.title}"
type: "video_summary"

# === Источник ===
speaker: "{metadata.speaker}"
date: "{metadata.date.isoformat()}"
stream: "{metadata.stream}"
duration: "{duration}"

# === Классификация для БЗ 2.0 ===
section: "{summary.section}"
subsection: "{summary.subsection}"
access_level: {summary.access_level}
tags:
{format_yaml_list(summary.tags)}
---

# {metadata.title}

**Спикер:** {metadata.speaker}
**Дата:** {metadata.date.strftime("%d %B %Y")}

---

## Краткое содержание

{summary.summary}

## Ключевые тезисы

{format_bullet_list(summary.key_points)}

## Практические рекомендации

{format_numbered_list(summary.recommendations)}

## Для кого полезно

{summary.target_audience}

## Вопросы, на которые отвечает видео

{format_bullet_list(summary.questions_answered)}
'''

    output_path = archive_path / "summary.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path
```

## Сохранение raw транскрипта (backup)

```python
def save_raw_transcript(
    raw_transcript: RawTranscript,
    archive_path: Path
) -> Path:
    """
    Сохраняет оригинальный транскрипт с тайм-кодами.
    Backup на случай необходимости переобработки.
    """

    output_path = archive_path / "transcript_raw.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(raw_transcript.text_with_timestamps)

    return output_path
```

---

## Связанные документы

- **Код:** [`backend/app/services/saver.py`](../../backend/app/services/saver.py)
- **Форматы:** [data-formats.md](../data-formats.md)
