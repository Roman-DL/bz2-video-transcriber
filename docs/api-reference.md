---
doc_type: reference
status: active
updated: 2026-01-24
audience: [developer, ai-agent]
tags:
  - api
  - reference
---

# API Reference: Локальные AI сервисы

> Справочник по HTTP API для интеграции с Ollama и Whisper.
> Все сервисы доступны через Tailscale по адресу `100.64.0.1`.

---

## API соглашения (v0.59+)

### JSON сериализация

Все ответы Backend API используют **camelCase** для ключей JSON:

| Слой | Формат | Пример |
|------|--------|--------|
| Python код | snake_case | `raw_transcript` |
| API JSON | camelCase | `rawTranscript` |
| TypeScript | camelCase | `rawTranscript` |

**Запросы** принимают оба формата (camelCase и snake_case) для обратной совместимости.

### Типизированные endpoints

Все API endpoints возвращают Pydantic модели (не `dict`):

| Endpoint | Метод | Response Model | Описание |
|----------|-------|----------------|----------|
| `/api/models/available` | GET | `AvailableModelsResponse` | Список доступных моделей |
| `/api/models/default` | GET | `DefaultModelsResponse` | Модели по умолчанию |
| `/api/models/config` | GET | `dict` (raw YAML) | Конфигурация моделей |
| `/api/archive` | GET | `ArchiveResponse` | Список файлов архива |
| `/api/archive/results` | GET | `PipelineResultsResponse` | Результаты обработки |
| `/api/cache/{video_id}` | GET | `CacheInfo` | Информация о кэше |
| `/api/cache/rerun` | POST | `RerunResponse` (SSE) | Перезапуск этапа |
| `/api/cache/version` | POST | `CacheVersionResponse` | Установка версии |
| `/api/prompts/{stage}` | GET | `PromptsResponse` | Варианты промптов |
| `/api/step/slides` | POST | `SlidesExtractionResult` (SSE) | Извлечение со слайдов |
| `/api/step/clean` | POST | `CleanedTranscript` (SSE) | Очистка транскрипта |
| `/api/step/longread` | POST | `Longread` (SSE) | Генерация лонгрида |
| `/api/step/summarize` | POST | `Summary` (SSE) | Генерация конспекта |
| `/api/step/story` | POST | `Story` (SSE) | Генерация истории |
| `/api/inbox` | GET | `list[str]` | Список файлов в inbox |
| `/api/step/parse` | POST | `VideoMetadata` | Парсинг имени файла |
| `/api/step/transcribe` | POST | `TranscribeResult` (SSE) | Транскрипция видео |
| `/api/step/chunk` | POST | `TranscriptChunks` | Чанкирование H2 |
| `/api/step/save` | POST | `list[str]` | Сохранение в архив |

Подробнее: [ADR-013: CamelCase сериализация](adr/013-api-camelcase-serialization.md)

---

## Whisper API (faster-whisper-server)

**Base URL:** `http://100.64.0.1:9000`

### Транскрипция аудио/видео

**Endpoint:** `POST /v1/audio/transcriptions`

**Параметры (multipart/form-data):**

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `file` | file | ✅ | Аудио/видео файл (mp3, mp4, wav, m4a, webm, flac) |
| `language` | string | ❌ | Код языка (ru, en). По умолчанию: ru |
| `response_format` | string | ❌ | Формат ответа: text, json, srt, vtt. По умолчанию: json |

### Python пример

```python
import requests

def transcribe(file_path: str, language: str = "ru") -> str:
    """Транскрибировать аудио/видео файл через Whisper API."""
    url = "http://100.64.0.1:9000/v1/audio/transcriptions"
    
    with open(file_path, "rb") as f:
        response = requests.post(
            url,
            files={"file": f},
            data={
                "language": language,
                "response_format": "text"
            },
            timeout=600  # 10 минут для длинных видео
        )
    
    response.raise_for_status()
    return response.text


def transcribe_with_timestamps(file_path: str, language: str = "ru") -> dict:
    """Транскрипция с таймкодами (JSON формат)."""
    url = "http://100.64.0.1:9000/v1/audio/transcriptions"
    
    with open(file_path, "rb") as f:
        response = requests.post(
            url,
            files={"file": f},
            data={
                "language": language,
                "response_format": "verbose_json"
            },
            timeout=600
        )
    
    response.raise_for_status()
    return response.json()
```

