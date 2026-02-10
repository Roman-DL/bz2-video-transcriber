# Фаза 5: Детерминированное H2 Чанкование (v0.25)

> **Цель:** Заменить LLM-чанкование на детерминированный парсинг по H2 заголовкам из longread/story

## Изменение порядка Pipeline

### Было (v0.24)
```
Clean -> Outline -> Chunk (LLM) -> Longread -> Summary -> Save
```

### Стало (v0.25)
```
Clean -> Longread -> Summary -> Chunk (H2 парсинг) -> Save
```

**Ключевое изменение:** Chunk теперь идёт ПОСЛЕ Longread/Story, а не до.

---

## Этапы реализации

### 1. Создать утилиту `chunk_by_h2()`

**Файл:** `backend/app/utils/h2_chunker.py` (новый)

```python
def chunk_by_h2(markdown: str, video_id: str) -> TranscriptChunks:
    """Детерминированное чанкование по H2 заголовкам."""
    sections = re.split(r'^## ', markdown, flags=re.MULTILINE)
    chunks = []
    for section in sections:
        if not section.strip():
            continue
        lines = section.split('\n', 1)
        title = lines[0].strip()
        # Убрать emoji из story (1️⃣ Кто они -> Кто они)
        clean_title = re.sub(r'^[\d️⃣]+\s*', '', title)
        content = lines[1].strip() if len(lines) > 1 else ""
        if content:
            chunks.append(TranscriptChunk(...))
    return TranscriptChunks(chunks=chunks, model_name="deterministic")
```

**Экспорт:** добавить в `backend/app/utils/__init__.py`

---

### 2. Обновить LongreadGenerator — принимать CleanedTranscript

**Файл:** `backend/app/services/longread_generator.py`

**Изменение сигнатуры:**
```python
# Было:
async def generate(self, chunks: TranscriptChunks, metadata, outline) -> Longread

# Стало:
async def generate(self, cleaned_transcript: CleanedTranscript, metadata) -> Longread
```

**Внутренние изменения:**
- Использовать `TextSplitter` для разбиения текста на части
- Вызывать `OutlineExtractor` если текст большой (> 10K chars)
- Генерировать секции из частей текста (вместо chunk groups)

---

### 3. Обновить LongreadStage — зависеть от clean

**Файл:** `backend/app/services/stages/longread_stage.py`

```python
class LongreadStage(BaseStage):
    name = "longread"
    depends_on = ["parse", "clean"]  # Было: ["parse", "chunk"]

    async def execute(self, context: StageContext) -> Longread:
        metadata = context.get_result("parse")
        cleaned = context.get_result("clean")  # Было: chunks, outline, _ = ...
        return await self.generator.generate(cleaned, metadata)
```

---

### 4. Обновить ChunkStage — детерминированное чанкование

**Файл:** `backend/app/services/stages/chunk_stage.py`

**Полная переработка:**
```python
class ChunkStage(BaseStage):
    name = "chunk"
    depends_on = ["parse", "longread", "story"]  # Было: ["parse", "clean"]

    def __init__(self, settings: Settings):
        # Не нужен AI client — детерминированно
        self.settings = settings

    async def execute(self, context: StageContext) -> TranscriptChunks:
        metadata = context.get_result("parse")

        # Определить источник markdown
        if context.has_result("longread"):
            longread = context.get_result("longread")
            markdown = longread.to_markdown()
        elif context.has_result("story"):
            story = context.get_result("story")
            markdown = story.to_markdown()
        else:
            raise StageError("No longread or story found")

        return chunk_by_h2(markdown, metadata.video_id)

    def estimate_time(self, input_size: int) -> float:
        return 0.1  # Мгновенно
```

**Удалить:**
- Зависимость от `SemanticChunker`
- Весь LLM-код (outline extraction, text splitting для чанков)

---

### 5. Обновить PipelineOrchestrator

**Файл:** `backend/app/services/pipeline/orchestrator.py`

**Educational pipeline (`_do_educational_pipeline`):**
```python
# Было:
# Phase 1: Extract outline
# Phase 2: Chunking (LLM)
# Phase 3: Longread (from chunks)
# Phase 4: Summary

# Стало:
# Phase 1: Longread (from cleaned transcript)
# Phase 2: Summary (from cleaned transcript) — без изменений
# Phase 3: Chunking (deterministic from longread markdown)
```

**Leadership pipeline (`_do_leadership_pipeline`):**
```python
# Было:
# Phase 1: Extract outline
# Phase 2: Chunking (LLM)
# Phase 3: Story

# Стало:
# Phase 1: Story (from cleaned transcript) — без изменений
# Phase 2: Chunking (deterministic from story markdown)
```

**Удалить:**
- `SemanticChunker` инициализацию
- `_extract_outline()` вызовы из pipeline (перенести внутрь LongreadGenerator)

---

### 6. Обновить Step API

**Файл:** `backend/app/models/schemas.py`

```python
class StepChunkRequest(BaseModel):
    """v0.25+: Детерминированное H2 чанкование."""
    markdown_content: str  # longread или story markdown
    metadata: VideoMetadata
    # Deprecated:
    cleaned_transcript: CleanedTranscript | None = None
    model: str | None = None
```

