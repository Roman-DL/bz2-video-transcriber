# Этап 4: Chunk (Semantic Splitting)

[< Назад: Clean](03-clean.md) | [Обзор Pipeline](README.md) | [Далее: Summarize >](05-summarize.md)

---

## Назначение

Разбиение очищенного транскрипта на смысловые блоки для RAG-поиска в БЗ 2.0.

## Текущая реализация: Простые чанки

LLM разбивает текст на самодостаточные блоки. Самодостаточность обеспечивается инструкциями в промпте.

| Критерий | Значение | Почему |
|----------|----------|--------|
| Размер chunk | 100-400 слов (оптимум 200-300) | Оптимально для embeddings |
| Смысловая завершённость | Одна тема/мысль | Chunk понятен без контекста |
| Overlap | Не требуется | LLM делает чанки самодостаточными |
| Метаданные | topic + text + word_count | Минимум для простоты и надёжности |

## Класс SemanticChunker

```python
class SemanticChunker:
    """Semantic chunking service using Ollama LLM."""

    def __init__(self, ai_client: AIClient, settings: Settings):
        """
        Initialize chunker.

        Args:
            ai_client: AI client for LLM calls
            settings: Application settings
        """
        self.ai_client = ai_client
        self.settings = settings
        self.prompt_template = load_prompt("chunker", settings)

    async def chunk(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
    ) -> TranscriptChunks:
        """
        Split cleaned transcript into semantic chunks.

        Args:
            cleaned_transcript: Cleaned transcript from cleaner service
            metadata: Video metadata (for chunk IDs)

        Returns:
            TranscriptChunks with list of semantic chunks
        """
```

## Пример использования

```python
async with AIClient(settings) as client:
    chunker = SemanticChunker(client, settings)
    result = await chunker.chunk(cleaned_transcript, metadata)

    print(f"Total chunks: {result.total_chunks}")
    print(f"Average size: {result.avg_chunk_size} words")
    for chunk in result.chunks:
        print(f"  - {chunk.id}: {chunk.topic} ({chunk.word_count} words)")
```

## Модель данных

```python
class TranscriptChunk(BaseModel):
    """Single semantic chunk of transcript."""

    id: str                # Формат: {video_id}_{index:03d}
    index: int             # Порядковый номер (1, 2, 3...)
    topic: str             # Краткая тема блока (3-7 слов)
    text: str              # Полный текст блока
    word_count: int        # Количество слов (вычисляется автоматически)


class TranscriptChunks(BaseModel):
    """Collection of transcript chunks."""

    chunks: list[TranscriptChunk]

    @computed_field
    @property
    def total_chunks(self) -> int:
        """Total number of chunks."""
        return len(self.chunks)

    @computed_field
    @property
    def avg_chunk_size(self) -> int:
        """Average chunk size in words."""
        if not self.chunks:
            return 0
        return sum(c.word_count for c in self.chunks) // len(self.chunks)
```

**Файл моделей:** [`backend/app/models/schemas.py`](../../backend/app/models/schemas.py)

## Извлечение JSON из ответа LLM

Метод `_extract_json()` обрабатывает различные форматы ответа LLM:

1. **Markdown code blocks** — извлекает JSON из ` ```json ... ``` `
2. **Поиск JSON-массива** — находит границы `[...]` в тексте
3. **Bracket counting** — корректно определяет закрывающую скобку для вложенных структур

```python
def _extract_json(self, text: str) -> str:
    """
    Extract JSON from LLM response.

    Handles:
    - Markdown-wrapped JSON: ```json [...] ```
    - Plain JSON array: [...]
    - JSON embedded in text with surrounding content
    """
```

**Алгоритм:**
1. Пытается извлечь из markdown code block (regex)
2. Если не markdown — ищет начало `[`
3. Подсчитывает скобки для нахождения корректной закрывающей `]`

## Логирование

Сервис логирует ключевые события:

```
INFO: Chunking transcript: 2500 chars, 380 words
INFO: Chunking complete: 3 chunks, avg size 127 words
ERROR: Failed to parse JSON: ...
DEBUG: Response was: ...
```

## Обработка ошибок

При невалидном JSON выбрасывается `ValueError`:

```python
try:
    data = json.loads(json_str)
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse JSON: {e}")
    raise ValueError(f"Invalid JSON in LLM response: {e}")
```

> **Примечание:** Retry-логика для chunker пока не реализована. При ошибке JSON нужно проверить промпт или повторить запрос вручную.

## Тестирование

Встроенные тесты запускаются командой:

```bash
python -m backend.app.services.chunker
```

**Тесты:**
1. Загрузка промпта и проверка плейсхолдера `{transcript}`
2. Извлечение JSON из plain-текста
3. Извлечение JSON из markdown-обёртки
4. Парсинг чанков с проверкой ID, topic, word_count
5. Полный chunking с LLM (если Ollama доступен)

---

## Альтернативные подходы

Текущая реализация выбрана за баланс простоты и качества. Ниже — альтернативы для будущего рассмотрения.

### Вариант B: Чанки с контекстом

Добавить поле `context` с описанием места чанка в общей теме видео.

| Плюсы | Минусы |
|-------|--------|
| Лучше для RAG-поиска | Сложнее промпт → больше ошибок LLM |
| Чанк понятен автономно | Больше токенов → медленнее |

**Когда использовать:** Если при тестировании RAG-поиска чанки недостаточно информативны.

### Вариант C: Двухэтапная обработка

Сначала LLM создаёт "план" транскрипта, затем разбивает на чанки со ссылкой на план.

| Плюсы | Минусы |
|-------|--------|
| Максимальная точность | 2 вызова LLM вместо 1 |
| Понимание общей структуры | Сильно усложняет реализацию |

**Когда использовать:** Если видео >1 час и спикер часто возвращается к темам.

### Вариант D: Гибридный (LLM + эвристики)

LLM определяет границы тем, финальное разбиение — программно по размеру.

| Плюсы | Минусы |
|-------|--------|
| Контроль размера чанков | Может разрезать середину мысли |
| Предсказуемый результат | Теряем "умное" разбиение LLM |

**Когда использовать:** Если нужен строгий контроль размера для RAG.

---

## Связанные документы

- **Код:** [`backend/app/services/chunker.py`](../../backend/app/services/chunker.py)
- **Модели:** [`backend/app/models/schemas.py`](../../backend/app/models/schemas.py)
- **Промпт:** [`config/prompts/chunker.md`](../../config/prompts/chunker.md)
