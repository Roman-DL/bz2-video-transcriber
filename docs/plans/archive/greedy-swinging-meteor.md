# План доработки Transcriptor v2

> **Требования:** [docs/proposals/transcriptor-v2-requirements.md](docs/proposals/transcriptor-v2-requirements.md)
> **Референс UI:** [docs/reference/StepByStepRedesign-reference.jsx](docs/reference/StepByStepRedesign-reference.jsx)

---

## Обзор изменений

### Цели
- Упростить интерфейс (убрать избыточные метрики)
- Добавить полезные метрики для отладки промптов (токены, стоимость, время)
- Реализовать Diff View для сравнения текстов
- Унифицировать отображение метрик

### Объём работы
- **Backend:** ~10 файлов
- **Frontend:** ~12 файлов
- **Документация:** ~5 файлов

---

## Фазы реализации

### Фаза 1: Backend — Расширенные метрики в API ✅ COMPLETED (v0.42)

**Цель:** Добавить confidence, tokens_used, cost, processing_time в API response

**Файлы для изменения:**

1. **[backend/app/models/schemas.py](backend/app/models/schemas.py)** — Расширение Pydantic моделей
   - Добавить `TokensUsed` модель: `{input: int, output: int}`
   - `RawTranscript`: добавить `confidence: float | None`, `chars: int`, `words: int`, `processing_time_sec: float`
   - `CleanedTranscript`: добавить `words: int`, `tokens_used: TokensUsed`, `cost: float`, `processing_time_sec: float`, `change_percent: float`
   - `Longread`: добавить `chars: int`, `tokens_used`, `cost`, `processing_time_sec`, `change_percent`
   - `Summary`: добавить `chars: int`, `words: int`, `tokens_used`, `cost`, `processing_time_sec`
   - `TranscriptChunks`: добавить `total_tokens: int`

2. **[config/models.yaml](config/models.yaml)** — Добавить pricing в конфигурацию моделей
   ```yaml
   # В секции models добавить pricing для каждой модели:
   claude-sonnet-4-5:
     provider: claude
     context_profile: large
     context_tokens: 200000
     pricing:
       input: 3.00   # $ per 1M tokens
       output: 15.00

   # Локальные модели — pricing не указывается (= бесплатно)
   gemma2:
     provider: ollama
     context_profile: small
     # pricing отсутствует = 0
   ```

3. **[backend/app/utils/pricing_utils.py](backend/app/utils/pricing_utils.py)** — НОВЫЙ файл
   ```python
   def get_model_pricing(model_name: str) -> dict | None
   def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float
   ```

4. **[backend/app/api/models_routes.py](backend/app/api/models_routes.py)** — Расширить API
   - Добавить pricing в response `/api/models/available`
   - Frontend получает цены из API, не хардкодит

5. **[backend/app/services/ai_clients/claude_client.py](backend/app/services/ai_clients/claude_client.py)**
   - Изменить `chat()` возвращать `tuple[str, dict]` где dict содержит `{input_tokens, output_tokens}`
   - Или добавить метод `chat_with_usage()`

6. **[backend/app/services/transcriber.py](backend/app/services/transcriber.py)**
   - В `_parse_response()` извлечь `avg_logprob` из сегментов Whisper
   - Рассчитать confidence: `math.exp(avg(avg_logprob))`
   - Добавить chars, words, processing_time в RawTranscript

7. **[backend/app/services/cleaner.py](backend/app/services/cleaner.py)**
   - Собирать `tokens_used` из Claude response
   - Рассчитать `cost` через `calculate_cost()`
   - Добавить `words`, `change_percent`, `processing_time_sec`

8. **[backend/app/services/longread_generator.py](backend/app/services/longread_generator.py)**
   - Аналогично cleaner: tokens_used, cost, processing_time_sec
   - Добавить chars, change_percent (vs cleaned_transcript)

9. **[backend/app/services/summary_generator.py](backend/app/services/summary_generator.py)**
   - tokens_used, cost, processing_time_sec, chars, words

