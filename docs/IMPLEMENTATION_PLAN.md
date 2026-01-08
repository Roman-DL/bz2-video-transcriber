# План реализации: bz2-video-transcriber

> Пошаговый план разработки с атомарными задачами для Claude Code. Каждая фаза — отдельная сессия. Проверяй результат перед переходом к следующей.

---

## Обзор фаз

|Фаза|Название|Зависимости|Время|
|---|---|---|---|
|0|Структура проекта|—|15 мин|
|1|Модели данных|Фаза 0|30 мин|
|2|Конфигурация|Фаза 0|20 мин|
|3|Парсер имени файла|Фазы 1, 2|30 мин|
|4|AI клиент|Фаза 2|30 мин|
|5|Транскрибер|Фазы 1, 4|30 мин|
|6|Cleaner|Фазы 1, 2, 4|45 мин|
|7|Chunker|Фазы 1, 2, 4|30 мин|
|8|Summarizer|Фазы 1, 2, 4|30 мин|
|9|Saver|Фазы 1, 2|30 мин|
|10|Pipeline|Фазы 3-9|45 мин|
|11|API|Фазы 1, 10|45 мин|
|12|Docker|Фаза 11|30 мин|
|13|Frontend|Фаза 11|3-4 часа|

**Общее время:** ~12-14 часов

---

## Фаза 0: Структура проекта

### Цель

Создать скелет проекта со всеми папками и базовыми файлами.

### Чеклист

- [ ] Создать структуру папок
- [ ] Создать `__init__.py` во всех пакетах
- [ ] Создать `requirements.txt`
- [ ] Создать `.env.example`
- [ ] Создать `.gitignore`

### Запрос для Claude Code

```
Прочитай CLAUDE.md.

Создай структуру проекта:

1. Папки:
   - backend/app/models/
   - backend/app/services/
   - backend/app/api/
   - config/prompts/
   - scripts/

2. Файлы __init__.py:
   - backend/app/__init__.py
   - backend/app/models/__init__.py
   - backend/app/services/__init__.py
   - backend/app/api/__init__.py

3. requirements.txt:
   fastapi==0.109.0
   uvicorn[standard]==0.27.0
   pydantic==2.5.3
   pydantic-settings==2.1.0
   httpx==0.26.0
   aiofiles==23.2.1
   pyyaml==6.0.1
   python-multipart==0.0.6
   tenacity==8.2.3

4. .env.example (из DEPLOYMENT.md):
   OLLAMA_URL=http://192.168.1.152:11434
   WHISPER_URL=http://192.168.1.152:9000
   LLM_MODEL=qwen2.5:14b
   WHISPER_LANGUAGE=ru
   LLM_TIMEOUT=300
   DATA_ROOT=/data
   INBOX_DIR=/data/inbox
   ARCHIVE_DIR=/data/archive
   TEMP_DIR=/data/temp
   CONFIG_DIR=/app/config

5. .gitignore:
   __pycache__/
   *.pyc
   .env
   .env.local
   .venv/
   venv/
   node_modules/
   temp/
   *.log
```

### Критерий готовности

```bash
# Структура создана
tree backend/
# backend/
# └── app/
#     ├── __init__.py
#     ├── api/
#     │   └── __init__.py
#     ├── models/
#     │   └── __init__.py
#     └── services/
#         └── __init__.py
```

---

## Фаза 1: Модели данных

### Цель

Создать все Pydantic модели из pipeline.md.

### Чеклист

- [ ] VideoMetadata
- [ ] TranscriptSegment
- [ ] RawTranscript
- [ ] CleanedTranscript
- [ ] TranscriptChunk
- [ ] TranscriptChunks
- [ ] VideoSummary
- [ ] ProcessingJob
- [ ] ProcessingStatus (enum)

### Запрос для Claude Code

