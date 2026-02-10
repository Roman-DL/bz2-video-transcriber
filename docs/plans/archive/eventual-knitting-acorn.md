# План: UI улучшения пошаговой обработки

## Примечание по архитектуре

**Данные остаются, убираем только отображение в UI:**

| Метрика | Где используется | Что делаем |
|---------|------------------|------------|
| `topic_area`, `tags` | Сохраняются в `pipeline_results.json` и frontmatter MD | Убираем отображение в UI |
| `change_percent` | Computed field в CleanedTranscript | Переносим в панель метрик |
| "X концепций", "Y цитат" | Подсчёт длины массивов (не отдельные поля) | Не отображаем |

**Никаких изменений в бэкенде или типах не требуется.** Все данные продолжают генерироваться LLM и сохраняться в архив для БЗ 2.0.

---

## Обзор задач

| # | Задача | Файл | Сложность |
|---|--------|------|-----------|
| 1 | Убрать message во время выполнения | StepByStep.tsx | Простая |
| 2 | Реорганизация метрик в шапках | 4 view-компонента | Средняя |
| 3 | Лонгрид: убрать Область/Теги, добавить % сокращения | LongreadView.tsx | Простая |
| 4 | Конспект: убрать Область/Теги и индикаторы | SummaryView.tsx | Простая |
| 5 | Исправить синхронизацию "ТЕКУЩИЙ" | StepByStep.tsx | Средняя |
| 6 | Упростить список файлов в CompletionCard | CompletionCard.tsx | Простая |

---

## Задача 1: Убрать message во время выполнения

**Файл:** `frontend/src/components/processing/StepByStep.tsx`

**Проблема:** Строка 940 показывает SSE message типа "Generating summary from transcript (4,188 chars)" — избыточная информация.

**Решение:** Строка 940 — убрать `message ||`:
```tsx
// Было:
{message || getStepDescription(currentStep)}

// Станет:
{getStepDescription(currentStep)}
```

---

## Задача 2: Реорганизация метрик в шапках

**Концепция:** Время выполнения выделить в badge, остальные метрики в отдельную панель.

### 2.1 CleanedTranscriptView

**Файл:** `frontend/src/components/results/TranscriptView.tsx` (строки 89-104)

**Изменения:**
```tsx
// Время — выделенный badge
{transcript.processing_time_sec !== undefined && (
  <div className="mb-2 shrink-0">
    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-50 text-emerald-700 text-xs font-medium rounded">
      {formatTime(transcript.processing_time_sec)}
    </span>
  </div>
)}

// Метрики — панель
<div className="text-xs text-gray-500 mb-2 shrink-0 flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 bg-gray-50 rounded-lg">
  <span>{formatNumber(transcript.cleaned_length)} симв.</span>
  <span>{formatNumber(transcript.words)} слов</span>
  <span title="Изменение объёма после очистки">
    {transcript.change_percent > 0 ? '+' : ''}{transcript.change_percent.toFixed(1)}%
  </span>
</div>
```

### 2.2 LongreadView

**Файл:** `frontend/src/components/results/LongreadView.tsx` (строки 66-78)

Аналогичная структура: время в badge, метрики в панель.

### 2.3 SummaryView

**Файл:** `frontend/src/components/results/SummaryView.tsx` (строки 75-87)

Аналогичная структура.

### 2.4 RawTranscriptView

**Файл:** `frontend/src/components/results/TranscriptView.tsx` (строки 27-50)

Аналогичная структура (время в badge, остальное в панель).

---

## Задача 3: Лонгрид — убрать структуру, добавить % сокращения

**Файл:** `frontend/src/components/results/LongreadView.tsx`

### 3.1 Удалить секцию Область/Теги (строки 98-122)
Удалить весь блок с `topic_area` и `tags`.

### 3.2 Добавить props для расчёта сокращения

```tsx
interface LongreadViewProps {
  longread: Longread;
  cleanedText?: string;
  cleanedChars?: number;  // ДОБАВИТЬ
  showDiff?: boolean;
  onToggleDiff?: () => void;
}
```

