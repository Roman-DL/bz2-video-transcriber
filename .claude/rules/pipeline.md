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

## Shared Utils
- ВСЕГДА импортировать из `app.utils`: `extract_json`, `get_media_duration`, `is_audio_file`
- НЕ дублировать утилиты в сервисах — выносить в `backend/app/utils/`