```
Прочитай docs/pipeline.md — секции "Модель данных" каждого этапа.

Создай backend/app/models/schemas.py с Pydantic v2 моделями:

1. VideoMetadata:
   - date: date
   - event_type: str
   - stream: str
   - title: str
   - speaker: str
   - original_filename: str
   - video_id: str
   - source_path: Path
   - archive_path: Path
   - computed property: stream_full

2. TranscriptSegment:
   - start: float
   - end: float
   - text: str
   - computed properties: start_time, end_time (форматированные HH:MM:SS)

3. RawTranscript:
   - segments: list[TranscriptSegment]
   - language: str
   - duration_seconds: float
   - whisper_model: str
   - computed properties: full_text, text_with_timestamps

4. CleanedTranscript:
   - text: str
   - original_length: int
   - cleaned_length: int
   - corrections_made: list[str]

5. TranscriptChunk:
   - id: str (video_id + "_chunk_" + index)
   - index: int
   - topic: str
   - text: str
   - word_count: int

6. TranscriptChunks:
   - chunks: list[TranscriptChunk]
   - computed properties: total_chunks, avg_chunk_size

7. VideoSummary:
   - summary: str
   - key_points: list[str]
   - recommendations: list[str]
   - target_audience: str
   - questions_answered: list[str]
   - section: str
   - subsection: str
   - tags: list[str]
   - access_level: int

8. ProcessingStatus (enum):
   - PENDING, PARSING, TRANSCRIBING, CLEANING, CHUNKING, SUMMARIZING, SAVING, COMPLETED, FAILED

9. ProcessingJob:
   - job_id: str
   - video_path: Path
   - status: ProcessingStatus
   - progress: float (0-100)
   - current_stage: str
   - error: str | None
   - created_at: datetime
   - completed_at: datetime | None
   - result: ProcessingResult | None

10. ProcessingResult:
    - video_id: str
    - archive_path: Path
    - chunks_count: int
    - duration_seconds: float
    - files_created: list[str]

Используй:
- from pydantic import BaseModel, Field, computed_field
- from pathlib import Path
- from datetime import date, datetime
- from enum import Enum
```

### Критерий готовности

```python
# Импорт работает без ошибок
from backend.app.models.schemas import (
    VideoMetadata, RawTranscript, ProcessingJob
)
```

---

## Фаза 2: Конфигурация

### Цель

Создать настройки приложения и загрузку конфигурационных файлов.

### Чеклист

- [ ] Settings класс с pydantic-settings
- [ ] Загрузка из .env
- [ ] Функция загрузки промптов
- [ ] Функция загрузки глоссария
- [ ] Функция загрузки events.yaml

### Запрос для Claude Code

```
Прочитай DEPLOYMENT.md — секцию "Переменные окружения".

Создай backend/app/config.py:

1. Settings (pydantic-settings):
   - ollama_url: str = "http://192.168.1.152:11434"
   - whisper_url: str = "http://192.168.1.152:9000"
   - llm_model: str = "qwen2.5:14b"
   - whisper_language: str = "ru"
   - llm_timeout: int = 300
   - data_root: Path = Path("/data")
   - inbox_dir: Path = Path("/data/inbox")
   - archive_dir: Path = Path("/data/archive")
   - temp_dir: Path = Path("/data/temp")
   - config_dir: Path = Path("/app/config")

   Config:
     env_prefix = ""
     env_file = ".env"

2. get_settings() -> Settings (cached with lru_cache)

3. load_prompt(name: str) -> str:
   - Загружает config/prompts/{name}.md
   - Возвращает содержимое файла

4. load_glossary() -> dict:
   - Загружает config/glossary.yaml
   - Возвращает словарь

5. load_events_config() -> dict:
   - Загружает config/events.yaml
   - Возвращает словарь

Используй:
- from pydantic_settings import BaseSettings
- from functools import lru_cache
- import yaml
```

### Дополнительно: создать конфигурационные файлы

```
Создай config/prompts/cleaner.md, config/prompts/chunker.md, 
config/prompts/summarizer.md из docs/llm-prompts.md.

Создай config/glossary.yaml и config/events.yaml 
из docs/architecture.md (секция "Конфигурация").
```

