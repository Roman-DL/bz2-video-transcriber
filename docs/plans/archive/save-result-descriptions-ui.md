# План: описание материала на вкладке Чанки + статистика LLM для save

## Контекст

После реализации BZ2-Bot chunk format (v0.60) бэкенд генерирует `description` и `short_description` через Claude при сохранении, но эти данные:
1. Не отображаются на вкладке **Чанки** — пользователь не видит сгенерированные описания
2. Не отражаются на вкладке **Статистика** — строка "Сохранение в архив" показывает прочерки для модели/токенов/стоимости, хотя save вызывает Claude для генерации description

**Корень проблемы:** save endpoint возвращает `list[str]` (только имена файлов). Token usage от `_generate_description()` присваивается переменной `usage`, но никуда не передаётся.

## Изменения

### 1. Backend: модель `SaveResult`
**Файл:** `backend/app/models/schemas.py`

Добавить модель:
```python
class SaveResult(CamelCaseModel):
    files: list[str]
    description: str = ""
    short_description: str = ""
    model_name: str | None = None
    tokens_used: TokensUsed | None = None
    cost: float | None = None
    processing_time_sec: float | None = None
```

### 2. Backend: `saver.py` — возвращать `SaveResult`
**Файл:** `backend/app/services/saver.py`

В `save_educational()` и `save_leadership()`:
- Изменить return type с `list[str]` на `SaveResult`
- Переместить вызов `_generate_description()` перед `_save_pipeline_results_*()`, чтобы описания вошли в pipeline_results.json
- Передать description/short_description в pipeline_results
- Собрать token usage + cost из `_generate_description()` в `SaveResult`
- Замерить время description generation (для `processing_time_sec`)

### 3. Backend: `_save_pipeline_results_*` — добавить описания в JSON
**Файл:** `backend/app/services/saver.py`

Добавить параметры `description` и `short_description` в `_save_pipeline_results_educational()` / `_save_pipeline_results_leadership()`, чтобы они сохранялись в `pipeline_results.json`.

### 4. Backend: `PipelineResults` — добавить поля описания
**Файл:** `backend/app/models/schemas.py`

```python
class PipelineResults(CamelCaseModel):
    ...
    description: str | None = None
    short_description: str | None = None
```

### 5. Backend: `save_stage.py` — обновить return type
**Файл:** `backend/app/services/stages/save_stage.py`

Изменить `execute()` return type с `list[str]` на `SaveResult`.

### 6. Backend: `orchestrator.py` — обновить return type метода `save()`
**Файл:** `backend/app/services/pipeline/orchestrator.py` (строка 458)

Изменить return type с `list[str]` на `SaveResult`.

### 7. Backend: `step_routes.py` — обновить endpoint
**Файл:** `backend/app/api/step_routes.py` (строка 538)

Изменить `response_model=list[str]` на `response_model=SaveResult`.

### 8. Frontend: типы
**Файл:** `frontend/src/api/types.ts`

Добавить `SaveResult`:
```typescript
export interface SaveResult {
  files: string[];
  description: string;
  shortDescription: string;
  modelName?: string;
  tokensUsed?: TokensUsed;
  cost?: number;
  processingTimeSec?: number;
}
```

Добавить `description` / `shortDescription` в `PipelineResults`:
```typescript
export interface PipelineResults {
  ...
  description?: string;
  shortDescription?: string;
}
```

### 9. Frontend: `useSteps.ts` — обновить мутацию save
**Файл:** `frontend/src/api/hooks/useSteps.ts` (строка 233)

Изменить тип ответа с `string[]` на `SaveResult`.

### 10. Frontend: `usePipelineProcessor.ts` — хранить `SaveResult`
**Файл:** `frontend/src/hooks/usePipelineProcessor.ts`

- Изменить `savedFiles?: string[]` на `saveResult?: SaveResult` в `StepData`
- Обновить все места, читающие `savedFiles`:
  - `data.savedFiles` → `data.saveResult?.files`
  - `isComplete` check → `data.saveResult !== undefined`
  - `stepDataKeys` маппинг: `save: ['saveResult']`

