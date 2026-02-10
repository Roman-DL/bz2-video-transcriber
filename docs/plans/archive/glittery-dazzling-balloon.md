# План реализации вкладки "Статистика"

## Цель
Добавить вкладку "Статистика" для отображения итоговых метрик обработки видео в пошаговом режиме и просмотре архива.

---

## Архитектура

### Подход
**Чистая архитектура** — унифицированная структура данных на бэкенде и фронтенде.

1. **Backend**: Pydantic модели сериализуются в camelCase (через `alias_generator`)
2. **Frontend**: `StepData` и `PipelineResults` имеют идентичную структуру
3. **Компоненты**: работают с единым интерфейсом, без преобразований

```
Backend (Pydantic)                    Frontend (TypeScript)
─────────────────                    ────────────────────
PipelineResults ─── JSON (camelCase) ──→ PipelineResults
     │                                        │
     │                                        ↓
     │                               StepData (идентичная структура)
     ↓
pipeline_results.json (camelCase)
```

---

## Файлы для изменения

| Файл | Изменения |
|------|-----------|
| `backend/app/models/schemas.py` | camelCase сериализация (alias_generator) |
| `frontend/src/api/types.ts` | Унификация PipelineResults → camelCase |
| `frontend/src/hooks/usePipelineProcessor.ts` | Переименование slidesResult → slidesExtraction |
| `frontend/src/components/results/StatisticsView.tsx` | **Новый** — компонент вкладки |
| `frontend/src/components/processing/StepByStep.tsx` | Добавить вкладку + автопереключение |
| `frontend/src/components/processing/CompletionCard.tsx` | Убрать метрики (оставить файлы) |
| `frontend/src/components/archive/ArchiveResultsModal.tsx` | Добавить вкладку |
| `docs/adr/011-camelcase-api-serialization.md` | **Новый** — ADR |
| `CLAUDE.md` | Обновить секцию форматов данных |

---

## Этапы реализации

### Этап 0: Унификация структур данных

#### Backend (schemas.py)

Добавить camelCase сериализацию через `alias_generator`:

```python
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

# Базовый класс для всех моделей с API-выводом
class CamelCaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # принимает и camelCase и snake_case
    )

# Применить к моделям результатов:
class RawTranscript(CamelCaseModel): ...
class CleanedTranscript(CamelCaseModel): ...
class SlidesExtractionResult(CamelCaseModel): ...
class Longread(CamelCaseModel): ...
class Summary(CamelCaseModel): ...
class Story(CamelCaseModel): ...
class PipelineResults(CamelCaseModel): ...
```

**Результат:** `pipeline_results.json` будет в camelCase:
```json
{
  "rawTranscript": { "processingTimeSec": 23.5, ... },
  "cleanedTranscript": { "tokensUsed": { ... }, "modelName": "..." },
  "slidesExtraction": { ... },
  "createdAt": "2026-01-23T..."
}
```

#### Frontend (api/types.ts)

Обновить `PipelineResults` на camelCase (станет идентичен StepData):

```typescript
export interface PipelineResults {
  version: string;
  createdAt: string;  // было created_at
  contentType?: ContentType;
  metadata: VideoMetadata;
  rawTranscript?: RawTranscript;       // было raw_transcript
  displayText?: string;
  cleanedTranscript?: CleanedTranscript; // было cleaned_transcript
  chunks?: TranscriptChunks;
  longread?: Longread;
  summary?: Summary;
  story?: Story;
  slidesExtraction?: SlidesExtractionResult; // было slides_extraction
}
```

**Также переименовать в StepData:**
- `slidesResult` → `slidesExtraction` (для консистентности)

**Затронутые файлы:**
- `usePipelineProcessor.ts` (StepData interface + использования)
- `StepByStep.tsx` (использования)

**Результат:** `PipelineResults` и `StepData` полностью идентичны, компоненты работают без преобразований.

---

### Этап 1: Компонент StatisticsView

**Файл:** `frontend/src/components/results/StatisticsView.tsx`

**Props (унифицированные, работают с обоими источниками):**
```typescript
interface StatisticsViewProps {
  // Данные этапов (идентичные для StepData и PipelineResults)
  rawTranscript?: RawTranscript;
  cleanedTranscript?: CleanedTranscript;
  slidesExtraction?: SlidesExtractionResult;
  longread?: Longread;
  summary?: Summary;
  story?: Story;
  // Мета
  pipelineSteps: PipelineStep[];
  processedAt?: string;
}
```

