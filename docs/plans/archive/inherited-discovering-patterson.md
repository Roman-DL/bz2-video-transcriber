# План: Повторный запуск шагов и выбор модели в step-by-step режиме

## Цель

Добавить в пошаговый режим обработки две фичи для A/B тестирования комбинаций модель+промпты:
1. **Кнопка перезапуска** — возможность вернуться к выполненному шагу и запустить его снова
2. **Селектор модели** — выбор LLM для этапов clean, longread, summarize, story

## Архитектура: переиспользование кода

Сейчас в `SettingsModal.tsx` есть:
- `ModelSelector` компонент
- Helper функции: `ollamaToOptions()`, `claudeToOptions()`
- `llmOptions` useMemo

**Решение:** Вынести в shared модули для переиспользования.

## Файлы для изменения

| Файл | Изменения |
|------|-----------|
| [modelUtils.ts](frontend/src/utils/modelUtils.ts) | **Новый** — helper функции для преобразования моделей |
| [ModelSelector.tsx](frontend/src/components/settings/ModelSelector.tsx) | **Новый** — переиспользуемый компонент выбора модели |
| [SettingsModal.tsx](frontend/src/components/settings/SettingsModal.tsx) | Рефакторинг: импортировать из shared модулей |
| [StepByStep.tsx](frontend/src/components/processing/StepByStep.tsx) | Добавить кликабельные шаги, state моделей, UI селектора |

## Реализация

### Шаг 1: Создать modelUtils.ts

**Файл:** `frontend/src/utils/modelUtils.ts`

Вынести helper функции:

```tsx
import type { WhisperModelConfig, ClaudeModelConfig, ProviderType } from '@/api/types';

export interface ModelOption {
  value: string;
  label: string;
  description?: string;
  provider?: ProviderType;
}

/** Convert whisper models to options */
export function whisperToOptions(models: WhisperModelConfig[]): ModelOption[] {
  return models.map((m) => ({
    value: m.id,
    label: m.name,
    description: m.description,
  }));
}

/** Convert ollama model names to options */
export function ollamaToOptions(models: string[]): ModelOption[] {
  return models.map((m) => ({ value: m, label: m, provider: 'local' as ProviderType }));
}

/** Convert claude models to options */
export function claudeToOptions(models: ClaudeModelConfig[]): ModelOption[] {
  return models.map((m) => ({
    value: m.id,
    label: `☁️ ${m.name}`,
    description: m.description,
    provider: 'cloud' as ProviderType,
  }));
}

/** Build combined LLM options from available models */
export function buildLLMOptions(
  ollamaModels?: string[],
  claudeModels?: ClaudeModelConfig[]
): ModelOption[] {
  const options: ModelOption[] = [];
  if (ollamaModels?.length) {
    options.push(...ollamaToOptions(ollamaModels));
  }
  if (claudeModels?.length) {
    options.push(...claudeToOptions(claudeModels));
  }
  return options;
}
```

### Шаг 2: Создать ModelSelector.tsx

**Файл:** `frontend/src/components/settings/ModelSelector.tsx`

Переиспользуемый компонент с режимами `compact` и `full`:

```tsx
interface ModelSelectorProps {
  label?: string;
  value: string | undefined;
  defaultValue: string;
  options: ModelOption[];
  onChange: (value: string | undefined) => void;
  disabled?: boolean;
  compact?: boolean;  // для StepByStep - без config info
  config?: ModelConfig;  // для SettingsModal - с config info
}

export function ModelSelector({
  label,
  value,
  defaultValue,
  options,
  onChange,
  disabled,
  compact = false,
  config,
}: ModelSelectorProps) {
  const selectedValue = value || defaultValue;
  const selectedOption = options.find((o) => o.value === selectedValue);
  const isCloudModel = selectedOption?.provider === 'cloud';

  return (
    <div className={compact ? 'space-y-1' : 'space-y-2'}>
      {/* Label with cloud badge */}
      <div className="flex items-center gap-2">
        <label className={compact ? 'text-xs text-gray-500' : 'block text-sm font-medium text-gray-700'}>
          {label || 'Модель'}
        </label>
        {isCloudModel && (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-blue-100 text-blue-700">
            cloud
          </span>
        )}
      </div>

      {/* Select dropdown */}
      <div className="relative">
        <select ... />
      </div>

      {/* Config info - only in full mode */}
      {!compact && config && (
        <div className="mt-2 p-3 bg-gray-50 rounded-lg text-xs text-gray-600">
          ...
        </div>
      )}
    </div>
  );
}
```

### Шаг 3: Рефакторинг SettingsModal.tsx

- Удалить локальные `ModelSelector`, `ollamaToOptions`, `claudeToOptions`, `whisperToOptions`
- Импортировать из shared модулей:

```tsx
import { ModelSelector } from '@/components/settings/ModelSelector';
import { whisperToOptions, buildLLMOptions, type ModelOption } from '@/utils/modelUtils';
```

- Заменить `llmOptions` useMemo на:

```tsx
const llmOptions = useMemo(() =>
  buildLLMOptions(availableModels?.ollama_models, availableModels?.claude_models),
  [availableModels]
);
```

### Шаг 4: Изменения в StepByStep.tsx

#### 4.1 Импорты

```tsx
import { useAvailableModels, useDefaultModels } from '@/api/hooks/useModels';
import { ModelSelector } from '@/components/settings/ModelSelector';
import { buildLLMOptions } from '@/utils/modelUtils';
```

