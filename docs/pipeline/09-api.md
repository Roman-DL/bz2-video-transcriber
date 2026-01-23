# Pipeline API

[< Назад: Orchestrator](08-orchestrator.md) | [Обзор Pipeline](README.md)

---

## Обзор

FastAPI приложение для управления pipeline обработки видео.

**Запуск:**
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8801
```

**Документация:** http://localhost:8801/docs

---

## Endpoints

### Health

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/health` | Базовый health check |
| GET | `/health/services` | Статус AI сервисов (Whisper, Ollama, Claude) |

### Archive

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/inbox` | Список файлов в inbox |
| GET | `/api/archive` | Структура архива (tree) |
| GET | `/api/archive/results` | Результаты pipeline по видео |

### Step-by-Step

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/api/step/parse` | Парсинг имени файла |
| POST | `/api/step/transcribe` | Транскрипция через Whisper (SSE) |
| POST | `/api/step/clean` | Очистка через LLM (SSE) |
| POST | `/api/step/slides` | Извлечение текста со слайдов (SSE, v0.50+) |
| POST | `/api/step/longread` | Генерация лонгрида (SSE) |
| POST | `/api/step/summarize` | Генерация конспекта (SSE) |
| POST | `/api/step/story` | Генерация лидерской истории (SSE, v0.23+) |
| POST | `/api/step/chunk` | H2 разбиение markdown |
| POST | `/api/step/save` | Сохранение результатов |

### Models API

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/models/available` | Доступные модели (Ollama, Claude, Whisper) |
| GET | `/api/models/default` | Модели по умолчанию для каждого этапа |
| GET | `/api/models/config` | Конфигурация моделей из models.yaml |

### Prompts API (v0.31+)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/prompts/{stage}` | Варианты промптов для этапа |

### Cache API (v0.18+)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/api/cache/{video_id}` | Информация о кэше видео |
| GET | `/api/cache/{video_id}/{stage}` | Кэшированный результат этапа |
| POST | `/api/cache/rerun` | Перезапуск этапа с другой моделью (SSE) |
| POST | `/api/cache/version` | Установка текущей версии результата |

> **Подробнее:** [ADR-005: Result Caching](../adr/005-result-caching.md)

---

## Archive API

### GET /api/inbox

Список медиа-файлов в inbox директории.

**Response:**
```json
["2025.01.09 ПШ.SV Title (Speaker).mp4", "recording.mp3"]
```

**Поддерживаемые форматы:**
- Видео: mp4, mkv, avi, mov, webm
- Аудио: mp3, wav, m4a, flac, aac, ogg

### GET /api/archive

Структура архива в виде дерева.

**Response:**
```json
{
  "tree": {
    "2025": {
      "01.22 ПШ": [
        {"title": "SV Topic", "speaker": "Speaker", "event_type": "ПШ", "mid_folder": "01.22"}
      ],
      "Форум Табтим": [
        {"title": "Leadership Story", "speaker": "Name", "event_type": "Выездные", "mid_folder": "Форум Табтим"}
      ]
    }
  },
  "total": 42
}
```

### GET /api/archive/results

Получение результатов pipeline для архивного видео.

**Query params:**
- `year` — год (2025)
- `event_type` — тип события (ПШ, Выездные)
- `mid_folder` — папка даты/события (01.22, Форум Табтим)
- `topic_folder` — папка темы (SV Topic (Speaker))

**Response:**
```json
{
  "available": true,
  "data": {
    "metadata": {...},
    "rawTranscript": {...},
    "cleanedTranscript": {...},
    "longread": {...},
    "summary": {...},
    "chunks": {...}
  }
}
```

---

## Пошаговый режим

Для тестирования промптов и глоссария без повторной транскрипции.

### SSE прогресс

Step-by-step endpoints возвращают SSE поток с оценочным прогрессом выполнения.

**Формат событий:**

```json
// Прогресс (каждую секунду)
{
  "type": "progress",
  "status": "transcribing",
  "progress": 45.5,
  "message": "Transcribing: video.mp4",
  "estimated_seconds": 200.0,
  "elapsed_seconds": 91.0
}

// Результат (после завершения)
{"type": "result", "data": {...}}

// Ошибка
{"type": "error", "error": "..."}
```

**Поля прогресса:**

| Поле | Тип | Описание |
|------|-----|----------|
| `progress` | float | Текущий прогресс в процентах (0-100) |
| `estimated_seconds` | float | Оценочное общее время операции |
| `elapsed_seconds` | float | Прошедшее время с начала операции |

Клиент может рассчитать оставшееся время: `remaining = estimated_seconds - elapsed_seconds`

**curl тест SSE:**

