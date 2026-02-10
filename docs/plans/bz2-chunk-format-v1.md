# План: Формат BZ2-Bot для transcript_chunks.json

## Контекст

`transcript_chunks.json` сейчас в собственном формате. Нужно изменить его на формат [контракта BZ2-Bot v1.0](docs/requirements/chunk-import-contract.md), чтобы файл можно было напрямую загрузить в BZ2-Bot через админ-портал без дополнительной трансформации.

**Подход:** модифицировать существующий ChunkStage (разбиение >600 слов) и FileSaver (формат вывода + LLM для description).

**Исключено:** Доработки BZ2-Bot, поле material_type (определяется на стороне BZ2-Bot).

---

## Pre-flight

**Совместимость с архитектурой:** Вписывается полностью. ChunkStage остаётся детерминированным (разбиение — это парсинг). LLM для description добавляется в save flow (уже async). ADR-007 (Claude default), ADR-013 (CamelCase) соблюдены.

**Риск:** формат `transcript_chunks.json` изменится → старые файлы в архиве останутся в старом формате. Фронтенд читает из `pipeline_results.json`, а не из `transcript_chunks.json` → UI не затронут.

---

## Что меняется

### 1. `backend/app/utils/h2_chunker.py` — разбиение >600 слов

Функция `chunk_by_h2()` после разбиения по H2 проверяет каждый чанк: если `word_count > 600`, разбивает по параграфам (`\n\n`). Каждый подчанк получает:
- Тот же `topic` (оригинальный, без суффикса)
- Новый последовательный `index`
- Пересчитанный `word_count`

**Новая функция** (в том же файле):
```python
MAX_CHUNK_WORDS = 600

def _split_large_chunks(chunks: list[TranscriptChunk], video_id: str) -> list[TranscriptChunk]:
    """Split chunks exceeding MAX_CHUNK_WORDS by paragraphs."""
    result = []
    for chunk in chunks:
        if chunk.word_count <= MAX_CHUNK_WORDS:
            result.append(chunk)
            continue
        parts = _split_by_paragraphs(chunk.text, MAX_CHUNK_WORDS)
        for part_idx, part_text in enumerate(parts):
            new_index = len(result) + 1
            result.append(TranscriptChunk(
                id=generate_chunk_id(video_id, new_index),
                index=new_index,
                topic=chunk.topic,  # Оригинальный топик
                text=part_text,
                word_count=count_words(part_text),
            ))
    # Перенумеровать все чанки
    for i, chunk in enumerate(result):
        chunk.index = i + 1
        chunk.id = generate_chunk_id(video_id, i + 1)
    return result
```

Вызывается в `chunk_by_h2()` перед возвратом:
```python
chunks = _split_large_chunks(chunks, video_id)
```

**Переиспользуемые утилиты:**
- `count_words()` из `app.utils.chunk_utils`
- `generate_chunk_id()` из `app.utils.chunk_utils`

### 2. `backend/app/services/saver.py` — формат BZ2 + description

#### 2a. Новый метод `_generate_description()`

Генерирует `description` и `short_description` через Claude на основе конспекта (Summary) или лонгрида/истории.

```python
async def _generate_description(
    self,
    summary: Summary | None,
    longread: Longread | None,
    story: Story | None,
    metadata: VideoMetadata,
) -> tuple[str, str]:
    """Generate description and short_description via Claude.

    Returns:
        Tuple of (description, short_description)
    """
```

**Источник контента** (по приоритету):
1. `Summary` — essence + key_concepts + practical_tools (самый компактный)
2. `Longread` / `Story` — если нет конспекта

**Работа с Claude API:**
```python
from app.services.ai_clients import ClaudeClient
from app.utils.json_utils import extract_json

async with ClaudeClient.from_settings(self.settings) as client:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    content, usage = await client.chat(messages, model=self.settings.summary_model)
    result = json.loads(extract_json(content))
    return result["description"], result["short_description"]
```

**Промпты:** `config/prompts/export/system.md` + `config/prompts/export/user.md`

#### 2b. Модификация `_save_chunks_json()`

Полная переработка метода для вывода в формате BZ2-Bot:

