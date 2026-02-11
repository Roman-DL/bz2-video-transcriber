# План: перенос генерации описаний из Save в Chunk

## Контекст

В v0.61 описания (`description`, `short_description`) генерируются через Claude при нажатии "Сохранить" (этап Save). Из-за этого:
1. На вкладке **Чанки** описания не видны до выполнения Save
2. В **Статистике** стоимость описания привязана к строке "Сохранение", а не "Чанки"

**Цель:** генерировать описания при разбиении на чанки, чтобы они были видны сразу. Save становится чистой записью файлов без LLM. Чистая архитектура — без backward-compatibility костылей.

## Изменения

### 1. Новый сервис: `backend/app/services/description_generator.py`

Извлечь из `saver.py` логику генерации описаний:
- `DescriptionGenerator(settings)` — конструктор, загружает events_config
- `async generate(summary, longread, story, metadata)` → `DescriptionResult`
- `_build_source_content(summary, longread, story)` — приоритет: Summary > Longread/Story
- `_get_stream_name(event_type, stream)` — имя потока из events config

Извлекаемый код из `saver.py`: строки 459-577 (`_generate_description`, `_build_source_content`, `_get_stream_name`).

### 2. Модель `DescriptionResult` в `backend/app/models/schemas.py`

```python
class DescriptionResult(CamelCaseModel):
    description: str = ""
    short_description: str = ""
    model_name: str | None = None
    tokens_used: TokensUsed | None = None
    cost: float | None = None
    processing_time_sec: float | None = None
```

### 3. Расширить `TranscriptChunks` в `backend/app/models/schemas.py`

Добавить поля описания:

```python
# Description fields (v0.62+)
description: str = ""
short_description: str = ""
describe_model_name: str | None = None
describe_tokens_used: TokensUsed | None = None
describe_cost: float | None = None
describe_processing_time_sec: float | None = None
```

Префикс `describe_` — чтобы не конфликтовать с существующим `model_name` ("deterministic").

### 4. Расширить `StepChunkRequest` в `backend/app/models/schemas.py`

Добавить опциональные поля для формирования промпта описания:

```python
summary: Summary | None = None
longread: Longread | None = None
story: Story | None = None
```

### 5. Обновить chunk endpoint в `backend/app/api/step_routes.py`

После H2-разбиения вызвать генерацию описания:

```python
@router.post("/chunk", response_model=TranscriptChunks)
async def step_chunk(request: StepChunkRequest) -> TranscriptChunks:
    chunks = orchestrator.chunk(request.markdown_content, request.metadata)

    if request.summary or request.longread or request.story:
        generator = DescriptionGenerator(settings)
        desc = await generator.generate(
            request.summary, request.longread, request.story, request.metadata
        )
        chunks.description = desc.description
        chunks.short_description = desc.short_description
        chunks.describe_model_name = desc.model_name
        chunks.describe_tokens_used = desc.tokens_used
        chunks.describe_cost = desc.cost
        chunks.describe_processing_time_sec = desc.processing_time_sec

    return chunks
```

### 6. Упростить `SaveResult` в `backend/app/models/schemas.py`

Убрать description и LLM-метрики — save теперь чистая запись файлов:

```python
class SaveResult(CamelCaseModel):
    files: list[str]
```

### 7. Убрать `description`/`short_description` из `PipelineResults`

Удалить top-level поля `description` и `short_description` из модели `PipelineResults`. Описания живут только в `TranscriptChunks`.

### 8. Обновить `saver.py` — убрать генерацию описаний

**`save_educational()`** и **`save_leadership()`**:
- **Удалить** вызов `_generate_description()` и замер времени
- **Читать** описания из `chunks.description` / `chunks.short_description`
- **Упростить** return: `SaveResult(files=created_files)`

**`_save_pipeline_results_educational/leadership()`**:
- Убрать параметры `description`/`short_description` — описания уже в `chunks` объекте внутри `PipelineResults`

**`_save_chunks_json()`**:
- Читать `description`/`short_description` из `chunks.description` / `chunks.short_description` вместо отдельных параметров

**Удалить методы**: `_generate_description()`, `_build_source_content()` (перенесены в description_generator). `_get_stream_name()` оставить — используется в `_save_chunks_json()`.

### 9. Frontend: типы в `frontend/src/api/types.ts`

**Расширить `TranscriptChunks`:**
```typescript
description?: string;
shortDescription?: string;
describeModelName?: string;
describeTokensUsed?: TokensUsed;
describeCost?: number;
describeProcessingTimeSec?: number;
```

**Расширить `StepChunkRequest`:**
```typescript
summary?: Summary;
longread?: Longread;
story?: Story;
```

**Упростить `SaveResult`:**
```typescript
export interface SaveResult {
  files: string[];
}
```