**Вызов из StepByStep (StepData):**
```typescript
<StatisticsView
  rawTranscript={data.rawTranscript}
  cleanedTranscript={data.cleanedTranscript}
  slidesExtraction={data.slidesExtraction}  // единое имя!
  longread={data.longread}
  summary={data.summary}
  story={data.story}
  pipelineSteps={pipelineSteps}
/>
```

**Вызов из ArchiveResultsModal (PipelineResults):**
```typescript
<StatisticsView
  rawTranscript={results.rawTranscript}       // теперь camelCase!
  cleanedTranscript={results.cleanedTranscript}
  slidesExtraction={results.slidesExtraction}
  longread={results.longread}
  summary={results.summary}
  story={results.story}
  pipelineSteps={derivedPipelineSteps}
  processedAt={results.createdAt}
/>
```

**Внутренняя логика (helper внутри компонента):**
```typescript
function getStepMetrics(step: PipelineStep, props: StatisticsViewProps) {
  switch (step) {
    case 'transcribe':
      return {
        time: props.rawTranscript?.processing_time_sec,
        model: props.rawTranscript?.whisper_model,
        modelType: 'local' as const,
        tokens: null,
        cost: null,
      };
    case 'clean':
      return {
        time: props.cleanedTranscript?.processing_time_sec,
        model: props.cleanedTranscript?.model_name,
        modelType: getModelType(props.cleanedTranscript?.model_name),
        tokens: props.cleanedTranscript?.tokens_used,
        cost: props.cleanedTranscript?.cost,
      };
    // ... slides, longread, summarize, story
    default:
      return { time: null, model: null, modelType: null, tokens: null, cost: null };
  }
}

function getModelType(model?: string): 'cloud' | 'local' | null {
  if (!model) return null;
  return model.includes('claude') ? 'cloud' : 'local';
}
```

**Структура UI:**
```
┌────────────────────────────────────────────────┐
│ [📊] Статистика обработки                       │
│      📅 22.01.2026 14:35:22 (если есть)        │
├────────────────────────────────────────────────┤
│ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│ │ ⏱ Время  │ │ ✨Токены │ │ 💰Стоим. │         │
│ │  1м 45с  │ │ 62K/6.8K │ │  $0.28   │         │
│ └──────────┘ └──────────┘ └──────────┘         │
│                                                │
│ Детализация по этапам                          │
│ ┌─────────┬────────────────┬─────┬──────┬────┐ │
│ │ Этап    │ Модель         │Время│Токены│ $  │ │
│ ├─────────┼────────────────┼─────┼──────┼────┤ │
│ │Трансриб.│🖥 large-v3     │ 23с │  —   │ —  │ │
│ │Очистка  │☁ claude-sonnet │ 20с │23K/2K│$0.1│ │
│ │...      │                │     │      │    │ │
│ ├─────────┴────────────────┼─────┼──────┼────┤ │
│ │ ИТОГО                    │1м45с│62K/7K│$0.3│ │
│ └──────────────────────────┴─────┴──────┴────┘ │
└────────────────────────────────────────────────┘
```

**Стилизация:**
- Summary cards: gradient backgrounds (blue→indigo, violet→purple, emerald→teal)
- Таблица: hover-эффекты
- Cloud модель: иконка Cloud (violet), Local: иконка Server (emerald)
- Footer таблицы: bg-stone-100, border-t-2, font-semibold
- **Таб статистики: violet** (отличается от blue остальных)

---

### Этап 2: Интеграция в StepByStep.tsx

1. **Расширить ResultTab:**
   ```typescript
   type ResultTab = '...' | 'statistics';
   ```

2. **Добавить иконку и лейбл:**
   ```typescript
   import { BarChart3 } from 'lucide-react';

   TAB_ICONS.statistics = BarChart3;
   TAB_LABELS.statistics = 'Статистика';
   ```

3. **Условие доступности (getAvailableTabs):**
   ```typescript
   if (data.savedFiles) tabs.push('statistics');
   ```

4. **Автопереключение после сохранения:**
   ```typescript
   const handleStepComplete = useCallback((step: PipelineStep) => {
     if (step === 'save') {
       switchTab('statistics');
       return;
     }
     const tabForStep = getTabForStep(step);
     if (tabForStep) switchTab(tabForStep);
   }, [switchTab]);
   ```

5. **Violet-стиль для таба:**
   ```typescript
   className={`... ${
     activeTab === tab
       ? tab === 'statistics'
         ? 'text-violet-600 bg-violet-50 border border-violet-200'
         : 'text-blue-600 bg-blue-50 border border-blue-200'
       : '...'
   }`}
   ```

