# Error Handling

[Обзор Pipeline](README.md)

---

## Иерархия исключений

```
Exception
├── PipelineError           # Pipeline-level ошибка со stage
├── StageError              # Stage-level ошибка с контекстом
├── FilenameParseError      # Ошибка парсинга имени файла
└── AIClientError           # Базовый для AI клиентов
    ├── AIClientTimeoutError      # Таймаут запроса
    ├── AIClientConnectionError   # Ошибка подключения
    └── AIClientResponseError     # HTTP ошибка (status, body)
```

### PipelineError

Ошибка уровня pipeline с контекстом этапа.

```python
from app.services.pipeline import PipelineError
from app.models.schemas import ProcessingStatus

class PipelineError(Exception):
    stage: ProcessingStatus  # Этап где произошла ошибка
    message: str             # Описание
    cause: Exception | None  # Оригинальное исключение

# Пример
raise PipelineError(
    ProcessingStatus.CLEANING,
    "LLM returned empty response",
    original_exception,
)
```

### StageError

Ошибка этапа с именем stage.

```python
from app.services.stages import StageError

class StageError(Exception):
    stage_name: str         # Имя этапа ("clean", "longread")
    message: str            # Описание
    cause: Exception | None # Оригинальное исключение

# Пример
raise StageError("clean", f"Cleaning failed: {e}", e)
```

### AIClientError

Базовый класс для ошибок AI клиентов.

```python
from app.services.ai_clients import (
    AIClientError,
    AIClientTimeoutError,
    AIClientConnectionError,
    AIClientResponseError,
)

class AIClientError(Exception):
    message: str
    provider: str | None    # "ollama", "claude", "whisper"
    model: str | None       # Модель вызвавшая ошибку
    original_error: Exception | None

class AIClientResponseError(AIClientError):
    status_code: int | None     # HTTP статус
    response_body: str | None   # Тело ответа
```

---

## Обработка ошибок по этапам

| Этап | Ошибка | Исключение | Действие |
|------|--------|------------|----------|
| Parse | Неверный формат имени | `FilenameParseError` | 400 Bad Request |
| Parse | Файл не найден | `StageError` | 404 Not Found |
| Transcribe | Whisper недоступен | `AIClientConnectionError` | Retry (3 попытки) |
| Transcribe | Таймаут | `AIClientTimeoutError` | Retry (3 попытки) |
| Transcribe | Corrupted video | `StageError` | 500 с описанием |
| Clean/LLM | Провайдер недоступен | `AIClientConnectionError` | Retry (3 попытки) |
| Clean/LLM | Таймаут | `AIClientTimeoutError` | Retry (3 попытки) |
| Clean/LLM | Ошибка API | `AIClientResponseError` | Пробросить ошибку |
| Save | Ошибка записи | `StageError` | 500 с описанием |

> **v0.29+:** Fallback механизмы удалены. При ошибках LLM выбрасывается `PipelineError`.

---

## Retry логика

Retry реализован в AI клиентах через `tenacity` для transient ошибок.

### Ollama Client

```python
# backend/app/services/ai_clients/ollama_client.py

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

RETRY_DECORATOR = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
)
```

### Whisper Client

```python
# backend/app/services/ai_clients/whisper_client.py

RETRY_DECORATOR = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
)
```

**Что retry-ится:**
- `httpx.ConnectError` — сервис временно недоступен
- `httpx.TimeoutException` — запрос не успел выполниться

**Что НЕ retry-ится:**
- HTTP 4xx/5xx ошибки
- Ошибки парсинга JSON
- Ошибки валидации

---

## Обработка ошибок парсинга JSON

Для извлечения JSON из ответов LLM используются утилиты:

```python
from app.utils import extract_json, parse_json_safe

# Извлечь JSON из ответа LLM (поддерживает ```json блоки)
json_str = extract_json(response, json_type="array")  # "array", "object", "auto"

# Безопасный парсинг с default значением
data = parse_json_safe(json_str, default=[])
```

> **Подробнее:** См. docstrings в `backend/app/utils/json_utils.py`

---

## API Error Responses

### HTTP коды

| Код | Ситуация |
|-----|----------|
| 400 | Неверный формат имени файла, невалидные параметры |
| 404 | Файл не найден, видео не в архиве |
| 500 | Ошибка AI сервиса, ошибка сохранения |

### SSE Error Event

```json
{
  "type": "error",
  "error": "[cleaning] LLM returned empty response"
}
```

### HTTP Error Response

```json
{
  "detail": "Video file not found: invalid.mp4"
}
```

---

## Примеры обработки ошибок

### В Stage

```python
# backend/app/services/stages/clean_stage.py

async def execute(self, context: StageContext) -> CleanedTranscript:
    try:
        # ... выполнение
        return result
    except Exception as e:
        raise StageError(self.name, f"Cleaning failed: {e}", e)
```

### В Orchestrator

```python
# backend/app/services/pipeline/orchestrator.py

try:
    result = await self._run_stage(stage, context)
except StageError as e:
    raise PipelineError(stage.status, e.message, e.cause)
```

### В API Route

```python
# backend/app/api/step_routes.py

@router.post("/parse")
async def step_parse(request: StepParseRequest) -> VideoMetadata:
    try:
        metadata = orchestrator.parse(video_path)
        return metadata
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

## Связанные документы

| Документ | Описание |
|----------|----------|
| [ai_clients/base.py](../../backend/app/services/ai_clients/base.py) | AIClientError иерархия |
| [stages/base.py](../../backend/app/services/stages/base.py) | StageError, StageContext |
| [pipeline/orchestrator.py](../../backend/app/services/pipeline/orchestrator.py) | PipelineError |
| [utils/json_utils.py](../../backend/app/utils/json_utils.py) | extract_json, parse_json_safe |
| [api-reference.md](../api-reference.md) | HTTP error codes |
