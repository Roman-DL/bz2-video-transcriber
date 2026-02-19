# Контракт импорта чанков

> Спецификация взаимодействия между внешней системой обработки видео (bz2-video-transcribe) и BZ2-Bot

**Версия контракта:** 1.2
**Обновлено:** 10 февраля 2026

---

## Обзор

Внешняя система (bz2-video-transcribe) обрабатывает видео-записи мероприятий: транскрибирует, разбивает на смысловые чанки, добавляет контекст. Результат — JSON-файл, который загружается в BZ2-Bot через админ-портал.

```
Видео → [bz2-video-transcribe] → JSON → [Admin Portal] → Embeddings → Поиск
```

### Предварительные условия

- Материал уже создан в BZ2-Bot (есть `material_id`, `title`, `section_id`)
- Тип материала: `topic_video` или `topic_longread` (остальные типы отклоняются)
- Загрузка через форму материала в админ-портале (кнопка "Импорт чанков")

---

## Целевой JSON-формат

```json
{
  "version": "1.0",
  "materials": [
    {
      "description": "Закрытие полной оценки: работа с возражениями и сомнениями клиентов. Скрипты и готовые тексты для ответов на возражения. Как реагировать на «я подумаю», работа с возвратами, перевод скептика в клиента. Техника заучивания скриптов, адаптация под свою интонацию. Уверенность при проведении встреч. Разница между экспресс-оценкой и полной оценкой, 100 встреч для навыка. Настройка рекламной кампании, поиск клиентов. Спикер: Иванова А., ПШ Супервайзеры, 22.01.2026.",
      "short_description": "Работа с возражениями при закрытии полной оценки — скрипты и техники",
      "metadata": {
        "video_id": "2026-01-22_ПШ-SV_тестовая-запись",
        "speaker": "Иванова А.",
        "event_type": "ПШ",
        "stream": "SV",
        "stream_name": "Понедельничная Школа — Супервайзеры",
        "date": "2026-01-22",
        "duration_formatted": "00:05:01",
        "whisper_model": "large-v3-turbo"
      },
      "chunks": [
        {
          "text": "Тема: Закрытие полной оценки — работа с возражениями\nСпикер: Иванова А. | ПШ — Супервайзеры | 22.01.2026\n\n## Подготовка к встрече\n\nСпасибо всем, кто присоединился, особенно тем, кто на более серьёзной школе впервые. Сегодня мы будем говорить про полную оценку...",
          "metadata": {
            "chunk_id": "2026-01-22_ПШ-SV_тестовая-запись_001",
            "chunk_index": 1,
            "topic": "Подготовка к встрече",
            "word_count": 414
          }
        }
      ]
    }
  ]
}
```

### Поля `materials[]` элемента

| Поле | Обязательно | Тип | Описание |
|------|:-----------:|-----|----------|
| `chunks` | да | array | Массив чанков (не пустой) |
| `description` | нет | string | Семантический индекс материала: ключевые темы, понятия, косвенные термины. Используется для embedding файлового поиска |
| `short_description` | нет | string | Краткое описание (1-2 предложения). Выводится в Telegram при доставке материала вместе со ссылкой |
| `metadata` | нет | object | Метаданные материала (спикер, мероприятие, дата и т.д.). Сохраняются в `materials.metadata` JSONB, отображаются в админке |
| `source_type` | нет | string | Тип источника. По умолчанию `"transcript"` |
| `trust_tier` | нет | int | Уровень доверия. По умолчанию `2` |

> `material_id` подставляется из URL эндпоинта — передавать в JSON не нужно.

### Поля чанка

| Поле | Обязательно | Тип | Описание |
|------|:-----------:|-----|----------|
| `text` | да | string | Текст чанка с контекстом. **Основное поле** — из него генерируется embedding (vector search) и full-text search индекс. Также передаётся в LLM при генерации ответа |
| `metadata` | нет | object | Произвольные метаданные. Сохраняются как JSONB, отображаются в админке |