**Сигнатура:**
```python
async def _save_chunks_json(
    self,
    archive_path: Path,
    metadata: VideoMetadata,
    raw_transcript: RawTranscript,
    chunks: TranscriptChunks,
    material_title: str,
    description: str,
    short_description: str,
) -> Path:
```

**Формат вывода:**
```json
{
  "version": "1.0",
  "materials": [{
    "description": "Семантический индекс...",
    "short_description": "Краткое описание...",
    "metadata": {
      "video_id": "...",
      "speaker": "...",
      "event_type": "...",
      "stream": "...",
      "stream_name": "Понедельничная Школа — Супервайзеры",
      "date": "2026-01-22",
      "duration_formatted": "00:05:01",
      "whisper_model": "large-v3-turbo"
    },
    "chunks": [{
      "text": "Тема: {title}\nСпикер: {speaker} | {stream_name} | {DD.MM.YYYY}\n\n## {topic}\n\n{text}",
      "metadata": {
        "chunk_id": "2026-01-22_ПШ-SV_001",
        "chunk_index": 1,
        "topic": "Подготовка к встрече",
        "word_count": 414
      }
    }]
  }]
}
```

**Контекстная шапка** (дата в DD.MM.YYYY):
```
Тема: {material_title}
Спикер: {speaker} | {stream_name} | {DD.MM.YYYY}

## {topic}

{текст чанка}
```

**Учёт split-чанков:** если несколько чанков подряд имеют одинаковый `topic`, добавить суффикс `(1/N)` к H2 в тексте. В `metadata.topic` — оригинал без суффикса.

#### 2c. Модификация `save_educational()` и `save_leadership()`

Добавить вызов `_generate_description()` перед `_save_chunks_json()`:

```python
# В save_educational():
description, short_description = await self._generate_description(
    summary=summary, longread=longread, story=None, metadata=metadata
)
chunks_path = await self._save_chunks_json(
    archive_path, metadata, raw_transcript, chunks,
    material_title=metadata.title,
    description=description,
    short_description=short_description,
)
```

Аналогично для `save_leadership()` (передаётся `story` вместо `longread`).

### 3. Настройка модели для описания

#### Backend: `backend/app/config.py`

Добавить в `Settings`:
```python
describe_model: str = "claude-haiku-4-5"  # Model for BZ2 description generation
```

#### Backend: `backend/app/models/schemas.py`

Добавить поле `describe` в `DefaultModelsResponse`:
```python
class DefaultModelsResponse(CamelCaseModel):
    transcribe: str
    clean: str
    longread: str
    summarize: str
    describe: str  # NEW
```

#### Backend: `backend/app/api/models_routes.py`

В `get_default_models()` добавить:
```python
describe=settings.describe_model,
```

#### Frontend: `frontend/src/api/types.ts`

```typescript
export interface ModelSettings {
  transcribe?: string;
  clean?: string;
  longread?: string;
  summarize?: string;
  describe?: string;  // NEW
}

export interface DefaultModelsResponse {
  transcribe: string;
  clean: string;
  longread: string;
  summarize: string;
  describe: string;  // NEW
}
```

#### Frontend: `frontend/src/components/settings/ModelSelector.tsx`

Добавить `describe` в `PipelineStage` и `STAGE_LABELS`:
```typescript
type PipelineStage = 'transcribe' | 'clean' | 'longread' | 'summarize' | 'describe';

const STAGE_LABELS: Record<PipelineStage, string> = {
  transcribe: 'Транскрипция',
  clean: 'Очистка',
  longread: 'Лонгрид',
  summarize: 'Конспект',
  describe: 'Описание',  // NEW
};
```

#### Frontend: `frontend/src/components/settings/SettingsModal.tsx`

Добавить селектор модели для этапа "Описание" (аналогично существующим).

#### Использование в saver.py

```python
# В _generate_description():
model = self.settings.describe_model
async with ClaudeClient.from_settings(self.settings) as client:
    content, usage = await client.chat(messages, model=model)
```

### 4. `config/prompts/export/system.md` (НОВЫЙ)

Инструкция Claude: создать семантический индекс и краткое описание на основе конспекта/лонгрида. Ответ строго JSON с полями `description` и `short_description`.

### 4. `config/prompts/export/user.md` (НОВЫЙ)

