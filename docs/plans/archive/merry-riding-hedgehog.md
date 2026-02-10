# План: Удаление Fallback и переход на Claude Sonnet

## Цель

1. Удалить все fallback механизмы для LLM генерации (оставить только duration estimation)
2. Сделать `claude-sonnet-4-5` моделью по умолчанию для всех LLM обработок
3. Добавить отдельный селектор для модели longread в форму настроек
4. Обновить фронтенд и документацию

## Часть 1: Удаление Fallback

### 1.1 Удалить файл fallback_factory.py

**Файл:** `backend/app/services/pipeline/fallback_factory.py`

**Действие:** Удалить полностью

---

### 1.2 Обновить pipeline/__init__.py

**Файл:** `backend/app/services/pipeline/__init__.py`

**Изменения:**
- Удалить строку 7 в docstring: `- fallback_factory: Fallback object creation`
- Удалить строку 37: `from .fallback_factory import FallbackFactory`
- Удалить строку 49: `"FallbackFactory",`

---

### 1.3 Обновить orchestrator.py

**Файл:** `backend/app/services/pipeline/orchestrator.py`

**Изменения:**
1. Удалить импорт `from .fallback_factory import FallbackFactory`
2. Удалить в `__init__`: `self.fallback_factory = FallbackFactory(self.settings)`
3. Метод `longread()`: убрать try/except, заменить на raise PipelineError
4. Метод `summarize_from_cleaned()`: убрать try/except, заменить на raise PipelineError
5. Метод `_do_educational_pipeline()`: убрать fallback для longread и summary, заменить на raise PipelineError

---

### 1.4 Обновить longread_stage.py

**Файл:** `backend/app/services/stages/longread_stage.py`

**Изменения:**
1. Убрать try/except в `execute()`, оставить только `return await self.generator.generate(...)`
2. Удалить метод `_create_fallback_longread()`

---

### 1.5 Обновить summarize_stage.py

**Файл:** `backend/app/services/stages/summarize_stage.py`

**Изменения:**
1. Убрать try/except в `execute()`, оставить только `return await self.generator.generate(...)`
2. Удалить метод `_create_fallback_summary()`

---

### 1.6 Обновить processing_strategy.py

**Файл:** `backend/app/services/pipeline/processing_strategy.py`

**Изменения:**
- Удалить метод `get_client_with_fallback()` — при недоступности модели падать с ошибкой

---

## Часть 2: Claude Sonnet по умолчанию

### 2.1 Обновить config.py

**Файл:** `backend/app/config.py`

**Изменения (строки 18-20):**
```python
# Было:
summarizer_model: str = "qwen2.5:14b"
longread_model: str = "qwen2.5:14b"
cleaner_model: str = "gemma2:9b"

# Станет:
summarizer_model: str = "claude-sonnet-4-5"
longread_model: str = "claude-sonnet-4-5"
cleaner_model: str = "claude-sonnet-4-5"
```

---

### 2.2 Обновить docker-compose.yml

**Файл:** `docker-compose.yml`

**Изменения (строки 17-18):**
```yaml
# Было:
- SUMMARIZER_MODEL=qwen2.5:14b
- CLEANER_MODEL=gemma2:9b

# Станет:
- SUMMARIZER_MODEL=claude-sonnet-4-5
- CLEANER_MODEL=claude-sonnet-4-5
```

---

### 2.3 Обновить models.yaml

**Файл:** `config/models.yaml`

**Изменения:** Убедиться что есть конфиг для `claude-sonnet-4-5` с параметрами для большого контекста

---

## Часть 3: Документация

### 3.1 Создать ADR

**Файл:** `docs/adr/007-remove-fallback-use-claude.md`

**Содержание:** Описание решения, причины, последствия

---

### 3.2 Обновить CLAUDE.md

**Файл:** `CLAUDE.md`

**Изменения:**
- Секция "Конфигурация моделей": обновить таблицу defaults
- Секция "AI Clients": удалить упоминание `get_client_with_fallback()`
- Секция "Ключевые настройки": обновить значения

---

### 3.3 Обновить docs/configuration.md

**Файл:** `docs/configuration.md`

**Изменения:** Обновить таблицу defaults моделей

---

### 3.4 Обновить docs/pipeline/stages.md

**Файл:** `docs/pipeline/stages.md`

**Изменения:** Удалить пример fallback логики в секции "Обработка ошибок"

---

## Часть 4: Фронтенд — добавить селектор Longread

### 4.1 Обновить types.ts

**Файл:** `frontend/src/api/types.ts`

**Изменения:**

1. `DefaultModelsResponse` (строка 350-354):
```typescript
// Было:
export interface DefaultModelsResponse {
  transcribe: string;
  clean: string;
  summarize: string;
}

// Станет:
export interface DefaultModelsResponse {
  transcribe: string;
  clean: string;
  longread: string;
  summarize: string;
}
```

