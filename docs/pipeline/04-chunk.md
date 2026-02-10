---
doc_type: reference
status: active
updated: 2026-02-11
audience: [developer, ai-agent]
tags:
  - pipeline
  - stage
---

# Этап 4: Chunk (Deterministic H2 Parsing)

[< Назад: Clean](03-clean.md) | [Обзор Pipeline](README.md) | [Далее: Longread >](05-longread.md)

---

## Назначение

Разбиение сгенерированного контента на смысловые блоки для RAG-поиска в БЗ 2.0.

> **Примечание:** H2 парсинг детерминистический — LLM не используется для разбиения.
> **v0.62+:** После парсинга опционально вызывается Claude для генерации описаний (description/short_description).

## Input / Output

| Направление | Тип | Описание |
|-------------|-----|----------|
| **Input** | `parse: VideoMetadata` | Метаданные (video_id, content_type) |
| | `longread: Longread` | Лонгрид для EDUCATIONAL контента |
| | `story: Story` | История для LEADERSHIP контента |
| **Output** | `TranscriptChunks` | Коллекция чанков из H2 заголовков |

**Зависимости:** `depends_on = ["parse", "longread", "story"]`

### Поля TranscriptChunk

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | `str` | Уникальный ID: `{video_id}_{index:03d}` |
| `index` | `int` | Порядковый номер чанка |
| `topic` | `str` | Заголовок H2 (без эмодзи и номеров) |
| `text` | `str` | Полный текст раздела |
| `word_count` | `int` | Количество слов |

### Поля TranscriptChunks

| Поле | Тип | Описание |
|------|-----|----------|
| `chunks` | `list[TranscriptChunk]` | Список чанков |
| `model_name` | `str` | `"deterministic"` |
| `total_tokens` | `int \| None` | Всего токенов (v0.42+) |
| `total_chunks` | computed | Количество чанков |
| `avg_chunk_size` | computed | Средний размер в словах |
| `description` | `str` | Семантическое описание для поиска (v0.62+) |
| `short_description` | `str` | Краткое описание для Telegram (v0.62+) |
| `describe_model_name` | `str \| None` | Модель для генерации описаний (v0.62+) |
| `describe_tokens_used` | `TokensUsed \| None` | Токены (v0.62+) |
| `describe_cost` | `float \| None` | Стоимость генерации (v0.62+) |
| `describe_processing_time_sec` | `float \| None` | Время генерации (v0.62+) |

## v0.26: Детерминированное чанкирование

**ВАЖНО:** Начиная с v0.25, чанкирование полностью детерминировано и не использует LLM.

### Изменение порядка в pipeline

```
До v0.25:  Clean → Chunk (LLM) → Longread → Summary
После:    Clean → Longread → Summary → Chunk (H2 parsing)
```

Чанкирование теперь выполняется **ПОСЛЕ** генерации longread/story, парсингом H2 заголовков из markdown.

---

## Архитектура

ChunkStage парсит H2 заголовки (`## `) из сгенерированного markdown и создаёт чанки:

| Критерий | Значение | Почему |
|----------|----------|--------|
| Источник данных | longread.md / story.md | Структурированный markdown |
| Метод разбиения | H2 парсинг | Детерминированно, предсказуемо |
| Смысловая завершённость | Один раздел | Каждый H2 — отдельная тема |
| Метаданные | topic + text + word_count | Минимум для простоты и надёжности |

## Реализация

### H2 Chunker (`app/utils/h2_chunker.py`)

```python
from app.utils.h2_chunker import chunk_by_h2

markdown = """
# Заголовок

## Введение
Текст введения...

## Основная часть
Текст основной части...

## Заключение
Текст заключения...
"""

chunks = chunk_by_h2(markdown, video_id="test-123")
# chunks.total_chunks == 3
# chunks.chunks[0].topic == "Введение"
```

### Обработка заголовков