### Критерий готовности

```python
from backend.app.config import get_settings, load_prompt

settings = get_settings()
print(settings.ollama_url)  # http://192.168.1.152:11434

prompt = load_prompt("cleaner")
print(len(prompt) > 0)  # True
```

---

## Фаза 3: Парсер имени файла

### Цель

Реализовать парсинг имени файла и генерацию video_id.

### Чеклист

- [ ] FILENAME_PATTERN regex
- [ ] parse_filename() функция
- [ ] generate_video_id() функция
- [ ] FilenameParseError exception
- [ ] Тесты

### Запрос для Claude Code

```
Прочитай docs/pipeline.md — "Этап 1: Parse Filename".

Создай backend/app/services/parser.py:

1. FILENAME_PATTERN — regex для парсинга:
   {дата} {тип}.{поток} {тема} ({спикер}).mp4
   Пример: "2025.04.07 ПШ.SV Группа поддержки (Светлана Дмитрук).mp4"

2. class FilenameParseError(Exception):
   - Сообщение с ожидаемым форматом

3. def slugify(text: str) -> str:
   - Транслитерация кириллицы
   - Замена пробелов на дефисы
   - Удаление спецсимволов
   - Lowercase

4. def generate_video_id(date: date, event_type: str, stream: str, title: str) -> str:
   - Формат: {date}_{event_type}-{stream}_{slug}
   - Пример: 2025-04-07_psh-sv_gruppa-podderzhki

5. def parse_filename(filename: str) -> VideoMetadata:
   - Парсинг regex
   - Raise FilenameParseError если не соответствует
   - Возвращает VideoMetadata

6. Тесты в конце файла (if __name__ == "__main__"):
   - Тест успешного парсинга
   - Тест генерации video_id
   - Тест ошибки на неправильный формат
```

### Критерий готовности

```bash
cd backend && python -m app.services.parser
# Все тесты проходят
```

---

## Фаза 4: AI клиент

### Цель

Создать HTTP клиент для Ollama и Whisper с retry логикой.

### Чеклист

- [ ] AIClient класс
- [ ] check_services() — проверка доступности
- [ ] transcribe() — вызов Whisper API
- [ ] generate() — вызов Ollama API
- [ ] chat() — OpenAI-совместимый вызов
- [ ] Retry с exponential backoff

### Запрос для Claude Code

```
Прочитай docs/api-reference.md.

Создай backend/app/services/ai_client.py:

1. class AIClient:
   def __init__(self, settings: Settings):
       self.settings = settings
       self.http_client = httpx.AsyncClient(timeout=settings.llm_timeout)

2. async def check_services(self) -> dict:
   - Проверяет Ollama: GET {ollama_url}/api/version
   - Проверяет Whisper: GET {whisper_url}/health
   - Возвращает {"ollama": bool, "whisper": bool, "ollama_version": str | None}

3. @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=4, max=60))
   async def transcribe(self, file_path: Path, language: str = "ru") -> dict:
   - POST {whisper_url}/v1/audio/transcriptions
   - multipart/form-data: file, language, response_format="verbose_json"
   - Возвращает JSON ответ

4. @retry(...)
   async def generate(self, prompt: str, model: str | None = None) -> str:
   - POST {ollama_url}/api/generate
   - json: model, prompt, stream=False
   - Возвращает response["response"]

5. @retry(...)
   async def chat(self, messages: list[dict], model: str | None = None) -> str:
   - POST {ollama_url}/v1/chat/completions
   - Возвращает choices[0].message.content

6. async def close(self):
   - Закрывает http_client

Используй:
- import httpx
- from tenacity import retry, stop_after_attempt, wait_exponential
- from backend.app.config import Settings
```

### Критерий готовности

