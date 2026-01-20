# API Reference: Локальные AI сервисы

> Справочник по HTTP API для интеграции с Ollama и Whisper.
> Все сервисы доступны через Tailscale по адресу `100.64.0.1`.

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

## Общий клиент для AI сервисов

```python
"""
ai_client.py — Клиент для работы с локальными AI сервисами.
"""

import requests
from typing import Optional
from dataclasses import dataclass


@dataclass
class AIConfig:
    """Конфигурация AI сервисов."""
    ollama_url: str = "http://100.64.0.1:11434"
    whisper_url: str = "http://100.64.0.1:9000"
    default_model: str = "qwen2.5:14b"
    timeout: int = 300


class AIClient:
    """Клиент для Ollama и Whisper."""
    
    def __init__(self, config: Optional[AIConfig] = None):
        self.config = config or AIConfig()
    
    def check_services(self) -> dict:
        """Проверить доступность всех сервисов."""
        return {
            "ollama": self._check_ollama(),
            "whisper": self._check_whisper()
        }
    
    def _check_ollama(self) -> bool:
        try:
            r = requests.get(f"{self.config.ollama_url}/api/version", timeout=5)
            return r.status_code == 200
        except:
            return False
    
    def _check_whisper(self) -> bool:
        try:
            r = requests.get(f"{self.config.whisper_url}/health", timeout=5)
            return r.text == "OK"
        except:
            return False
    
    def transcribe(
        self,
        file_path: str,
        language: str = "ru",
        response_format: str = "text"
    ) -> str:
        """Транскрибировать файл через Whisper."""
        with open(file_path, "rb") as f:
            response = requests.post(
                f"{self.config.whisper_url}/v1/audio/transcriptions",
                files={"file": f},
                data={
                    "language": language,
                    "response_format": response_format
                },
                timeout=600
            )
        response.raise_for_status()
        return response.text if response_format == "text" else response.json()
    
    def generate(self, prompt: str, model: Optional[str] = None) -> str:
        """Генерация текста через Ollama."""
        response = requests.post(
            f"{self.config.ollama_url}/api/generate",
            json={
                "model": model or self.config.default_model,
                "prompt": prompt,
                "stream": False
            },
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()["response"]
    
    def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """Chat через Ollama (OpenAI формат)."""
        response = requests.post(
            f"{self.config.ollama_url}/v1/chat/completions",
            json={
                "model": model or self.config.default_model,
                "messages": messages,
                "temperature": temperature
            },
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


# Использование
if __name__ == "__main__":
    client = AIClient()
    
    # Проверка сервисов
    status = client.check_services()
    print(f"Ollama: {'✅' if status['ollama'] else '❌'}")
    print(f"Whisper: {'✅' if status['whisper'] else '❌'}")
    
    # Транскрипция
    # text = client.transcribe("video.mp4", language="ru")
    
    # Генерация
    # result = client.generate("Привет! Как дела?")
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

**Response:**
```json
{
  "ollama_models": ["gemma2:9b", "qwen2.5:14b", "qwen2.5:7b"],
  "whisper_models": [
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
  "claude_models": [
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
  "clean": "gemma2:9b",
  "chunk": "gemma2:9b",
  "summarize": "qwen2.5:14b"
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
  "corrections_made": ["Коррекция 1", "Коррекция 2"],
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

## Связанные документы

- [architecture.md](architecture.md) — схема системы
- [pipeline.md](pipeline.md) — этапы обработки
- [adr/005-result-caching.md](adr/005-result-caching.md) — решение по кэшированию
