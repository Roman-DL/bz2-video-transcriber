# План: Интеграция ProcessingStrategy в Pipeline + UI для Claude моделей

## Цель
Подключить существующий ProcessingStrategy к orchestrator, добавить Claude модели в UI форму настроек.

**Архитектура AI сервисов:**
- **Whisper** (`WHISPER_URL`) — отдельный сервис транскрипции audio→text
- **Ollama** (`OLLAMA_URL`) — локальные LLM модели (gemma2, qwen2.5)
- **Claude API** (`ANTHROPIC_API_KEY`) — облачные LLM модели

---

## Фаза 0: Конфигурация — ANTHROPIC_API_KEY

### Файл: `.env.example`
```env
# Claude API (optional - for cloud models)
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### Файл: `docker-compose.yml`
Добавить в секцию environment:
```yaml
# Cloud AI (optional)
- ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
```

### Актуальные Claude модели:
- `claude-sonnet-4-20250514` — Sonnet 4 (быстрая)
- `claude-opus-4-20250514` — Opus 4 (мощная)

---

## Фаза 1: Backend — Обновление типов (BaseAIClient)

### Файлы для изменения:
| Файл | Изменение |
|------|-----------|
| `backend/app/services/cleaner.py:39` | `OllamaClient` → `BaseAIClient` |
| `backend/app/services/chunker.py` | Аналогично |
| `backend/app/services/longread_generator.py` | Аналогично |
| `backend/app/services/summary_generator.py` | Аналогично |
| `backend/app/services/outline_extractor.py` | Аналогично |
| `backend/app/services/stages/clean_stage.py` | Аналогично |
| `backend/app/services/stages/chunk_stage.py` | Аналогично |
| `backend/app/services/stages/longread_stage.py` | Аналогично |
| `backend/app/services/stages/summarize_stage.py` | Аналогично |

**Важно:** `transcriber.py` и `transcribe_stage.py` НЕ меняем — они работают с Whisper сервисом через `OllamaClient.transcribe()`.

### Добавить импорт:
```python
from app.services.ai_clients import BaseAIClient
```

---

## Фаза 2: Backend — Интеграция ProcessingStrategy в orchestrator

### Файл: `backend/app/services/pipeline/orchestrator.py`

#### 2.1 Добавить импорт:
```python
from .processing_strategy import ProcessingStrategy
```

#### 2.2 Добавить в `__init__`:
```python
self.processing_strategy = ProcessingStrategy(self.settings)
```

#### 2.3 Рефакторинг методов step-by-step:

**Метод `clean()` (строки ~302-322):**
```python
async def clean(self, raw_transcript, metadata, model=None):
    settings = self.config_resolver.with_model(model, "cleaner")
    actual_model = model or settings.cleaner_model

    async with self.processing_strategy.create_client(actual_model) as ai_client:
        cleaner = TranscriptCleaner(ai_client, settings)
        return await cleaner.clean(raw_transcript, metadata)
```

Аналогично для `chunk()`, `longread()`, `summarize_from_longread()`, `summarize()`.

#### 2.4 Рефакторинг `process()` (полный pipeline):

Разделить на две фазы:
1. Транскрипция через `OllamaClient` (Whisper)
2. LLM-этапы через `ProcessingStrategy`

---

## Фаза 3: Backend — API для Claude моделей

### Файл: `backend/app/api/models_routes.py`

#### 3.1 Добавить импорты:
```python
from app.services.pipeline import ProcessingStrategy
```

#### 3.2 Расширить endpoint `/api/models/available`:
```python
@router.get("/available")
async def get_available_models() -> dict:
    settings = get_settings()
    strategy = ProcessingStrategy(settings)
    availability = await strategy.check_availability()

    # ... existing ollama/whisper code ...

    # Claude models from config
    config = load_models_config()
    claude_models_config = config.get("claude_models", [])

    cloud_available = availability[ProviderType.CLOUD].available

    return {
        "ollama_models": sorted(ollama_models),
        "whisper_models": whisper_models,
        "claude_models": claude_models_config if cloud_available else [],
        "providers": {
            "local": {"available": availability[ProviderType.LOCAL].available, "name": "Ollama"},
            "cloud": {"available": cloud_available, "name": "Claude API"}
        }
    }
```

### Файл: `config/models.yaml`

#### 3.3 Добавить секцию claude_models:
```yaml
# Claude models available for selection in UI
claude_models:
  - id: "claude-sonnet-4-20250514"
    name: "Claude Sonnet 4"
    description: "Облачная модель (200K контекст)"
```

---

## Фаза 4: Frontend — Типы и UI

### Файл: `frontend/src/api/types.ts`

#### 4.1 Добавить типы:
```typescript
export type ProviderType = 'local' | 'cloud';

export interface ClaudeModelConfig {
  id: string;
  name: string;
  description?: string;
}

export interface ProviderStatus {
  available: boolean;
  name: string;
}
```

### Файл: `frontend/src/components/settings/SettingsModal.tsx`

#### 4.2 Объединить Ollama + Claude модели для LLM-этапов:
```typescript
const llmOptions = useMemo((): ModelOption[] => {
  const options: ModelOption[] = [];

  // Ollama models (local)
  availableModels?.ollama_models.forEach(m => {
    options.push({ value: m, label: m, provider: 'local' });
  });

  // Claude models (cloud)
  availableModels?.claude_models?.forEach(m => {
    options.push({
      value: m.id,
      label: `☁️ ${m.name}`,
      description: m.description,
      provider: 'cloud'
    });
  });

  return options;
}, [availableModels]);
```

#### 4.3 Обновить ModelOption:
```typescript
interface ModelOption {
  value: string;
  label: string;
  description?: string;
  provider?: ProviderType;
}
```

#### 4.4 Показать индикацию cloud в dropdown и badge под селектом.

---

## Фаза 5: Тестирование

1. **Локально:** Проверить что Ollama модели работают как раньше
2. **Claude:** Установить `ANTHROPIC_API_KEY` и проверить:
   - Claude модели появляются в dropdown
   - Step-by-step clean/chunk/longread/summarize работают с Claude
3. **Fallback:** Убрать API key — Claude модели должны исчезнуть из UI

---

## Файлы для изменения (итого)

### Backend:
- `backend/app/services/cleaner.py`
- `backend/app/services/chunker.py`
- `backend/app/services/longread_generator.py`
- `backend/app/services/summary_generator.py`
- `backend/app/services/outline_extractor.py`
- `backend/app/services/stages/clean_stage.py`
- `backend/app/services/stages/chunk_stage.py`
- `backend/app/services/stages/longread_stage.py`
- `backend/app/services/stages/summarize_stage.py`
- `backend/app/services/pipeline/orchestrator.py`
- `backend/app/api/models_routes.py`

### Config:
- `config/models.yaml`

### Frontend:
- `frontend/src/api/types.ts`
- `frontend/src/components/settings/SettingsModal.tsx`

---

## Ограничения

1. **Транскрипция** — отдельный сервис Whisper (не меняется)
2. **ANTHROPIC_API_KEY** требуется для работы Claude моделей
3. **Без ключа** Claude модели не показываются в UI (graceful degradation)

---

## Конфигурационные файлы (итого)

- `.env.example` — добавить ANTHROPIC_API_KEY
- `.env` / `.env.local` — вставить реальный ключ (пользователь)
- `docker-compose.yml` — добавить переменную ANTHROPIC_API_KEY
- `config/models.yaml` — добавить секцию claude_models
