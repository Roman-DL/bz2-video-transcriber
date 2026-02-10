# План: Фаза 7 — Step API и UI для промптов (v0.31)

> **Цель:** Добавить возможность выбора модели и вариантов промптов при повторной обработке.

---

## Разбивка на подфазы

| Подфаза | Описание | Файлы | Верификация | Статус |
|---------|----------|-------|-------------|--------|
| **7.1** | Backend: API промптов | config.py, schemas.py, prompts_routes.py, main.py + удалить *_gemma2.md | curl /api/prompts/cleaning | ✅ v0.31 |
| **7.2** | Backend: сервисы | cleaner, generators, orchestrator, step_routes | curl /step/clean с prompt_overrides | ✅ v0.32 |
| **7.3** | Frontend | types, usePrompts, ComponentPromptSelector, StepByStep | UI показывает селекторы | ✅ v0.33 |
| **7.4** | Документация | CLAUDE.md, configuration.md, api-reference.md, etc. | Проверка docs | ✅ v0.34 |

**Каждая подфаза — отдельная беседа. После каждой — деплой и верификация.**

---

## Принцип чистой архитектуры

При реализации изменений:
- **Удалять устаревший код** — не помечать `@deprecated`, а удалять полностью
- **Не сохранять старые сигнатуры** — если параметр больше не нужен, удалить его
- **Не поддерживать обратную совместимость для внутреннего кода** — миграции делаем один раз
- **Переименовывать** — если новое имя точнее отражает назначение

Это позволит эффективнее развивать проект в дальнейшем.

---

## Общая информация

### Компоненты промптов по этапам

| Этап | Компоненты |
|------|------------|
| cleaning | system, user |
| longread | system, instructions, template |
| summary | system, instructions, template |
| story | system, instructions, template |

### Соглашение об именовании файлов

```
config/prompts/{stage}/
├── system.md                         # default
├── system_v2.md                      # вариант
├── system_для_локальных_моделей.md   # вариант
├── user.md                           # default
└── instructions.md                   # default
```

**Логика:** файлы с "system" в имени → системные промпты.

---

# Подфаза 7.1: Backend API промптов

## Файлы для изменения

| Файл | Действие |
|------|----------|
| `config/prompts/cleaning/system_gemma2.md` | Удалить |
| `config/prompts/cleaning/user_gemma2.md` | Удалить |
| `backend/app/config.py` | Упростить load_prompt() |
| `backend/app/models/schemas.py` | Добавить новые модели |
| `backend/app/api/prompts_routes.py` | Создать новый файл |
| `backend/app/main.py` | Зарегистрировать router |

## 1. Удалить model-specific промпты

```bash
rm config/prompts/cleaning/system_gemma2.md
rm config/prompts/cleaning/user_gemma2.md
```

## 2. Упростить load_prompt() (config.py)

```python
def load_prompt(
    stage: str,
    name: str,  # Имя файла без .md: "system", "system_v2"
    settings: Settings | None = None,
) -> str:
    """Load prompt by stage and filename."""
    if settings is None:
        settings = get_settings()

    paths_to_check = []
    if settings.prompts_dir and settings.prompts_dir.exists():
        paths_to_check.append(settings.prompts_dir / stage / f"{name}.md")
    paths_to_check.append(settings.config_dir / "prompts" / stage / f"{name}.md")

    for path in paths_to_check:
        if path.exists():
            return path.read_text(encoding="utf-8")

    raise FileNotFoundError(f"Prompt not found: {stage}/{name}.md")
```

## 3. Новые модели (schemas.py)

```python
class PromptVariantInfo(BaseModel):
    """Information about a prompt file."""
    name: str             # "system", "system_v2"
    source: Literal["external", "builtin"]
    filename: str         # "system_v2.md"

class ComponentPrompts(BaseModel):
    """Variants available for a component."""
    component: str        # "system", "user", "instructions", "template"
    default: str          # "system"
    variants: list[PromptVariantInfo]

class StagePromptsResponse(BaseModel):
    """Response for GET /api/prompts/{stage}."""
    stage: str
    components: list[ComponentPrompts]

class PromptOverrides(BaseModel):
    """Override prompts for a step."""
    system: str | None = None
    user: str | None = None
    instructions: str | None = None
    template: str | None = None
```

