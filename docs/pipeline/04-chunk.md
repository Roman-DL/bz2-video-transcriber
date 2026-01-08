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
| Метаданные | topic + text | Минимум для простоты и надёжности |

## Класс SemanticChunker

```python
class SemanticChunker:
    """Сервис семантического разбиения транскриптов."""

    def __init__(self, ai_client: AIClient, settings: Settings):
        self.ai_client = ai_client
        self.settings = settings
        self.prompt_template = load_prompt("chunker", settings)

    async def chunk(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
    ) -> TranscriptChunks:
        """Разбивает очищенный транскрипт на смысловые чанки."""
        text = cleaned_transcript.text

        # Используем replace() вместо format() из-за JSON в промпте
        prompt = self.prompt_template.replace("{transcript}", text)
        response = await self.ai_client.generate(prompt)

        # Парсим JSON из ответа LLM
        chunks = self._parse_chunks(response, metadata.video_id)

        return TranscriptChunks(chunks=chunks)
```

**Использование:**
```python
async with AIClient(settings) as client:
    chunker = SemanticChunker(client, settings)
    result = await chunker.chunk(cleaned_transcript, metadata)
    print(f"Создано {result.total_chunks} чанков, avg {result.avg_chunk_size} слов")
```

## Модель данных

```python
class TranscriptChunk(BaseModel):
    """Один смысловой блок транскрипта."""

    id: str                # Формат: {video_id}_{index:03d}
    index: int             # Порядковый номер (1, 2, 3...)
    topic: str             # Краткая тема блока (3-7 слов)
    text: str              # Полный текст блока
    word_count: int        # Количество слов (вычисляется)


class TranscriptChunks(BaseModel):
    """Результат chunking."""

    chunks: list[TranscriptChunk]

    @computed_field
    def total_chunks(self) -> int:
        return len(self.chunks)

    @computed_field
    def avg_chunk_size(self) -> int:
        if not self.chunks:
            return 0
        return sum(c.word_count for c in self.chunks) // len(self.chunks)
```

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
- **Промпт:** [`config/prompts/chunker.md`](../../config/prompts/chunker.md)
- **API:** [api-reference.md](../api-reference.md#ollama-api)
