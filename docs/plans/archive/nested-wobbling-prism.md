# План реализации: Интеграция слайдов презентаций

## Обзор

Добавление функции извлечения текста со слайдов презентаций для обогащения генерации лонгрида/истории.

**Pipeline со слайдами:**
```
Video + Slides → Parse → Transcribe → Clean → [SLIDES] → Longread/Story → Summary → Chunk → Save
```

Шаг `slides` появляется условно между `clean` и `longread/story` если пользователь прикрепил слайды.

---

## Фаза 1: Backend (v0.51) ✅ DONE

**Реализовано:**
- ✅ `backend/requirements.txt` — добавлен `PyMuPDF>=1.23.0`
- ✅ `backend/app/utils/pdf_utils.py` — `pdf_to_images()`, `pdf_page_count()`
- ✅ `backend/app/services/ai_clients/claude_client.py` — vision API в `chat()`
- ✅ `backend/app/models/schemas.py` — `ProcessingStatus.SLIDES`, `SlideInput`, `SlidesExtractionResult`, `StepSlidesRequest`, `StepLongreadRequest.slides_text`
- ✅ `backend/app/services/slides_extractor.py` — сервис извлечения текста
- ✅ `backend/app/api/step_routes.py` — `POST /api/step/slides`
- ✅ `config/prompts/slides/` — `system.md`, `user.md`
- ✅ `config/models.yaml` — секция `slides` с моделями
- ✅ `backend/app/services/longread_generator.py` — параметр `slides_text`
- ✅ `backend/app/services/pipeline/orchestrator.py` — параметр `slides_text` в `longread()`

### 1.1 Зависимости и утилиты

| Файл | Действие |
|------|----------|
| `backend/requirements.txt` | Добавить `PyMuPDF>=1.23.0` |
| `backend/app/utils/pdf_utils.py` | **Создать** — конвертация PDF в PNG |

### 1.2 Vision API в ClaudeClient

**Файл:** [claude_client.py](backend/app/services/ai_clients/claude_client.py)

Модифицировать метод `chat()` для поддержки multimodal content:
- Принимать `content` как список (vision format)
- Поддержка `{"type": "image", "source": {"type": "base64", ...}}`
- Не ломать существующие text-only вызовы

### 1.3 Модели данных

**Файл:** [schemas.py](backend/app/models/schemas.py)

Добавить:
```python
class ProcessingStatus(str, Enum):
    SLIDES = "slides"  # NEW

class SlideInput(BaseModel):
    filename: str
    content_type: str  # image/jpeg, image/png, application/pdf
    data: str          # base64 encoded

class SlidesExtractionResult(BaseModel):
    extracted_text: str
    slides_count: int
    chars_count: int
    words_count: int
    tables_count: int
    model: str
    tokens_used: TokensUsed | None
    cost: float | None
    processing_time_sec: float | None

class StepSlidesRequest(BaseModel):
    slides: list[SlideInput]
    model: str | None = None
    prompt_overrides: PromptOverrides | None = None
```

Обновить `StepLongreadRequest`:
```python
slides_text: str | None = None  # NEW
```

### 1.4 Сервис извлечения

**Файл:** `backend/app/services/slides_extractor.py` — **Создать**

- Конвертация PDF → PNG через pdf_utils
- Батчинг по 5 слайдов (управление контекстом)
- Вызов ClaudeClient.chat() с vision content
- Сбор метрик (tokens, cost, time)

### 1.5 API Endpoint

**Файл:** [step_routes.py](backend/app/api/step_routes.py)

Добавить:
```python
@router.post("/slides")
async def step_slides(request: StepSlidesRequest) -> StreamingResponse:
    # SSE progress + SlidesExtractionResult
```

### 1.6 Интеграция в Longread

**Файл:** [longread_generator.py](backend/app/services/longread_generator.py)

Добавить параметр `slides_text: str | None` в `generate()`:
```python
if slides_text:
    context += "\n\n## Дополнительная информация со слайдов\n\n" + slides_text
```

### 1.7 Промпты

**Создать:**
- `config/prompts/slides/system.md` — роль и правила извлечения
- `config/prompts/slides/user.md` — инструкции по извлечению

### 1.8 Конфигурация моделей

**Файл:** [models.yaml](config/models.yaml)

Добавить секцию:
```yaml
slides:
  default: claude-haiku-4-5
  available:
    - claude-haiku-4-5   # быстро, дешево
    - claude-sonnet-4-5  # баланс
    - claude-opus-4-5    # качество
```

---

## Фаза 2: Frontend — Главный экран (v0.52) ✅ DONE