### Формирование `text`

Контекст включается **прямо в тело `text`** — так он участвует во всех этапах поиска (vector, FTS, LLM).

#### Структура чанка

```
Тема: {material_title}
Спикер: {speaker} | {stream_name} | {date}

## {H2-заголовок раздела}

{текст раздела}
```

- **Тема** — название материала (общая тема записи), связывает раздел с контекстом
- **Мета-строка** — спикер, мероприятие, дата (компактно, одна строка)
- **H2-заголовок** — название раздела внутри лонгрида (уже в тексте)
- **Текст** — содержание раздела

#### Размер чанка

| Параметр | Значение | Примечание |
|----------|----------|------------|
| Целевой размер | 150-500 слов | Оптимально для text-embedding-3-small |
| Максимум (без шапки) | **600 слов** | Выше — качество embedding снижается |
| Контекстная шапка | ~30-40 слов | Не учитывается в лимите |

Если H2-раздел превышает 600 слов — внешняя система разбивает по параграфам с сохранением шапки и H2-заголовка в каждом подчанке:

```
Тема: Закрытие полной оценки — работа с возражениями
Спикер: Иванова А. | ПШ — Супервайзеры | 22.01.2026

## Работа с возражениями (1/2)

[первая часть параграфов...]
```

```
Тема: Закрытие полной оценки — работа с возражениями
Спикер: Иванова А. | ПШ — Супервайзеры | 22.01.2026

## Работа с возражениями (2/2)

[вторая часть параграфов...]
```

Суффикс `(1/2)` — информационный, на embedding почти не влияет. В `metadata.topic` хранится оригинальный H2-заголовок без суффикса.

### Формирование `description`

Описание — **семантический индекс материала** для файлового поиска. Из него генерируется embedding, по которому пользователь находит материал даже косвенными запросами ("найди материалы про набор мышечной массы", "где описан куркумин").

Должно содержать:
- Ключевые темы и понятия, обсуждаемые в материале
- Косвенные термины, по которым могут искать (синонимы, связанные понятия)
- Контекст: спикер, мероприятие, дата
- Практические аспекты: что можно узнать из материала

**Пример для документа (продукт Формула 1):**
```
Полное руководство по Формуле 1 Herbalife: состав, пищевая ценность, способы применения, рецепты коктейлей. Заменитель приема пищи для снижения и поддержания веса. Информация о вкусах (шоколад, ванилия, клубника, капучино), дозировках, противопоказаниях. Как презентовать продукт клиентам, ответы на частые вопросы. Научное обоснование эффективности, сравнение с аналогами. Базовое питание, сбалансированный рацион, контроль калорий, белковое питание.
```

**Пример для видео-транскрипта:**
```
Закрытие полной оценки: работа с возражениями и сомнениями клиентов. Скрипты и готовые тексты для ответов на возражения. Как реагировать на "я подумаю", работа с возвратами, перевод скептика в клиента. Техника заучивания скриптов, адаптация под свою интонацию. Уверенность при проведении встреч. Разница между экспресс-оценкой и полной оценкой, 100 встреч для навыка. Настройка рекламной кампании, поиск клиентов. Спикер: Иванова А., ПШ Супервайзеры, 22.01.2026.
```

### Метаданные материала (`materials[].metadata`)

Информация об исходном материале и процессе обработки. Сохраняется в `materials.metadata` (JSONB), мержится с существующими метаданными. Отображается в админ-портале на странице материала.

| Поле | Описание | Пример |
|------|----------|--------|
| `video_id` | ID видео во внешней системе | `"2026-01-22_ПШ-SV_тестовая-запись"` |
| `speaker` | Спикер | `"Иванова А."` |
| `event_type` | Тип мероприятия | `"ПШ"` |
| `stream` | Код потока | `"SV"` |
| `stream_name` | Название потока | `"ПШ — Супервайзеры"` |
| `date` | Дата мероприятия | `"2026-01-22"` |
| `duration_formatted` | Длительность видео | `"00:05:01"` |
| `whisper_model` | Модель транскрибации | `"large-v3-turbo"` |

