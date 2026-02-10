# План: Лонгрид и Конспект (новый режим обработки транскриптов)

## Цель

Заменить текущий summarizer на двухэтапную генерацию:
1. **Лонгрид** (5-10 страниц) — полное содержание с голосом автора
2. **Конспект** (2-4 страницы) — краткий документ для тех, кто уже слушал

## Новый Pipeline

```
Parse → Transcribe → Clean → Outline → Chunk → Longread → Summary → Save
                               ↑                   ↑
                          существует          использует
                                              outline
```

**Ключевое изменение:** Outline становится shared resource — используется и в Chunk, и в Longread.

## Стратегия для маленького контекста

**Проблема**: gemma2 имеет 8K токенов, а лонгрид для часового видео — 50K+ символов.

**Решение: Map-Reduce с общим Outline как контекстом**

```
Cleaned text
    ↓
OutlineExtractor → TranscriptOutline (темы + структура)
    ↓
Chunker (использует outline) → Chunks
    ↓
LongreadGenerator:
    Параллельно для каждой группы чанков:
      outline + чанки 1-4 → секция 1
      outline + чанки 5-8 → секция 2
      ...
    ↓
    Reduce: добавить intro/conclusion
    ↓
Longread (единый документ)
    ↓
SummaryGenerator (из section titles + intro)
    ↓
Конспект (краткий документ)
```

**Преимущества:**
- Каждая секция знает общую структуру через outline
- Сохраняется параллелизм генерации секций
- Переиспользуется существующий OutlineExtractor

---

## Файлы для создания/изменения

### 1. Промпты (`config/prompts/`)

| Файл | Назначение |
|------|------------|
| `longread_section.md` | Генерация одной секции из 4-5 чанков |
| `longread_combine.md` | Генерация intro/conclusion для лонгрида |
| `summary.md` | **Заменяет** текущий `summarizer.md` — конспект из лонгрида |
| `summarizer.md.backup` | Архив старого промпта (на случай отладки) |

**Стратегия адаптации промптов:**

1. **Сейчас (gemma2/qwen2.5):** Создаём сжатые промпты (~50-100 строк) с ключевыми правилами
2. **Оригиналы остаются:** `docs/template prompts/` — полные инструкции как референс
3. **Масштабирование:** Можно использовать механизм fallback из `load_prompt()`:
   - `longread_section.md` — базовый сжатый промпт
   - `longread_section_qwen3.md` — расширенный для моделей с большим контекстом

**Что включаем в сжатые промпты:**
- Принципы (голос автора, самодостаточность секций для RAG)
- Формат вывода (JSON)
- Минимальные правила очистки
- Classification (section/subsection/tags)

**Что НЕ включаем:**
- Детальные примеры редактирования
- Работу со слайдами (на будущее)
- Чек-листы (для human review)

### 2. Pydantic-модели (`backend/app/models/schemas.py`)

```python
# Новые модели:
class LongreadSection(BaseModel):
    index: int
    title: str
    content: str
    source_chunks: list[int]
    word_count: int

class LongreadMetadata(BaseModel):
    video_id: str
    title: str
    speaker: str
    date: date
    # ... + classification fields

class Longread(BaseModel):
    metadata: LongreadMetadata
    introduction: str
    sections: list[LongreadSection]
    conclusion: str

    def to_markdown(self) -> str: ...

class Summary(BaseModel):
    video_id: str
    title: str
    essence: str                    # 2-3 абзаца о сути
    key_concepts: list[str]         # Ключевые концепции
    practical_tools: list[str]      # Инструменты
    quotes: list[str]               # 2-4 цитаты
    insight: str                    # Главный инсайт
    # Classification (как в текущем VideoSummary):
    section: str
    subsection: str
    tags: list[str]
    access_level: int

# Новый статус:
class ProcessingStatus(str, Enum):
    ...
    LONGREAD = "longread"  # Добавить после CHUNKING
```

### 3. Сервисы (`backend/app/services/`)

| Файл | Назначение |
|------|------------|
| `longread_generator.py` | **Новый** — генерация лонгрида из чанков + outline |
| `summary_generator.py` | **Новый** — генерация конспекта из лонгрида |
| `summarizer.py` | Сохранить для обратной совместимости, но не использовать в основном pipeline |
| `outline_extractor.py` | **Без изменений** — переиспользуется как есть |
| `pipeline.py` | Обновить порядок этапов, передавать outline в longread |
| `saver.py` | Добавить сохранение `longread.md` |

