---
globs: backend/app/services/pipeline/**,backend/app/services/stages/**,backend/app/services/audio_extractor.py,backend/app/services/progress_estimator.py
---

# Rules: Pipeline & Stages

## PipelineOrchestrator
- ВСЕГДА координировать этапы через `PipelineOrchestrator` — НЕ вызывать stages напрямую
- Fallback механизмы удалены (v0.29+) — при ошибках LLM выбрасывается `PipelineError`
- `progress_manager.py` содержит `STAGE_WEIGHTS` для расчёта прогресса

## BaseStage Pattern
- ВСЕГДА наследовать от `BaseStage` при создании нового этапа
- Указывать `name` и `depends_on` — оркестратор определяет порядок автоматически
- Условный пропуск: переопределить `should_skip(context: StageContext) -> bool`
- НЕ менять оркестратор для добавления нового этапа — только создать новый stage
- Пример нового этапа:
  ```python
  class MyStage(BaseStage):
      name = "my_stage"
      depends_on = ["clean"]
      async def execute(self, context: StageContext) -> MyResult: ...
  ```

## StageResultCache
- Кэш версионирован: `archive_path/.cache/{stage}/v{N}.json`
- `CacheStageName` enum для имён этапов — НЕ использовать строки напрямую
- Сохранение: `await cache.save(archive_path, stage, result, model_name)`
- Загрузка: `await cache.load(archive_path, stage, version=None)`

## Chunk
- Chunk детерминистический — парсинг H2 заголовков (v0.25+), без LLM
- Выполняется ПОСЛЕ longread/story, НЕ параллельно
- **Преамбула (текст до первого `##`) безусловно пропускается** (v0.74+) — остаётся в лонгриде для читателей
- MAX_CHUNK_WORDS=600 — чанки >600 слов разбиваются по параграфам (v0.60+)
- Суффикс `(N/M)` в H2 добавляется в saver, НЕ в h2_chunker

## Chunk — Description Generation (v0.62+)
- `DescriptionGenerator` (`app.services.description_generator`) вызывает Claude (`describe_model`) для генерации description/short_description
- Вызывается из chunk endpoint (`/api/step/chunk`), НЕ из saver
- Описания хранятся в `TranscriptChunks` (поля с префиксом `describe_`)
- При ошибке Claude — chunk продолжается с пустыми описаниями (warning в лог, НЕ PipelineError)

## Save (v0.62+)
- Save — чистое сохранение файлов, без LLM вызовов
- `SaveResult` содержит только `files: list[str]`
- `transcript_chunks.json` — формат BZ2-Bot v1.0 (snake_case, НЕ camelCase)
- Описания читаются из `TranscriptChunks`, НЕ генерируются в saver

## Slides
- Slides — отдельный API endpoint (`/api/step/slides`), НЕ часть stage абстракции
- Появляется условно между `clean` и `longread/story` при наличии слайдов
- batch_size: 5 слайдов за вызов Claude Vision API

## MD Transcripts (v0.64+)
- `.md` файлы — готовые транскрипты из MacWhisper, Whisper пропускается
- `is_transcript_file()` из `app.utils` — проверка типа файла
- `whisper_model="macwhisper-large-v2"` — маркер источника в RawTranscript
- `audio_path=None` для MD файлов — нет медиафайла
- `SpeakerInfo` в `VideoMetadata.speaker_info` — парсится из текста MD
- `speaker_utils.parse_speakers()` — обнаружение спикеров по паттерну `Фамилия Имя` / `SpeakerN`

## Longread — Auto-selection (v0.67+)
- `LongreadGenerator` авто-выбирает путь по `context_tokens` модели vs размер текста
- **Single-pass** (1 LLM вызов) — когда текст помещается в контекст (Claude 200K)
- **Map-reduce** (split → outline → sections → frame) — когда текст НЕ помещается (Ollama 8-32K)
- Промпты (`system.md`, `instructions.md`, `template.md`) — общие для обоих путей
- `_fits_in_context()` — оценка: Russian ~2.0 tokens/char, overhead ~35K tokens
- `max_input_chars` из `config/models.yaml` — лимит для large-контекста
- ВСЕГДА передавать `num_predict` для single-pass (default 4096 недостаточно для полного лонгрида)
- `SINGLE_PASS_MAX_TOKENS = 16384` — константа для single-pass генерации

## Speaker Context (v0.79+)
- `build_speaker_context(speaker_info, host_name)` → `list[str]` для unpacking в prompt_parts
- Возвращает `[]` для `single` / `None` → zero-impact на односпикерный pipeline
- Вставляется через `*build_speaker_context(...)` во ВСЕ prompt builder методы генератора
- Longread: 3 точки вставки (single-pass, section, frame) — покрывает оба пути
- Summary, Story: по 1 точке в `_build_prompt()`
- **Story видит только co_speakers** — lineup обрабатывается через longread (ADR-022)

## Saver — Multi-Speaker Headers (v0.79+)
- `abbreviate_name("Фамилия Имя")` → `"Фамилия И."`
- Со-спикеры: `Спикеры:` вместо `Спикер:` + abbreviated names
- Линейка: per-chunk `Участник: {имя} | Линейка, ведущий: {вед.}`
- Regex `\(([^)]+)\)$` для извлечения имени из H2 — **ТОЛЬКО при `is_lineup=True`** (ADR-022)
- `metadata.speaker` в JSON: co_speakers → abbreviated через запятую, lineup → ведущий

## Shared Utils
- ВСЕГДА импортировать из `app.utils`: `extract_json`, `get_media_duration`, `is_audio_file`, `is_transcript_file`
- НЕ дублировать утилиты в сервисах — выносить в `backend/app/utils/`
