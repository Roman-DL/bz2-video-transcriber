# План: Исправление отображения лидерской истории и порядка блоков

## Проблемы

### 1. Лидерская история показывает структурированный вид
- `StoryView.tsx` выводит: заголовок с инсайтом, 4-колоночную сетку метрик, наставника/паттерн, 8 блоков с номерами в кружках, метаданные
- Формат лидерской истории ещё не финализирован
- Нужно выводить простым текстом как `LongreadView.tsx`

### 2. Неправильный порядок блоков результатов
Текущий порядок отображения в `StepByStep.tsx`:
```
metadata → rawTranscript → cleanedTranscript → chunks → longread → summary → story
```

Порядок выполнения для leadership: `parse → transcribe → clean → story → chunk → save`

**Проблема:** chunks отображается ПЕРЕД story, хотя выполняется ПОСЛЕ.

---

## Изменения

### Файл 1: [StoryView.tsx](frontend/src/components/results/StoryView.tsx)

Упростить по образцу `LongreadView.tsx`:
1. Добавить функцию `formatStoryAsMarkdown(story)` которая форматирует story как простой текст
2. Заменить сложную разметку на `whitespace-pre-wrap` текст
3. Оставить только футер с метаданными (модель, access_level)

**Формат вывода:**
```markdown
{main_insight}

## 1. {block_name}
{content}

## 2. {block_name}
{content}

...
```

### Файл 2: [StepByStep.tsx](frontend/src/components/processing/StepByStep.tsx)

Изменить порядок отображения блоков (строки 520-586):

**Было:**
```
cleanedTranscript → chunks → longread → summary → story
```

**Станет:**
```
cleanedTranscript → longread → summary → story → chunks
```

Переместить блок `{data.chunks && ...}` (строки 520-535) после блока `{data.story && ...}` (строки 571-586).

---

## Файлы для изменения

| Файл | Изменение |
|------|-----------|
| [frontend/src/components/results/StoryView.tsx](frontend/src/components/results/StoryView.tsx) | Упростить отображение до простого текста |
| [frontend/src/components/processing/StepByStep.tsx](frontend/src/components/processing/StepByStep.tsx) | Переместить chunks после story |

---

## Проверка

1. Запустить frontend: `cd frontend && npm run dev`
2. Открыть step-by-step обработку для leadership файла (с маркером #)
3. Проверить:
   - Лидерская история отображается простым текстом без структурированных метрик
   - После выполнения story и chunk — блок "Семантические чанки" появляется ПОСЛЕ "Лидерская история"