### curl примеры

```bash
# Простой текст
curl -X POST "http://100.64.0.1:9000/v1/audio/transcriptions" \
  -F "file=@video.mp4" \
  -F "language=ru" \
  -F "response_format=text"

# SRT субтитры
curl -X POST "http://100.64.0.1:9000/v1/audio/transcriptions" \
  -F "file=@video.mp4" \
  -F "language=ru" \
  -F "response_format=srt" \
  -o subtitles.srt

# JSON с детальной информацией
curl -X POST "http://100.64.0.1:9000/v1/audio/transcriptions" \
  -F "file=@video.mp4" \
  -F "language=ru" \
  -F "response_format=verbose_json"
```

### Проверка доступности

```python
def check_whisper() -> bool:
    """Проверить доступность Whisper сервиса."""
    try:
        response = requests.get("http://100.64.0.1:9000/health", timeout=5)
        return response.text == "OK"
    except:
        return False
```

### Производительность

| Метрика | Значение |
|---------|----------|
| Модель | large-v3 |
| Первая загрузка | ~65 сек (модель в VRAM) |
| Транскрипция | ~4-5 сек на 15 сек аудио |
| VRAM | ~3.5 GB |

> **Важно:** Первый запрос после простоя медленный (загрузка модели). Последующие — быстрые.

---

## Ollama API

**Base URL:** `http://100.64.0.1:11434`

### Генерация текста (Native API)

**Endpoint:** `POST /api/generate`

```python
import requests

def generate(prompt: str, model: str = "qwen2.5:14b") -> str:
    """Генерация текста через Ollama API."""
    response = requests.post(
        "http://100.64.0.1:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False
        },
        timeout=300  # 5 минут для длинных промптов
    )
    
    response.raise_for_status()
    return response.json()["response"]
```

### Chat Completions (OpenAI-совместимый)

**Endpoint:** `POST /v1/chat/completions`

```python
def chat(
    messages: list[dict],
    model: str = "qwen2.5:14b",
    temperature: float = 0.7
) -> str:
    """Chat через OpenAI-совместимый API."""
    response = requests.post(
        "http://100.64.0.1:11434/v1/chat/completions",
        json={
            "model": model,
            "messages": messages,
            "temperature": temperature
        },
        timeout=300
    )
    
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


# Пример использования
result = chat([
    {"role": "system", "content": "Ты — редактор текста. Отвечай только исправленным текстом."},
    {"role": "user", "content": "Исправь ошибки: Привет как дел вчера ходил в магазин"}
])
```

### curl примеры

```bash
# Простая генерация
curl http://100.64.0.1:11434/api/generate -d '{
  "model": "qwen2.5:14b",
  "prompt": "Переведи на английский: Привет, мир!",
  "stream": false
}'

# Chat (OpenAI формат)
curl http://100.64.0.1:11434/v1/chat/completions -d '{
  "model": "qwen2.5:14b",
  "messages": [
    {"role": "system", "content": "Ты помощник."},
    {"role": "user", "content": "Привет!"}
  ]
}'
```

### Проверка доступности

```python
def check_ollama() -> dict:
    """Проверить Ollama и список моделей."""
    try:
        # Версия
        version = requests.get(
            "http://100.64.0.1:11434/api/version", 
            timeout=5
        ).json()
        
        # Список моделей
        models = requests.get(
            "http://100.64.0.1:11434/api/tags",
            timeout=5
        ).json()
        
        return {
            "available": True,
            "version": version.get("version"),
            "models": [m["name"] for m in models.get("models", [])]
        }
    except Exception as e:
        return {"available": False, "error": str(e)}
```

### Доступные модели

| Модель | VRAM | Контекст | Назначение |
|--------|------|----------|------------|
| qwen2.5:14b | ~9 GB | 32K | Основная (русский язык, качество) |
| qwen2.5:7b | ~5 GB | 32K | Быстрая (простые задачи) |

### Производительность

