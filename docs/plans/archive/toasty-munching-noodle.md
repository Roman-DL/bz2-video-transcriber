# План: Добавить шаги Longread и Summary в step-by-step режим

## Проблема

В v0.12.0 добавили генерацию лонгрида и конспекта в full pipeline, но step-by-step режим остался со старым 6-шаговым flow:
- Шаг `summarize` возвращает устаревшую модель `VideoSummary`
- Шаг `save` ожидает `VideoSummary` вместо `Longread + Summary`
- Нет отдельного шага для генерации лонгрида

## Важно: Оба режима используют один API

Frontend имеет два режима обработки:
- **Пошаговый** (`autoRun=false`) — ручное выполнение каждого шага
- **Автоматический** (`autoRun=true`) — автоматический запуск всех шагов

Оба режима используют **один и тот же `StepByStep` компонент** и вызывают **одни и те же step API endpoints**. Нет отдельного full pipeline endpoint. Поэтому наши изменения автоматически затронут оба режима.

## Решение

Обновить step API до 7 шагов:
```
parse → transcribe → clean → chunk → longread → summarize → save
```

---

## Backend изменения

### 1. schemas.py — добавить Request модели

**Файл:** `backend/app/models/schemas.py`

Добавить после существующих StepXxxRequest:

```python
class StepLongreadRequest(BaseModel):
    """Request for /step/longread endpoint."""
    chunks: TranscriptChunks
    metadata: VideoMetadata
    outline: TranscriptOutline | None = None
    model: str | None = None

class StepSummarizeRequestV2(BaseModel):
    """Request for updated /step/summarize endpoint (from longread)."""
    longread: Longread
    metadata: VideoMetadata
    model: str | None = None

class StepSaveRequestV2(BaseModel):
    """Request for updated /step/save endpoint."""
    metadata: VideoMetadata
    raw_transcript: RawTranscript
    cleaned_transcript: CleanedTranscript
    chunks: TranscriptChunks
    longread: Longread
    summary: Summary
    audio_path: str | None = None
```

### 2. step_routes.py — добавить /longread endpoint

**Файл:** `backend/app/api/step_routes.py`

Добавить импорты:
```python
from app.models.schemas import (
    Longread, Summary, TranscriptOutline,
    StepLongreadRequest, StepSummarizeRequestV2, StepSaveRequestV2,
)
from app.services.longread_generator import LongreadGenerator
from app.services.summary_generator import SummaryGenerator
```

Добавить endpoint:
```python
@router.post("/longread")
async def step_longread(request: StepLongreadRequest) -> StreamingResponse:
    """Generate longread from chunks with SSE progress."""
    # Use LongreadGenerator.generate(chunks, metadata, outline)
    # Return SSE stream → Longread
```

### 3. step_routes.py — обновить /summarize endpoint

Заменить текущую реализацию (принимала `CleanedTranscript`, возвращала `VideoSummary`):
```python
@router.post("/summarize")
async def step_summarize(request: StepSummarizeRequestV2) -> StreamingResponse:
    """Generate summary (конспект) from longread with SSE progress."""
    # Use SummaryGenerator.generate(longread, metadata)
    # Return SSE stream → Summary (новый формат)
```

### 4. step_routes.py — обновить /save endpoint

```python
@router.post("/save", response_model=list[str])
async def step_save(request: StepSaveRequestV2) -> list[str]:
    """Save all results including longread and summary."""
    # Use FileSaver.save(metadata, raw, cleaned, chunks, longread, summary, audio_path)
```

---

## Frontend изменения

### 5. types.ts — добавить типы Longread и Summary

**Файл:** `frontend/src/api/types.ts`

```typescript
export interface LongreadSection {
  index: number;
  title: string;
  content: string;
  source_chunks: number[];
  word_count: number;
}

export interface Longread {
  video_id: string;
  title: string;
  speaker: string;
  date: string;
  event_type: string;
  stream: string;
  introduction: string;
  sections: LongreadSection[];
  conclusion: string;
  total_sections: number;
  total_word_count: number;
  section: string;
  subsection: string;
  tags: string[];
  access_level: number;
  model_name: string;
}

export interface Summary {
  video_id: string;
  title: string;
  speaker: string;
  date: string;
  essence: string;
  key_concepts: string[];
  practical_tools: string[];
  quotes: string[];
  insight: string;
  actions: string[];
  section: string;
  subsection: string;
  tags: string[];
  access_level: number;
  model_name: string;
}
```

### 6. types.ts — обновить PIPELINE_STEPS и STEP_LABELS

