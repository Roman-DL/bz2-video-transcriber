# План: Улучшение UI настроек в пошаговой обработке

## Проблема

### Текущее поведение:
1. После выполнения шага (например `clean`) → `currentStep` автоматически переключается на следующий (`longread`)
2. Селекторы показывают настройки для нового `currentStep` (longread)
3. Пользователь меняет настройки, думая что это для "перезапуска" предыдущего шага
4. Нажимает "Выполнить" — запускается следующий шаг, а не перезапуск
5. **Результат:** путаница — настройки применяются не к тому шагу

### Дополнительная проблема:
- Селекторы модели и промптов визуально сливаются в одну кучу
- Непонятно что к чему относится

## Решение

### 1. Добавить кнопку "Перезапустить" для выполненных LLM шагов

После выполнения LLM шага (clean, longread, summarize, story) показывать:
- Настройки для этого выполненного шага
- Кнопку "Перезапустить" для повторного выполнения с новыми настройками
- Кнопку "Выполнить" для продолжения к следующему шагу

```
┌─────────────────────────────────────────────────────────────┐
│ Шаг 4: Генерация лонгрида                        [Выполнить]│
│ (Следующий шаг)                                             │
├─────────────────────────────────────────────────────────────┤
│ ✓ Шаг 3: Очистка текста                       [Перезапустить]│
│   Модель: [Claude Sonnet 4.5 ▾]                             │
│   ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─                               │
│   Промпты: [system ▾]  [user ▾]                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. Визуальное разделение селекторов модели и промптов

Разделить на две группы с чётким визуальным разделением:
- Верхняя секция: селектор модели
- Нижняя секция: селекторы промптов (с заголовком "Промпты")

### 3. Структура UI (упрощённая)

**Ключевое упрощение:** Селекторы только в блоке перезапуска! Текущий шаг использует глобальные настройки.

```
┌─── Индикатор прогресса (шаги) ───────────────────────────────┐
│  ✓ ─── ✓ ─── ✓ ─── ● ─── ○ ─── ○ ─── ○                       │
│  1     2     3     4     5     6     7                       │
└──────────────────────────────────────────────────────────────┘

┌─── Блок текущего шага (синий) ───────────────────────────────┐
│ Шаг 4: Генерация лонгрида                        [Выполнить] │
│ Создание структурированного текста из очищенной транскрипции │
│ (использует модель из глобальных настроек)                   │
└──────────────────────────────────────────────────────────────┘

┌─── Блок перезапуска (зелёный) ── ТОЛЬКО step-by-step ────────┐
│ ✓ Шаг 3: Очистка текста                      [Перезапустить] │
│                                                              │
│ Модель: [cloud] [Claude Sonnet 4.5 ▾]                        │
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─                          │
│ Промпты:                                                     │
│ [system (по умолчанию) * ▾]  [user (по умолчанию) * ▾]       │
└──────────────────────────────────────────────────────────────┘