**Ключевой момент**: `LongreadGenerator.generate()` принимает `outline: TranscriptOutline` как параметр:

```python
async def generate(
    self,
    chunks: TranscriptChunks,
    metadata: VideoMetadata,
    outline: TranscriptOutline,  # ← общий контекст
) -> Longread:
```

### 4. Конфигурация (`config/models.yaml`)

```yaml
models:
  gemma2:
    longread:
      chunks_per_section: 4
      max_parallel_sections: 2
    summary:
      max_input_chars: 8000

  qwen2:
    longread:
      chunks_per_section: 6
      max_parallel_sections: 3
    summary:
      max_input_chars: 25000
```

---

## Структура выходных файлов

```
archive/2025/01/ПШ.SV/Title (Speaker)/
├── pipeline_results.json    # Обновить: добавить longread + summary
├── longread.md              # НОВЫЙ: 5-10 страниц, markdown
├── summary.md               # ОБНОВИТЬ: 2-4 страницы (вместо текущего формата)
├── transcript_chunks.json   # Без изменений
├── transcript_raw.txt       # Без изменений
├── transcript_cleaned.txt   # Без изменений
├── audio.mp3
└── video.mp4
```

---

## План реализации по этапам

### Этап 1: Промпты
1. Создать `config/prompts/longread_section.md`
2. Создать `config/prompts/longread_combine.md`
3. Переименовать `summarizer.md` → `summarizer.md.backup`
4. Создать новый `summary.md` (формат конспекта)

### Этап 2: Модели данных
1. Добавить в `schemas.py`:
   - `LongreadSection`, `LongreadMetadata`, `Longread`
   - `Summary` (новый формат)
   - `ProcessingStatus.LONGREAD`

### Этап 3: Сервисы
1. Создать `longread_generator.py`:
   - `LongreadGenerator` класс
   - Map-Reduce: `_generate_sections()` → `_generate_frame()`
   - Семафор для параллельных LLM-запросов
2. Создать `summary_generator.py`:
   - `SummaryGenerator` класс
   - Генерация из section summaries лонгрида

### Этап 4: Интеграция в Pipeline
1. Обновить `pipeline.py`:
   - Добавить `ProcessingStatus.LONGREAD` в `STAGE_WEIGHTS`
   - Изменить `_do_chunk_and_summarize()` → `_do_chunk_longread_summarize()`
   - Outline извлекается один раз и передаётся в chunker и longread_generator

   ```python
   async def _do_chunk_longread_summarize(self, ...):
       # 1. Извлечь outline (уже есть в текущем коде)
       text_parts, outline = await self._extract_outline(cleaned_transcript)

       # 2. Chunk с outline (уже есть)
       chunks = await chunker.chunk_with_outline(..., outline)

       # 3. Longread с outline (НОВОЕ)
       longread = await longread_generator.generate(chunks, metadata, outline)

       # 4. Summary из longread (НОВОЕ)
       summary = await summary_generator.generate(longread, metadata)

       return chunks, longread, summary
   ```

2. Обновить `saver.py`:
   - Добавить `_save_longread_md()`
   - Обновить `_save_summary_md()` для нового формата
   - Обновить `pipeline_results.json`

### Этап 5: Конфигурация
1. Добавить секции `longread` и `summary` в `config/models.yaml`

### Этап 6: API (опционально)
1. Добавить `/step/longread` endpoint
2. Добавить `/step/summary` endpoint
3. Обновить WebSocket progress messages

---

## Ключевые файлы для изменения

| Файл | Изменения |
|------|-----------|
| [schemas.py](backend/app/models/schemas.py) | +4 модели, +1 статус |
| [pipeline.py](backend/app/services/pipeline.py) | Новый порядок этапов |
| [saver.py](backend/app/services/saver.py) | Сохранение longread.md |
| [models.yaml](config/models.yaml) | Параметры longread/summary |

## Верификация

1. **Unit-тесты**: Запустить тесты для новых сервисов
2. **Интеграция**: Обработать тестовое видео через полный pipeline
3. **Проверить файлы**:
   - `longread.md` — 5-10 страниц, структура по разделам
   - `summary.md` — 2-4 страницы, конспект с цитатами
   - `pipeline_results.json` — содержит все данные
4. **Контекстное окно**: Убедиться, что Map-Reduce работает для больших видео (>1 часа)