| Метрика | Значение |
|---------|----------|
| Загрузка модели | ~10-20 сек |
| Генерация | ~30-50 токенов/сек |
| VRAM (14b) | ~9 GB |
| Timeout модели | 10 мин неактивности |

---

## AI клиенты (v0.27+)

Система использует разделённые клиенты для разных AI сервисов:

- **WhisperClient** — транскрибация через Whisper API
- **OllamaClient** — LLM операции (generate, chat) через Ollama
- **ClaudeClient** — LLM операции через Anthropic API

```python
"""
Примеры использования AI клиентов.
"""

from app.services.ai_clients import WhisperClient, OllamaClient, ClaudeClient
from app.config import get_settings

settings = get_settings()

# ═══════════════════════════════════════════════════════════════════
# WhisperClient — транскрибация
# ═══════════════════════════════════════════════════════════════════

async with WhisperClient.from_settings(settings) as whisper:
    # Проверка доступности
    available = await whisper.check_health()
    print(f"Whisper: {'✅' if available else '❌'}")

    # Транскрибация
    result = await whisper.transcribe(
        file_path="audio.mp3",
        language="ru"
    )
    print(f"Текст: {result['text'][:100]}...")

# ═══════════════════════════════════════════════════════════════════
# OllamaClient — локальные LLM
# ═══════════════════════════════════════════════════════════════════

async with OllamaClient.from_settings(settings) as ollama:
    # Проверка доступности
    status = await ollama.check_services()
    print(f"Ollama: {'✅' if status['ollama'] else '❌'}")

    # Генерация текста
    response = await ollama.generate(
        prompt="Привет! Как дела?",
        model="qwen2.5:14b"
    )
    print(f"Ответ: {response}")

    # Chat completion
    response = await ollama.chat(
        messages=[
            {"role": "user", "content": "Что такое Python?"}
        ],
        model="qwen2.5:14b",
        temperature=0.7
    )
    print(f"Chat: {response}")

# ═══════════════════════════════════════════════════════════════════
# ClaudeClient — облачные LLM
# ═══════════════════════════════════════════════════════════════════

async with ClaudeClient.from_settings(settings) as claude:
    response = await claude.generate(
        prompt="Проанализируй этот документ...",
        model="claude-sonnet-4-5"
    )
```

---

## Error Handling

### Retry с exponential backoff

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout))
)
def call_ollama(prompt: str, model: str = "qwen2.5:14b") -> str:
    """Вызов Ollama с автоматическим retry."""
    response = requests.post(
        "http://100.64.0.1:11434/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=300
    )
    response.raise_for_status()
    return response.json()["response"]
```

### Типичные ошибки

| Ошибка | Причина | Решение |
|--------|---------|---------|
| Connection refused | Сервис не запущен | Проверить Docker контейнер |
| Timeout | Долгая генерация | Увеличить timeout |
| 500 Internal Server Error | Проблема с моделью | Проверить логи сервиса |
| CUDA out of memory | Нехватка VRAM | Подождать выгрузки другой модели |

---

---

## Backend API (bz2-transcriber)

**Base URL:** `http://100.64.0.1:8801`

### Models API

Эндпоинты для получения информации о доступных моделях и их конфигурациях.

#### GET /api/models/available

Список доступных моделей. Ollama модели получаются динамически, Whisper и Claude модели — из `config/models.yaml`.
Claude модели показываются только если `ANTHROPIC_API_KEY` установлен и валиден.

**Response (camelCase, v0.59+):**
```json
{
  "ollamaModels": ["gemma2:9b", "qwen2.5:14b", "qwen2.5:7b"],
  "whisperModels": [
    {
      "id": "Systran/faster-whisper-large-v3",
      "name": "large-v3",
      "description": "Высокое качество, медленнее"
    },
    {
      "id": "deepdml/faster-whisper-large-v3-turbo-ct2",
      "name": "large-v3-turbo",
      "description": "Быстрее, хорошее качество"
    }
  ],
  "claudeModels": [
    {
      "id": "claude-sonnet-4-5",
      "name": "Claude Sonnet 4.5",
      "description": "Быстрая и умная ($3/$15 за 1M токенов)"
    },
    {
      "id": "claude-haiku-4-5",
      "name": "Claude Haiku 4.5",
      "description": "Самая быстрая ($1/$5 за 1M токенов)"
    },
    {
      "id": "claude-opus-4-5",
      "name": "Claude Opus 4.5",
      "description": "Максимальный интеллект ($5/$25 за 1M токенов)"
    }
  ],
  "providers": {
    "local": {
      "available": true,
      "name": "Ollama"
    },
    "cloud": {
      "available": true,
      "name": "Claude API"
    }
  }
}
```