**Убрать из `PipelineResults`** поля `description?` и `shortDescription?`.

### 10. Frontend: `frontend/src/hooks/usePipelineProcessor.ts`

**Chunk step** (строки 484-506) — передать контекст:
```typescript
const chunks = await stepChunk.mutateAsync({
  markdownContent,
  metadata: data.metadata,
  summary: data.summary,
  longread: data.longread,
  story: data.story,
});
```

**calculateTotals** (строки 629-682) — добавить chunk метрики, убрать saveResult метрики:
```typescript
if (data.chunks) {
  totalTime += data.chunks.describeProcessingTimeSec || 0;
  totalInputTokens += data.chunks.describeTokensUsed?.input || 0;
  totalOutputTokens += data.chunks.describeTokensUsed?.output || 0;
  totalCost += data.chunks.describeCost || 0;
}
// Убрать блок data.saveResult (у save больше нет LLM метрик)
```

### 11. Frontend: `frontend/src/components/results/ChunksView.tsx`

Изменить отображение описаний — два отдельных поля вместо одного блока:

```tsx
{/* Краткое описание */}
{shortDescription && (
  <div className="mb-2 shrink-0">
    <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">Краткое описание</span>
    <p className="text-sm font-medium text-gray-900 mt-0.5">{shortDescription}</p>
  </div>
)}

{/* Описание */}
{description && (
  <div className="mb-3 shrink-0">
    <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">Описание</span>
    <p className="text-xs text-gray-600 leading-relaxed mt-0.5">{description}</p>
  </div>
)}
```

### 12. Frontend: `frontend/src/components/processing/StepByStep.tsx`

Строки 731-735 — описания из chunks:
```tsx
<ChunksView
  chunks={data.chunks}
  description={data.chunks?.description}
  shortDescription={data.chunks?.shortDescription}
/>
```

### 13. Frontend: `frontend/src/components/archive/ArchiveResultsModal.tsx`

Описания из chunks (без fallback):
```tsx
<ChunksView
  chunks={results.chunks}
  description={results.chunks?.description}
  shortDescription={results.chunks?.shortDescription}
/>
```

### 14. Frontend: `frontend/src/components/results/StatisticsView.tsx`

**Chunk step** (строки 182-188) — показать LLM метрики:
```typescript
if (data.chunks) {
  const model = data.chunks.describeModelName;
  steps.push({
    id: 'chunk', name: 'Разбиение на чанки', icon: Layers,
    time: data.chunks.describeProcessingTimeSec,
    model: model || undefined,
    modelType: model && isCloudModel(model) ? 'cloud' : undefined,
    tokens: data.chunks.describeTokensUsed,
    cost: data.chunks.describeCost,
  });
}
```

**Save step** (строки 191-203) — убрать LLM метрики:
```typescript
if (data.saveResult) {
  steps.push({ id: 'save', name: 'Сохранение в архив', icon: Save });
}
```

## Файлы для изменения

| Файл | Что меняется |
|------|-------------|
| `backend/app/services/description_generator.py` | **НОВЫЙ** — извлечённая логика генерации описаний |
| `backend/app/models/schemas.py` | + `DescriptionResult`, расширение `TranscriptChunks`, расширение `StepChunkRequest`, упрощение `SaveResult`, убрать description из `PipelineResults` |
| `backend/app/api/step_routes.py` | Chunk endpoint вызывает description generator |
| `backend/app/services/saver.py` | Удалить `_generate_description()`, читать из chunks, упростить save_* |
| `frontend/src/api/types.ts` | Описания в `TranscriptChunks`, упрощение `SaveResult`, расширение `StepChunkRequest` |
| `frontend/src/hooks/usePipelineProcessor.ts` | Передать summary/longread/story в chunk, обновить totals |
| `frontend/src/components/results/ChunksView.tsx` | Два отдельных поля вместо одного блока |
| `frontend/src/components/processing/StepByStep.tsx` | Описания из chunks |
| `frontend/src/components/archive/ArchiveResultsModal.tsx` | Описания из chunks |
| `frontend/src/components/results/StatisticsView.tsx` | Метрики на chunk, убрать из save |

## Верификация

1. **Деплой** на сервер через `./scripts/deploy.sh`
2. Пошаговая обработка → после шага "Разбиение на чанки":
   - Вкладка **Чанки** показывает blue-блок с описаниями
   - Описания видны ДО нажатия "Сохранить"
3. Нажать "Сохранить" → вкладка **Статистика**:
   - Строка "Разбиение на чанки" показывает модель, токены, стоимость
   - Строка "Сохранение в архив" — без LLM метрик (прочерки)
4. Проверить ошибку Claude: если API недоступен — чанки формируются без описаний (blue-блок не показывается)