### Метаданные чанка (`chunks[].metadata`)

Информация о конкретном чанке. Сохраняется в `embeddings.source_metadata` (JSONB).

| Поле | Описание | Пример |
|------|----------|--------|
| `chunk_id` | Уникальный ID чанка во внешней системе | `"2026-01-22_ПШ-SV_001"` |
| `chunk_index` | Порядковый номер чанка | `1` |
| `topic` | H2-заголовок раздела (оригинал, до вставки в text) | `"Подготовка к встрече"` |
| `word_count` | Количество слов | `414` |

---

## Как контекст влияет на поиск

В BZ2-Bot два режима поиска, они используют **разные embeddings**:

### 1. Файловый поиск ("найди документ")

```
Запрос → embedding → сравнение с material-level embedding → список материалов
```

- Material-level embedding генерируется из `title | description` материала
- **Поле `description`** из JSON обновляет описание → влияет на качество файлового поиска
- Чанки НЕ участвуют в файловом поиске

### 2. Q&A поиск ("ответь на вопрос")

```
Запрос → embedding → сравнение с content embeddings → топ чанков → LLM генерирует ответ
```

- Content embedding генерируется из `text` каждого чанка
- Найденные чанки передаются в Claude как контекст для ответа
- **Контекст в `text`** улучшает и поиск (embedding), и качество ответа (LLM видит тему)

#### Уровни поиска (trust_tier)

Q&A поиск разделён на два уровня по степени доверия к источникам:

| | Tier 1 (основной) | Tier 2 (расширенный) |
|---|---|---|
| Источники | Документы (`source_type="document"`) | Транскрипты (`source_type="transcript"`) |
| Качество | Выверенная, точная информация | Менее точная, но полезные общие концепции |
| Доступ | Все пользователи | Настраивается (`qa_tier2_min_role`) |
| Fallback | — | Автоматический, если tier 1 не дал результатов (`qa_auto_fallback`) |

Импортированные чанки получают `trust_tier=2` по умолчанию — они попадают в расширенный поиск.

### Схема: какое поле куда попадает

```
JSON                          БД                              Использование
─────────────────────────────────────────────────────────────────────────────
description          →  materials.description          →  FILE SEARCH embedding
                        (title | description)              chunk_type="material"

metadata             →  materials.metadata (merge)     →  отображение в админке
                                                          (спикер, мероприятие, дата...)

chunks[].text        →  embeddings.chunk_text          →  Q&A SEARCH embedding
                        + fts (tsvector, auto)             chunk_type="content"
                                                        →  LLM промпт (ответ)
                                                           trust_tier=2

chunks[].metadata    →  embeddings.source_metadata     →  отображение в админке
                                                          (topic, word_count...)
```

> **Принцип:** внешняя система формирует **контекстуализированные чанки** — контекст (тема, спикер, мероприятие) включён прямо в `text`. Это даёт максимальное качество: контекст влияет на vector search, keyword search и LLM-ответ одновременно.

---

## Что происходит при импорте

1. JSON загружается как файл через `POST /api/materials/{id}/import-chunks`
2. `material_id` подставляется из URL — значение из JSON игнорируется
3. Если переданы `description` / `short_description` — обновляют поля материала
3a. Если передан `metadata` — мержится в `materials.metadata` (JSONB)
4. **Удаляются** все старые embeddings материала (delete-before-insert)
5. Создаётся **material-level embedding** (chunk_index=0) из `title | description`
6. Для каждого чанка создаётся **content embedding** (chunk_index=1, 2, ...)
7. Материал помечается `is_indexed=True`, `indexed_at=now`

**Важно:** повторный импорт полностью заменяет предыдущие чанки.

---

## Ограничения

