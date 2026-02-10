# План: Автоматический parse при открытии пошаговой обработки

## Цель

Оптимизировать UX пошаговой обработки:
1. Автоматически выполнять parse при открытии формы (убрать лишний клик)
2. Показывать правильный pipeline сразу после определения content_type
3. Подтвердить что summarize отображается как отдельный шаг

## Текущее поведение

1. Открывается StepByStep → `currentStep='parse'`, `contentType='educational'` (по умолчанию)
2. Показываются EDUCATIONAL_STEPS до выполнения parse (может быть неправильно для leadership)
3. Пользователь нажимает кнопку "Выполнить" для парсинга
4. После parse: получаем metadata с content_type, pipeline пересчитывается

## Проверка summarize

✅ **Summarize уже отдельный шаг** в [types.ts:265-267](frontend/src/api/types.ts#L265-L267):
```typescript
export const EDUCATIONAL_STEPS: PipelineStep[] = [
  'parse', 'transcribe', 'clean', 'longread', 'summarize', 'chunk', 'save',
];
```

## Изменения

### Файл: [frontend/src/components/processing/StepByStep.tsx](frontend/src/components/processing/StepByStep.tsx)

#### 1. Добавить состояния (после строки 76)

```typescript
const [isInitializing, setIsInitializing] = useState(true);
const [parseError, setParseError] = useState<string | null>(null);
```

#### 2. Добавить auto-parse useEffect (после строки 102)

```typescript
// Auto-parse on mount to determine content_type
useEffect(() => {
  let mounted = true;

  const autoParse = async () => {
    try {
      const metadata = await stepParse.mutateAsync({
        video_filename: filename,
        whisper_model: models.transcribe,
      });
      if (mounted) {
        setData({ metadata });
        setCurrentStep('transcribe');
        setIsInitializing(false);
      }
    } catch (err) {
      if (mounted) {
        setParseError(err instanceof Error ? err.message : 'Ошибка парсинга');
        setIsInitializing(false);
      }
    }
  };

  autoParse();

  return () => { mounted = false; };
}, [filename]);
```

#### 3. Добавить ранний return для loading/error (перед основным return, ~строка 356)

```typescript
// Loading state during auto-parse
if (isInitializing) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-medium text-gray-500 mb-1">
          Определение типа контента
        </h3>
        <p className="text-sm text-gray-900 truncate">{filename}</p>
      </div>

      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <Spinner size="lg" />
          <p className="mt-4 text-sm text-gray-600">
            Анализ метаданных файла...
          </p>
        </div>
      </div>
    </div>
  );
}

// Parse error state
if (parseError) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-medium text-gray-500 mb-1">
          Ошибка определения типа контента
        </h3>
        <p className="text-sm text-gray-900 truncate">{filename}</p>
      </div>

      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center gap-2 text-red-700">
          <AlertCircle className="w-5 h-5" />
          <span className="font-medium">Ошибка парсинга</span>
        </div>
        <p className="mt-1 text-sm text-red-600">{parseError}</p>
      </div>

      <div className="flex justify-end">
        <Button variant="secondary" onClick={onCancel}>
          Закрыть
        </Button>
      </div>
    </div>
  );
}
```

#### 4. Обновить auto-run effect (строка 198)

Добавить проверку `isInitializing`:

```typescript
useEffect(() => {
  if (!autoRun) return;
  if (isInitializing) return; // Wait for auto-parse to complete
  if (isLoading) return;
  // ... остальной код
}, [autoRun, currentStep, isLoading, isComplete, error, data, isInitializing]);
```

#### 5. Показывать parse как completed в индикаторе

В функции `getStepStatus` (строка 349) можно оставить как есть — parse будет автоматически completed, т.к. `currentStep` начинается с 'transcribe' после auto-parse.

## Результат

### Новый flow:

1. Пользователь выбирает файл → открывается ProcessingModal
2. Выбирает "Пошагово" → открывается StepByStep
3. **Автоматически** выполняется parse (показывается loading)
4. После parse: показывается форма с **правильным pipeline** (educational или leadership)
5. `currentStep='transcribe'`, parse уже показан как ✅ completed
6. Пользователь продолжает с transcribe

### UI состояния:

```
┌─────────────────┐
│  isInitializing │  ← Loading: "Анализ метаданных файла..."
│     (true)      │
└────────┬────────┘
         │ parse success
         ▼
┌─────────────────┐
│  isInitializing │  ← Ready: правильный pipeline + кнопка "Выполнить" для transcribe
│    (false)      │
└─────────────────┘
```

## Верификация

1. Открыть inbox, выбрать файл, нажать "Обработать"
2. Выбрать "Пошагово"
3. **Проверить:** появляется loading "Анализ метаданных файла..."
4. **Проверить:** после загрузки показывается форма с:
   - Parse как ✅ completed
   - Transcribe как текущий шаг
   - Правильный pipeline (educational или leadership в зависимости от файла)
5. Проверить для файла с `#` маркером (leadership) — должен показываться pipeline со story
6. Проверить для обычного файла (ПШ) — должен показываться pipeline с longread + summarize
