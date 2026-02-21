# Редактирование лонгрида перед чанкированием

## Контекст

После генерации лонгрида в пошаговом режиме артефакты транскрипции (ошибки распознавания, гарбледные слова, неточные формулировки) попадают в финальный текст. Сейчас единственный вариант — перезапустить весь этап. Нужна возможность точечно исправить текст лонгрида до запуска chunk.

**Ключевое наблюдение:** Chunk читает `data.longread.sections` из React-стейта (`usePipelineProcessor.ts:497`). Бэкенд менять не нужно — достаточно обновить стейт на фронтенде.

## Подход: Markdown-textarea + обратный парсинг

Единый `<textarea>` с полным markdown лонгрида. После сохранения правок — парсинг markdown обратно в объект `Longread` (split по `## ` заголовкам). Это обеспечивает консистентность для chunk, description generator и save.

## Изменения

### 1. `usePipelineProcessor.ts` — добавить `updateStepData`

Метод для обновления `data` из внешних компонентов:

```typescript
// Интерфейс (~строка 108):
updateStepData: (updates: Partial<StepData>) => void;

// Реализация:
const updateStepData = useCallback((updates: Partial<StepData>) => {
  setData(prev => ({ ...prev, ...updates }));
}, []);
```

~5 строк кода. Также изменить chunk case (строка 487-500): если есть `data.editedMarkdown` — использовать его вместо построения из `sections`.

Добавить `editedMarkdown?: string` в `StepData`.

### 2. `LongreadView.tsx` — режим редактирования

Основное изменение. Новые пропсы:

```typescript
editable?: boolean;
onLongreadUpdate?: (updated: Longread) => void;
```

**Локальный стейт:**
- `isEditing` — тоглер просмотр/редактирование
- `editedText` — текст в textarea (инициализируется из `formatLongreadAsMarkdown`)
- `isModified` — были ли изменения

**UI в режиме редактирования:**
- Кнопка "Редактировать" / "Просмотр" (рядом с "Сравнить с очисткой")
- Один `<textarea>` с auto-resize на весь контент
- Кнопки "Сохранить" и "Сбросить" при наличии изменений
- Бейдж "изменено" в метриках

**Обратный парсинг при сохранении (~15 строк):**

```typescript
function parseMarkdownToLongread(markdown: string, original: Longread): Longread {
  // 1. Split по "---" → до разделителя = основной контент, после = conclusion
  // 2. Split основного контента по /^## /m → первый блок = introduction, остальные = sections
  // 3. Из каждой секции: первая строка = title, остальное = content
  // 4. Пересчитать wordCount по секциям и totalWordCount
  // 5. Сохранить метаданные из original (modelName, tokensUsed, cost, etc.)
}
```

**Взаимоисключение:** diff-режим и edit-режим не показываются одновременно.

### 3. `StepByStep.tsx` — проброс пропсов

```tsx
<LongreadView
  longread={data.longread}
  editable={!isLoading}
  onLongreadUpdate={(updated) => updateStepData({ longread: updated })}
/>
```

### 4. `usePipelineProcessor.ts` — chunk case обновление

Строки 496-499: заменить построение markdown из sections на `formatLongreadAsMarkdown(data.longread)` — так chunk получит markdown идентичный тому, что видел и редактировал пользователь (включая introduction и conclusion).

## Файлы для изменения

| Файл | Изменение |
|------|-----------|
| `frontend/src/hooks/usePipelineProcessor.ts` | +`updateStepData`, обновить chunk case |
| `frontend/src/components/results/LongreadView.tsx` | Режим редактирования (основной объём) |
| `frontend/src/components/processing/StepByStep.tsx` | Проброс пропсов в LongreadView |

**Бэкенд: изменений НЕТ.**

## Проверка

1. Сгенерировать лонгрид → "Редактировать" → изменить текст → "Сохранить"
2. Word count обновился в метриках
3. Chunk → чанки содержат отредактированный текст
4. Save → сохранённый файл содержит правки
5. "Сбросить" → текст возвращается к оригиналу
6. Перезапустить longread → edit-стейт сбрасывается
7. Diff-режим и edit-режим не конфликтуют