```python
# Тест (при запущенных сервисах)
import asyncio
from backend.app.services.ai_client import AIClient
from backend.app.config import get_settings

async def test():
    client = AIClient(get_settings())
    status = await client.check_services()
    print(status)  # {"ollama": True, "whisper": True, ...}
    await client.close()

asyncio.run(test())
```

---

## Фаза 5: Транскрибер

### Цель

Сервис транскрипции видео через Whisper API.

### Чеклист

- [ ] WhisperTranscriber класс
- [ ] transcribe() — основной метод
- [ ] Парсинг ответа в RawTranscript
- [ ] Обработка ошибок

### Запрос для Claude Code

```
Прочитай docs/pipeline.md — "Этап 2: Transcribe" (исправленную версию с HTTP API).
Прочитай docs/api-reference.md — секцию "Whisper API".

Создай backend/app/services/transcriber.py:

1. class WhisperTranscriber:
   def __init__(self, ai_client: AIClient, settings: Settings):
       self.ai_client = ai_client
       self.settings = settings

2. async def transcribe(self, video_path: Path) -> RawTranscript:
   - Вызывает ai_client.transcribe(video_path)
   - Парсит JSON ответ в список TranscriptSegment
   - Возвращает RawTranscript

3. def _parse_response(self, data: dict) -> RawTranscript:
   - Извлекает segments, language, duration из ответа API
   - Создаёт TranscriptSegment для каждого сегмента
   - Возвращает RawTranscript

Модели из backend.app.models.schemas:
- TranscriptSegment
- RawTranscript
```

### Критерий готовности

```python
# Тест с реальным файлом
transcript = await transcriber.transcribe(Path("test.mp4"))
print(transcript.full_text[:100])
print(f"Segments: {len(transcript.segments)}")
```

---

## Фаза 6: Cleaner

### Цель

Сервис очистки транскрипта через Ollama.

### Чеклист

- [ ] TranscriptCleaner класс
- [ ] clean() — основной метод
- [ ] Загрузка промпта
- [ ] Применение глоссария
- [ ] Парсинг ответа LLM

### Запрос для Claude Code

```
Прочитай docs/pipeline.md — "Этап 3: Clean".
Прочитай docs/llm-prompts.md — промпт cleaner.

Создай backend/app/services/cleaner.py:

1. class TranscriptCleaner:
   def __init__(self, ai_client: AIClient, settings: Settings):
       self.ai_client = ai_client
       self.settings = settings
       self.prompt_template = load_prompt("cleaner")
       self.glossary = load_glossary()

2. async def clean(self, raw_transcript: RawTranscript, metadata: VideoMetadata) -> CleanedTranscript:
   - Применяет глоссарий к тексту (pre-processing)
   - Формирует промпт с контекстом (спикер, тема)
   - Вызывает ai_client.generate()
   - Парсит ответ
   - Возвращает CleanedTranscript

3. def _apply_glossary(self, text: str) -> str:
   - Заменяет вариации терминов на канонические
   - Использует self.glossary

4. def _build_prompt(self, text: str, metadata: VideoMetadata) -> str:
   - Подставляет переменные в шаблон промпта
   - speaker, title, text
```

### Критерий готовности

```python
cleaned = await cleaner.clean(raw_transcript, metadata)
print(f"Original: {cleaned.original_length}, Cleaned: {cleaned.cleaned_length}")
```

---

## Фаза 7: Chunker

### Цель

Сервис смыслового разбиения через Ollama.

### Чеклист

- [ ] SemanticChunker класс
- [ ] chunk() — основной метод
- [ ] Парсинг JSON ответа LLM
- [ ] Генерация chunk IDs

### Запрос для Claude Code