6. **Рендеринг:**
   ```typescript
   {activeTab === 'statistics' && (
     <StatisticsView
       rawTranscript={data.rawTranscript}
       cleanedTranscript={data.cleanedTranscript}
       slidesExtraction={data.slidesExtraction}  // единое имя
       longread={data.longread}
       summary={data.summary}
       story={data.story}
       pipelineSteps={pipelineSteps}
     />
   )}
   ```

---

### Этап 3: Упрощение CompletionCard.tsx

**Убрать:**
- Interface `TotalMetrics`
- Props `totals`
- Блок метрик (строки 48-67)

**Оставить:**
- Заголовок "Успешно сохранено" + количество файлов
- Список файлов (компактный, max-h-32)
- Кнопка "Закрыть"

**Новые props:**
```typescript
interface CompletionCardProps {
  files: string[];
  onClose: () => void;
}
```

---

### Этап 4: Интеграция в ArchiveResultsModal.tsx

**Изменения аналогичны StepByStep:**

1. Добавить 'statistics' в ResultTab
2. Добавить иконку BarChart3 и лейбл "Статистика"
3. Добавить в getAvailableTabs (всегда в конце)
4. Violet-стиль для таба
5. **НЕ менять** начальную вкладку (оставить metadata/summary/longread)

**Рендеринг (без преобразований благодаря унификации!):**
```typescript
{activeTab === 'statistics' && (
  <StatisticsView
    rawTranscript={results.rawTranscript}
    cleanedTranscript={results.cleanedTranscript}
    slidesExtraction={results.slidesExtraction}
    longread={results.longread}
    summary={results.summary}
    story={results.story}
    pipelineSteps={derivedPipelineSteps}
    processedAt={results.createdAt}
  />
)}
```

**Вычисление pipelineSteps для архива:**
```typescript
const derivedPipelineSteps = useMemo(() => {
  const steps: PipelineStep[] = ['parse', 'transcribe', 'clean'];
  if (results.slidesExtraction) steps.push('slides');
  if (results.longread) steps.push('longread');
  if (results.summary) steps.push('summarize');
  if (results.story) steps.push('story');
  steps.push('chunk', 'save');
  return steps;
}, [results]);
```

---

### Этап 5: Документация

#### ADR (docs/adr/011-camelcase-api-serialization.md)

```markdown
# ADR 011: CamelCase сериализация API

## Контекст
Frontend использует camelCase (TypeScript конвенции), backend — snake_case (Python конвенции).
Это приводило к дублированию типов (StepData vs PipelineResults) и логики преобразования.

## Решение
Pydantic модели сериализуются в camelCase через `alias_generator=to_camel`.
Python код продолжает использовать snake_case, JSON вывод — camelCase.

## Последствия
- StepData и PipelineResults имеют идентичную структуру
- Компоненты работают с единым интерфейсом
- Старые pipeline_results.json несовместимы (нужна переобработка файлов)
```

#### Обновить CLAUDE.md

В секции "Форматы данных" добавить:
```markdown
**API сериализация (v0.58+):** JSON API использует camelCase (rawTranscript, cleanedTranscript).
Python код использует snake_case. Преобразование через `alias_generator=to_camel`.
```

---

## Верификация

### Пошаговый режим
1. Обработать educational файл → автопереключение на статистику после save
2. Обработать leadership файл → проверить story вместо longread/summary
3. Обработать файл со слайдами → проверить шаг slides в таблице
4. Проверить violet-стиль таба "Статистика"
5. Проверить CompletionCard без метрик

### Архив
1. Открыть educational запись → вкладка статистики доступна
2. Открыть leadership запись → правильные шаги
3. Начальная вкладка НЕ статистика

---

## Оценка объёма

| Файл | Изменения |
|------|-----------|
| `backend/app/models/schemas.py` | +15 (CamelCaseModel + наследование) |
| `frontend/src/api/types.ts` | ~10 (переименование полей) |
| `frontend/src/hooks/usePipelineProcessor.ts` | ~5 (переименование slidesResult) |
| `frontend/src/components/results/StatisticsView.tsx` | ~150 (новый) |
| `frontend/src/components/processing/StepByStep.tsx` | +25 |
| `frontend/src/components/processing/CompletionCard.tsx` | -20 |
| `frontend/src/components/archive/ArchiveResultsModal.tsx` | +30 |
| `docs/adr/011-camelcase-api-serialization.md` | ~30 (новый) |
| `CLAUDE.md` | +5 |

**Итого:** ~250 строк изменений (выполнимо за одну беседу)

**Бонус унификации:** Убираем дублирование логики преобразования, код становится чище.