┌─── Результаты ── ТОЛЬКО step-by-step ────────────────────────┐
│ > Метаданные                                                 │
│ > Сырая транскрипция                                         │
│ v Очищенный текст                                            │
│   [содержимое...]                                            │
└──────────────────────────────────────────────────────────────┘
```

**Auto-run режим:** показывается ТОЛЬКО индикатор прогресса и синий блок текущего шага (без кнопки).

### 4. Поведение в auto-run режиме

При автоматической обработке (`autoRun=true`):
- **НЕ показывать** блок перезапуска (зелёный)
- **НЕ показывать** результаты шагов (collapsible cards)
- Использовать модели из глобальных настроек (`useSettings()`)
- Показывать только индикатор прогресса и синий блок текущего шага (без кнопки)

Это уже частично реализовано (условие `!autoRun`), просто добавляем такое же условие для нового блока перезапуска.

## Файлы для изменения

| Файл | Изменения |
|------|-----------|
| [StepByStep.tsx](frontend/src/components/processing/StepByStep.tsx) | Добавить блок перезапуска, разделить селекторы, убедиться что в auto-run ничего лишнего не показывается |

## Детальная реализация

### Шаг 1: Логика выбора модели (без изменений)

Текущая логика `getModelForStage` уже правильная:
```tsx
const getModelForStage = (stage: StageWithModels): string | undefined => {
  const settingsKey = stage === 'story' ? 'summarize' : stage;
  return modelOverrides[stage] || models[settingsKey];  // override или глобальные
};
```

- **Первый запуск:** `modelOverrides[stage]` = undefined → используются глобальные настройки
- **Перезапуск:** пользователь выбрал модель в селекторе → используется override

### Шаг 2: Определить предыдущий LLM шаг для блока перезапуска

```tsx
// Найти последний выполненный LLM шаг перед текущим
const getPreviousCompletedLLMStep = (): StageWithModels | null => {
  const currentIndex = pipelineSteps.indexOf(currentStep);
  for (let i = currentIndex - 1; i >= 0; i--) {
    const step = pipelineSteps[i];
    if (isLLMStep(step)) {
      // Проверяем что шаг действительно выполнен (есть результат)
      const hasResult = (() => {
        switch (step) {
          case 'clean': return !!data.cleanedTranscript;
          case 'longread': return !!data.longread;
          case 'summarize': return !!data.summary;
          case 'story': return !!data.story;
          default: return false;
        }
      })();
      if (hasResult) return step as StageWithModels;
    }
  }
  return null;
};
```

### Шаг 3: Добавить функцию перезапуска

```tsx
const rerunStep = async (step: PipelineStep) => {
  // Сбросить данные начиная с этого шага
  resetDataFromStep(step);
  // Установить текущий шаг
  setCurrentStep(step);
  // Запустить выполнение
  await runStep(step);
};
```

### Шаг 4: UI блока перезапуска (зелёный)

```tsx
{/* Rerun block for previous LLM step */}
{!autoRun && !isLoading && previousLLMStep && (
  <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
    <div className="flex items-center justify-between mb-3">
      <div className="flex items-center gap-2">
        <CheckCircle className="w-4 h-4 text-green-600" />
        <span className="text-sm font-medium text-gray-700">
          {STEP_LABELS[previousLLMStep]}
        </span>
      </div>
      <Button
        variant="outline"
        size="sm"
        onClick={() => rerunStep(previousLLMStep)}
      >
        <RefreshCw className="w-3 h-3 mr-1" />
        Перезапустить
      </Button>
    </div>

    {/* Model selector */}
    <div className="space-y-2">
      <ModelSelector
        label="Модель"
        value={modelOverrides[previousLLMStep]}
        defaultValue={...}
        options={llmOptions}
        onChange={(value) => setModelOverrides(...)}
        compact
      />

      {/* Divider */}
      <div className="border-t border-gray-200 my-2" />

      {/* Prompt selectors */}
      {hasSelectablePrompts(...) && (
        <div>
          <span className="text-xs text-gray-500 mb-1 block">Промпты:</span>
          <div className="grid grid-cols-2 gap-2">
            {/* prompt selectors */}
          </div>
        </div>
      )}
    </div>
  </div>
)}
```

### Шаг 5: Удалить селекторы из блока текущего шага

**Удалить** весь блок селекторов модели и промптов из синего блока текущего шага (строки ~676-717).

Текущий шаг теперь использует только глобальные настройки из `useSettings()`.

```tsx
{/* Current step info - БЕЗ селекторов */}
<div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
  <div className="flex items-center justify-between">
    <div className="flex-1 mr-4">
      <h4 className="text-sm font-medium text-blue-900">
        Шаг {currentStepIndex + 1}: {STEP_LABELS[currentStep]}
      </h4>
      <p className="text-xs text-blue-700 mt-1">
        {isLoading && message ? message : getStepDescription(currentStep)}
      </p>
    </div>
    {!autoRun && (
      <Button onClick={() => runStep(currentStep)} disabled={isLoading}>
        {isLoading ? 'Выполняется...' : 'Выполнить'}
      </Button>
    )}
  </div>
  {/* Progress bar остаётся */}
</div>
```

## Обновление документации

### 1. Обновить версию в `frontend/package.json`
- Обновить minor версию (0.36) — новая UX фича

### 2. Обновить CLAUDE.md (если нужно)
- Если появляются новые концепции или изменения в архитектуре — добавить в документацию

### 3. Commit message
```
Improve step-by-step UI: add rerun button and visual separation (v0.36)

- Add rerun block for completed LLM steps with dedicated button
- Visually separate model and prompt selectors
- Fix UX confusion between current step and rerun settings
```

## Верификация

1. Запустить frontend: `cd frontend && npm run dev`
2. Открыть пошаговую обработку файла
3. Проверить сценарии в **step-by-step режиме**:
   - [ ] После выполнения LLM шага появляется блок перезапуска с кнопкой "Перезапустить"
   - [ ] В блоке перезапуска селекторы модели и промптов визуально разделены
   - [ ] В блоке текущего шага НЕТ селекторов (только кнопка "Выполнить")
   - [ ] Кнопка "Перезапустить" корректно перезапускает шаг с новыми настройками
   - [ ] Кнопка "Выполнить" запускает следующий шаг (с глобальными настройками)
   - [ ] Настройки overrides сохраняются отдельно для каждого шага
4. Проверить сценарии в **auto-run режиме**:
   - [ ] Блок перезапуска НЕ показывается
   - [ ] Результаты шагов НЕ показываются
   - [ ] Показывается только индикатор прогресса и синий блок (без кнопки)
   - [ ] Используются модели из глобальных настроек
5. После успешной верификации:
   - [ ] Обновить версию в `frontend/package.json`
   - [ ] Сделать коммит
