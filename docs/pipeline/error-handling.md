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

```python
def _extract_json(self, text: str) -> str:
    """Извлекает JSON из ответа LLM."""
    # Удаляет ```json ... ``` обёртку если есть
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        text = text[start:end]

    # Находит JSON массив или объект
    start = text.find("[") if "[" in text else text.find("{")
    end = text.rfind("]") + 1 if "]" in text else text.rfind("}") + 1

    return text[start:end].strip()
```

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

- **API клиент:** [`backend/app/services/ai_client.py`](../../backend/app/services/ai_client.py)
- **API:** [api-reference.md](../api-reference.md)