#### 4.2 State для моделей

```tsx
type StageWithModels = 'clean' | 'longread' | 'summarize' | 'story';
const [modelOverrides, setModelOverrides] = useState<Record<StageWithModels, string | undefined>>({
  clean: undefined,
  longread: undefined,
  summarize: undefined,
  story: undefined,
});
```

#### 4.3 Хуки и options

```tsx
const { data: availableModels } = useAvailableModels();
const { data: defaultModels } = useDefaultModels();

const llmOptions = useMemo(() =>
  buildLLMOptions(availableModels?.ollama_models, availableModels?.claude_models),
  [availableModels]
);
```

#### 4.4 Кликабельные шаги (строки 519-545)

```tsx
<button
  key={step}
  onClick={() => status === 'completed' && !isLoading && handleStepClick(step)}
  disabled={status === 'pending' || isLoading}
  className={clsx(
    'flex items-center gap-2',
    status === 'completed' && !isLoading && 'cursor-pointer hover:opacity-70'
  )}
  title={status === 'completed' ? 'Нажмите для перезапуска' : undefined}
>
```

#### 4.5 Функция перехода к шагу

```tsx
const handleStepClick = (step: PipelineStep) => {
  resetDataFromStep(step);
  setCurrentStep(step);
};

const resetDataFromStep = (step: PipelineStep) => {
  const stepIndex = pipelineSteps.indexOf(step);
  const fieldsToReset: Record<PipelineStep, (keyof StepData)[]> = {
    parse: ['metadata'],
    transcribe: ['rawTranscript', 'displayText', 'audioPath'],
    clean: ['cleanedTranscript'],
    longread: ['longread'],
    summarize: ['summary'],
    story: ['story'],
    chunk: ['chunks'],
    save: ['savedFiles'],
  };

  setData(prev => {
    const next = { ...prev };
    for (let i = stepIndex; i < pipelineSteps.length; i++) {
      fieldsToReset[pipelineSteps[i]]?.forEach(field => {
        next[field] = undefined;
      });
    }
    return next;
  });
  setExpandedBlocks(new Set());
};
```

#### 4.6 UI селектора модели

```tsx
{!autoRun && !isLoading && STAGES_WITH_PROMPTS.includes(currentStep as StageWithPrompts) && (
  <div className="mt-3 pt-3 border-t border-blue-200">
    <div className="grid grid-cols-2 gap-3">
      {/* Model selector - compact mode */}
      <ModelSelector
        label="Модель"
        value={modelOverrides[currentStep as StageWithModels]}
        defaultValue={defaultModels?.[currentStep as keyof typeof defaultModels] || ''}
        options={llmOptions}
        onChange={(value) => setModelOverrides(prev => ({ ...prev, [currentStep]: value }))}
        compact
      />

      {/* Prompt selectors */}
      {getPromptsForStep(currentStep)?.components.map((comp) => (
        <ComponentPromptSelector ... />
      ))}
    </div>
  </div>
)}
```

#### 4.7 Использование модели в runStep()

```tsx
case 'clean':
  const cleanedTranscript = await stepClean.mutate({
    raw_transcript: data.rawTranscript,
    metadata: data.metadata,
    model: modelOverrides.clean || models.clean,  // приоритет per-step выбора
    prompt_overrides: getPromptOverridesForApi('clean'),
  });
```

## Верификация

1. **Пошаговый режим:** Выбрать файл → перейти к шагу clean
2. **Селектор модели:** Убедиться что показывается dropdown с моделями
3. **Выбор модели:** Выбрать другую модель → выполнить → проверить что использовалась
4. **Перезапуск:** Кликнуть на зелёную галочку → шаг стал current, последующие сброшены
5. **SettingsModal:** Убедиться что работает как раньше после рефакторинга

## Преимущества подхода

- **Единая логика:** `buildLLMOptions()` используется и в Settings, и в StepByStep
- **Единый компонент:** `ModelSelector` с режимами `compact` и `full`
- **Расширяемость:** При добавлении нового провайдера (например, OpenAI) — изменения только в `modelUtils.ts`
- **Тестируемость:** Helper функции можно юнит-тестировать отдельно

---

## Шаг 5: Обновление документации

### 5.1 docs/web-ui.md

Обновить секцию "Пошаговый режим" (строки 47-81):

**Добавить:**
- Описание кликабельных шагов в прогресс-баре (возврат к выполненному этапу)
- Селектор модели для LLM-этапов (clean, longread, summarize, story)
- Сценарий A/B тестирования комбинаций модель+промпты

**Обновить ASCII-диаграмму** — показать что галочки кликабельны.

### 5.2 docs/research/pipeline-optimization-for-rag.md

Обновить статус в заголовке:
```
> **Статус:** Фазы 1-8 реализованы (v0.21-v0.35)
```

Добавить в конец секцию:
```markdown
## Фаза 8: A/B тестирование моделей и промптов (v0.35)

**Цель:** Возможность сравнивать результаты разных комбинаций модель+промпты.

**Реализовано:**
- Кликабельные шаги в прогресс-баре — возврат к выполненному этапу
- Селектор модели для LLM-этапов (clean, longread, summarize, story)
- Сохранение выбора модели per-session (не влияет на глобальные настройки)
- При перезапуске шага — сброс результатов последующих этапов
```

### 5.3 CLAUDE.md (опционально)

В секцию "Структура проекта" добавить:
```
frontend/src/utils/             # Shared utilities (modelUtils)
```