```
Прочитай docs/pipeline.md — "Этап 4: Chunk".
Прочитай docs/llm-prompts.md — промпт chunker.

Создай backend/app/services/chunker.py:

1. class SemanticChunker:
   def __init__(self, ai_client: AIClient, settings: Settings):
       self.ai_client = ai_client
       self.settings = settings
       self.prompt_template = load_prompt("chunker")

2. async def chunk(self, cleaned: CleanedTranscript, metadata: VideoMetadata) -> TranscriptChunks:
   - Формирует промпт
   - Вызывает ai_client.generate()
   - Парсит JSON из ответа
   - Генерирует IDs для чанков
   - Возвращает TranscriptChunks

3. def _parse_chunks(self, response: str, video_id: str) -> list[TranscriptChunk]:
   - Извлекает JSON из ответа (может быть обёрнут в markdown)
   - Создаёт TranscriptChunk с ID = {video_id}_chunk_{index}
   - Считает word_count

4. def _extract_json(self, text: str) -> dict:
   - Извлекает JSON из текста (убирает ```json ... ```)
```

### Критерий готовности

```python
chunks = await chunker.chunk(cleaned_transcript, metadata)
print(f"Chunks: {chunks.total_chunks}, Avg size: {chunks.avg_chunk_size}")
```

---

## Фаза 8: Summarizer

### Цель

Сервис саммаризации и классификации через Ollama.

### Чеклист

- [ ] VideoSummarizer класс
- [ ] summarize() — основной метод
- [ ] Парсинг структурированного ответа
- [ ] Валидация полей

### Запрос для Claude Code

```
Прочитай docs/pipeline.md — "Этап 5: Summarize".
Прочитай docs/llm-prompts.md — промпт summarizer.

Создай backend/app/services/summarizer.py:

1. class VideoSummarizer:
   def __init__(self, ai_client: AIClient, settings: Settings):
       self.ai_client = ai_client
       self.settings = settings
       self.prompt_template = load_prompt("summarizer")

2. async def summarize(self, cleaned: CleanedTranscript, metadata: VideoMetadata) -> VideoSummary:
   - Формирует промпт с контекстом
   - Вызывает ai_client.generate()
   - Парсит JSON ответ
   - Валидирует поля
   - Возвращает VideoSummary

3. def _parse_summary(self, response: str) -> VideoSummary:
   - Извлекает JSON
   - Создаёт VideoSummary
   - Устанавливает defaults для отсутствующих полей

4. VALID_SECTIONS = ["Обучение", "Продукты", "Бизнес", "Мотивация"]
   - Валидация section
```

### Критерий готовности

```python
summary = await summarizer.summarize(cleaned_transcript, metadata)
print(f"Section: {summary.section}")
print(f"Tags: {summary.tags}")
```

---

## Фаза 9: Saver

### Цель

Сервис сохранения результатов в файловую систему.

### Чеклист

- [ ] FileSaver класс
- [ ] save() — сохранение всех файлов
- [ ] Генерация transcript_chunks.json
- [ ] Генерация summary.md
- [ ] Сохранение transcript_raw.txt
- [ ] Перемещение видео в archive

### Запрос для Claude Code

```
Прочитай docs/pipeline.md — "Этап 6: Save Files".
Прочитай docs/data-formats.md — форматы файлов.

Создай backend/app/services/saver.py:

1. class FileSaver:
   def __init__(self, settings: Settings):
       self.settings = settings

2. async def save(
       self,
       metadata: VideoMetadata,
       raw_transcript: RawTranscript,
       chunks: TranscriptChunks,
       summary: VideoSummary
   ) -> list[str]:
   - Создаёт папку archive
   - Сохраняет все файлы
   - Перемещает видео
   - Возвращает список созданных файлов

3. def _create_archive_path(self, metadata: VideoMetadata) -> Path:
   - Формат: archive/{год}/{месяц}/{тип}.{поток}/{тема} ({спикер})/

4. def _save_chunks_json(self, path: Path, metadata, raw_transcript, chunks) -> Path:
   - Формат из docs/data-formats.md

5. def _save_summary_md(self, path: Path, metadata, raw_transcript, summary) -> Path:
   - Markdown с YAML frontmatter

6. def _save_raw_transcript(self, path: Path, raw_transcript) -> Path:
   - Текст с таймкодами

7. def _move_video(self, source: Path, dest_dir: Path) -> Path:
   - shutil.move

Используй:
- import aiofiles
- import shutil
- import json
```