Шаблон с переменными:
- `{material_title}` — название материала
- `{speaker}` — спикер
- `{event_name}` — мероприятие
- `{date}` — дата
- `{source_content}` — текст конспекта/лонгрида/истории

---

## Файлы для изменения

| Файл | Действие |
|------|----------|
| `backend/app/utils/h2_chunker.py` | Добавить `_split_large_chunks()`, `_split_by_paragraphs()`, вызов в `chunk_by_h2()` |
| `backend/app/services/saver.py` | Добавить `_generate_description()`, переработать `_save_chunks_json()`, обновить `save_educational()` / `save_leadership()` |
| `backend/app/config.py` | Добавить `describe_model: str = "claude-haiku-4-5"` в `Settings` |
| `backend/app/models/schemas.py` | Добавить `describe: str` в `DefaultModelsResponse` |
| `backend/app/api/models_routes.py` | Добавить `describe=settings.describe_model` |
| `config/prompts/export/system.md` | **Создать** — системный промпт для description |
| `config/prompts/export/user.md` | **Создать** — пользовательский промпт |
| `frontend/src/api/types.ts` | Добавить `describe` в `ModelSettings` и `DefaultModelsResponse` |
| `frontend/src/components/settings/ModelSelector.tsx` | Добавить `describe` в `PipelineStage` |
| `frontend/src/components/settings/SettingsModal.tsx` | Добавить селектор модели "Описание" |

**Не меняется:**
- `frontend/` компоненты результатов — читают из `pipeline_results.json`, не из `transcript_chunks.json`
- `backend/app/api/` — нет новых endpoints
- `backend/app/main.py` — нет изменений

---

## Порядок реализации (3 фазы, одна беседа)

### Фаза 1: Backend — ядро (h2_chunker + saver + prompts)
1. `h2_chunker.py` — добавить `_split_large_chunks()`, `_split_by_paragraphs()`, тесты
2. `config/prompts/export/system.md` + `user.md` — создать промпты
3. `config.py` — добавить `describe_model`
4. `saver.py` — `_generate_description()`, переработать `_save_chunks_json()`, обновить save methods
5. Проверить синтаксис + запустить тесты h2_chunker

### Фаза 2: Backend — API настроек + Frontend
6. `schemas.py` — добавить `describe` в `DefaultModelsResponse`
7. `models_routes.py` — добавить `describe=settings.describe_model`
8. `types.ts` — добавить `describe` в TypeScript типы
9. `ModelSelector.tsx` — добавить `describe` stage
10. `SettingsModal.tsx` — добавить селектор модели "Описание"

### Фаза 3: Проверка + документация
11. Синтаксис-проверка всех изменённых файлов
12. `/finalize` — обновление документации

---

## Проверка

1. **Синтаксис:**
   ```bash
   python3 -m py_compile backend/app/utils/h2_chunker.py
   python3 -m py_compile backend/app/services/saver.py
   ```

2. **Встроенные тесты h2_chunker:**
   ```bash
   cd backend && python3 -m app.utils.h2_chunker
   ```
   Добавить тесты:
   - Чанк 700 слов → разбивается на 2
   - Чанк 500 слов → не разбивается
   - Чанк 1200 слов → разбивается на 2-3
   - Пограничный случай: 600 слов → не разбивается

3. **Ручная проверка на сервере:**
   - Деплой → обработать educational видео → проверить `transcript_chunks.json`
   - Деплой → обработать leadership видео → проверить `transcript_chunks.json`
   - Валидировать JSON против контракта v1.0
   - Проверить контекстные шапки (дата DD.MM.YYYY, спикер, мероприятие)
   - Проверить разбиение длинных чанков (суффикс (1/N))
   - Проверить description/short_description (качество)

---

## Документация после реализации

- `docs/data-formats.md` — обновить секцию transcript_chunks.json (новый формат BZ2)
- `docs/pipeline/chunk.md` — добавить секцию про разбиение >600 слов
- `CLAUDE.md` — обновить статус (v0.60: BZ2-Bot chunk format)
- `.claude/rules/pipeline.md` — добавить: "Chunk MAX_CHUNK_WORDS=600, разбиение по параграфам"
