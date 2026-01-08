# Pipeline обработки видео

> Детальное описание этапов обработки видео от inbox до готовых файлов для БЗ 2.0.

## Схема Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                      VIDEO PROCESSING PIPELINE                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐       │
│  │ 1.PARSE │───▶│2.WHISPER│───▶│3.CLEAN  │───▶│4.CHUNK  │       │
│  │ filename│    │transcr. │    │ + gloss │    │semantic │       │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘       │
│                                                   │             │
│                                                   ▼             │
│                              ┌─────────┐    ┌─────────┐         │
│                              │6.SAVE   │◀───│5.SUMMAR.│         │
│                              │ files   │    │ + class │         │
│                              └─────────┘    └─────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Этапы

| # | Этап | Документ | Инструмент | Вход | Выход |
|---|------|----------|------------|------|-------|
| 1 | Parse Filename | [01-parse.md](01-parse.md) | Python regex | `*.mp4` filename | `VideoMetadata` |
| 2 | Transcribe | [02-transcribe.md](02-transcribe.md) | Whisper API | `*.mp4` file | `RawTranscript` |
| 3 | Clean | [03-clean.md](03-clean.md) | Ollama + Glossary | `RawTranscript` | `CleanedTranscript` |
| 4 | Chunk | [04-chunk.md](04-chunk.md) | Ollama | `CleanedTranscript` | `TranscriptChunks` |
| 5 | Summarize | [05-summarize.md](05-summarize.md) | Ollama | `CleanedTranscript` | `Summary` + classification |
| 6 | Save | [06-save.md](06-save.md) | Python | All data | Files in archive |

## Полный Pipeline Flow

```python
async def process_video(video_path: Path) -> ProcessingResult:
    """Полный pipeline обработки видео."""

    # 1. Parse filename
    metadata = parse_filename(video_path.name)
    video_id = generate_video_id(metadata)

    # 2. Transcribe
    raw_transcript = await transcribe(video_path, WHISPER_CONFIG)

    # 3. Clean
    glossary = load_glossary()
    text_with_glossary = apply_glossary(raw_transcript.full_text, glossary)
    cleaned_text = await llm_clean_transcript(text_with_glossary, metadata)

    # 4. Chunk
    chunks = await chunk_transcript(cleaned_text, metadata)

    # 5. Summarize
    summary = await summarize_transcript(cleaned_text, metadata)

    # 6. Save
    archive_path = create_archive_path(metadata)
    shutil.move(video_path, archive_path / video_path.name)
    save_transcript_chunks(video_id, metadata, raw_transcript, chunks, archive_path)
    save_summary_md(video_id, metadata, raw_transcript, summary, archive_path)
    save_raw_transcript(raw_transcript, archive_path)

    return ProcessingResult(
        video_id=video_id,
        archive_path=archive_path,
        chunks_count=len(chunks),
        duration=raw_transcript.duration_seconds,
    )
```

## Связанные документы

- [architecture.md](../architecture.md) — схема системы, компоненты
- [data-formats.md](../data-formats.md) — форматы файлов
- [api-reference.md](../api-reference.md) — HTTP API сервисов
- [error-handling.md](error-handling.md) — обработка ошибок
