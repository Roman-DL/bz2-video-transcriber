# Этап 4: Chunk (Semantic Splitting)

[< Назад: Clean](03-clean.md) | [Обзор Pipeline](README.md) | [Далее: Summarize >](05-summarize.md)

---

## Назначение

Разбиение очищенного транскрипта на смысловые блоки для RAG-поиска в БЗ 2.0.

## Архитектура

LLM разбивает текст на самодостаточные блоки. Для длинных транскриптов (>10K символов) используется подход **Map-Reduce + Overlap**, обеспечивающий глобальный контекст.

| Критерий | Значение | Почему |
|----------|----------|--------|
| Размер chunk | 100-400 слов (оптимум 200-300) | Оптимально для embeddings |
| Смысловая завершённость | Одна тема/мысль | Chunk понятен без контекста |
| Overlap между частями | 1500 символов (~20%) | Сохраняет контекст на границах |
| Метаданные | topic + text + word_count | Минимум для простоты и надёжности |

### Модель данных

Каждый чанк содержит:
- **id** — уникальный идентификатор (формат: `{video_id}_{index:03d}`)
- **topic** — краткая тема блока (3-7 слов)
- **text** — полный текст блока
- **word_count** — количество слов (вычисляется автоматически)

---

## Обработка больших текстов: Map-Reduce + Overlap

Для транскриптов > 10,000 символов используется двухэтапный подход:

### Архитектура

```
CleanedTranscript
       │
       ▼
┌─────────────────┐
│   TextSplitter  │  → Split с overlap (1500 chars)
└────────┬────────┘
         │ list[TextPart]
         ▼
┌──────────────────────┐
│   OutlineExtractor   │  → MAP: parallel outline extraction
│                      │  → REDUCE: дедупликация тем (>60%)
└────────┬─────────────┘
         │ TranscriptOutline
         ▼
┌──────────────────────┐
│   SemanticChunker    │  → Chunking с контекстом outline
└──────────────────────┘
```

### Этап 1: Split with Overlap (TextSplitter)

Текст разбивается на перекрывающиеся части:

| Параметр | Значение | Описание |
|----------|----------|----------|
| PART_SIZE | 8000 символов | Размер одной части |
| OVERLAP_SIZE | 1500 символов | Перекрытие между частями (~20%) |
| MIN_PART_SIZE | 2000 символов | Минимум для последней части |

**Почему overlap важен:**
- Темы на границах частей не теряют контекст
- LLM видит начало и конец смежных тем
- Решает ~80% проблем "разрезанных" тем

### Этап 2: MAP — Извлечение Outline

Из каждой части параллельно извлекается структура:

```python
class PartOutline:
    part_index: int
    topics: list[str]      # 2-4 основных темы
    key_points: list[str]  # 3-5 ключевых тезисов
    summary: str           # 1-2 предложения
```

**Параллельность:** Используется `Semaphore(2)` для ограничения нагрузки на сервер.

### Этап 3: REDUCE — Объединение

Все PartOutline объединяются в единый TranscriptOutline:

```python
class TranscriptOutline:
    parts: list[PartOutline]
    all_topics: list[str]  # Дедуплицированный список тем

    def to_context(self) -> str:
        """Форматирует outline для вставки в промпт LLM"""
```

**Дедупликация тем:** Jaccard similarity >60% считается дубликатом.

### Этап 4: Chunking с контекстом

При создании чанков LLM получает глобальный контекст:

```
## КОНТЕКСТ ВСЕГО ВИДЕО

Транскрипт состоит из 34 частей.

### Основные темы видео:
- Белки и их роль в питании
- Жиры и гормональная система
- Углеводы как источник энергии

### Структура по частям:
**Часть 1:** Темы: Введение, Питание
Содержание: Обсуждение важности правильного питания...
```

---

## Валидация размера чанков

LLM иногда игнорирует требования к размеру. После получения ответа:
- Чанки < 50 слов объединяются с соседними
- Индексы перенумеровываются

---

## Оценка времени обработки

Для 2-часового видео (220 KB, ~34 части) с Semaphore(2):

| Этап | Время |
|------|-------|
| Split | ~1 сек |
| MAP (outline) | ~8-9 мин |
| REDUCE | ~1 сек |
| Chunking | ~8-9 мин |
| **Итого** | **~17-20 мин** |

*При увеличении Semaphore до 4 время сократится до ~10-12 мин*

---

## Конфигурация

Параметры можно настроить в соответствующих файлах:

| Параметр | Файл | Значение по умолчанию |
|----------|------|----------------------|
| PART_SIZE | text_splitter.py | 8000 |
| OVERLAP_SIZE | text_splitter.py | 1500 |
| MAX_PARALLEL_LLM_REQUESTS | outline_extractor.py | 2 |
| TOPIC_SIMILARITY_THRESHOLD | outline_extractor.py | 0.6 |
| LARGE_TEXT_THRESHOLD | chunker.py | 10000 |
| MIN_CHUNK_WORDS | chunker.py | 50 |

---

## Тестирование

```bash
# TextSplitter
python3 -m backend.app.services.text_splitter

# OutlineExtractor
python3 -m backend.app.services.outline_extractor

# SemanticChunker (полный тест)
python3 -m backend.app.services.chunker
```

---

## Связанные файлы

- **Сервис chunking:** `backend/app/services/chunker.py`
- **TextSplitter:** `backend/app/services/text_splitter.py`
- **OutlineExtractor:** `backend/app/services/outline_extractor.py`
- **Модели:** `backend/app/models/schemas.py` (TextPart, PartOutline, TranscriptOutline)
- **Промпт chunking:** `config/prompts/chunker.md`
- **Промпт outline:** `config/prompts/map_outline.md`