## 4. Создать prompts_routes.py

```python
from fastapi import APIRouter, HTTPException
from collections import defaultdict
from app.config import get_settings
from app.models.schemas import PromptVariantInfo, ComponentPrompts, StagePromptsResponse

router = APIRouter(prefix="/api/prompts", tags=["prompts"])

VALID_STAGES = ["cleaning", "longread", "summary", "story"]
STAGE_COMPONENTS = {
    "cleaning": ["system", "user"],
    "longread": ["system", "instructions", "template"],
    "summary": ["system", "instructions", "template"],
    "story": ["system", "instructions", "template"],
}

def get_component_for_file(filename: str, expected_components: set[str]) -> str | None:
    name = filename.removesuffix(".md").lower()
    for comp in expected_components:
        if comp in name:
            return comp
    return None

@router.get("/{stage}", response_model=StagePromptsResponse)
async def get_stage_prompts(stage: str) -> StagePromptsResponse:
    if stage not in VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {stage}")

    settings = get_settings()
    expected_components = set(STAGE_COMPONENTS.get(stage, []))
    variants_by_component: dict[str, list[PromptVariantInfo]] = defaultdict(list)
    seen_files: set[str] = set()

    dirs_to_scan = []
    if settings.prompts_dir:
        dirs_to_scan.append((settings.prompts_dir / stage, "external"))
    dirs_to_scan.append((settings.config_dir / "prompts" / stage, "builtin"))

    for prompt_dir, source in dirs_to_scan:
        if not prompt_dir.exists():
            continue
        for f in prompt_dir.glob("*.md"):
            if f.name in seen_files:
                continue
            seen_files.add(f.name)
            component = get_component_for_file(f.name, expected_components)
            if component:
                variants_by_component[component].append(
                    PromptVariantInfo(name=f.name.removesuffix(".md"), source=source, filename=f.name)
                )

    components = [
        ComponentPrompts(component=comp, default=comp, variants=variants_by_component.get(comp, []))
        for comp in expected_components
    ]
    return StagePromptsResponse(stage=stage, components=components)
```

## 5. Зарегистрировать в main.py

```python
from app.api import prompts_routes
app.include_router(prompts_routes.router)
```

## Верификация подфазы 7.1

```bash
cd backend && source .venv/bin/activate
python -m uvicorn app.main:app --reload --port 8801

# Проверить API
curl http://localhost:8801/api/prompts/cleaning | jq

# Ожидается:
# {"stage":"cleaning","components":[{"component":"system","default":"system","variants":[{"name":"system",...}]},{"component":"user",...}]}

# Проверить что файлы удалены
ls config/prompts/cleaning/
# Ожидается: system.md, user.md (без *_gemma2.md)
```

## ✅ Результаты подфазы 7.1

**Коммит:** `8d8d8f0` — Add prompts API and simplify load_prompt signature (v0.31)

**Изменённые файлы:**
| Файл | Изменение |
|------|-----------|
| `config/prompts/cleaning/system_gemma2.md` | ❌ Удалён |
| `config/prompts/cleaning/user_gemma2.md` | ❌ Удалён |
| `backend/app/config.py` | Новая сигнатура `load_prompt(stage, name, settings)` |
| `backend/app/models/schemas.py` | Добавлены `PromptVariantInfo`, `ComponentPrompts`, `StagePromptsResponse`, `PromptOverrides` |
| `backend/app/api/prompts_routes.py` | ✨ Создан — `GET /api/prompts/{stage}` |
| `backend/app/main.py` | Зарегистрирован `prompts_routes.router` |
| `backend/app/services/cleaner.py` | Обновлён на новую сигнатуру |
| `backend/app/services/longread_generator.py` | Обновлён на новую сигнатуру |
| `backend/app/services/summary_generator.py` | Обновлён на новую сигнатуру |
| `backend/app/services/story_generator.py` | Обновлён на новую сигнатуру |
| `backend/app/services/outline_extractor.py` | Обновлён на новую сигнатуру |
| `backend/app/services/summarizer.py` | Обновлён (deprecated class) |
| `frontend/package.json` | version → 0.31.0 |