### 3.3 Добавить метрику сокращения в панель метрик

```tsx
{cleanedChars !== undefined && cleanedChars > 0 && (
  <span title="Изменение относительно очищенного транскрипта">
    {Math.round(((longread.chars - cleanedChars) / cleanedChars) * 100)}% от очистки
  </span>
)}
```

### 3.4 Обновить вызов в StepByStep.tsx

Передать `cleanedChars={data.cleanedTranscript?.cleaned_length}`.

---

## Задача 4: Конспект — убрать структуру и индикаторы

**Файл:** `frontend/src/components/results/SummaryView.tsx`

### 4.1 Удалить секцию Область/Теги (строки 94-121)
Удалить весь блок с `topic_area` и `tags`.

### 4.2 Удалить индикаторы в StepByStep.tsx

Найти и удалить отображение "X концепций", "Y цитат" для summary в правой панели (если есть в header вкладки).

---

## Задача 5: Исправить синхронизацию "ТЕКУЩИЙ"

**Файл:** `frontend/src/components/processing/StepByStep.tsx`

### 5.1 Изменить логику isCurrent (строка 1012)

```tsx
// Было:
const isCurrent = step === lastCompletedLLMStep && status === 'completed';

// Станет:
const stepTab = getTabForStep(step);
const isSelected = stepTab !== null && stepTab === activeTab;
const isCurrent = isSelected && status === 'completed';
```

### 5.2 Кнопка настроек (строка 1013)

Логика `hasSettings` остаётся: `isLLMStep(step) && isCurrent` — теперь будет привязана к выбранной вкладке.

### 5.3 Проверить каскадный сброс

Функция `resetDataFromStep()` (строки 360-383) уже реализует каскадный сброс — нужно только убедиться, что работает корректно при перезапуске.

---

## Задача 6: Упростить список файлов в CompletionCard

**Файл:** `frontend/src/components/processing/CompletionCard.tsx`

### 6.1 Заменить карточки на простой список (строки 37-46)

```tsx
// Было:
<div className="space-y-1 mb-4 max-h-40 overflow-y-auto">
  {files.map((file, i) => (
    <div key={i} className="px-2.5 py-1.5 bg-white rounded-lg border border-emerald-100 text-xs">
      <span className="font-mono text-gray-700 break-all">{file}</span>
    </div>
  ))}
</div>

// Станет:
<ul className="space-y-0.5 mb-4 text-xs">
  {files.map((file, i) => (
    <li key={i} className="flex items-start gap-2">
      <span className="text-emerald-500 mt-0.5">•</span>
      <span className="font-mono text-gray-700 break-all">{file}</span>
    </li>
  ))}
</ul>
```

Удаление `max-h-40` убирает прокрутку.

---

## Порядок реализации

1. **Задача 6** — CompletionCard (изолированный компонент)
2. **Задача 1** — message (одна строка)
3. **Задача 4** — SummaryView (удаление кода)
4. **Задача 3** — LongreadView (удаление + добавление props)
5. **Задача 2** — Метрики (4 компонента, один паттерн)
6. **Задача 5** — isCurrent (логика синхронизации)

---

## Файлы для изменения

- `frontend/src/components/processing/StepByStep.tsx`
- `frontend/src/components/processing/CompletionCard.tsx`
- `frontend/src/components/results/TranscriptView.tsx`
- `frontend/src/components/results/LongreadView.tsx`
- `frontend/src/components/results/SummaryView.tsx`

---

## Тестирование

1. Запустить пошаговую обработку
2. Проверить отсутствие динамического message во время выполнения
3. Проверить новую структуру метрик (время в badge, остальное в панели)
4. Проверить отсутствие Область/Теги в лонгриде и конспекте
5. Проверить метрику "% от очистки" в лонгриде
6. Проверить синхронизацию "ТЕКУЩИЙ" при клике на вкладки и этапы
7. Проверить простой список файлов в CompletionCard
