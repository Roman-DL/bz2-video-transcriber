# Импорт MD-транскриптов (v0.64)

## Контекст

При записи выездных мероприятий запись идёт одним файлом на несколько тем. Фрагмент с темой вырезается в MacWhisper, где же происходит транскрибация с определением спикеров. Итог — готовый `.md` файл с транскриптом.

Сейчас pipeline принимает только медиафайлы (видео/аудио), поэтому готовые транскрипты из MacWhisper обрабатываются вручную. Задача — добавить `.md` как входной формат: пропустить Whisper, загрузить текст из файла, остальной pipeline без изменений.

**Требования:** [docs/requirements/md-transcript-import.md](../requirements/md-transcript-import.md)

---

## Pre-flight: архитектурный анализ

### Совместимость

Задача органично вписывается в архитектуру. Ключевые точки:

- **Parser** (`DATED_OFFSITE_PATTERN`) — regex уже принимает любое расширение `(?:\.\w+)?$`
- **Saver** — `_copy_audio()` защищён `if audio_path and audio_path.exists()`; `_move_video()` перемещает `source.name` — работает для любого файла
- **StepSaveRequest.audio_path** — уже `str | None = None`
- **StepData.audioPath** (frontend) — уже `string | undefined`
- Новый stage не нужен — conditional логика внутри существующего Transcribe

### Релевантные ADR

- **ADR-001** (Stage Abstraction) — conditional внутри stage, не новый stage
- **ADR-007** (Claude Default) — clean stage обязателен для MD (MacWhisper тоже ошибается)

### Конфликтов с ограничениями нет

### Rules

- `pipeline.md` — учтены (BaseStage, chunk детерминистический)
- `api.md` — учтены (CamelCaseModel, TokensUsed)
- `content.md` — учтены (dated offsite pattern)
- `infrastructure.md` — не затрагивается

---

## План реализации

### Этап 1: Models

#### 1.1 SpeakerInfo + VideoMetadata.speaker_info

**Файл:** `backend/app/models/schemas.py`

- Добавить `SpeakerInfo(CamelCaseModel)` перед `VideoMetadata` (после строки 97):
  ```python
  class SpeakerInfo(CamelCaseModel):
      named_speakers: list[str]
      anonymous_speakers: list[str]
      scenario: str  # single | co_speakers | lineup | qa | co_speakers_qa | lineup_qa
  ```
- В `VideoMetadata` добавить поле:
  ```python
  speaker_info: SpeakerInfo | None = None  # v0.64+: from MD transcript
  ```

#### 1.2 TranscribeResult.audio_path → optional

**Файл:** `backend/app/models/schemas.py` (строка 213)

- `audio_path: str` → `audio_path: str | None = None`

#### 1.3 TypeScript типы

**Файл:** `frontend/src/api/types.ts`

- Добавить `SpeakerInfo` интерфейс
- В `VideoMetadata` добавить `speakerInfo?: SpeakerInfo | null`
- В `TranscribeResult` (строка 74): `audioPath: string` → `audioPath?: string | null`

---

### Этап 2: Backend Utils

#### 2.1 media_utils — определение типа файла

**Файл:** `backend/app/utils/media_utils.py`

- Добавить `TRANSCRIPT_EXTENSIONS = frozenset({".md"})`
- Добавить `is_transcript_file(file_path: Path) -> bool`
- Добавить `estimate_duration_from_text(text: str, words_per_minute: int = 130) -> float`

#### 2.2 Экспорт из utils

**Файл:** `backend/app/utils/__init__.py`

- Добавить экспорт: `is_transcript_file`, `estimate_duration_from_text`, `TRANSCRIPT_EXTENSIONS`

#### 2.3 speaker_utils.py (новый файл)

**Файл:** `backend/app/utils/speaker_utils.py` (НОВЫЙ)

- `SPEAKER_PATTERN` — regex для `Фамилия Имя` и `SpeakerN`
- `parse_speakers(text: str) -> SpeakerInfo` — парсинг строк текста
- `_determine_scenario(named_count, has_anonymous) -> str`
- Тесты в `__main__`

