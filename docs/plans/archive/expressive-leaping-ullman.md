# Аудит: Автоматическое переключение вкладок в StepByStep

## Резюме

**Вердикт: ✅ Решение корректно реализовано**

Все изменения логически верны, не ломают существующий функционал, и решают исходную проблему.

---

## Проверка по пунктам

### 1. onStepComplete вызывается для ВСЕХ шагов? ✅

| Шаг | Где вызывается | Статус |
|-----|----------------|--------|
| parse | `usePipelineProcessor.ts:587` (autoParse) | ✅ |
| transcribe | `usePipelineProcessor.ts:390` (runStep) | ✅ |
| clean | `usePipelineProcessor.ts:409` (runStep) | ✅ |
| slides | `usePipelineProcessor.ts:432` (runStep) | ✅ |
| longread | `usePipelineProcessor.ts:448` (runStep) | ✅ |
| summarize | `usePipelineProcessor.ts:463` (runStep) | ✅ |
| story | `usePipelineProcessor.ts:479` (runStep) | ✅ |
| chunk | `usePipelineProcessor.ts:504` (runStep) | ✅ |
| save | `usePipelineProcessor.ts:522,537` (runStep) | ✅ |

### 2. Метка "ТЕКУЩИЙ" появляется? ✅

Логика в `StepByStep.tsx:413`:
```tsx
const isCurrent = status === 'completed' && getTabForStep(step) === activeTab && !isLoading;
```

После выполнения шага:
1. `handleStepComplete(step)` вызывается
2. `switchTab(tabForStep)` переключает `activeTab`
3. `isCurrent` становится `true` для выполненного шага
4. Метка отображается (строки 462-465)

### 3. Переключение вкладок работает? ✅

- При клике на шаг: `onClick={() => switchTab(tabForStep)}` (строка 425)
- При клике на вкладку: `onClick={() => switchTab(tab)}` (строка 580)
- `switchTab` корректно сбрасывает diff mode (строки 137-140)

### 4. ArchiveResultsModal не сломан? ✅

Изменения минимальны и улучшают код:
- Добавлен `useMemo` для `availableTabs` — оптимизация
- Создан `switchTab` wrapper — унифицирует логику с StepByStep
- Удалён лишний `useEffect` для сброса diff mode
- `eslint-disable` для валидного паттерна setState в useEffect

### 5. AutoProcessingCompact не сломан? ✅

Компонент **не использует** `onStepComplete`:
```tsx
// AutoProcessingCompact.tsx:186-190
const processor = usePipelineProcessor({
  filename,
  initialSlides,
  autoRun: true,
  // onStepComplete не передаётся
});
```

Логика автозапуска (`autoRun: true`) не изменилась — компонент работает как раньше.

---

## Анализ изменений

### usePipelineProcessor.ts

**Добавлено:**
```tsx
// строка 587
onStepComplete?.('parse', { metadata });
```

**eslint-disable объяснение:**
```tsx
// строки 600-602
// Intentionally only depend on filename - we want to parse once on mount
// eslint-disable-next-line react-hooks/exhaustive-deps
}, [filename]);
```

Это валидный паттерн — parse должен выполняться однократно при монтировании. Если бы `onStepComplete` был в зависимостях, эффект перезапускался бы при каждом изменении callback.

### StepByStep.tsx

**Структурные улучшения:**
1. `getTabForStep()` вынесен на уровень модуля — чистая функция без зависимостей от компонента
2. `switchTab()` wrapper — единая точка для переключения вкладок и сброса diff mode
3. `handleStepComplete()` — callback для хука, вызывает switchTab

**Удалённые useEffect:**
```tsx
// Было:
useEffect(() => {
  setShowCleanedDiff(false);
  setShowLongreadDiff(false);
}, [activeTab]);

useEffect(() => {
  if (data.metadata && !activeTab) {
    setActiveTab('metadata');
  }
}, [data.metadata, activeTab]);

// Стало:
// Оба эффекта заменены на callback-подход через onStepComplete
```

---

## Lint-исправления в других файлах

| Файл | Изменение | Обоснование |
|------|-----------|-------------|
| `SettingsModal.tsx:25-26` | `eslint-disable react-hooks/set-state-in-effect` | Валидный паттерн синхронизации с props |
| `SlidesModal.tsx:83-84` | `eslint-disable react-hooks/set-state-in-effect` | Сброс error при открытии модала |
| `SettingsContext.tsx:1` | `eslint-disable react-refresh/only-export-components` | Context + Provider в одном файле |
| `ArchiveResultsModal.tsx:129-130` | `eslint-disable react-hooks/set-state-in-effect` | Авто-выбор вкладки при загрузке данных |

Все эти случаи — стандартные React-паттерны, где setState в useEffect оправдан.

---

## Потенциальные улучшения (не обязательны)

1. **Типизация callback в handleStepComplete**
   ```tsx
   // Сейчас:
   const handleStepComplete = useCallback((step: PipelineStep) => {...

   // Полная сигнатура:
   const handleStepComplete = useCallback((step: PipelineStep, _data: StepData) => {...
   ```
   Не ошибка, но делает интерфейс явным.

2. **Шаг 'save' не имеет вкладки**
   `getTabForStep('save')` возвращает `null` — это корректно, т.к. показывается CompletionCard.

---

## Верификация

Для проверки работы изменений:

1. **Пошаговый режим:**
   - Открыть StepByStep
   - Убедиться что вкладка "Метаданные" активна после auto-parse
   - Выполнить шаг "Транскрипция" → вкладка переключится на "Транскрипт"
   - Проверить метку "ТЕКУЩИЙ" на выполненном шаге

2. **Автоматический режим:**
   - Открыть AutoProcessingCompact
   - Убедиться что обработка проходит без ошибок
   - Все шаги выполняются последовательно

3. **Просмотр архива:**
   - Открыть ArchiveResultsModal
   - Переключить вкладки
   - Проверить что diff mode сбрасывается при переключении

---

## Вывод

Решение готово к коммиту. Рекомендую протестировать в браузере перед деплоем.