**Файл:** `backend/app/api/step_routes.py`

```python
@router.post("/chunk")
async def step_chunk(request: StepChunkRequest):
    if request.markdown_content:
        # Новый путь: детерминированное чанкование
        chunks = chunk_by_h2(request.markdown_content, request.metadata.video_id)
        return JSONResponse(chunks.model_dump())
    elif request.cleaned_transcript:
        # Legacy: LLM чанкование (deprecated)
        ...
```

---

### 7. Обновить Progress Weights

**Файл:** `backend/app/services/pipeline/progress_manager.py`

```python
STAGE_WEIGHTS = {
    ProcessingStatus.PARSING: 2,
    ProcessingStatus.TRANSCRIBING: 45,
    ProcessingStatus.CLEANING: 10,
    ProcessingStatus.LONGREAD: 25,      # +7: теперь включает outline extraction
    ProcessingStatus.SUMMARIZING: 10,
    ProcessingStatus.CHUNKING: 5,       # -7: теперь детерминированно
    ProcessingStatus.SAVING: 3,
}
```

---

### 8. Удалить LLM чанкер

**Удалить файлы:**
- `config/prompts/chunker.md`
- `config/prompts/chunker_gemma2.md`

**Упростить:**
- `backend/app/services/chunker.py` — удалить `SemanticChunker`, оставить только fallback
- `backend/app/config.py` — `CHUNKER_MODEL` deprecated

---

### 9. Обновить документацию

**docs/pipeline/04-chunk.md** — полная переработка:
- Удалить всё про LLM чанкование, Map-Reduce, outline extraction
- Описать детерминированный H2 парсинг
- Обновить диаграмму: chunk теперь ПОСЛЕ longread/story
- Обновить конфигурацию (нет LLM параметров)
- Обновить тестирование

**docs/pipeline/05-longread.md** — обновить:
- Изменить диаграмму: longread теперь принимает CleanedTranscript, а не chunks
- Удалить упоминания об outline как shared с Chunker
- Описать новую архитектуру: Clean → Longread (с внутренним TextSplitter)

**docs/architecture.md** — обновить:
- Схему pipeline (строки 74-78): удалить Chunker → Ollama стрелку
- Таблицу компонентов (строки 126-129): Chunker теперь детерминированный
- Stage Abstraction диаграмму (строки 321-334): chunk после longread/story

**docs/data-formats.md** — минорное обновление:
- Поле `model_name` в chunks секции: `"deterministic"` вместо `"gemma2:9b"`
- Добавить примечание что чанки создаются из H2 заголовков longread/story

**CLAUDE.md** — обновить:
- Схему pipeline (строки 11-13): новый порядок
- Упоминания Chunker/CHUNKER_MODEL

**docs/research/pipeline-optimization-for-rag.md** — отметить ✅ v0.25

**frontend/package.json** — версия `0.25.0`

---

## Критические файлы

### Код (backend)

| Файл | Изменение |
|------|-----------|
| `backend/app/utils/h2_chunker.py` | НОВЫЙ: chunk_by_h2() |
| `backend/app/services/longread_generator.py` | Сигнатура: CleanedTranscript вместо chunks |
| `backend/app/services/stages/longread_stage.py` | depends_on: ["parse", "clean"] |
| `backend/app/services/stages/chunk_stage.py` | Полная переработка |
| `backend/app/services/pipeline/orchestrator.py` | Новый порядок этапов |
| `backend/app/services/pipeline/progress_manager.py` | Перебалансировка весов |
| `backend/app/api/step_routes.py` | Новый StepChunkRequest |
| `backend/app/models/schemas.py` | StepChunkRequest модель |

### Промпты (удалить)

| Файл | Действие |
|------|----------|
| `config/prompts/chunker.md` | УДАЛИТЬ |
| `config/prompts/chunker_gemma2.md` | УДАЛИТЬ |

### Документация

| Файл | Изменение |
|------|-----------|
| `docs/pipeline/04-chunk.md` | Полная переработка: детерминированный алгоритм |
| `docs/pipeline/05-longread.md` | Обновить: CleanedTranscript вместо chunks |
| `docs/architecture.md` | Обновить схему pipeline и компоненты |
| `docs/data-formats.md` | model_name: "deterministic" |
| `docs/research/pipeline-optimization-for-rag.md` | Отметить ✅ v0.25 |
| `CLAUDE.md` | Обновить схему pipeline |
| `frontend/package.json` | Версия 0.25.0 |

---

## Проверка (Verification)

1. **Unit тест `chunk_by_h2()`:**
   - Markdown с H2 заголовками → корректные чанки
   - Story с emoji (1️⃣) → emoji убраны из topic
   - Пустой markdown → один fallback чанк

2. **Integration тест pipeline:**
   - Educational: Clean -> Longread -> Summary -> Chunk -> Save
   - Leadership: Clean -> Story -> Chunk -> Save
   - Проверить transcript_chunks.json корректен

3. **Step API тест:**
   - POST /step/chunk с markdown_content
   - Результат — детерминированные чанки

4. **Deploy и smoke test:**
   - Обработать реальное видео обоих типов
   - Сравнить качество чанков с LLM версией