---

### Этап 3: Backend API

#### 3.1 Inbox — добавить .md

**Файл:** `backend/app/api/routes.py` (строка 39-44)

- Добавить `".md"` в set `extensions`

#### 3.2 step_parse — duration и speaker_info для MD

**Файл:** `backend/app/api/step_routes.py` (функция `step_parse`, строка 206-243)

После `metadata = orchestrator.parse(video_path)`, conditional:

```python
if is_transcript_file(video_path):
    text = video_path.read_text(encoding="utf-8")
    metadata.duration_seconds = estimate_duration_from_text(text)
    metadata.speaker_info = parse_speakers(text)
else:
    metadata.duration_seconds = get_media_duration(video_path)
    if metadata.duration_seconds is None:
        metadata.duration_seconds = video_path.stat().st_size / 83333
```

#### 3.3 step_transcribe — загрузка MD вместо Whisper

**Файл:** `backend/app/api/step_routes.py` (функция `step_transcribe`, строка 246-312)

Conditional после проверки `video_path.exists()`:

```python
if is_transcript_file(video_path):
    # MD файл — загрузка текста, мгновенный SSE
    async def load_md_transcript():
        text = video_path.read_text(encoding="utf-8")
        word_count = len(text.split())
        estimated_duration = word_count / 130 * 60

        transcript = RawTranscript(
            segments=[TranscriptSegment(start=0, end=estimated_duration, text=text)],
            language="ru",
            duration_seconds=estimated_duration,
            whisper_model="macwhisper-large-v2",
            processing_time_sec=0,
        )
        display_text = transcript.full_text
        return TranscribeResult(
            raw_transcript=transcript,
            audio_path=None,
            display_text=display_text,
        )

    return create_sse_response(
        run_with_sse_progress(
            stage=ProcessingStatus.TRANSCRIBING,
            estimator=estimator,
            estimated_seconds=1.0,
            message=f"Loading transcript: {request.video_filename}",
            operation=load_md_transcript,
        )
    )
```

SSE обязателен — фронтенд использует `createStepWithProgress` для transcribe.

#### 3.4 Orchestrator — conditional в transcribe/process

**Файл:** `backend/app/services/pipeline/orchestrator.py`

1. `transcribe()` (строка 274): return type → `tuple[RawTranscript, Path | None]`. Conditional: если `is_transcript_file` → `_load_md_transcript()`
2. Новый приватный метод `_load_md_transcript(self, md_path: Path) -> RawTranscript`
3. `process()`: conditional для duration (MD → текст, медиа → ffprobe) и для transcribe (MD → load, медиа → Whisper). `audio_path = None` для MD.

#### 3.5 TranscribeStage — conditional

**Файл:** `backend/app/services/stages/transcribe_stage.py` (строка 47-71)

Return type → `tuple[RawTranscript, Path | None]`. Conditional: если `is_transcript_file(video_path)` → загрузка из файла, return `(transcript, None)`.

#### 3.6 Clean prompt — метки спикеров

**Файл:** `config/prompts/cleaning/system.md`

Добавить в секцию "КРИТИЧЕСКИ ВАЖНО" (после строки 47):

```
8. СОХРАНЯЙ метки спикеров: если строка содержит только имя в формате "Фамилия Имя" (например, "Беркин Андрей") или "SpeakerN" — оставь её как есть на отдельной строке. Это метки смены спикеров, они нужны для последующей обработки.
```

---

### Этап 4: Frontend

#### 4.1 fileUtils — isTranscriptFile

**Файл:** `frontend/src/utils/fileUtils.ts`

- `TRANSCRIPT_EXTENSIONS = ['md']`
- `isTranscriptFile(filename: string): boolean`

#### 4.2 VideoItem — иконка и бейдж

**Файл:** `frontend/src/components/inbox/VideoItem.tsx`

- Import `FileText` из lucide-react, `isTranscriptFile` из fileUtils
- Тройной выбор иконки: `isTranscript ? FileText : isAudio ? Music : Film`
- Цвет для transcript: `amber-50/amber-500`
- Бейдж "Транскрипт" рядом со спикером