**Реализовано:**
- ✅ `frontend/src/api/types.ts` — `SlideFile`, `SlideInput`, `SlidesExtractionResult`, `StepSlidesRequest`, `SLIDES_LIMITS`
- ✅ `frontend/src/components/slides/SlidesAttachment.tsx` — компонент в карточке (кнопка/счётчик)
- ✅ `frontend/src/components/slides/SlidesModal.tsx` — модалка с drag & drop, превью сеткой, валидацией
- ✅ `frontend/src/components/inbox/VideoItem.tsx` — интеграция SlidesAttachment
- ✅ `frontend/src/components/inbox/InboxList.tsx` — управление slidesMap state, рендер SlidesModal
- ✅ `frontend/src/components/processing/ProcessingModal.tsx` — проброс slides в StepByStep
- ✅ `frontend/src/components/processing/StepByStep.tsx` — props `initialSlides`, badge слайдов в header
- ✅ `frontend/src/App.tsx` — обновлена сигнатура handleProcessVideo

### 2.1 TypeScript типы

**Файл:** [types.ts](frontend/src/api/types.ts)

Добавить:
```typescript
interface SlideFile {
  id: string;
  name: string;
  size: number;
  type: 'image' | 'pdf';
  file?: File;
  preview?: string;
}

interface SlidesExtractionResult { ... }
interface StepSlidesRequest { ... }
```

### 2.2 Компоненты слайдов

**Создать:**
- `frontend/src/components/slides/SlidesModal.tsx` — модалка загрузки (drag & drop, превью, удаление)
- `frontend/src/components/slides/SlidesAttachment.tsx` — компонент в карточке

Референс: [SlidesPrototype.jsx](docs/reference/SlidesPrototype.jsx) (строки 114-359)

### 2.3 Интеграция в InboxCard

**Файл:** [VideoItem.tsx](frontend/src/components/inbox/VideoItem.tsx)

- Добавить state для слайдов
- Добавить `<SlidesAttachment />` после info секции
- Добавить `<SlidesModal />` с условным рендером

---

## Фаза 3: Frontend — Пошаговый режим (v0.53) ✅ DONE

**Реализовано:**
- ✅ `frontend/src/api/hooks/useSteps.ts` — `useStepSlides` hook
- ✅ `frontend/src/api/types.ts` — `slides` в PipelineStep, `slides_text` в requests
- ✅ `frontend/src/components/results/SlidesResultView.tsx` — компонент результата
- ✅ `frontend/src/components/processing/StepByStep.tsx` — полная интеграция slides step
- ✅ `backend/app/models/schemas.py` — `slides_text` в StepStoryRequest
- ✅ `backend/app/services/story_generator.py` — slides_text параметр
- ✅ `backend/app/services/pipeline/orchestrator.py` — slides_text в story()
- ✅ `backend/app/api/step_routes.py` — slides_text в story endpoint
- ✅ `frontend/nginx.conf` — `client_max_body_size 150M` для загрузки слайдов (base64)

### 3.1 API Hook

**Файл:** [useSteps.ts](frontend/src/api/hooks/useSteps.ts)

Добавить:
```typescript
export const useStepSlides = createStepWithProgress<
  SlidesExtractionResult,
  StepSlidesRequest
>('/api/step/slides');
```

### 3.2 Result View

**Создать:** `frontend/src/components/results/SlidesResultView.tsx`
- Header с метриками (slides_count, chars, tables, time)
- Markdown content (extracted_text)
- Footer с tokens и cost

### 3.3 Условный шаг в pipeline

**Файл:** [StepByStep.tsx](frontend/src/components/processing/StepByStep.tsx)

Изменения:
1. Props: добавить `initialSlides?: SlideFile[]`
2. Динамический pipeline:
```typescript
const pipelineSteps = useMemo(() => {
  const base = contentType === 'leadership' ? LEADERSHIP_STEPS : EDUCATIONAL_STEPS;
  if (initialSlides?.length > 0) {
    const idx = base.indexOf(contentType === 'leadership' ? 'story' : 'longread');
    return [...base.slice(0, idx), 'slides', ...base.slice(idx)];
  }
  return base;
}, [contentType, initialSlides]);
```
3. Добавить в `STEP_LABELS`: `slides: 'Извлечение слайдов'`
4. Добавить в `STEP_ICONS`: `slides: Layers`
5. Добавить case для `slides` в `runStep()`
6. Добавить `SlidesResultView` в табы

---

## Фаза 4: Сохранение и архив (v0.54) ✅ DONE

**Реализовано:**
- ✅ `backend/app/services/saver.py` — добавлен параметр `slides_extraction` в `save_educational()`, `save_leadership()`, и методы сохранения pipeline results
- ✅ `frontend/src/api/types.ts` — добавлен `slides_extraction` в `PipelineResults`
- ✅ `frontend/src/components/archive/ArchiveResultsModal.tsx` — добавлен таб "Слайды" с `SlidesResultView`