```typescript
export const PIPELINE_STEPS = [
  'parse',
  'transcribe',
  'clean',
  'chunk',
  'longread',   // NEW
  'summarize',
  'save',
] as const;

export const STEP_LABELS: Record<PipelineStep, string> = {
  parse: 'Парсинг метаданных',
  transcribe: 'Транскрипция (Whisper)',
  clean: 'Очистка текста',
  chunk: 'Разбиение на чанки',
  longread: 'Генерация лонгрида',   // NEW
  summarize: 'Генерация конспекта', // Updated
  save: 'Сохранение в архив',
};
```

### 7. types.ts — добавить Request типы

```typescript
export interface StepLongreadRequest {
  chunks: TranscriptChunks;
  metadata: VideoMetadata;
  outline?: TranscriptOutline;
  model?: string;
}

export interface StepSummarizeRequestV2 {
  longread: Longread;
  metadata: VideoMetadata;
  model?: string;
}

export interface StepSaveRequestV2 {
  metadata: VideoMetadata;
  raw_transcript: RawTranscript;
  cleaned_transcript: CleanedTranscript;
  chunks: TranscriptChunks;
  longread: Longread;
  summary: Summary;
  audio_path?: string;
}
```

### 8. useSteps.ts — добавить useStepLongread

**Файл:** `frontend/src/api/hooks/useSteps.ts`

```typescript
export const useStepLongread = createStepWithProgress<Longread, StepLongreadRequest>(
  '/api/step/longread'
);
```

### 9. useSteps.ts — обновить useStepSummarize и useStepSave

```typescript
export const useStepSummarize = createStepWithProgress<Summary, StepSummarizeRequestV2>(
  '/api/step/summarize'
);

export function useStepSave() {
  return useMutation({
    mutationFn: async (request: StepSaveRequestV2) => {
      const { data } = await apiClient.post<string[]>('/api/step/save', request);
      return data;
    },
  });
}
```

### 10. LongreadView.tsx — создать компонент отображения

**Файл:** `frontend/src/components/results/LongreadView.tsx`

Компонент для отображения:
- Вступление (introduction)
- Секции (collapsible, с title и word_count)
- Заключение (conclusion)
- Метаданные (section/subsection/tags)

### 11. SummaryView.tsx — обновить для нового формата

**Файл:** `frontend/src/components/results/SummaryView.tsx`

Обновить для отображения новой модели Summary:
- Суть темы (essence)
- Ключевые концепции (key_concepts)
- Инструменты и методы (practical_tools)
- Ключевые цитаты (quotes)
- Главный инсайт (insight)
- Что сделать (actions)

### 12. StepByStep.tsx — интегрировать новый flow

**Файл:** `frontend/src/components/processing/StepByStep.tsx`

Изменения:
1. Добавить `longread?: Longread` в StepData interface
2. Изменить тип `summary` с `VideoSummary` на `Summary`
3. Добавить `stepLongread = useStepLongread()`
4. Обновить `isLoading` — добавить `stepLongread.isPending`
5. Обновить `getCurrentProgress` — добавить case 'longread'
6. Обновить `hasDataForStep`:
   - 'longread': `!!data.chunks && !!data.metadata`
   - 'summarize': `!!data.longread && !!data.metadata`
   - 'save': добавить `!!data.longread`
7. Обновить `runStep`:
   - 'chunk' → setCurrentStep('longread')
   - Добавить case 'longread'
   - 'summarize' принимает longread вместо cleanedTranscript
   - 'save' передаёт longread и summary
8. Добавить CollapsibleCard для longread в JSX
9. Обновить stats для summary (key_concepts.length, quotes.length)

---

## Файлы для изменения

| Файл | Изменения |
|------|-----------|
| `backend/app/models/schemas.py` | +3 Request модели |
| `backend/app/api/step_routes.py` | +1 endpoint, обновить 2 endpoint |
| `frontend/src/api/types.ts` | +Longread, +Summary, +Request типы, обновить PIPELINE_STEPS |
| `frontend/src/api/hooks/useSteps.ts` | +useStepLongread, обновить useStepSummarize/Save |
| `frontend/src/components/results/LongreadView.tsx` | Новый файл |
| `frontend/src/components/results/SummaryView.tsx` | Обновить для нового формата |
| `frontend/src/components/processing/StepByStep.tsx` | Добавить longread шаг |

---

## Проверка

1. Запустить step-by-step обработку видео
2. Проверить что все 7 шагов выполняются корректно
3. Убедиться что longread и summary отображаются в UI
4. Проверить что файлы сохраняются в архив (longread.md, summary.md)
5. Деплой на сервер: `./scripts/deploy.sh`