```bash
curl -N -X POST http://localhost:8801/api/step/transcribe \
  -H "Content-Type: application/json" \
  -d '{"video_filename": "test.mp4"}'

# Ожидаемый вывод:
data: {"type": "progress", "status": "transcribing", "progress": 0.0, "message": "...", "estimated_seconds": 200.0, "elapsed_seconds": 0.0}
data: {"type": "progress", "status": "transcribing", "progress": 48.2, "message": "...", "estimated_seconds": 200.0, "elapsed_seconds": 96.4}
data: {"type": "result", "data": {...}}
```

> **Архитектура прогресса:** [docs/pipeline/08-orchestrator.md#progressmanager](08-orchestrator.md#progressmanager)

### Сценарий тестирования промптов

```python
import requests

BASE = "http://localhost:8801/api/step"

# 1. Parse (быстро, без SSE)
r = requests.post(f"{BASE}/parse", json={"video_filename": "video.mp4"})
metadata = r.json()

# 2. Transcribe (долго, SSE) - один раз
r = requests.post(f"{BASE}/transcribe", json={"video_filename": "video.mp4"}, stream=True)
for line in r.iter_lines():
    if line:
        event = json.loads(line.decode().removeprefix("data: "))
        if event["type"] == "result":
            raw_transcript = event["data"]["rawTranscript"]
            audio_path = event["data"]["audioPath"]
            break

# 3. Clean (SSE)
r = requests.post(f"{BASE}/clean", json={
    "rawTranscript": raw_transcript,
    "metadata": metadata
}, stream=True)
# ... parse SSE for cleaned_transcript

# 4. Slides (опционально, SSE) - если есть слайды
r = requests.post(f"{BASE}/slides", json={
    "slides": [
        {"filename": "slide1.jpg", "contentType": "image/jpeg", "data": "base64..."}
    ]
}, stream=True)
# ... parse SSE for slides_text

# 5a. Longread (EDUCATIONAL, SSE) - из cleaned_transcript
r = requests.post(f"{BASE}/longread", json={
    "cleanedTranscript": cleaned_transcript,
    "metadata": metadata,
    "slidesText": slides_text  # опционально
}, stream=True)
# ... parse SSE for longread

# 5b. Story (LEADERSHIP, SSE) - из cleaned_transcript
r = requests.post(f"{BASE}/story", json={
    "cleanedTranscript": cleaned_transcript,
    "metadata": metadata,
    "slidesText": slides_text  # опционально
}, stream=True)
# ... parse SSE for story

# 6. Summarize (EDUCATIONAL, SSE) - из cleaned_transcript
r = requests.post(f"{BASE}/summarize", json={
    "cleanedTranscript": cleaned_transcript,
    "metadata": metadata
}, stream=True)
# ... parse SSE for summary

# 7. Chunk (быстро, без SSE) - H2 парсинг markdown
markdown_content = longread["markdown"] if metadata["content_type"] == "educational" else story["markdown"]
r = requests.post(f"{BASE}/chunk", json={
    "markdownContent": markdown_content,
    "metadata": metadata
})
chunks = r.json()

# 8. Save (быстро, без SSE)
r = requests.post(f"{BASE}/save", json={
    "metadata": metadata,
    "rawTranscript": raw_transcript,
    "cleanedTranscript": cleaned_transcript,
    "chunks": chunks,
    "longread": longread,      # для EDUCATIONAL
    "summary": summary,        # для EDUCATIONAL
    "story": story,            # для LEADERSHIP
    "audioPath": audio_path,
    "slidesExtraction": slides_extraction  # опционально
})
files = r.json()
print(f"Saved: {files}")
```

---

## Step Endpoints

### POST /api/step/parse

**Input:** `StepParseRequest`
```json
{"videoFilename": "2025.01.09 ПШ.SV Title (Speaker).mp4"}
```

**Output:** `VideoMetadata`
```json
{
  "date": "2025-01-09",
  "eventType": "ПШ",
  "stream": "SV",
  "title": "Title",
  "speaker": "Speaker",
  "videoId": "2025-01-09_ПШ-SV_title",
  "contentType": "educational",
  "eventCategory": "regular",
  "durationSeconds": 3600.5
}
```

### POST /api/step/transcribe

**Input:** `StepParseRequest`
```json
{"videoFilename": "video.mp4"}
```

**Output (SSE):** `TranscribeResult`
```json
{
  "rawTranscript": {
    "segments": [...],
    "fullText": "...",
    "textWithTimestamps": "..."
  },
  "audioPath": "/data/inbox/video.mp3",
  "displayText": "..."
}
```

### POST /api/step/clean

**Input:** `StepCleanRequest`
```json
{
  "rawTranscript": {...},
  "metadata": {...},
  "model": "claude-sonnet-4-5",
  "promptOverrides": {"system": "system_v2"}
}
```

**Output (SSE):** `CleanedTranscript`
```json
{
  "text": "...",
  "tokensUsed": {"input": 1000, "output": 500, "total": 1500},
  "cost": 0.015,
  "processingTimeSec": 12.5,
  "words": 5000,
  "changePercent": 15.2
}
```

### POST /api/step/slides (v0.50+)

Извлечение текста со слайдов через Claude Vision API.

**Input:** `StepSlidesRequest`
```json
{
  "slides": [
    {"filename": "slide1.jpg", "contentType": "image/jpeg", "data": "base64..."},
    {"filename": "presentation.pdf", "contentType": "application/pdf", "data": "base64..."}
  ],
  "model": "claude-haiku-4-5",
  "promptOverrides": {}
}
```

**Output (SSE):** `SlidesExtractionResult`
```json
{
  "extractedText": "# Slide 1\n\nContent...",
  "slidesCount": 15,
  "charsCount": 5000,
  "wordsCount": 800,
  "tablesCount": 3,
  "model": "claude-haiku-4-5",
  "tokensUsed": {"input": 2000, "output": 1000, "total": 3000},
  "cost": 0.007,
  "processingTimeSec": 45.0
}
```

### POST /api/step/longread

Генерация лонгрида из очищенного транскрипта (для `content_type=educational`).

**Input:** `StepLongreadRequest`
```json
{
  "cleanedTranscript": {...},
  "metadata": {...},
  "model": "claude-sonnet-4-5",
  "promptOverrides": {},
  "slidesText": "..."
}
```

**Output (SSE):** `Longread`
```json
{
  "markdown": "# Title\n\n## Introduction\n...",
  "totalSections": 8,
  "totalWordCount": 3500,
  "tokensUsed": {...},
  "cost": 0.045,
  "processingTimeSec": 60.0,
  "chars": 25000
}
```

### POST /api/step/summarize

Генерация конспекта из очищенного транскрипта (для `content_type=educational`).

**Input:** `StepSummarizeRequest`
```json
{
  "cleanedTranscript": {...},
  "metadata": {...},
  "model": "claude-sonnet-4-5",
  "promptOverrides": {}
}
```

**Output (SSE):** `Summary`
```json
{
  "markdown": "# Конспект\n\n## Суть\n...",
  "tokensUsed": {...},
  "cost": 0.025,
  "processingTimeSec": 30.0,
  "chars": 8000,
  "words": 1200
}
```

### POST /api/step/story (v0.23+)

Генерация лидерской истории из очищенного транскрипта (для `content_type=leadership`).

**Input:** `StepStoryRequest`
```json
{
  "cleanedTranscript": {...},
  "metadata": {...},
  "model": "claude-sonnet-4-5",
  "promptOverrides": {},
  "slidesText": "..."
}
```

**Output (SSE):** `Story`
```json
{
  "markdown": "# История\n\n## Блок 1: Контекст\n...",
  "tokensUsed": {...},
  "cost": 0.035,
  "processingTimeSec": 45.0,
  "chars": 12000
}
```

### POST /api/step/chunk

Детерминированное разбиение markdown по H2 заголовкам (без LLM).

**Input:** `StepChunkRequest`
```json
{
  "markdownContent": "# Title\n\n## Section 1\n...",
  "metadata": {...}
}
```

**Output:** `TranscriptChunks`
```json
{
  "chunks": [
    {"id": "chunk-001", "title": "Section 1", "content": "...", "tokens": 500}
  ],
  "totalTokens": 3500
}
```

### POST /api/step/save

**Input:** `StepSaveRequest`
```json
{
  "metadata": {...},
  "rawTranscript": {...},
  "cleanedTranscript": {...},
  "chunks": {...},
  "longread": {...},
  "summary": {...},
  "story": {...},
  "audioPath": "/data/inbox/video.mp3",
  "slidesExtraction": {...}
}
```

**Output:** `list[str]`
```json
["raw.json", "cleaned.json", "chunks.json", "longread.md", "summary.md", "pipeline_results.json"]
```

---

## Models API

### GET /api/models/available

**Response:** `AvailableModelsResponse`
```json
{
  "ollamaModels": ["gemma2:9b", "qwen2.5:14b"],
  "whisperModels": [
    {"id": "Systran/faster-whisper-large-v3", "name": "large-v3"}
  ],
  "claudeModels": [
    {"id": "claude-sonnet-4-5", "name": "Claude Sonnet 4.5", "pricing": {"input": 3.0, "output": 15.0}}
  ],
  "providers": {
    "local": {"available": true, "name": "Ollama"},
    "cloud": {"available": true, "name": "Claude API"}
  }
}
```

### GET /api/models/default

**Response:** `DefaultModelsResponse`
```json
{
  "transcribe": "Systran/faster-whisper-large-v3",
  "clean": "claude-sonnet-4-5",
  "longread": "claude-sonnet-4-5",
  "summarize": "claude-sonnet-4-5"
}
```

---

## Prompts API

### GET /api/prompts/{stage}

Получение доступных вариантов промптов для этапа pipeline.

**Stages:** `cleaning`, `longread`, `summary`, `story`

**Response:** `StagePromptsResponse`
```json
{
  "stage": "cleaning",
  "components": [
    {
      "component": "system",
      "default": "system",
      "variants": [
        {"name": "system", "source": "builtin", "filename": "system.md"},
        {"name": "system_v2", "source": "external", "filename": "system_v2.md"}
      ]
    },
    {
      "component": "user",
      "default": "user",
      "variants": [
        {"name": "user", "source": "builtin", "filename": "user.md"}
      ]
    }
  ]
}
```

---

## Cache API

### GET /api/cache/{video_id}

**Response:** `CacheInfo`
```json
{
  "videoId": "2025-01-09_ПШ-SV_title",
  "stages": {
    "cleaning": {
      "currentVersion": 2,
      "versions": [
        {"version": 1, "model": "gemma2:9b", "createdAt": "2025-01-09T10:00:00"},
        {"version": 2, "model": "claude-sonnet-4-5", "createdAt": "2025-01-09T11:00:00"}
      ]
    }
  }
}
```

### GET /api/cache/{video_id}/{stage}

Получение кэшированного результата этапа.

**Query params:**
- `version` — номер версии (опционально, по умолчанию текущая)

**Response:** Результат этапа (CleanedTranscript, Longread, Summary и т.д.)

### POST /api/cache/rerun

Перезапуск этапа с другой моделью. Создаёт новую версию в кэше.

**Input:** `RerunRequest`
```json
{
  "videoId": "2025-01-09_ПШ-SV_title",
  "stage": "cleaning",
  "model": "claude-sonnet-4-5"
}
```

**Output (SSE):** `RerunResponse`
```json
{
  "videoId": "2025-01-09_ПШ-SV_title",
  "stage": "cleaning",
  "newVersion": 3,
  "modelName": "claude-sonnet-4-5"
}
```

### POST /api/cache/version

Установка конкретной версии как текущей.

**Query params:**
- `video_id` — идентификатор видео
- `stage` — название этапа
- `version` — номер версии

**Response:** `CacheVersionResponse`
```json
{
  "status": "ok",
  "stage": "cleaning",
  "version": 1
}
```

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────────────┐
│                           FastAPI App                                │
│                                                                      │
│  ┌───────────┐ ┌─────────────┐ ┌──────────────┐ ┌────────────────┐  │
│  │  routes   │ │ step_routes │ │ cache_routes │ │ models_routes  │  │
│  │ /api/*    │ │ /api/step/* │ │ /api/cache/* │ │ /api/models/*  │  │
│  └─────┬─────┘ └──────┬──────┘ └──────┬───────┘ └───────┬────────┘  │
│        │              │               │                  │           │
│        │       ┌──────────────┐       │                  │           │
│        │       │prompts_routes│       │                  │           │
│        │       │/api/prompts/*│       │                  │           │
│        │       └──────┬───────┘       │                  │           │
│        │              │               │                  │           │
│        └──────────────┴───────────────┴──────────────────┘           │
│                               │                                      │
│                        ┌──────▼──────┐                               │
│                        │ Orchestrator│                               │
│                        └──────┬──────┘                               │
│                               │                                      │
│              ┌────────────────┼────────────────┐                     │
│              ▼                ▼                ▼                     │
│       ┌────────────┐   ┌────────────┐   ┌────────────┐               │
│       │ AI Clients │   │StageCache  │   │  Services  │               │
│       │Claude/Ollama│   │VersionMgr │   │Parser/Saver│               │
│       └────────────┘   └────────────┘   └────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Файлы

| Файл | Описание |
|------|----------|
| `backend/app/main.py` | FastAPI приложение, health endpoints |
| `backend/app/api/routes.py` | Archive API (inbox, archive, results) |
| `backend/app/api/step_routes.py` | Step-by-step режим с SSE |
| `backend/app/api/cache_routes.py` | Cache API (v0.18+) |
| `backend/app/api/models_routes.py` | Models API |
| `backend/app/api/prompts_routes.py` | Prompts API (v0.31+) |