2. `ModelSettings` (строка 380-384):
```typescript
// Было:
export interface ModelSettings {
  transcribe?: string;
  clean?: string;
  summarize?: string;
}

// Станет:
export interface ModelSettings {
  transcribe?: string;
  clean?: string;
  longread?: string;
  summarize?: string;
}
```

---

### 4.2 Обновить models_routes.py (backend)

**Файл:** `backend/app/api/models_routes.py`

**Изменения в endpoint `/default` (строка 118-122):**
```python
# Было:
return {
    "transcribe": transcribe_model,
    "clean": settings.cleaner_model,
    "summarize": settings.summarizer_model,
}

# Станет:
return {
    "transcribe": transcribe_model,
    "clean": settings.cleaner_model,
    "longread": settings.longread_model,
    "summarize": settings.summarizer_model,
}
```

---

### 4.3 Обновить SettingsModal.tsx

**Файл:** `frontend/src/components/settings/SettingsModal.tsx`

**Изменения:**

1. `PipelineStage` (строка 10):
```typescript
// Было:
type PipelineStage = 'transcribe' | 'clean' | 'summarize';

// Станет:
type PipelineStage = 'transcribe' | 'clean' | 'longread' | 'summarize';
```

2. `STAGE_LABELS` (строка 12-16):
```typescript
// Было:
const STAGE_LABELS: Record<PipelineStage, string> = {
  transcribe: 'Транскрипция',
  clean: 'Очистка',
  summarize: 'Суммаризация',
};

// Станет:
const STAGE_LABELS: Record<PipelineStage, string> = {
  transcribe: 'Транскрипция',
  clean: 'Очистка',
  longread: 'Лонгрид',
  summarize: 'Конспект',
};
```

3. `STAGE_CONFIG_KEYS` (строка 18-22):
```typescript
// Было:
const STAGE_CONFIG_KEYS: Record<PipelineStage, keyof ModelConfig | null> = {
  transcribe: null,
  clean: 'cleaner',
  summarize: null,
};

// Станет:
const STAGE_CONFIG_KEYS: Record<PipelineStage, keyof ModelConfig | null> = {
  transcribe: null,
  clean: 'cleaner',
  longread: null,
  summarize: null,
};
```

4. Добавить новый `ModelSelector` для longread после clean (после строки 254):
```tsx
{/* Longread */}
<ModelSelector
  stage="longread"
  value={localModels.longread}
  defaultValue={defaultModels?.longread || ''}
  options={llmOptions}
  onChange={(v) => handleChange('longread', v)}
  config={getModelConfig(localModels.longread || defaultModels?.longread)}
/>
```

---

### 4.4 Обновить StepByStep.tsx

**Файл:** `frontend/src/components/processing/StepByStep.tsx`

**Изменения:**

Строка 292 — использовать `models.longread` вместо `models.summarize` для longread:
```typescript
// Было:
const longread = await stepLongread.mutate({
  cleaned_transcript: data.cleanedTranscript!,
  metadata: data.metadata!,
  model: models.summarize,
});

// Станет:
const longread = await stepLongread.mutate({
  cleaned_transcript: data.cleanedTranscript!,
  metadata: data.metadata!,
  model: models.longread,
});
```

---

## Порядок выполнения

1. Backend: удалить fallback (файлы 1.1-1.6)
2. Backend: изменить defaults на Claude (файлы 2.1-2.3)
3. Backend: добавить longread в /api/models/default (файл 4.2)
4. Frontend: добавить longread в типы и UI (файлы 4.1, 4.3, 4.4)
5. Docs: создать ADR и обновить документацию (файлы 3.1-3.4)

---

## Верификация

1. **Проверить синтаксис Python:**
   ```bash
   cd backend
   python3 -m py_compile app/services/pipeline/orchestrator.py
   python3 -m py_compile app/services/stages/longread_stage.py
   python3 -m py_compile app/services/stages/summarize_stage.py
   python3 -m py_compile app/api/models_routes.py
   ```

2. **Проверить импорты:**
   ```bash
   cd backend
   python3 -c "from app.services.pipeline import PipelineOrchestrator"
   ```

3. **Проверить TypeScript:**
   ```bash
   cd frontend
   npm run typecheck  # или npx tsc --noEmit
   ```

4. **После деплоя:**
   - Проверить что в UI Settings отображается 4 селектора: Транскрипция, Очистка, Лонгрид, Конспект
   - Проверить что Claude показывается как default для всех LLM этапов
   - Запустить обработку тестового видео и убедиться что используется Claude

---

## Что НЕ удаляется

- `backend/app/utils/media_utils.py` — duration estimation (graceful degradation для UX)
- `backend/app/utils/h2_chunker.py` — детерминированное чанкирование (не LLM)
- `backend/app/services/outline_extractor.py` — промежуточный этап в LongreadGenerator