| Ограничение | Значение |
|-------------|----------|
| `version` | Строго `"1.0"` |
| Допустимые типы материала | `topic_video`, `topic_longread` |
| Массив `chunks` | Не может быть пустым |
| `text` в чанке | Обязательное, не может быть пустой строкой |
| Размер чанка (без шапки) | Макс. 600 слов (оптимально 150-500) |
| Повторный импорт | Полная замена (delete-before-insert) |
| Авторизация | JWT-токен администратора |

---

## Эндпоинт

```
POST /api/materials/{material_id}/import-chunks
Content-Type: multipart/form-data
Authorization: Bearer {jwt_token}

Body: file (JSON-файл)
```

### Ответ (успех)

```json
{
  "status": "imported",
  "material_id": 4,
  "chunks_created": 5,
  "errors": []
}
```

### Ответ (частичные ошибки)

```json
{
  "status": "imported",
  "material_id": 4,
  "chunks_created": 3,
  "errors": [
    "Материал 4: пустой text в чанке 2"
  ]
}
```

---

## Миграция bz2-video-transcribe

Текущий формат внешней системы и что нужно изменить для совместимости.

### Текущий формат → целевой

| Текущее поле | Действие | Целевое поле |
|-------------|----------|-------------|
| `statistics` | убрать или оставить, BZ2-Bot игнорирует | — |
| — | **добавить** | `version: "1.0"` |
| — | **добавить**, обёртка массивом | `materials: [{ ... }]` |
| — | **добавить**, AI-суммаризация содержимого | `materials[].description` |
| — | **добавить**, краткое описание темы | `materials[].short_description` |
| `metadata` (корень) | **переместить** внутрь materials[0] | `materials[].metadata` |
| `video_id` | **переместить** внутрь metadata | `materials[].metadata.video_id` |
| `chunks` | **переместить** внутрь materials[0] | `materials[].chunks` |
| `chunks[].text` | **обернуть** контекстной шапкой + H2 | `chunks[].text` (шапка: `material_title`, спикер, мероприятие, дата + `## topic`) |
| `chunks[].text` | **разбить** если > 600 слов | По параграфам, с дублированием шапки и H2 |
| `chunks[].id` | **переименовать** | `chunks[].metadata.chunk_id` |
| `chunks[].index` | **переименовать** | `chunks[].metadata.chunk_index` |
| `chunks[].word_count` | **пересчитать** (после разбиения) | `chunks[].metadata.word_count` |
| `chunks[].topic` | **скопировать** (оригинал без суффикса) | `chunks[].metadata.topic` |

### Псевдокод трансформации