**Примечание:** `claude_models` и `providers.cloud.available` присутствуют только если `ANTHROPIC_API_KEY` настроен.

#### GET /api/models/default

Модели по умолчанию из настроек сервера. Для `transcribe` возвращается полный ID модели.

**Response:**
```json
{
  "transcribe": "deepdml/faster-whisper-large-v3-turbo-ct2",
  "clean": "claude-sonnet-4-5",
  "longread": "claude-sonnet-4-5",
  "summarize": "claude-sonnet-4-5"
}
```

#### GET /api/models/config

Конфигурации моделей из `config/models.yaml`.

**Response:**
```json
{
  "gemma2": {
    "context_tokens": 8192,
    "cleaner": {"chunk_size": 3000, "chunk_overlap": 200},
    "chunker": {"large_text_threshold": 10000}
  },
  "qwen2": {
    "context_tokens": 32768,
    "cleaner": {"chunk_size": 12000}
  }
}
```

---

## Inbox API

### GET /api/inbox

Список медиафайлов в директории inbox.

**Response:**
```json
["video1.mp4", "audio.mp3", "presentation.mkv"]
```

**Поддерживаемые форматы:**
- Видео: mp4, mkv, avi, mov, webm
- Аудио: mp3, wav, m4a, flac, aac, ogg

---

## Cache API (v0.18+)

API для управления версионированным кэшем промежуточных результатов.

### GET /api/cache/{video_id}

Получить информацию о кэше для видео.

**Параметры:**
- `video_id` (path) — идентификатор видео (например, `2025-01-09_ПШ-SV_topic`)

**Response:**
```json
{
  "video_id": "2025-01-09_ПШ-SV_topic",
  "has_cache": true,
  "stages": [
    {
      "stage": "cleaning",
      "total_versions": 2,
      "current_version": 2,
      "versions": [
        {
          "version": 1,
          "model_name": "gemma2:9b",
          "created_at": "2025-01-20T10:30:00Z",
          "is_current": false
        },
        {
          "version": 2,
          "model_name": "qwen2.5:14b",
          "created_at": "2025-01-20T14:15:00Z",
          "is_current": true
        }
      ]
    }
  ]
}
```

### POST /api/cache/rerun

Перезапустить этап обработки с опциональным override модели.

**Request:**
```json
{
  "video_id": "2025-01-09_ПШ-SV_topic",
  "stage": "cleaning",
  "model": "qwen2.5:14b"
}
```

**stage** — одно из: `transcription`, `cleaning`, `chunking`, `longread`, `summary`

**Response (SSE):**
```json
{"type": "progress", "status": "cleaning", "progress": 45.5, "message": "..."}
{"type": "result", "data": {"video_id": "...", "stage": "cleaning", "new_version": 2, "model_name": "qwen2.5:14b"}}
```

### POST /api/cache/version

Установить конкретную версию как текущую.

**Query параметры:**
- `video_id` — идентификатор видео
- `stage` — название этапа
- `version` — номер версии

**curl пример:**
```bash
curl -X POST "http://100.64.0.1:8801/api/cache/version?video_id=2025-01-09_ПШ-SV_topic&stage=cleaning&version=1"
```

**Response:**
```json
{
  "status": "ok",
  "stage": "cleaning",
  "version": 1
}
```

### GET /api/cache/{video_id}/{stage}

Получить кэшированный результат для этапа.

**Query параметры:**
- `version` (optional) — номер версии (по умолчанию текущая)

**curl пример:**
```bash
# Текущая версия
curl "http://100.64.0.1:8801/api/cache/2025-01-09_ПШ-SV_topic/cleaning"

# Конкретная версия
curl "http://100.64.0.1:8801/api/cache/2025-01-09_ПШ-SV_topic/cleaning?version=1"
```