**Дополнительные изменения (не в плане):**
- Обновлены все вызовы `load_prompt()` во всех сервисах на новую сигнатуру
- `VideoSummarizer` помечен как deprecated (не используется в production)

**Следующий шаг:** Деплой и верификация на сервере

---

# Подфаза 7.2: Backend сервисы

## Файлы для изменения

| Файл | Действие |
|------|----------|
| `backend/app/models/schemas.py` | Добавить prompt_overrides в Step*Request |
| `backend/app/services/cleaner.py` | Добавить prompt_overrides в конструктор |
| `backend/app/services/longread_generator.py` | Добавить prompt_overrides |
| `backend/app/services/summary_generator.py` | Добавить prompt_overrides |
| `backend/app/services/story_generator.py` | Добавить prompt_overrides |
| `backend/app/services/outline_extractor.py` | Убрать model в load_prompt |
| `backend/app/services/pipeline/orchestrator.py` | Добавить prompt_overrides в методы |
| `backend/app/api/step_routes.py` | Пробросить prompt_overrides |

## 1. Обновить Step*Request (schemas.py)

```python
class StepCleanRequest(BaseModel):
    raw_transcript: RawTranscript
    metadata: VideoMetadata
    model: str | None = None
    prompt_overrides: PromptOverrides | None = None  # NEW

# Аналогично для StepLongreadRequest, StepSummarizeRequest, StepStoryRequest
```

## 2. Обновить генераторы

### cleaner.py
```python
def __init__(self, ai_client, settings, prompt_overrides: PromptOverrides | None = None):
    overrides = prompt_overrides or PromptOverrides()
    self.system_prompt = load_prompt("cleaning", overrides.system or "system", settings)
    self.user_template = load_prompt("cleaning", overrides.user or "user", settings)
```

### longread_generator.py, summary_generator.py, story_generator.py
```python
def __init__(self, ai_client, settings, prompt_overrides: PromptOverrides | None = None):
    overrides = prompt_overrides or PromptOverrides()
    self.system_prompt = load_prompt("{stage}", overrides.system or "system", settings)
    self.instructions = load_prompt("{stage}", overrides.instructions or "instructions", settings)
    self.template = load_prompt("{stage}", overrides.template or "template", settings)
```

### outline_extractor.py
```python
self.prompt_template = load_prompt("outline", "map", settings)  # ✅ уже обновлено в 7.1
```

## 3. Обновить orchestrator.py

```python
async def clean(self, raw_transcript, metadata, model=None, prompt_overrides=None):
    settings = self.config_resolver.with_model(model, "cleaner")
    actual_model = model or settings.cleaner_model
    async with self.processing_strategy.create_client(actual_model) as ai_client:
        cleaner = TranscriptCleaner(ai_client, settings, prompt_overrides=prompt_overrides)
        return await cleaner.clean(raw_transcript, metadata)

# Аналогично для longread(), summarize_from_cleaned(), story()
```

## 4. Обновить step_routes.py

```python
operation=lambda: orchestrator.clean(
    raw_transcript=request.raw_transcript,
    metadata=request.metadata,
    model=request.model,
    prompt_overrides=request.prompt_overrides,  # NEW
),
```

## Верификация подфазы 7.2

```bash
# Тест API с prompt_overrides
curl -X POST http://localhost:8801/api/step/clean \
  -H "Content-Type: application/json" \
  -d '{"raw_transcript":{"text":"test"},"metadata":{...},"prompt_overrides":{"system":"system_v2"}}'

# Проверить логи что загружается system_v2.md
```