### 11. Frontend: `ChunksView.tsx` — отобразить описания
**Файл:** `frontend/src/components/results/ChunksView.tsx`

Добавить опциональные props `description` / `shortDescription`:
```typescript
interface ChunksViewProps {
  chunks: TranscriptChunks;
  description?: string;
  shortDescription?: string;
}
```

Перед списком чанков (после header с метриками) отобразить блок:
- **short_description** — жирный текст, 1-2 строки
- **description** — обычный текст, серый, расширяемый если длинный
- Показывать только если `description` непустой

### 12. Frontend: `StepByStep.tsx` — передать описания в ChunksView
**Файл:** `frontend/src/components/processing/StepByStep.tsx` (строка 731)

Передать `data.saveResult?.description` и `data.saveResult?.shortDescription` в `ChunksView`.

### 13. Frontend: `ArchiveResultsModal.tsx` — передать описания из archive
**Файл:** `frontend/src/components/archive/ArchiveResultsModal.tsx` (строка 331)

Передать `results.description` и `results.shortDescription` в `ChunksView`.

### 14. Frontend: `StatisticsView.tsx` — показать метрики save
**Файл:** `frontend/src/components/results/StatisticsView.tsx`

- Изменить `savedFiles?: string[]` на `saveResult?: SaveResult` в `StatisticsData`
- В `buildStepStats()` для save step: добавить model/tokens/cost из `saveResult`
- Обновить проверку наличия save step: `data.saveResult` вместо `data.savedFiles`

### 15. Frontend: `StepByStep.tsx` — обновить передачу данных в StatisticsView
**Файл:** `frontend/src/components/processing/StepByStep.tsx` (строка 751)

Заменить `savedFiles: data.savedFiles` на `saveResult: data.saveResult`.

### 16. Frontend: `ArchiveResultsModal.tsx` — обновить StatisticsView
**Файл:** `frontend/src/components/archive/ArchiveResultsModal.tsx`

Для archive view нет `SaveResult` — нужно сконструировать его из `PipelineResults` или оставить savedFiles как fallback. Проще всего: StatisticsData поддерживает оба варианта — `saveResult` и legacy `savedFiles`.

## Файлы для изменения

| Файл | Что меняется |
|------|-------------|
| `backend/app/models/schemas.py` | + `SaveResult`, + description в `PipelineResults` |
| `backend/app/services/saver.py` | Return `SaveResult`, реордер description gen |
| `backend/app/services/stages/save_stage.py` | Return type → `SaveResult` |
| `backend/app/services/pipeline/orchestrator.py` | Return type → `SaveResult` |
| `backend/app/api/step_routes.py` | response_model → `SaveResult` |
| `frontend/src/api/types.ts` | + `SaveResult`, + description в `PipelineResults` |
| `frontend/src/api/hooks/useSteps.ts` | Тип ответа save → `SaveResult` |
| `frontend/src/hooks/usePipelineProcessor.ts` | `savedFiles` → `saveResult` |
| `frontend/src/components/results/ChunksView.tsx` | + блок описаний |
| `frontend/src/components/results/StatisticsView.tsx` | Save step метрики |
| `frontend/src/components/processing/StepByStep.tsx` | Прокинуть данные |
| `frontend/src/components/archive/ArchiveResultsModal.tsx` | Прокинуть данные |

## Верификация

1. **Деплой** на сервер через `./scripts/deploy.sh`
2. Запустить пошаговую обработку тестового видео
3. Проверить вкладку **Чанки**: перед списком чанков должны отображаться short_description и description
4. Проверить вкладку **Статистика**: строка "Сохранение в архив" должна показывать модель, токены и стоимость
5. Проверить **Архив**: открыть обработанное видео → вкладки Чанки и Статистика должны отображать описания и метрики
6. Проверить случай ошибки description: если Claude недоступен — save должен работать как раньше (пустые описания, прочерки в статистике)