**Response:**
Зависит от этапа. Для `cleaning`:
```json
{
  "text": "Очищенный транскрипт...",
  "original_length": 15000,
  "cleaned_length": 14500,
  "model_name": "gemma2:9b"
}
```

### Структура кэша

Кэш хранится в директории `.cache/` внутри архива видео:

```
archive/2025/01.09 ПШ/Video Title/
├── pipeline_results.json    # Текущие результаты
└── .cache/
    ├── manifest.json        # Версии и метаданные
    ├── transcription/v1.json
    ├── cleaning/v1.json
    ├── cleaning/v2.json     # Re-run
    └── ...
```

---

## Prompts API (v0.31+)

API для получения доступных вариантов промптов.

### GET /api/prompts/{stage}

Получить список вариантов промптов для этапа.

**Параметры:**
- `stage` (path) — название этапа (`cleaning`, `longread`, `summary`, `story`)

**curl пример:**
```bash
curl http://100.64.0.1:8801/api/prompts/cleaning
```

**Response:**
```json
{
  "stage": "cleaning",
  "components": [
    {
      "component": "system",
      "default": "system",
      "variants": [
        {
          "name": "system",
          "source": "builtin",
          "filename": "system.md"
        },
        {
          "name": "system_v2",
          "source": "external",
          "filename": "system_v2.md"
        }
      ]
    },
    {
      "component": "user",
      "default": "user",
      "variants": [
        {
          "name": "user",
          "source": "builtin",
          "filename": "user.md"
        }
      ]
    }
  ]
}
```

**Поля:**
- `component` — тип компонента (`system`, `user`, `instructions`, `template`)
- `default` — имя варианта по умолчанию
- `source` — источник: `builtin` (встроенный) или `external` (внешняя папка)

---

## Step API (v0.32+, updated v0.51)

API для пошаговой обработки с возможностью override модели и промптов.

С версии v0.42 response содержит расширенные метрики: `tokens_used`, `cost`, `processing_time_sec`.

### POST /api/step/parse

Парсинг имени видеофайла для извлечения метаданных. Синхронная операция.

**Request:**
```json
{
  "video_filename": "2025.01.13 ПШ.SV Название темы (Спикер).mp4"
}
```

**Response:**
```json
{
  "date": "2025-01-13",
  "eventType": "ПШ",
  "stream": "SV",
  "title": "Название темы",
  "speaker": "Спикер",
  "originalFilename": "2025.01.13 ПШ.SV Название темы (Спикер).mp4",
  "videoId": "2025-01-13_ПШ-SV_название-темы",
  "contentType": "educational",
  "eventCategory": "regular",
  "durationSeconds": 1234.5
}
```

**Ошибки:**
- `400` — Неверный формат имени файла
- `404` — Файл не найден в inbox

---

### POST /api/step/transcribe

Транскрипция видео через Whisper API с SSE прогрессом.

**Request:**
```json
{
  "video_filename": "2025.01.13 ПШ.SV Название темы (Спикер).mp4"
}
```

**Response (SSE):**
```json
{"type": "progress", "status": "transcribing", "progress": 45.5, "message": "Transcribing...", "estimatedSeconds": 120.0, "elapsedSeconds": 54.0}
{"type": "result", "data": {
  "rawTranscript": {
    "segments": [...],
    "language": "ru",
    "durationSeconds": 1234.5,
    "whisperModel": "large-v3-turbo",
    "fullText": "...",
    "textWithTimestamps": "..."
  },
  "audioPath": "/data/inbox/audio_extracted.wav",
  "displayText": "..."
}}
```

**Ошибки:**
- `404` — Файл не найден в inbox

---

### POST /api/step/slides (v0.51+)

Извлечение текста со слайдов презентации через Claude Vision API.

**Request:**
```json
{
  "slides": [
    {
      "filename": "slide1.jpg",
      "content_type": "image/jpeg",
      "data": "base64_encoded_image_data"
    },
    {
      "filename": "presentation.pdf",
      "content_type": "application/pdf",
      "data": "base64_encoded_pdf_data"
    }
  ],
  "model": "claude-haiku-4-5",
  "prompt_overrides": {
    "system": "system",
    "user": "user"
  }
}
```

