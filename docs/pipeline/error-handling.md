# Error Handling

[Обзор Pipeline](README.md)

---

## Типы ошибок

| Этап | Ошибка | Действие |
|------|--------|----------|
| 1. Parse | Неверный формат имени | Пропустить, уведомить |
| 2. Whisper | OOM (нехватка VRAM) | Retry с меньшей моделью |
| 2. Whisper | Corrupted video | Пропустить, уведомить |
| 3-5. LLM | Ollama недоступен | Retry с backoff |
| 3-5. LLM | Invalid JSON response | Retry (до 3 раз) |
| 6. Save | Disk full | Остановить pipeline |

## Retry логика

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60)
)
async def call_ollama_with_retry(prompt: str, **kwargs):
    """Вызов Ollama с автоматическим retry."""
    return await ollama_client.chat(...)
```

## Обработка ошибок парсинга JSON

Для извлечения и парсинга JSON из ответов LLM используются утилиты из `app/utils/`:

```python
from app.utils import extract_json, parse_json_safe

# Извлечь JSON из ответа LLM (поддерживает ```json блоки)
json_str = extract_json(response, json_type="array")  # "array", "object", "auto"

# Безопасный парсинг с default значением
data = parse_json_safe(json_str, default=[])
```

> **Подробнее:** См. docstrings в `backend/app/utils/json_utils.py`

## Валидация результатов

```python
def validate_chunks(chunks: list[TranscriptChunk]) -> bool:
    """Проверяет валидность чанков."""
    if not chunks:
        return False

    for chunk in chunks:
        if not chunk.text or len(chunk.text) < 10:
            return False
        if chunk.word_count < 5 or chunk.word_count > 1000:
            return False

    return True
```

---

## Связанные документы

- **AI клиенты:** [`backend/app/services/ai_clients/`](../../backend/app/services/ai_clients/) — OllamaClient, ClaudeClient
- **Утилиты:** [`backend/app/utils/`](../../backend/app/utils/) — extract_json, parse_json_safe
- **StageError:** [`backend/app/services/stages/base.py`](../../backend/app/services/stages/base.py) — исключение с контекстом stage
- **API:** [api-reference.md](../api-reference.md)