### 4.1 Сохранение slides_extraction в pipeline_results.json

**Файл:** [saver.py](backend/app/services/saver.py)

Обновить методы сохранения:
```python
async def save_educational(..., slides_extraction: SlidesExtractionResult | None = None)
async def save_leadership(..., slides_extraction: SlidesExtractionResult | None = None)

def _save_pipeline_results_educational(...):
    data = {
        # ... existing ...
        "slides_extraction": slides_extraction.model_dump() if slides_extraction else None,
    }
```

### 4.2 Отображение в архиве

**Файл:** [ArchiveResultsModal.tsx](frontend/src/components/archive/ArchiveResultsModal.tsx)

Изменения:
1. Добавить `'slides'` в `ResultTab` type
2. Добавить в `TAB_ICONS`: `slides: Layers`
3. Добавить в `TAB_LABELS`: `slides: 'Слайды'`
4. Обновить `getAvailableTabs()`:
```typescript
if (results.slides_extraction) tabs.push('slides');
```
5. Добавить render блок для `activeTab === 'slides'`

**Файл:** [types.ts](frontend/src/api/types.ts)

Обновить `PipelineResults`:
```typescript
export interface PipelineResults {
  // ... existing ...
  slides_extraction?: SlidesExtractionResult;  // NEW
}
```

### 4.3 View компонент для архива

**Создать:** `frontend/src/components/results/SlidesExtractionView.tsx`
- Статистика (слайдов, символов, таблиц)
- Extracted markdown текст
- ResultFooter с метриками

---

## Фаза 5: Документация (v0.55)

### 5.1 Обновить CLAUDE.md

**Файл:** [CLAUDE.md](CLAUDE.md)

Добавить секцию про слайды:
- Описание SlidesStage
- Конфигурация slides в models.yaml
- Формат промптов slides/

### 5.2 Создать ADR

**Создать:** `docs/adr/007-slides-integration.md`
- Контекст и решение
- Архитектура vision API
- Примеры использования

### 5.3 Обновить data-formats.md

**Файл:** [data-formats.md](docs/data-formats.md)

Добавить:
- Формат SlidesExtractionResult
- Метрики для слайдов

### 5.4 Обновить pipeline docs

**Файл:** [stages.md](docs/pipeline/stages.md)

Добавить документацию по SlidesStage:
- Зависимости
- Условное выполнение
- Параметры

---

## Критические файлы для изменения

| Файл | Приоритет | Изменения |
|------|-----------|-----------|
| [claude_client.py](backend/app/services/ai_clients/claude_client.py) | **Высокий** | Vision API support |
| [schemas.py](backend/app/models/schemas.py) | **Высокий** | Slides-модели |
| [step_routes.py](backend/app/api/step_routes.py) | **Высокий** | Новый endpoint |
| [saver.py](backend/app/services/saver.py) | **Высокий** | Сохранение slides_extraction |
| [longread_generator.py](backend/app/services/longread_generator.py) | Средний | slides_text param |
| [StepByStep.tsx](frontend/src/components/processing/StepByStep.tsx) | Средний | Условный шаг |
| [VideoItem.tsx](frontend/src/components/inbox/VideoItem.tsx) | Средний | Slides UI |
| [ArchiveResultsModal.tsx](frontend/src/components/archive/ArchiveResultsModal.tsx) | Средний | Таб слайдов |
| [types.ts](frontend/src/api/types.ts) | Средний | PipelineResults + slides |

---

## Верификация

### Backend (после фазы 1)

```bash
# 1. Тест PDF конвертации
python -m app.utils.pdf_utils

# 2. Тест endpoint через curl
curl -X POST http://100.64.0.1:8801/api/step/slides \
  -H "Content-Type: application/json" \
  -d '{"slides": [{"filename": "test.jpg", "content_type": "image/jpeg", "data": "...base64..."}]}'

# 3. Проверить SSE прогресс
```

### Frontend (после фаз 2-3)

1. Открыть inbox → нажать "Добавить слайды" → drag & drop файлов
2. Проверить превью в модалке
3. Запустить пошаговую обработку → проверить появление шага "slides"
4. Проверить SlidesResultView с метриками
5. Проверить что slides_text попадает в longread

### Архив (после фазы 4)

1. Обработать видео со слайдами до конца (Save)
2. Открыть архив → найти обработанный файл
3. Проверить появление таба "Слайды"
4. Проверить отображение extracted_text и метрик
5. Проверить что slides_extraction сохранён в pipeline_results.json

---

## Ограничения

| Параметр | Лимит | Причина |
|----------|-------|---------|
| Макс. файлов | 50 | Контекст модели |
| Макс. размер файла | 10 MB | API ограничение |
| Общий размер | 100 MB | Память браузера |
| Batch size | 5 слайдов | Управление контекстом |