**Параметры:**
- `slides` (required) — массив объектов SlideInput
  - `filename` — имя файла
  - `content_type` — MIME тип: `image/jpeg`, `image/png`, `image/webp`, `application/pdf`
  - `data` — base64 encoded содержимое файла
- `model` (optional) — модель для обработки (claude-haiku-4-5, claude-sonnet-4-5, claude-opus-4-5)
- `prompt_overrides` (optional) — override промптов

**Response (SSE):**
```json
{"type": "progress", "status": "slides", "progress": 33.3, "message": "Processing batch 1/3..."}
{"type": "progress", "status": "slides", "progress": 66.7, "message": "Processing batch 2/3..."}
{"type": "result", "data": {
  "extracted_text": "# Слайд 1: Введение\n\nОсновные темы презентации...\n\n## Таблица данных\n| Колонка 1 | Колонка 2 |\n...",
  "slides_count": 15,
  "chars_count": 4250,
  "words_count": 580,
  "tables_count": 3,
  "model": "claude-haiku-4-5",
  "tokens_used": {"input": 45000, "output": 1200, "total": 46200},
  "cost": 0.051,
  "processing_time_sec": 12.4
}}
```

**Ограничения:**
- Максимум 50 файлов
- Максимум 10 MB на файл
- Общий размер до 100 MB
- PDF конвертируется в изображения (максимум 50 страниц)

**curl пример:**
```bash
# Подготовить base64 данные
IMAGE_DATA=$(base64 -i slide1.jpg)

curl -X POST "http://100.64.0.1:8801/api/step/slides" \
  -H "Content-Type: application/json" \
  -d "{
    \"slides\": [{
      \"filename\": \"slide1.jpg\",
      \"content_type\": \"image/jpeg\",
      \"data\": \"$IMAGE_DATA\"
    }],
    \"model\": \"claude-haiku-4-5\"
  }"
```

---

### POST /api/step/clean

**Request:**
```json
{
  "raw_transcript": {
    "segments": [...],
    "language": "ru",
    "duration_seconds": 301.5,
    "whisper_model": "large-v3-turbo"
  },
  "metadata": {
    "title": "...",
    "speaker": "...",
    "content_type": "educational"
  },
  "model": "claude-sonnet-4-5",
  "prompt_overrides": {
    "system": "system_v2",
    "user": "user"
  }
}
```

**Параметры:**
- `model` (optional) — override модели для обработки
- `prompt_overrides` (optional) — override промптов для компонентов

**Response (SSE):**
```json
{"type": "progress", "status": "cleaning", "progress": 45.5, "message": "..."}
{"type": "result", "data": {
  "text": "Очищенный транскрипт...",
  "original_length": 4412,
  "cleaned_length": 4187,
  "model_name": "claude-sonnet-4-5",
  "tokens_used": {"input": 1850, "output": 1720, "total": 3570},
  "cost": 0.0314,
  "processing_time_sec": 6.2,
  "words": 698,
  "change_percent": -5.1
}}
```

### POST /api/step/longread

Генерация лонгрида из очищенного транскрипта.

**Request:**
```json
{
  "cleaned_transcript": {...},
  "metadata": {...},
  "model": "claude-sonnet-4-5",
  "slides_text": "# Слайд 1\n\nТекст со слайдов...",
  "prompt_overrides": {
    "system": "system",
    "instructions": "instructions",
    "template": "template"
  }
}
```

