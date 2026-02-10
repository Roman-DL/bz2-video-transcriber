# План: Компактная форма автоматической обработки

## Цель

Обновить дизайн формы автоматической обработки согласно требованиям:
- Сократить высоту с ~500px до ~280px
- Убрать метрики этапов и список файлов
- Добавить кнопку "Открыть в архиве"

## Архитектурное решение

**Вынести общую логику в хук `usePipelineProcessor`** — гарантирует одинаковое поведение в обоих режимах:

```
┌─────────────────────────────────────────────────────────────┐
│                   usePipelineProcessor                       │
│  (общая логика: state, steps, auto-run, progress, retry)    │
└─────────────────────┬───────────────────┬───────────────────┘
                      │                   │
         ┌────────────▼────────┐  ┌───────▼─────────────┐
         │    StepByStep.tsx   │  │ AutoProcessingCompact│
         │   (пошаговый UI)    │  │   (компактный UI)    │
         └─────────────────────┘  └──────────────────────┘
```

**Преимущества:**
- Изменения логики в одном месте
- Разные UI для разных сценариев
- Чистая архитектура без дублирования

## Файлы

| Файл | Действие |
|------|----------|
| `frontend/src/hooks/usePipelineProcessor.ts` | Создать |
| `frontend/src/components/processing/AutoProcessingCompact.tsx` | Создать |
| `frontend/src/components/processing/ProcessingModal.tsx` | Изменить |
| `frontend/src/components/processing/StepByStep.tsx` | Рефакторинг (использовать хук) |
| `frontend/src/App.tsx` | Изменить (передать onOpenArchive) |
| `docs/architecture.md` | Обновить |

## Детали реализации

### 1. Создать usePipelineProcessor.ts

Хук инкапсулирует всю логику обработки pipeline:

```typescript
interface UsePipelineProcessorOptions {
  filename: string;
  initialSlides: SlideFile[];
  autoRun: boolean;
}

interface UsePipelineProcessorResult {
  // State
  status: 'idle' | 'running' | 'completed' | 'error';
  currentStep: PipelineStep;
  currentStepIndex: number;
  pipelineSteps: PipelineStep[];
  progress: number;
  message: string | null;
  estimatedSeconds: number | null;
  elapsedSeconds: number | null;
  error: string | null;

  // Data
  data: StepData;
  contentType: ContentType;

  // Actions
  runStep: (step: PipelineStep) => Promise<void>;
  retry: () => void;

  // Helpers
  getStepStatus: (step: PipelineStep) => StepStatus;
  isLoading: boolean;
  isComplete: boolean;
}

export function usePipelineProcessor(options: UsePipelineProcessorOptions): UsePipelineProcessorResult
```

**Логика внутри хука:**
- Инициализация step хуков (useStepParse, useStepTranscribe, etc.)
- Определение pipelineSteps на основе contentType и hasSlides
- Auto-run эффект для последовательного выполнения
- Функции getCurrentProgress, getStepStatus
- Управление состоянием (currentStep, data, error)

### 2. Создать AutoProcessingCompact.tsx

Компактный UI согласно референсу:

```
┌─────────────────────────────────────────────────────────────┐
│ АВТОМАТИЧЕСКАЯ ОБРАБОТКА                           Отменить │
├─────────────────────────────────────────────────────────────┤
│ filename.mp3                                                │
├─────────────────────────────────────────────────────────────┤
│  🔄 ВЫПОЛНЯЕТСЯ                                             │
│  Этап (N/M)                                     менее 5 сек │
│  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  33%   │
├─────────────────────────────────────────────────────────────┤
│  ✓ Парсинг метаданных                                       │
│  ● Транскрипция (Whisper)                                   │
│  ○ Очистка текста                                           │
│  ...                                                        │
├─────────────────────────────────────────────────────────────┤
│  [📂 Открыть в архиве]  (при завершении)                    │
└─────────────────────────────────────────────────────────────┘
```

**Размеры:**
- Отступ между этапами: 6px (py-1.5)
- Иконка статуса: 20px (w-5 h-5)
- Шрифт этапа: 13px (text-[13px])
- Padding секций: 12px (p-3)
- Progress bar height: 6px (h-1.5)

**Состояния:**
- `running` — spinner, прогресс-бар, ETA
- `completed` — зелёная иконка, кнопка "Открыть в архиве"
- `error` — красная иконка, кнопки "Повторить" / "Закрыть"

### 3. Рефакторинг StepByStep.tsx

Заменить внутреннюю логику на вызов `usePipelineProcessor`:

```typescript
export function StepByStep({ filename, onComplete, onCancel, autoRun = false, initialSlides = [] }) {
  const processor = usePipelineProcessor({
    filename,
    initialSlides,
    autoRun,
  });

  // UI использует processor.status, processor.currentStep, etc.
}
```

**Удалить из StepByStep:**
- Строки 790-956 (auto-режим layout) — переносится в AutoProcessingCompact
- Дублированную логику state/effects — переносится в хук

### 4. Изменить ProcessingModal.tsx

```tsx
export function ProcessingModal({ isOpen, filename, mode, slides, onClose, onOpenArchive }) {
  if (!filename) return null;

  const isAutoRun = mode === 'auto';

  return (
    <Modal isOpen={isOpen} onClose={onClose} closable={!isAutoRun} size={isAutoRun ? 'md' : 'full'} noPadding>
      {isAutoRun ? (
        <AutoProcessingCompact
          filename={filename}
          initialSlides={slides}
          onCancel={onClose}
          onOpenArchive={onOpenArchive}
        />
      ) : (
        <StepByStep
          filename={filename}
          autoRun={false}
          initialSlides={slides}
          onComplete={onClose}
          onCancel={onClose}
        />
      )}
    </Modal>
  );
}
```

### 5. Изменить App.tsx

Добавить callback `onOpenArchive`:
- Закрыть модалку
- Переключить вкладку на Archive
- Выбрать элемент по archive_path из metadata

### 6. Обновить документацию

Добавить в `docs/architecture.md` описание:
- Хук `usePipelineProcessor` — общая логика обработки
- Разделение UI компонентов (StepByStep / AutoProcessingCompact)

## Порядок выполнения

1. **Создать `usePipelineProcessor.ts`** — извлечь логику из StepByStep
2. **Создать `AutoProcessingCompact.tsx`** — компактный UI
3. **Рефакторинг `StepByStep.tsx`** — использовать хук
4. **Обновить `ProcessingModal.tsx`** — ветвление по mode
5. **Обновить `App.tsx`** — передать onOpenArchive
6. **Тестирование** — все состояния и режимы
7. **Обновить `docs/architecture.md`**

## Верификация

1. Запустить автоматическую обработку файла без слайдов (7 этапов)
2. Запустить с прикреплёнными слайдами (8 этапов)
3. Проверить пошаговый режим — функциональность не изменилась
4. Проверить состояние "Завершено" — кнопка "Открыть в архиве"
5. Проверить состояние "Ошибка" — кнопки "Повторить" / "Закрыть"
6. Проверить отмену во время обработки
7. Убедиться в высоте ~280px (визуально компактнее)