#### 4.3 usePipelineProcessor — isTranscript

**Файл:** `frontend/src/hooks/usePipelineProcessor.ts`

- `const isTranscript = isTranscriptFile(filename)` в теле hook
- Добавить `isTranscript` в return (`UsePipelineProcessorResult`)
- `getStepDescription('transcribe')`: для MD → "Загрузка транскрипта из файла"

#### 4.4 StepByStep — UI адаптация

**Файл:** `frontend/src/components/processing/StepByStep.tsx`

- Бейдж "MD-транскрипт" в header при `processor.isTranscript`
- Динамический лейбл для transcribe step

#### 4.5 MetadataView — speakerInfo

**Файл:** `frontend/src/components/results/MetadataView.tsx`

- Секция "Спикеры" при наличии `metadata.speakerInfo`: named_speakers, anonymous count, scenario

---

### Этап 5: Тесты и документация

- Тест parser: `.md` файл в dated offsite формате (в `parser.py __main__`)
- Тесты speaker_utils: все scenario варианты (в `speaker_utils.py __main__`)
- `docs/requirements/md-transcript-import.md` — статус → "Implemented"
- `CLAUDE.md` — v0.64 в таблице статуса
- `.claude/rules/pipeline.md` — правило: MD файлы → whisper_model=macwhisper-large-v2

---

## Критические файлы

| Файл | Роль |
|------|------|
| `backend/app/models/schemas.py` | SpeakerInfo, optional audio_path |
| `backend/app/api/step_routes.py` | Conditional в step_parse и step_transcribe |
| `backend/app/api/routes.py` | `.md` в inbox extensions |
| `backend/app/utils/media_utils.py` | is_transcript_file, estimate_duration_from_text |
| `backend/app/utils/speaker_utils.py` | parse_speakers (НОВЫЙ) |
| `backend/app/services/pipeline/orchestrator.py` | Conditional в transcribe(), process() |
| `backend/app/services/stages/transcribe_stage.py` | Conditional для full pipeline |
| `config/prompts/cleaning/system.md` | Правило сохранения меток спикеров |
| `frontend/src/api/types.ts` | SpeakerInfo, optional audioPath |
| `frontend/src/utils/fileUtils.ts` | isTranscriptFile |
| `frontend/src/components/inbox/VideoItem.tsx` | Иконка, бейдж |
| `frontend/src/hooks/usePipelineProcessor.ts` | isTranscript flag |

## Что НЕ меняется

- Clean stage — работает с тем же `RawTranscript.full_text`
- Longread/Story/Chunk/Save — не затрагиваются (работают с CleanedTranscript)
- Saver — `_copy_audio` уже защищён guard, `_move_video` работает для любого файла

## Верификация

1. Положить `.md` файл с датированным именем в inbox (например: `2026.02 ФСТ. Тема (Спикер).md`)
2. Проверить inbox API: файл виден
3. Проверить UI: файл с иконкой документа и бейджем "Транскрипт"
4. Parse: корректные metadata, duration по словам, speaker_info
5. Transcribe: мгновенная загрузка, `whisper_model="macwhisper-large-v2"`, нет audio_path
6. Clean → Longread → Chunk → Save: pipeline проходит полностью
7. Архив: исходный `.md` скопирован, нет `audio.mp3`, остальные файлы на месте
8. MD с метками спикеров: Clean сохраняет `Фамилия Имя` на отдельных строках
9. MD с `#` в имени: content_type=leadership, pipeline через Story
10. `python3 backend/app/services/parser.py` — тесты парсера проходят
11. `python3 backend/app/utils/speaker_utils.py` — тесты спикеров проходят

## Вероятные обновления документации

- `CLAUDE.md` — v0.64 в таблице статуса
- `.claude/rules/pipeline.md` — правило для MD файлов
- `docs/requirements/md-transcript-import.md` — статус Implemented
- ADR — не нужен (изменения внутри существующей архитектуры)