### Критерий готовности

```python
files = await saver.save(metadata, raw_transcript, chunks, summary)
print(f"Created: {files}")
# ['transcript_chunks.json', 'summary.md', 'transcript_raw.txt', 'video.mp4']
```

---

## Фаза 10: Pipeline

### Цель

Оркестратор всех этапов обработки.

### Чеклист

- [ ] PipelineOrchestrator класс
- [ ] process() — полный pipeline
- [ ] Обновление статуса/прогресса
- [ ] Error handling с rollback
- [ ] Callback для прогресса

### Запрос для Claude Code

```
Прочитай docs/pipeline.md — "Полный Pipeline Flow".

Создай backend/app/services/pipeline.py:

1. class PipelineOrchestrator:
   def __init__(self, settings: Settings):
       self.settings = settings
       self.ai_client = AIClient(settings)
       self.parser = ...  # создать все сервисы
       self.transcriber = ...
       self.cleaner = ...
       self.chunker = ...
       self.summarizer = ...
       self.saver = ...

2. async def process(
       self,
       video_path: Path,
       progress_callback: Callable[[ProcessingJob], None] | None = None
   ) -> ProcessingResult:
   
   Этапы:
   - PARSING: parse_filename()
   - TRANSCRIBING: transcriber.transcribe()
   - CLEANING: cleaner.clean()
   - CHUNKING: chunker.chunk()
   - SUMMARIZING: summarizer.summarize()
   - SAVING: saver.save()
   
   После каждого этапа:
   - Обновить job.status, job.progress
   - Вызвать progress_callback(job)

3. def _create_job(self, video_path: Path) -> ProcessingJob:
   - Создаёт новый job с PENDING статусом

4. async def _handle_error(self, job: ProcessingJob, error: Exception):
   - Устанавливает FAILED статус
   - Сохраняет error message
   - Логирует

5. async def close(self):
   - Закрывает ai_client
```

### Критерий готовности

```python
result = await pipeline.process(
    Path("inbox/2025.04.07 ПШ.SV Test.mp4"),
    progress_callback=lambda job: print(f"{job.status}: {job.progress}%")
)
print(f"Done: {result.video_id}")
```

---

## Фаза 11: API

### Цель

FastAPI endpoints для управления обработкой.

### Чеклист

- [ ] Lifespan (startup/shutdown)
- [ ] GET /api/health — статус
- [ ] GET /api/files/inbox — список файлов
- [ ] POST /api/jobs — создать задачу
- [ ] GET /api/jobs — список задач
- [ ] GET /api/jobs/{id} — статус задачи
- [ ] WebSocket /ws/jobs/{id} — прогресс

### Запрос для Claude Code

```
Прочитай docs/architecture.md — секцию "API Endpoints".

Создай backend/app/api/routes.py:

1. router = APIRouter(prefix="/api")

2. GET /health — проверка сервисов
   - Возвращает статус app + AI сервисов

3. GET /files/inbox — список файлов в inbox
   - Фильтр по расширению (.mp4, .mkv, .mov)

4. GET /files/archive — список обработанных

5. POST /jobs — создать задачу обработки
   - Body: {"file_path": "inbox/video.mp4"}
   - Запускает pipeline в background task
   - Возвращает job_id

6. GET /jobs — список всех задач

7. GET /jobs/{job_id} — статус задачи

8. DELETE /jobs/{job_id} — отменить задачу

Создай backend/app/main.py:

1. Lifespan context manager:
   - startup: создать PipelineOrchestrator
   - shutdown: закрыть соединения

2. FastAPI app с routes

3. CORS middleware (для frontend)
```

### Критерий готовности

```bash
cd backend
uvicorn app.main:app --reload --port 8801

# В другом терминале
curl http://localhost:8801/api/health
curl http://localhost:8801/api/files/inbox
```