10. **[backend/app/services/story_generator.py](backend/app/services/story_generator.py)**
    - tokens_used, cost, processing_time_sec (для полноты)

11. **[backend/app/services/chunker.py](backend/app/services/chunker.py)**
    - Добавить `total_tokens` через `estimate_tokens()`

**Критерии завершения:**
- [x] API response содержит все новые поля
- [x] Тест на сервере: `/api/step/clean` возвращает tokens_used, cost
- [x] Backward compatibility сохранена

**Зависимости:** Нет

**Реализовано в v0.42:**
- `TokensUsed` модель с computed `total`
- `ChatUsage` dataclass + методы `chat_with_usage()`, `generate_with_usage()` в ClaudeClient
- Confidence из avg_logprob в transcriber
- Token tracking и cost calculation во всех LLM сервисах
- Pricing в config/models.yaml
- `pricing_utils.py` — расчёт стоимости

---

### Фаза 1.1: Рефакторинг AI клиентов ✅ COMPLETED (v0.43)

**Цель:** Убрать дублирование кода и `isinstance()` проверки. Унифицировать интерфейс.

**Изменения:**
- Перенести `ChatUsage` в `base.py`
- Изменить Protocol: `chat()` и `generate()` возвращают `tuple[str, ChatUsage]`
- ClaudeClient: удалить старые методы, переименовать `*_with_usage` → основные
- OllamaClient: возвращать `ChatUsage(0, 0)` — честно отражает отсутствие tracking
- Сервисы: убрать все `isinstance(self.ai_client, ClaudeClient)` проверки