**Параметры:**
- `cleaned_transcript` (required) — очищенный транскрипт
- `metadata` (required) — метаданные видео
- `model` (optional) — override модели
- `slides_text` (optional, v0.51+) — текст извлечённый со слайдов для обогащения
- `prompt_overrides` (optional) — override промптов
```

**Response (SSE):**
```json
{"type": "progress", "status": "longread", "progress": 75.0, "message": "..."}
{"type": "result", "data": {
  "video_id": "...",
  "title": "...",
  "sections": [...],
  "model_name": "claude-sonnet-4-5",
  "tokens_used": {"input": 3200, "output": 2800, "total": 6000},
  "cost": 0.0516,
  "processing_time_sec": 12.4,
  "chars": 8500,
  "total_word_count": 1250
}}
```

### POST /api/step/summarize

Генерация конспекта из очищенного транскрипта.

**Request:**
```json
{
  "cleaned_transcript": {...},
  "metadata": {...},
  "model": "claude-sonnet-4-5",
  "prompt_overrides": {
    "system": "system",
    "instructions": "instructions",
    "template": "template"
  }
}
```

**Параметры:**
- `cleaned_transcript` (required) — очищенный транскрипт
- `metadata` (required) — метаданные видео
- `model` (optional) — override модели
- `prompt_overrides` (optional) — override промптов

**Response (SSE):**
```json
{"type": "result", "data": {
  "video_id": "...",
  "essence": "...",
  "key_concepts": [...],
  "model_name": "claude-sonnet-4-5",
  "tokens_used": {"input": 2100, "output": 890, "total": 2990},
  "cost": 0.0196,
  "processing_time_sec": 5.8,
  "chars": 2150,
  "words": 312
}}
```

### POST /api/step/story

Генерация 8-блочной истории (для content_type=LEADERSHIP).

**Request:**
```json
{
  "cleaned_transcript": {...},
  "metadata": {...},
  "model": "claude-sonnet-4-5",
  "slides_text": "# Слайд 1\n\nТекст со слайдов...",
  "prompt_overrides": {...}
}
```

**Параметры:**
- `cleaned_transcript` (required) — очищенный транскрипт
- `metadata` (required) — метаданные видео
- `model` (optional) — override модели
- `slides_text` (optional, v0.51+) — текст извлечённый со слайдов для обогащения
- `prompt_overrides` (optional) — override промптов

**Response (SSE):**
```json
{"type": "result", "data": {
  "video_id": "...",
  "names": "...",
  "blocks": [...],
  "model_name": "claude-sonnet-4-5",
  "tokens_used": {"input": 4500, "output": 3200, "total": 7700},
  "cost": 0.0615,
  "processing_time_sec": 18.2,
  "chars": 12500,
  "total_blocks": 8
}}
```

### POST /api/step/chunk

Чанкирование markdown по H2 заголовкам. Детерминистическая операция (без LLM).

**Request:**
```json
{
  "markdown_content": "# Title\n\n## Section 1\n\nContent...\n\n## Section 2\n\nMore content...",
  "metadata": {...}
}
```

**Response:**
```json
{
  "videoId": "2025-01-13_ПШ-SV_название-темы",
  "chunks": [
    {
      "id": "chunk_a1b2c3",
      "title": "Section 1",
      "content": "Content...",
      "order": 0,
      "tokens": 150
    },
    {
      "id": "chunk_d4e5f6",
      "title": "Section 2",
      "content": "More content...",
      "order": 1,
      "tokens": 200
    }
  ],
  "totalChunks": 2,
  "totalTokens": 350
}
```

---

### POST /api/step/save

Сохранение результатов обработки в архив. Синхронная операция.

**Request:**
```json
{
  "metadata": {...},
  "raw_transcript": {...},
  "cleaned_transcript": {...},
  "chunks": {...},
  "longread": {...},
  "summary": {...},
  "story": null,
  "audio_path": "/data/inbox/audio.wav",
  "slides_extraction": null
}
```

**Параметры:**
- `metadata` (required) — метаданные видео
- `raw_transcript` (required) — сырой транскрипт
- `cleaned_transcript` (required) — очищенный транскрипт
- `chunks` (required) — чанки
- `longread` (optional) — лонгрид (для educational)
- `summary` (optional) — конспект (для educational)
- `story` (optional) — история (для leadership)
- `audio_path` (optional) — путь к аудио для копирования
- `slides_extraction` (optional) — результат извлечения со слайдов

**Response:**
```json
["longread.md", "summary.md", "transcript.txt", "audio.mp3", "pipeline_results.json"]
```

**Ошибки:**
- `500` — Ошибка сохранения

---

## Связанные документы

- [ARCHITECTURE.md](ARCHITECTURE.md) — схема системы
- [pipeline.md](pipeline.md) — этапы обработки
- [adr/005-result-caching.md](adr/005-result-caching.md) — решение по кэшированию
- [configuration.md](configuration.md) — настройка промптов
