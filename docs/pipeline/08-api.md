# Pipeline API

[< Назад: Orchestrator](07-orchestrator.md) | [Обзор Pipeline](README.md)

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
| GET | `/health/services` | Статус AI сервисов (Whisper, Ollama) |

### Full Pipeline

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/api/process` | Запуск полного pipeline |
| GET | `/api/jobs` | Список всех jobs |
| GET | `/api/jobs/{job_id}` | Статус конкретного job |
| GET | `/api/inbox` | Список файлов в inbox |
| WS | `/ws/{job_id}` | Real-time progress |

### Step-by-Step

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/api/step/parse` | Парсинг имени файла |
| POST | `/api/step/transcribe` | Транскрипция (долго) |
| POST | `/api/step/clean` | Очистка через LLM |
| POST | `/api/step/chunk` | Семантическое разбиение |
| POST | `/api/step/summarize` | Создание саммари |
| POST | `/api/step/save` | Сохранение результатов |

---

## Полный Pipeline

### POST /api/process

Запуск обработки видео с real-time progress через WebSocket.

**Request:**
```bash
curl -X POST http://localhost:8801/api/process \
  -H "Content-Type: application/json" \
  -d '{"video_filename": "2025.01.09 ПШ.SV Title (Speaker).mp4"}'
```

**Response:**
```json
{
  "job_id": "abc123",
  "video_path": "/data/inbox/2025.01.09 ПШ.SV Title (Speaker).mp4",
  "status": "pending",
  "progress": 0,
  "current_stage": "",
  "created_at": "2025-01-09T12:00:00"
}
```

### WebSocket /ws/{job_id}

Real-time progress updates.

**Python client:**
```python
import asyncio
import websockets
import json

async def monitor_job(job_id: str):
    uri = f"ws://localhost:8801/ws/{job_id}"
    async with websockets.connect(uri) as ws:
        async for message in ws:
            data = json.loads(message)
            print(f"[{data['status']}] {data['progress']:.0f}% - {data['message']}")

            if data['status'] in ('completed', 'failed'):
                if 'result' in data:
                    print(f"Result: {data['result']}")
                break

asyncio.run(monitor_job("abc123"))
```

**Messages:**
```json
// Progress update
{
  "status": "transcribing",
  "progress": 25.5,
  "message": "Transcribing: video.mp4",
  "timestamp": "2025-01-09T12:00:05"
}

// Completion
{
  "status": "completed",
  "progress": 100,
  "message": "Saved 4 files",
  "timestamp": "2025-01-09T12:05:00",
  "result": {
    "video_id": "2025-01-09_ПШ-SV_title",
    "chunks_count": 12,
    "files_created": ["raw.json", "chunks.json", "summary.json", "summary.md"]
  }
}

// Failure
{
  "status": "failed",
  "progress": 25,
  "message": "[transcribing] Whisper API error",
  "timestamp": "2025-01-09T12:00:30",
  "error": "Connection refused"
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

> **Архитектура прогресса:** [docs/pipeline/07-orchestrator.md#progressestimator](07-orchestrator.md#progressestimator)

### Сценарий тестирования промптов

```python
import requests

BASE = "http://localhost:8801/api/step"

# 1. Parse (быстро)
r = requests.post(f"{BASE}/parse", json={"video_filename": "video.mp4"})
metadata = r.json()

# 2. Transcribe (долго - один раз)
r = requests.post(f"{BASE}/transcribe", json={"video_filename": "video.mp4"})
raw_transcript = r.json()

# 3. Clean
r = requests.post(f"{BASE}/clean", json={
    "raw_transcript": raw_transcript,
    "metadata": metadata
})
cleaned = r.json()

# 4. Chunk
r = requests.post(f"{BASE}/chunk", json={
    "cleaned_transcript": cleaned,
    "metadata": metadata
})
chunks = r.json()

# 5. Summarize с разными промптами
for prompt in ["summarizer", "summarizer_v2", "summarizer_detailed"]:
    r = requests.post(f"{BASE}/summarize", json={
        "cleaned_transcript": cleaned,
        "metadata": metadata,
        "prompt_name": prompt
    })
    summary = r.json()
    print(f"\n=== {prompt} ===")
    print(f"Summary: {summary['summary'][:200]}...")
    print(f"Key points: {len(summary['key_points'])}")

# 6. Save лучший вариант
r = requests.post(f"{BASE}/save", json={
    "metadata": metadata,
    "raw_transcript": raw_transcript,
    "chunks": chunks,
    "summary": best_summary
})
files = r.json()
print(f"Saved: {files}")
```

### POST /api/step/summarize

Тестирование разных промптов.

**Request:**
```json
{
  "cleaned_transcript": {...},
  "metadata": {...},
  "prompt_name": "summarizer_v2"
}
```

Промпты читаются из `config/prompts/{prompt_name}.md`.

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI App                              │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   routes    │  │ step_routes │  │  websocket  │              │
│  │ /api/*      │  │ /api/step/* │  │  /ws/*      │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                      │
│         └────────────────┼────────────────┘                      │
│                          │                                       │
│                   ┌──────▼──────┐                                │
│                   │ JobManager  │ ← in-memory dict               │
│                   └──────┬──────┘                                │
│                          │                                       │
│                   ┌──────▼──────┐                                │
│                   │ Orchestrator│                                │
│                   └─────────────┘                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Файлы

| Файл | Описание |
|------|----------|
| `backend/app/main.py` | FastAPI приложение |
| `backend/app/api/routes.py` | HTTP endpoints |
| `backend/app/api/step_routes.py` | Пошаговый режим |
| `backend/app/api/websocket.py` | WebSocket handler |
| `backend/app/services/job_manager.py` | In-memory job store |
