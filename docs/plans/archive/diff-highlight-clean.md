# Подсветка глоссарных замен в InlineDiffView

## Контекст

В v0.72 очистка упрощена до глоссарной подстановки — output ≈ input (-0.8%), разница только в заменённых терминах. Сейчас InlineDiffView показывает два plain-text блока без подсветки различий. Пользователь не видит, что именно изменилось, и не может быстро оценить качество очистки.

**Цель:** добавить word-level diff подсветку + кнопку "Копировать отчёт" для анализа качества очистки в AI-разговоре.

## Шаги реализации

### 1. Установить `diff` npm пакет

```bash
cd frontend && npm install diff && npm install -D @types/diff
```

### 2. Создать `frontend/src/utils/diffUtils.ts`

Три чистые функции:

- **`computeWordDiff(left, right)`** → `{ leftTokens, rightTokens }` — массивы `DiffToken { text, type: 'equal'|'added'|'removed' }` для рендера подсветки в каждой панели
- **`aggregateDiffChanges(left, right)`** → `DiffReport { replacements, deletions, additions, totalChanges }` — агрегированная статистика (соседние removed+added = замена, одиночные = удаление/вставка)
- **`generateDiffReport(left, right, meta)`** → markdown-строка отчёта для буфера обмена

### 3. Добавить экспорт в `frontend/src/utils/index.ts`

Реэкспорт `computeWordDiff`, `generateDiffReport`, типов.

### 4. Модифицировать `frontend/src/components/common/InlineDiffView.tsx`

Главное изменение компонента:

- **Новый проп** `reportMeta?: { modelName?: string }` — если передан, включается подсветка diff и кнопка "Отчёт". Без пропа — компонент работает как раньше (plain text)
- **`useMemo`** для `computeWordDiff(leftText, rightText)` — вычисляет токены при изменении текстов (только если `reportMeta` передан)
- **`renderTokens(tokens, highlight)`** — рендерит массив `<span>` с CSS-классами:
  - `removed`: `bg-red-100 text-red-800 line-through`
  - `added`: `bg-emerald-100 text-emerald-800`
  - `equal`: без стилей
  - Если `highlight=false` — plain text без подсветки
- **Состояние** `highlightEnabled` (toggle в хедере, чекбокс + иконка `Highlighter`)
- **Кнопка "Отчёт"** с `Copy`/`Check` иконкой — вызывает `generateDiffReport()` и `navigator.clipboard.writeText()`, показывает "Скопировано" на 2 секунды

### 5. Передать `reportMeta` из `TranscriptView.tsx`

В `CleanedTranscriptView` (строка 76) добавить `reportMeta={{ modelName: transcript.modelName }}` к `<InlineDiffView>`.

`LongreadView` **не меняется** — не передаёт `reportMeta`, компонент работает как раньше (plain text, без подсветки и без кнопки "Отчёт"). Для лонгрида diff бессмысленен — текст переработан на ~70-80%.

## Затрагиваемые файлы

| Файл | Действие |
|------|----------|
| `frontend/package.json` | Добавить `diff`, `@types/diff` |
| `frontend/src/utils/diffUtils.ts` | **Новый файл** — утилиты diff |
| `frontend/src/utils/index.ts` | Добавить реэкспорт |
| `frontend/src/components/common/InlineDiffView.tsx` | Подсветка, toggle, кнопка "Отчёт" |
| `frontend/src/components/results/TranscriptView.tsx` | Передать `reportMeta` |

## Формат отчёта (буфер обмена)

```
## Отчёт об очистке
Модель: claude-haiku-4-5 | Слов: 9656 → 9575 (-0.8%) | Замен: 52

### Замены (сгруппированные)
Гербалай → Herbalife (×21)
волл-тим → Ворлд-тим (×5)
встречи возможностей → ВВК (×2)

### Удаления
короче, (×12) | ну, (×1)
```

## Проверка

1. `cd frontend && npm run build` — проект собирается без ошибок
2. Открыть пошаговый режим → очистка → "Сравнить с транскриптом"
3. Убедиться: замены подсвечены красным/зелёным в обеих панелях
4. Переключить "Подсветка" — подсветка пропадает, plain text
5. Нажать "Отчёт" — отчёт в буфере, кнопка показывает "Скопировано"
6. Вставить отчёт — формат корректный, замены агрегированы
7. Синхронный скролл продолжает работать с подсветкой
8. LongreadView → без подсветки и без кнопки "Отчёт" (как раньше)