---

## Фаза 12: Docker

### Цель

Контейнеризация backend.

### Чеклист

- [ ] Dockerfile
- [ ] docker-compose.yml
- [ ] Тест локального запуска
- [ ] Деплой на сервер

### Запрос для Claude Code

```
Прочитай DEPLOYMENT.md.

Создай backend/Dockerfile:
- FROM python:3.11-slim
- Установить зависимости
- Копировать код
- CMD uvicorn

Создай docker-compose.yml (из DEPLOYMENT.md).

Создай scripts/deploy.sh (из DEPLOYMENT.md).
```

### Критерий готовности

```bash
docker-compose up -d --build
curl http://localhost:8801/api/health

# Деплой на сервер
./scripts/deploy.sh
curl http://100.64.0.1:8801/api/health
```

---

## Фаза 13: Frontend

### Цель

React приложение для управления транскрипцией.

### Подфазы

|#|Задача|Время|
|---|---|---|
|13.1|Структура + Vite + Tailwind|30 мин|
|13.2|API клиент + типы|20 мин|
|13.3|Layout + Navigation|30 мин|
|13.4|Dashboard (статус сервисов)|30 мин|
|13.5|FileBrowser (inbox)|45 мин|
|13.6|JobQueue (список задач)|30 мин|
|13.7|JobDetails (прогресс)|30 мин|
|13.8|Settings (промпты, глоссарий)|45 мин|

### Запрос для 13.1

```
Создай frontend/:

1. Инициализация:
   npm create vite@latest . -- --template react-ts
   npm install

2. Зависимости:
   npm install @tanstack/react-query axios zustand
   npm install -D tailwindcss postcss autoprefixer
   npx tailwindcss init -p

3. Структура:
   frontend/
   ├── src/
   │   ├── api/
   │   │   └── client.ts
   │   ├── components/
   │   │   ├── Layout/
   │   │   ├── Dashboard/
   │   │   ├── FileBrowser/
   │   │   ├── JobQueue/
   │   │   └── Settings/
   │   ├── store/
   │   │   └── useStore.ts
   │   ├── types/
   │   │   └── index.ts
   │   ├── App.tsx
   │   └── main.tsx
   └── ...
```

---

## Советы по работе с Claude Code

### Общие принципы

1. **Один файл = один запрос** (желательно)
2. **Проверяй после каждой фазы** — не накапливай ошибки
3. **Давай контекст** — указывай какие файлы читать
4. **Будь конкретен** — "создай функцию X" лучше чем "сделай парсер"

### Если что-то не работает

```
Посмотри ошибку:
[вставить ошибку]

Файл: backend/app/services/parser.py

Исправь.
```

### Рефакторинг

```
Прочитай backend/app/services/cleaner.py.

Проблема: [описание]

Исправь: [что нужно сделать]
```

### Добавление фичи

```
Прочитай backend/app/services/pipeline.py.

Добавь:
- Сохранение промежуточных результатов в temp/
- Возможность продолжить с последнего этапа при ошибке
```

---

## Статус реализации

> Обновляй по мере выполнения

|Фаза|Статус|Дата|Заметки|
|---|---|---|---|
|0. Структура|✅|2025-01-08|Папки, __init__.py, requirements.txt, .env.example|
|1. Модели|✅|2025-01-08|10 Pydantic моделей в schemas.py|
|2. Конфигурация|✅|2025-01-08|config.py + prompts + glossary + events|
|3. Парсер|⏳|||
|4. AI клиент|⏳|||
|5. Транскрибер|⏳|||
|6. Cleaner|⏳|||
|7. Chunker|⏳|||
|8. Summarizer|⏳|||
|9. Saver|⏳|||
|10. Pipeline|⏳|||
|11. API|⏳|||
|12. Docker|⏳|||
|13. Frontend|⏳|||

Легенда: ⏳ Ожидает | 🔄 В процессе | ✅ Готово | ❌ Проблема