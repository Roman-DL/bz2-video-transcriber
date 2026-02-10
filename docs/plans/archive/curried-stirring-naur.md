# План: Исправление сохранения slides_extraction

## Проблема

При обработке видео со слайдами `slides_extraction` не сохраняется в `pipeline_results.json`:
- UI показывает шаг "Извлечение слайдов" ✅
- Слайды обрабатываются через Vision API ✅
- `slides_text` передаётся в longread/story ✅
- **При сохранении `slidesResult` НЕ передаётся** ❌

## Причина

Цепочка передачи данных разорвана в 4 местах:

```
Frontend StepByStep.tsx       slidesResult в state, но НЕ передаётся в save ❌
        ↓
StepSaveRequest (types.ts)    НЕТ поля slides_extraction ❌
        ↓
step_routes.py step_save()    НЕ передаёт slides_extraction ❌
        ↓
orchestrator.save()           НЕТ параметра slides_extraction ❌
        ↓
saver.save_educational()      УЖЕ поддерживает slides_extraction ✅
saver.save_leadership()       УЖЕ поддерживает slides_extraction ✅
```

## Изменения (5 файлов)

### 1. Backend: schemas.py

**Файл:** [schemas.py](backend/app/models/schemas.py) строка ~1098

Добавить поле в `StepSaveRequest`:

```python
# После audio_path (строка ~1098)
slides_extraction: SlidesExtractionResult | None = Field(
    default=None,
    description="Slides extraction result (v0.55+)",
)
```

### 2. Backend: orchestrator.py

**Файл:** [orchestrator.py](backend/app/services/pipeline/orchestrator.py)

**Импорт** (строка ~15-28): добавить `SlidesExtractionResult`

**Метод save()** (строка 457): добавить параметр и передать в saver

```python
async def save(
    self,
    ...
    audio_path: Path | None = None,
    slides_extraction: SlidesExtractionResult | None = None,  # NEW
) -> list[str]:
    ...
    if story is not None:
        return await saver.save_leadership(
            metadata, raw_transcript, cleaned_transcript, chunks,
            story, audio_path, slides_extraction  # NEW
        )
    elif longread is not None and summary is not None:
        return await saver.save_educational(
            metadata, raw_transcript, cleaned_transcript, chunks,
            longread, summary, audio_path, slides_extraction  # NEW
        )
```

### 3. Backend: step_routes.py

**Файл:** [step_routes.py](backend/app/api/step_routes.py) строка 558

Добавить передачу `slides_extraction`:

```python
files = await orchestrator.save(
    ...
    audio_path=audio_path,
    slides_extraction=request.slides_extraction,  # NEW
)
```

### 4. Frontend: types.ts

**Файл:** [types.ts](frontend/src/api/types.ts) строка 290

Добавить поле в `StepSaveRequest`:

```typescript
export interface StepSaveRequest {
  ...
  audio_path?: string;
  slides_extraction?: SlidesExtractionResult;  // NEW v0.55+
}
```

### 5. Frontend: StepByStep.tsx

**Файл:** [StepByStep.tsx](frontend/src/components/processing/StepByStep.tsx) строки 570-591

Добавить `slides_extraction: data.slidesResult` в оба вызова `stepSave.mutateAsync()`:

```typescript
// Leadership (строка ~577)
const savedFilesLeadership = await stepSave.mutateAsync({
  ...
  audio_path: data.audioPath,
  slides_extraction: data.slidesResult,  // NEW
});

// Educational (строка ~589)
const savedFiles = await stepSave.mutateAsync({
  ...
  audio_path: data.audioPath,
  slides_extraction: data.slidesResult,  // NEW
});
```

## Порядок изменений

**Backend:**
1. schemas.py — добавить поле в StepSaveRequest
2. orchestrator.py — добавить импорт и параметр
3. step_routes.py — передать в orchestrator.save()

**Frontend:**
4. types.ts — добавить поле в интерфейс
5. StepByStep.tsx — передать slidesResult

**Документация:**
6. CLAUDE.md — убрать "только в step-by-step"
7. docs/pipeline/stages.md — обновить описание и диаграмму
8. docs/adr/010-slides-integration.md — обновить описание

## Верификация

1. Запустить деплой: `./scripts/deploy.sh`
2. Обработать видео со слайдами (авто или пошагово)
3. Проверить `pipeline_results.json` — должен содержать `slides_extraction`
4. Открыть архив — должен появиться таб "Слайды"

## Обратная совместимость

Все поля опциональные — старые запросы без слайдов работают без изменений.

## Обновление документации (3 файла)

### 6. CLAUDE.md

**Файл:** [CLAUDE.md](CLAUDE.md) строка 343

**Было:**
> Шаг `slides` реализован как отдельный API endpoint (`/api/step/slides`) и не является частью stage абстракции, т.к. выполняется условно **только в step-by-step режиме** при наличии прикреплённых слайдов.

**Стало:**
> Шаг `slides` реализован как отдельный API endpoint (`/api/step/slides`) и не является частью stage абстракции. Выполняется условно при наличии прикреплённых слайдов (работает в обоих режимах: пошаговом и автоматическом).

### 7. docs/pipeline/stages.md

**Файл:** [stages.md](docs/pipeline/stages.md) строки 273-290

**Было:**
```
1. Шаг выполняется **условно** — только если пользователь прикрепил слайды
2. Работает только в **step-by-step режиме** (не в автоматическом pipeline)
3. Требует **multimodal API** (Claude Vision)
```

**Стало:**
```
1. Шаг выполняется **условно** — только если пользователь прикрепил слайды
2. Работает в **обоих режимах** — пошаговом и автоматическом (v0.55+)
3. Требует **multimodal API** (Claude Vision)
```

Также обновить диаграмму — убрать "(Step-by-step Pipeline (Frontend))" заголовок или заменить на просто "Pipeline".

### 8. docs/adr/010-slides-integration.md

**Файл:** [010-slides-integration.md](docs/adr/010-slides-integration.md) строка 31

**Было:**
> Слайды обрабатываются как опциональный шаг в step-by-step режиме

**Стало:**
> Слайды обрабатываются как опциональный шаг в pipeline (v0.55+: работает в обоих режимах)