```python
MAX_CHUNK_WORDS = 600  # Без учёта контекстной шапки

def transform_to_bz2_format(
    old_json: dict,
    material_title: str,
    description: str,
    short_description: str,
) -> dict:
    """
    Трансформация из текущего формата bz2-video-transcribe в целевой.

    Args:
        old_json: Текущий JSON внешней системы
        material_title: Название материала (общая тема записи) для шапки чанков
        description: Семантический индекс материала (AI-суммаризация содержимого)
        short_description: Краткое описание (1-2 предложения) для Telegram
    """
    meta = old_json.get("metadata", {})

    # Метаданные материала (из корня)
    material_metadata = {
        "video_id": old_json.get("video_id"),
        "speaker": meta.get("speaker"),
        "event_type": meta.get("event_type"),
        "stream": meta.get("stream"),
        "stream_name": meta.get("stream_name"),
        "date": meta.get("date"),
        "duration_formatted": meta.get("duration_formatted"),
        "whisper_model": meta.get("whisper_model"),
    }

    # Контекстная шапка (одинаковая для всех чанков материала)
    header_parts = [f"Тема: {material_title}"]
    meta_parts = []
    if meta.get("speaker"):
        meta_parts.append(meta["speaker"])
    if meta.get("stream_name"):
        meta_parts.append(meta["stream_name"])
    if meta.get("date"):
        meta_parts.append(meta["date"])
    if meta_parts:
        header_parts.append(f"Спикер: {' | '.join(meta_parts)}")
    context_header = "\n".join(header_parts)

    # Трансформация чанков
    new_chunks = []
    for chunk in old_json.get("chunks", []):
        topic = chunk.get("topic", "")
        body = chunk["text"]

        # Разбиение больших разделов
        sub_chunks = _split_if_needed(body, MAX_CHUNK_WORDS)

        for part_idx, part_text in enumerate(sub_chunks):
            # H2-заголовок с суффиксом части (если разбит)
            h2 = topic
            if len(sub_chunks) > 1:
                h2 = f"{topic} ({part_idx + 1}/{len(sub_chunks)})"

            text = f"{context_header}\n\n## {h2}\n\n{part_text}"

            new_chunks.append({
                "text": text,
                "metadata": {
                    "chunk_id": chunk.get("id"),
                    "chunk_index": chunk.get("index"),
                    "topic": topic,  # Оригинал без суффикса
                    "word_count": len(part_text.split()),
                },
            })

    return {
        "version": "1.0",
        "materials": [{
            "description": description,
            "short_description": short_description,
            "metadata": material_metadata,
            "chunks": new_chunks,
        }],
    }


def _split_if_needed(text: str, max_words: int) -> list[str]:
    """Разбить текст по параграфам, если превышает лимит."""
    if len(text.split()) <= max_words:
        return [text]

    paragraphs = text.split("\n\n")
    parts, current, current_words = [], [], 0

    for para in paragraphs:
        para_words = len(para.split())
        if current and current_words + para_words > max_words:
            parts.append("\n\n".join(current))
            current, current_words = [para], para_words
        else:
            current.append(para)
            current_words += para_words

    if current:
        parts.append("\n\n".join(current))

    return parts
```

> **`description` не формируется автоматически из метаданных.** Это семантический индекс, который должен содержать ключевые темы и понятия из содержимого. Рекомендуется генерировать на основе лонгрида.

---

## Доработки BZ2-Bot

Что нужно изменить на нашей стороне для полной поддержки целевого формата.

### 1. Сохранение `metadata` материала при импорте

**Файл:** `src/content/services/indexer.py` → `import_transcript_batch()`

Сейчас `metadata` из `materials[]` не читается. Нужно добавить merge входящих метаданных в `material.metadata_`:

```python
# После обновления description/short_description (строка ~311)
import_metadata = mat_data.get("metadata")
if import_metadata:
    existing = material.metadata_ or {}
    existing.update(import_metadata)
    material.metadata_ = existing
```

### 2. Убрать упрощённый формат из эндпоинта

**Файл:** `src/admin/routers/materials.py` (строки 152-162)

Блок `if "materials" not in data` оборачивает JSON без `materials[]` в стандартный формат. С переходом на целевой контракт — не нужен. Заменить на валидацию:

```python
if "materials" not in data:
    raise HTTPException(
        status_code=400,
        detail='JSON должен содержать ключ "materials"',
    )
```

### 3. Отображение метаданных материала в админке

**Файл:** `admin-portal/src/pages/materials/detail.tsx`

Показать `metadata` материала (спикер, мероприятие, дата) в карточке материала — рядом с секцией чанков. Пока информационный блок без редактирования.

### 4. Удалить `contextualized_text` из кода

Поле `contextualized_text` больше не нужно — внешняя система формирует контекстуализированные чанки, контекст включён прямо в `text`.

Что убрать:
- **Модель:** `contextualized_text` из `Embedding` (`src/content/models.py`)
- **Импорт:** `chunk.get("contextualized_text")` из `import_transcript_batch()` (`src/content/services/indexer.py`)
- **LLM:** fallback `chunk.get("contextualized_text") or chunk.get("chunk_text")` → просто `chunk.get("chunk_text")` (`src/search/services/llm_provider.py`)
- **SQL:** `contextualized_text` из `hybrid_search()` (миграция)
- **БД:** колонка `contextualized_text` из таблицы `embeddings` (миграция)

---

_Версия: 1.2 | Обновлено: 10 февраля 2026_