## ✅ Результаты подфазы 7.2

**Изменённые файлы:**
| Файл | Изменение |
|------|-----------|
| `backend/app/models/schemas.py` | Добавлен `prompt_overrides: PromptOverrides | None` в StepCleanRequest, StepLongreadRequest, StepSummarizeRequest, StepStoryRequest |
| `backend/app/services/cleaner.py` | `__init__` принимает `prompt_overrides`, загружает промпты с override |
| `backend/app/services/longread_generator.py` | `__init__` принимает `prompt_overrides` |
| `backend/app/services/summary_generator.py` | `__init__` принимает `prompt_overrides` |
| `backend/app/services/story_generator.py` | `__init__` принимает `prompt_overrides` |
| `backend/app/services/pipeline/orchestrator.py` | Методы `clean()`, `longread()`, `summarize_from_cleaned()`, `story()` принимают `prompt_overrides` |
| `backend/app/api/step_routes.py` | Пробрасывает `request.prompt_overrides` в orchestrator |

**Логика работы:**
- `prompt_overrides=None` → текущее поведение (загружаются defaults)
- `prompt_overrides.system="system_v2"` → загружается `config/prompts/{stage}/system_v2.md`
- Каждый компонент (system, user, instructions, template) может быть переопределён отдельно

**Следующий шаг:** Деплой и верификация на сервере

---

# Подфаза 7.3: Frontend

## Файлы для изменения

| Файл | Действие |
|------|----------|
| `frontend/src/api/types.ts` | Новые типы |
| `frontend/src/api/hooks/usePrompts.ts` | Новый файл |
| `frontend/src/components/settings/ComponentPromptSelector.tsx` | Новый файл |
| `frontend/src/components/processing/StepByStep.tsx` | Добавить селекторы |
| `frontend/package.json` | version → 0.31.0 |

## 1. Типы (api/types.ts)

```typescript
export interface PromptVariantInfo {
  name: string;
  source: 'external' | 'builtin';
  filename: string;
}

export interface ComponentPrompts {
  component: string;
  default: string;
  variants: PromptVariantInfo[];
}

export interface StagePromptsResponse {
  stage: string;
  components: ComponentPrompts[];
}

export interface PromptOverrides {
  system?: string;
  user?: string;
  instructions?: string;
  template?: string;
}

// Обновить Step*Request
export interface StepCleanRequest {
  raw_transcript: RawTranscript;
  metadata: VideoMetadata;
  model?: string;
  prompt_overrides?: PromptOverrides;
}
```

## 2. API hook (usePrompts.ts)

```typescript
export function useStagePrompts(stage: string, enabled = true) {
  return useQuery<StagePromptsResponse>({
    queryKey: ['prompts', stage],
    queryFn: () => fetch(`/api/prompts/${stage}`).then(r => r.json()),
    enabled,
    staleTime: 5 * 60 * 1000,
  });
}
```

## 3. ComponentPromptSelector.tsx

```tsx
export function ComponentPromptSelector({ label, componentData, value, onChange }) {
  if (componentData.variants.length <= 1) return null;

  return (
    <div className="space-y-1">
      <label className="text-xs text-gray-500">{label}</label>
      <select
        value={value || componentData.default}
        onChange={(e) => onChange(e.target.value === componentData.default ? undefined : e.target.value)}
        className="w-full text-sm border rounded px-2 py-1"
      >
        {componentData.variants.map((v) => (
          <option key={v.name} value={v.name}>
            {v.name}{v.name === componentData.default ? ' (по умолчанию)' : ''}
          </option>
        ))}
      </select>
    </div>
  );
}
```

## 4. StepByStep.tsx — добавить селекторы

- Добавить useStagePrompts() для каждого этапа
- Добавить локальный state для stepPromptOverrides
- Показывать ComponentPromptSelector для каждого компонента
- Передавать prompt_overrides в API

## Верификация подфазы 7.3