**Файлы:** 8 файлов (ai_clients/*, cleaner, longread, summary, story)

**Детальный план:** см. `.claude/plans/bubbly-twirling-feather.md`

**Критерии завершения:**
- [x] Единый интерфейс BaseAIClient
- [x] Нет `isinstance()` проверок в сервисах
- [x] Тесты проходят (синтаксис проверен)

**Зависимости:** Фаза 1

**Реализовано в v0.43:**
- `ChatUsage` перенесён в `base.py`
- Protocol `BaseAIClient` изменён: методы возвращают `tuple[str, ChatUsage]`
- `ClaudeClient`: удалены старые методы, `chat_with_usage()` → `chat()`
- `OllamaClient`: возвращает `ChatUsage(0, 0)`
- Сервисы: убраны все `isinstance(self.ai_client, ClaudeClient)` проверки
- Унифицированный код: `response, usage = await client.chat(...)`

---

### Фаза 2: Frontend — Типы и утилиты ✅ COMPLETED (v0.44)

**Цель:** Синхронизировать TypeScript типы и добавить утилиты форматирования

**Файлы для изменения:**

1. **[frontend/src/api/types.ts](frontend/src/api/types.ts)** — Расширить TypeScript типы
   - Добавить `TokensUsed` interface: `{input: number, output: number}`
   - Добавить `ModelPricing` interface: `{input: number, output: number}`
   - Расширить `RawTranscript`: confidence, chars, words, processing_time_sec
   - Расширить `CleanedTranscript`, `Longread`, `Summary`: tokens_used, cost, processing_time_sec
   - Расширить `AvailableModelsResponse` для передачи pricing

2. **[frontend/src/utils/formatUtils.ts](frontend/src/utils/formatUtils.ts)** — НОВЫЙ файл
   ```typescript
   formatTime(seconds: number): string  // "235мс" / "23с" / "1м 23с"
   formatCost(cost: number): string     // "бесплатно" / "~$0.03"
   countWords(text: string): number
   formatNumber(n: number): string      // "1 234"
   ```

3. **[frontend/src/utils/index.ts](frontend/src/utils/index.ts)** — экспорт новых утилит

4. **Pricing из API:** Frontend получает pricing из `/api/models/available`, не хардкодит цены

**Критерии завершения:**
- [x] TypeScript компилируется без ошибок
- [x] Утилиты работают корректно (проверить в консоли)

**Зависимости:** Фаза 1

**Реализовано в v0.44:**
- `TokensUsed` interface
- Расширены типы: `RawTranscript`, `CleanedTranscript`, `Longread`, `Summary`, `Story`, `TranscriptChunks`
- `formatUtils.ts`: `formatTime()`, `formatCost()`, `formatNumber()`, `formatTokens()`
- `index.ts` для re-export всех утилит

---

### Фаза 3: Frontend — Компоненты результатов ✅ COMPLETED (v0.45)

**Цель:** Обновить отображение метрик в компонентах результатов

**Файлы для изменения:**

1. **[frontend/src/components/results/TranscriptView.tsx](frontend/src/components/results/TranscriptView.tsx)**
   - Header: язык, символы, слова, confidence (📈 94%), время
   - Убрать "сегменты"
   - Badge с моделью

2. **[frontend/src/components/results/CleanedTranscriptView.tsx](frontend/src/components/results/CleanedTranscriptView.tsx)** — может потребоваться рефакторинг
   - Header: символы, слова, % изменения, время
   - Footer: токены (вх/вых), стоимость
   - Кнопка "Сравнить с транскриптом"

3. **[frontend/src/components/results/LongreadView.tsx](frontend/src/components/results/LongreadView.tsx)**
   - Убрать "секции" из header
   - Header: символы, слова, % изменения, время
   - Footer: токены, стоимость
   - Кнопка "Сравнить с очисткой"

4. **[frontend/src/components/results/SummaryView.tsx](frontend/src/components/results/SummaryView.tsx)**
   - Убрать "концепции/цитаты" из header
   - Header: символы, слова, время
   - Footer: токены, стоимость

5. **[frontend/src/components/results/ChunksView.tsx](frontend/src/components/results/ChunksView.tsx)**
   - Header: количество чанков, общие токены
   - Убрать "слов/чанк"

6. **[frontend/src/components/common/ResultFooter.tsx](frontend/src/components/common/ResultFooter.tsx)** — НОВЫЙ компонент
   ```tsx
   <ResultFooter
     tokensUsed={{input: 1850, output: 1720}}
     cost={0.03}
     model="claude-sonnet-4-5"
   />
   ```

**Критерии завершения:**
- [x] Все компоненты показывают обновленные метрики
- [x] Footer отображается для LLM-шагов
- [ ] Визуально соответствует референсу → ожидает Фазу 4 (Diff View, CompletionCard)

**Зависимости:** Фаза 2

**Реализовано в v0.45:**
- `ResultFooter` компонент для отображения токенов, стоимости, модели
- `RawTranscriptView`: язык, символы, слова, уверенность (%), время, модель
- `CleanedTranscriptView`: символы, слова, % изменения, время + ResultFooter
- `LongreadView`: символы, слова, время + ResultFooter (убраны "секции")
- `SummaryView`: символы, слова, время + ResultFooter (убраны "концепции/цитаты")
- `ChunksView`: количество чанков, общие токены, модель
- `StoryView`: символы, блоки, время + ResultFooter

---

### Фаза 4: Frontend — Diff View и UI улучшения ✅ COMPLETED (v0.46)

**Цель:** Реализовать Diff View и улучшить общий UI

**Файлы для изменения:**

1. **[frontend/src/components/common/InlineDiffView.tsx](frontend/src/components/common/InlineDiffView.tsx)** — НОВЫЙ компонент
   - Toggle-режим (замена контента)
   - Два столбца с синхронным скроллом
   - Header: кнопка "Назад", checkbox синхронного скролла, разница в символах/%
   - Использовать референс из StepByStepRedesign-reference.jsx

2. **[frontend/src/components/processing/StepByStep.tsx](frontend/src/components/processing/StepByStep.tsx)**
   - Состояние: `showCleanedDiff`, `showLongreadDiff`
   - Интеграция InlineDiffView в content area
   - Контент на всю высоту: `flex-1 h-full min-h-0`
   - Обновить формат времени через `formatTime()`

3. **Обновление компонентов результатов:**
   - CleanedTranscriptView: props `showDiff`, `onToggleDiff`, `rawTranscript`
   - LongreadView: props `showDiff`, `onToggleDiff`, `cleanedTranscript`

4. **[frontend/src/components/processing/CompletionCard.tsx](frontend/src/components/processing/CompletionCard.tsx)** — выделить из StepByStep
   - Размеры файлов
   - Итоговые метрики: общее время, токены (вх/вых), стоимость
   - Без скролла (адаптивная высота)

**Критерии завершения:**
- [x] Diff View работает для очистки и лонгрида
- [x] Синхронный скролл функционирует
- [x] Контент занимает всю высоту
- [x] Итоговый блок показывает все метрики

**Зависимости:** Фаза 3

**Реализовано в v0.46:**
- `InlineDiffView` компонент с синхронным скроллом
- `CompletionCard` компонент с итоговыми метриками
- `CleanedTranscriptView`: props `rawText`, `showDiff`, `onToggleDiff`
- `LongreadView`: props `cleanedText`, `showDiff`, `onToggleDiff`
- `StepByStep`: состояния diff, функция `calculateTotals()`, интеграция CompletionCard

---

### Фаза 5: Документация и финализация

**Цель:** Актуализировать документацию, обновить версию

**Файлы для изменения:**

1. **[docs/proposals/transcriptor-v2-requirements.md](docs/proposals/transcriptor-v2-requirements.md)**
   - Отметить выполненные пункты в чеклисте
   - Добавить раздел "Реализовано"

2. **[docs/data-formats.md](docs/data-formats.md)**
   - Документировать новые поля в моделях
   - Примеры API response с tokens_used, cost

3. **[docs/api-reference.md](docs/api-reference.md)**
   - Обновить описание endpoints
   - Примеры response с новыми полями

4. **[CLAUDE.md](CLAUDE.md)**
   - Добавить информацию о MODEL_PRICING
   - Обновить структуру schemas.py

5. **[frontend/package.json](frontend/package.json)**
   - Обновить версию (0.41 → 0.42)

**Критерии завершения:**
- [ ] Документация актуальна
- [ ] Все требования выполнены
- [ ] Версия обновлена
- [ ] Деплой успешен

**Зависимости:** Фазы 1-4

---

## Сводная таблица

| Фаза | Название | Файлов | Можно деплоить | Зависимости |
|------|----------|--------|----------------|-------------|
| 1 | Backend метрики | ~10 | Да | — |
| 1.1 | Рефакторинг AI клиентов | 8 | Да | 1 |
| 2 | Frontend типы/утилиты | ~4 | Да | 1 |
| 3 | Компоненты результатов | ~6 | Да | 2 |
| 4 | Diff View и UI | ~4 | Да | 3 |
| 5 | Документация | ~5 | Да | 1-4 |

---

## Верификация

После каждой фазы:

1. **Фаза 1:** Запустить step-by-step на сервере, проверить API response
   ```bash
   curl -X POST http://100.64.0.1:8801/api/step/clean ...
   # Проверить: tokens_used, cost, processing_time_sec
   ```

2. **Фаза 2:** Убедиться что TypeScript компилируется
   ```bash
   cd frontend && npm run build
   ```

3. **Фаза 3-4:** Визуальная проверка в UI
   - Открыть step-by-step режим
   - Проверить метрики на каждом шаге
   - Проверить Diff View

4. **Фаза 5:** Полный E2E тест
   - Обработать тестовое видео
   - Проверить все метрики
   - Проверить итоговый блок

---

## Риски и митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Whisper API не возвращает avg_logprob | Низкая | Проверить verbose_json формат, сделать поле optional |
| Большой объём изменений в StepByStep.tsx | Средняя | Выделить компоненты: CompletionCard, InlineDiffView |