- **Эмодзи удаляются:** `## 1️⃣ Кто они` → `Кто они`
- **Номера удаляются:** `## 3. Решение` → `Решение`
- **YAML front matter игнорируется**

### ChunkStage

```python
class ChunkStage(BaseStage):
    name = "chunk"
    depends_on = ["parse", "longread", "story"]  # После генерации контента

    def __init__(self, settings: Settings):
        # v0.26: AI client НЕ нужен
        self.settings = settings

    async def execute(self, context: StageContext) -> TranscriptChunks:
        metadata = context.get_result("parse")
        markdown = self._get_source_markdown(context, metadata)
        return chunk_by_h2(markdown, metadata.video_id)
```

---

## Выбор источника по content_type

| ContentType | Источник | Пример структуры |
|-------------|----------|------------------|
| EDUCATIONAL | longread.md | `## Введение`, `## Основные понятия`, ... |
| LEADERSHIP | story.md | `## 1️⃣ Кто они`, `## 2️⃣ Проблема`, ... |

---

## Разбиение длинных чанков (v0.60+)

После парсинга H2 заголовков, чанки проверяются на размер. Если чанк превышает `MAX_CHUNK_WORDS=600`, он разбивается по параграфам (`\n\n`):

```python
MAX_CHUNK_WORDS = 600

# Процесс:
# 1. chunk_by_h2() парсит H2 заголовки
# 2. _split_large_chunks() проверяет каждый чанк
# 3. _split_by_paragraphs() разбивает жадно по параграфам
# 4. Все чанки перенумеровываются последовательно
```

### Поведение при split

| Исходный размер | Результат |
|-----------------|-----------|
| ≤ 600 слов | Без изменений |
| 601-1200 слов | 2 чанка |
| > 1200 слов | 2-3+ чанков |

**Сохранение topic:** все подчанки сохраняют оригинальный `topic` (заголовок H2). Суффикс `(1/N)` добавляется только в saver при формировании контекстной шапки для BZ2-Bot.

## Генерация описаний (v0.62+)

После H2 парсинга, chunk endpoint опционально генерирует `description` и `short_description` через Claude (`describe_model`).

### Условие вызова

Описания генерируются если в запросе передан хотя бы один из: `summary`, `longread`, `story`. В step-by-step режиме frontend передаёт все доступные данные автоматически.

### DescriptionGenerator (`app.services.description_generator`)

Извлечён из saver.py в v0.62. Приоритет источника контента:
1. **Summary** — essence + key_concepts + practical_tools
2. **Longread** — секции лонгрида
3. **Story** — блоки истории

При ошибке Claude — chunk возвращается с пустыми описаниями (warning в лог, НЕ PipelineError).

### Оценка времени

| Этап | Время |
|------|-------|
| H2 parsing | < 0.1 сек |
| Description generation | ~3-5 сек (Claude API) |

---

## Преимущества v0.26

1. **Детерминированность** — одинаковый input всегда даёт одинаковый output
2. **Скорость** — мгновенно (~0.1s вместо минут LLM)
3. **Надёжность** — нет проблем с JSON parsing, timeout, rate limits
4. **Качество** — структура определяется longread/story промптами

---

---

## Тестирование

```bash
# H2 Chunker
cd backend && python -m app.utils.h2_chunker

# ChunkStage
cd backend && python -m app.services.stages.chunk_stage
```

---

## Связанные файлы

- **Stage:** [`backend/app/services/stages/chunk_stage.py`](../../backend/app/services/stages/chunk_stage.py)
- **H2 Chunker:** [`backend/app/utils/h2_chunker.py`](../../backend/app/utils/h2_chunker.py)
- **Description Generator:** [`backend/app/services/description_generator.py`](../../backend/app/services/description_generator.py) (v0.62+)
- **Модели:** [`backend/app/models/schemas.py`](../../backend/app/models/schemas.py) — `TranscriptChunks`, `TranscriptChunk`
