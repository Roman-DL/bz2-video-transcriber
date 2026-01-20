# ADR-003: Shared utils для LLM сервисов

## Статус

Принято (2025-01-20)

## Контекст

При анализе сервисов обнаружен дублированный код в 5 файлах:

1. **JSON extraction** — идентичный метод `_extract_json()` в:
   - `chunker.py` (для JSON arrays)
   - `summarizer.py` (для JSON objects)
   - `longread_generator.py`
   - `summary_generator.py`
   - `outline_extractor.py`

2. **Token estimation** — inline расчёт `num_predict` в:
   - `chunker.py` — `(char_count // 3) * 1.3 + 500`
   - `cleaner.py` — `len(chunk) * 0.5`

3. **Chunk utilities** — inline функции в `chunker.py`:
   - Проверка cyrillic ratio
   - Генерация chunk ID
   - Word counting

Дублирование нарушает DRY и создаёт риск рассинхронизации при исправлении багов.

## Решение

Создать пакет `backend/app/utils/` с shared утилитами:

```
backend/app/utils/
├── __init__.py          # Экспорт публичных функций
├── json_utils.py        # extract_json(), parse_json_safe()
├── token_utils.py       # estimate_tokens(), calculate_num_predict()
└── chunk_utils.py       # validate_cyrillic_ratio(), generate_chunk_id()
```

### json_utils.py

```python
def extract_json(
    text: str,
    json_type: Literal["object", "array", "auto"] = "auto"
) -> str:
    """
    Extract JSON from LLM response.

    Handles:
    - Markdown code blocks (```json ... ```)
    - Surrounding text (preamble/postamble)
    - Nested brackets/braces with string escaping

    Args:
        text: Raw LLM response
        json_type: "object" for {}, "array" for [], "auto" to detect

    Returns:
        Clean JSON string
    """

def parse_json_safe(
    json_str: str,
    default: T = None,
    log_errors: bool = True
) -> Any | T:
    """Parse JSON with error handling, returning default on failure."""
```

**Почему:**
- Единая реализация для arrays и objects
- Правильная обработка escaped quotes в строках
- Централизованное логирование ошибок

### token_utils.py

```python
# Task-specific multipliers
TASK_MULTIPLIERS = {
    "cleaner": 0.95,    # Output slightly smaller
    "chunker": 1.3,     # JSON overhead
    "summarizer": 0.3,  # Summary is ~30% of input
    "longread": 1.2,    # Formatting adds ~20%
}

def estimate_tokens(text: str, lang: str = "ru") -> int:
    """Estimate token count (ru: 3 chars/token, en: 4 chars/token)."""

def calculate_num_predict(
    input_tokens: int,
    task: str = "default",
    buffer_tokens: int = 500
) -> int:
    """Calculate optimal num_predict for LLM call."""
```

**Почему:**
- Task-specific multipliers в одном месте
- Легко настроить для новых моделей
- Документированные assumptions (chars per token)

### chunk_utils.py

```python
def validate_cyrillic_ratio(text: str) -> float:
    """Check if text is Russian (returns 0.0-1.0)."""

def generate_chunk_id(video_id: str, index: int, zero_pad: int = 3) -> str:
    """Generate standardized chunk ID: {video_id}_{index:03d}."""

def count_words(text: str) -> int:
    """Count words in text."""
```

**Почему:**
- Cyrillic validation нужен для проверки LLM output
- Единый формат chunk ID во всей системе

## Рефакторинг chunker.py

Помимо выноса утилит, объединены методы `chunk()` и `chunk_with_outline()`:

**До (2 метода с ~95% дублирования):**
```python
async def chunk(cleaned_transcript, metadata) -> TranscriptChunks:
    # Вычисляет text_parts и outline сам
    ...

async def chunk_with_outline(cleaned_transcript, metadata, text_parts, outline):
    # Использует готовые text_parts и outline
    ...
```

**После (1 метод с опциональными параметрами):**
```python
async def chunk(
    cleaned_transcript,
    metadata,
    text_parts: list[TextPart] | None = None,  # Optional
    outline: TranscriptOutline | None = None,   # Optional
) -> TranscriptChunks:
    # Если text_parts не передан — вычисляет сам
    # Если передан — использует готовый
```

`chunk_with_outline()` сохранён как deprecated wrapper для backward compatibility.

## Использование

```python
# Старый код работает без изменений
from app.services.chunker import SemanticChunker
chunks = await chunker.chunk(transcript, metadata)

# Новый код использует shared utils
from app.utils import extract_json, calculate_num_predict

json_str = extract_json(response, json_type="array")
num_predict = calculate_num_predict(tokens, task="chunker")
```

## Последствия

### Положительные

- **DRY**: 5 идентичных `_extract_json()` → 1 shared функция
- **Consistency**: единый алгоритм JSON extraction везде
- **Testability**: утилиты тестируются отдельно (embedded tests)
- **Maintainability**: багфиксы в одном месте
- **~250 строк экономии**: удалено дублирование в chunker.py

### Отрицательные

- **Дополнительная зависимость**: сервисы зависят от `app.utils`
- **Миграция**: нужно обновить импорты в существующих сервисах

## Альтернативы

### 1. Оставить дублирование

Отклонено — риск рассинхронизации, сложнее исправлять баги.

### 2. Base class с методами

Отклонено — создаёт ненужное наследование, усложняет тестирование.

### 3. Mixin класс

Отклонено — скрывает зависимости, усложняет понимание кода.

## Связанные документы

- [002-pipeline-decomposition.md](002-pipeline-decomposition.md) — декомпозиция pipeline
- [configuration.md](../configuration.md) — конфигурация моделей
- [CLAUDE.md](../../CLAUDE.md) — структура проекта

## Примечания

Embedded tests в каждом модуле (`if __name__ == "__main__"`):
```bash
python -m app.utils.json_utils    # Запуск тестов json_utils
python -m app.utils.token_utils   # Запуск тестов token_utils
python -m app.utils.chunk_utils   # Запуск тестов chunk_utils
```