```bash
cd frontend && npm run dev

# 1. Открыть Step-by-Step
# 2. Проверить что селекторы НЕ показываются (только один вариант)
# 3. Создать /data/prompts/cleaning/system_v2.md на сервере
# 4. Перезагрузить — должен появиться селектор
# 5. Выбрать system_v2, запустить — проверить Network tab
```

## ✅ Результаты подфазы 7.3

**Изменённые файлы:**
| Файл | Изменение |
|------|-----------|
| `frontend/src/api/types.ts` | Добавлены типы `PromptVariantInfo`, `ComponentPrompts`, `StagePromptsResponse`, `PromptOverrides` |
| `frontend/src/api/types.ts` | Обновлены `StepCleanRequest`, `StepLongreadRequest`, `StepSummarizeRequest`, `StepStoryRequest` с `prompt_overrides?` |
| `frontend/src/api/hooks/usePrompts.ts` | ✨ Создан — хук `useStagePrompts(stage, enabled)` |
| `frontend/src/components/settings/ComponentPromptSelector.tsx` | ✨ Создан — селектор для выбора варианта промпта |
| `frontend/src/components/processing/StepByStep.tsx` | Интеграция селекторов промптов в пошаговый режим |
| `frontend/package.json` | version → 0.33.0 |

**Ключевые особенности:**
- Селекторы показываются только если `variants.length > 1`
- Промпты загружаются только в step-by-step режиме (`!autoRun`)
- Сброс на default = `undefined` — не передаётся в API
- Grid layout 2 колонки для компактности
- Маркировка external промптов звёздочкой

**Следующий шаг:** Деплой и верификация на сервере

---

# Подфаза 7.4: Документация

## Файлы для изменения

| Файл | Действие |
|------|----------|
| `CLAUDE.md` | API endpoints, load_prompt() |
| `docs/configuration.md` | Секция "Варианты промптов" |
| `docs/api-reference.md` | GET /api/prompts/{stage} |
| `docs/pipeline/stages.md` | Генераторы с PromptOverrides |
| `docs/adr/008-external-prompts.md` | Убрать model-specific |
| `docs/research/pipeline-optimization-for-rag.md` | Статус Фазы 7 |

## Обновления

### CLAUDE.md
- Добавить `GET /api/prompts/{stage}` в API
- Обновить структуру промптов (убрать *_gemma2.md)
- Новая сигнатура load_prompt()

### docs/configuration.md
- Новая секция "Варианты промптов"
- Как создать вариант
- Как выбрать в UI/API

### docs/api-reference.md
- Новый endpoint GET /api/prompts/{stage}
- prompt_overrides в Step endpoints

### docs/research/pipeline-optimization-for-rag.md
- Фаза 7 → ✅ (v0.31)

## Верификация подфазы 7.4

Проверить что документация актуальна и соответствует реализации.

## ✅ Результаты подфазы 7.4

**Коммит:** `2a8966c` — Update documentation for prompt variants API (v0.34)

**Изменённые файлы:**
| Файл | Изменение |
|------|-----------|
| `CLAUDE.md` | Обновлена структура промптов (убрали model-specific), новая сигнатура `load_prompt()`, добавлена секция Prompts API |
| `docs/configuration.md` | Обновлена структура промптов, добавлена секция "Варианты промптов" |
| `docs/api-reference.md` | Добавлены Prompts API и Step API секции |
| `docs/pipeline/stages.md` | Добавлена секция "Генераторы и PromptOverrides" |
| `docs/adr/008-external-prompts.md` | Убраны упоминания model-specific, обновлена сигнатура load_prompt() |
| `docs/research/pipeline-optimization-for-rag.md` | Фаза 7 → ✅ (v0.31-v0.34) |
| `frontend/package.json` | version → 0.34.0 |

**Фаза 7 полностью завершена!**

---

## Обратная совместимость

- `prompt_overrides=None` → текущее поведение
- Существующие API вызовы работают без изменений
- localStorage с новым полем не ломает старый формат
