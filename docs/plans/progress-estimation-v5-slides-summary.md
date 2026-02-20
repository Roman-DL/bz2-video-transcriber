# План: Обновление оценок прогресса + слайды в конспект

## Контекст

Обработка транскрипта со слайдами (19 слайдов, ~60K символов) выявила:

| Этап | Оценка | Факт | Ratio | Проблема |
|------|--------|------|-------|----------|
| Clean (haiku) | 74.6s | 163.2s | 2.19x | Коэффициент под Ollama |
| Slides (haiku) | 3.0s | 43.4s | 14.5x | Хардкод 3s/слайд |
| Longread (sonnet) | 86.0s | 306.1s | 3.56x | map-reduce вместо single-pass |
| Summary (sonnet) | 28.7s | 47.0s | 1.64x | Близко к норме |

Дополнительные находки:
- **Summary пустой** — Claude вернул невалидный JSON, парсинг упал, 0 concepts / 0 quotes
- **slides_text** не передаётся в summary (только в longread и story)
- **`cache_routes.py:280`** вызывает несуществующий `estimate_longread()`
- **TextSplitter** нарезает текст по 6K символов (под gemma2:9b), при Claude 200K это 15 частей вместо 2-3
- **`_fits_in_context()`** слишком консервативна — текст 67K ушёл в map-reduce, хотя помещается в single-pass

---

# Фаза 1: Исправления и доработки

Деплой → тестовый прогон → сбор PERF логов

## 1.1 Калибровка single-pass / map-reduce для longread

**Проблема:** Транскрипт 67K символов ушёл в map-reduce (15 частей, 306s), хотя при Claude 200K мог быть обработан single-pass (~30-60s).

**Причина 1: Слишком консервативная `_fits_in_context()`**

**Файл:** `backend/app/services/longread_generator.py`

Текущие константы и расчёт available:
```
available = 200K × 0.85 − 15K − 30K = 125K токенов
text = 67K × 2.5 = 168K токенов → 168K > 125K → map-reduce
```

Скорректировать:
- `TOKENS_PER_CHAR`: 2.5 → 2.0 (ближе к реальности для Claude tokenizer + русский)
- `OUTPUT_RESERVE_TOKENS`: 30K → 20K (при SINGLE_PASS_MAX_TOKENS=16K двойной запас не нужен)
- `CONTEXT_UTILIZATION`: 0.85 → 0.90 (prompt overhead уже учтён отдельно)

Новый расчёт: `200K × 0.90 − 15K − 20K = 145K` → `67K × 2.0 = 134K < 145K` → **single-pass**

**Причина 2: TextSplitter нарезает под 8K контекст**

**Файл:** `backend/app/services/text_splitter.py`

`PART_SIZE = 6000` (комментарий: *«Уменьшено для совместимости с gemma2:9b»*). Для Claude 200K — бессмысленно мелкая нарезка.

**Решение:** Передавать `part_size` в TextSplitter из конфига модели:
- `LongreadGenerator.__init__()` — читать `min_part_size` из конфига (large: 20000)
- Передавать в `TextSplitter(part_size=min_part_size)` вместо хардкода 6000
- Результат: `67K / (20K - 1.5K) = 3-4 части` вместо 15

## 1.2 Слайды в конспект (summary)

Добавить `slides_text` по цепочке (по паттерну longread/story):

1. **schemas.py** — добавить `slides_text: str | None = Field(default=None, ...)` в `StepSummarizeRequest`
2. **summary_generator.py** — добавить параметр `slides_text: str | None = None` в `generate()`, конкатенировать текст слайдов к транскрипту (паттерн: `"\n\n---\n\n## Дополнительная информация со слайдов презентации\n\n" + slides_text`)
3. **step_routes.py** — передать `slides_text=request.slides_text` в `orchestrator.summarize_from_cleaned()`
4. **orchestrator.py** — добавить `slides_text` параметр в `summarize_from_cleaned()`, передать в `generator.generate()`
5. **orchestrator.py** — `_do_educational_pipeline()` пока НЕ трогаем (full pipeline — отдельная задача)

## 1.3 Надёжный парсинг JSON (json-repair + retry)

**Проблема:** Claude вернул невалидный JSON (5084 символов, `stop=end_turn`), парсинг упал с `Expecting ',' delimiter` на позиции 3702. Вероятная причина — неэкранированная кавычка в русском тексте. Конспект пустой.

Longread устойчив благодаря map-reduce (8 независимых вызовов, сбой 1 не ломает остальные). Summary — 1 вызов со сложной JSON-схемой, сбой = пустой результат.

**Решение (2 уровня защиты):**

1. **json-repair** в `json_utils.py` — обогатить `parse_json_safe()`, чтобы все генераторы получили выгоду:
   - При `JSONDecodeError` → попытка repair → если успех, логировать `"JSON repaired successfully"`
2. **1 retry** в `summary_generator.generate()` — если json-repair не помог:
   - Повторить LLM вызов один раз, суммировать tokens_used

## 1.4 Инфраструктура оценки (estimate_longread, estimate_slides)

**Файлы:**
- `backend/app/services/progress_estimator.py` — добавить `estimate_longread()`, `estimate_slides()`
- `config/performance.yaml` — добавить секции `longread` и `slides` с начальными коэффициентами

Начальные коэффициенты (будут уточнены в Фазе 2):
- **longread**: `factor_per_1k_chars: 4.4, base_time: 10.0` (на основе map-reduce, завышены для single-pass)
- **slides**: `factor_per_slide: 2.3, base_time: 3.0`

**Обновление вызовов:**
- `step_routes.py`: заменить хардкод-множители на `estimate_longread()`, `estimate_slides()`, убрать `* 0.5` для summarize
- `orchestrator.py`: аналогично в `_do_educational_pipeline()` и `_do_leadership_pipeline()`
- `cache_routes.py:280`: уже вызывает `estimate_longread()` — заработает автоматически

## 1.5 ADR-016 — Надёжность парсинга JSON из LLM

**Файл:** `docs/decisions/016-llm-json-parsing-reliability.md`

- **Контекст:** Claude иногда возвращает невалидный JSON. Summary — single call со сложной схемой, падение = пустой результат.
- **Решение:** json-repair + 1 retry
- **Альтернатива на будущее:** structured output (Claude tool_use API), рассмотреть если текущее решение недостаточно надёжно
- **Статус:** Accepted

## Файлы Фазы 1

| Файл | Изменения |
|------|-----------|
| `backend/app/services/longread_generator.py` | Калибровка констант single-pass, part_size из конфига |
| `backend/app/models/schemas.py` | Добавить slides_text в StepSummarizeRequest |
| `backend/app/services/summary_generator.py` | slides_text + retry при JSON ошибке |
| `backend/app/utils/json_utils.py` | Интегрировать json-repair в parse_json_safe() |
| `backend/requirements.txt` | Добавить json-repair |
| `backend/app/services/progress_estimator.py` | Добавить estimate_longread(), estimate_slides() |
| `config/performance.yaml` | Добавить секции longread, slides |
| `backend/app/api/step_routes.py` | Заменить хардкод-оценки, передать slides_text |
| `backend/app/services/pipeline/orchestrator.py` | Заменить хардкод-оценки, slides_text в summarize |
| `docs/decisions/016-llm-json-parsing-reliability.md` | ADR |

## Верификация Фазы 1

1. `python3 -m py_compile` для всех изменённых .py файлов
2. Деплой → обработка того же транскрипта со слайдами
3. Проверить в логах:
   - Longread пошёл через single-pass (не map-reduce)
   - Summary не пустой (json-repair или retry сработали)
   - Summary содержит контекст слайдов
   - PERF логи с новыми таймингами

---

# Фаза 2: Калибровка коэффициентов (после тестового прогона)

На основе PERF логов из Фазы 1:

## 2.1 Обновление performance.yaml (коэффициенты v5)

Пересчитать по формуле `(actual - base_time) / (input_chars / 1000)`:
- **clean**: текущий 1.2, ожидаем ~2.7 (haiku)
- **longread**: начальный 4.4, пересчитать для single-pass (ожидаем значительно меньше)
- **slides**: начальный 2.3, проверить
- **summarize**: текущий 0.9, проверить

## 2.2 Обновление STAGE_WEIGHTS в progress_manager.py

Текущие веса откалиброваны на Ollama. После single-pass longread будет значительно быстрее (~30-60s вместо 306s), что изменит пропорции всех этапов.

Пересчитать по пропорции фактических таймингов из PERF логов.

## 2.3 Калибровка transcribe (отдельный прогон)

Требуется обработка реального видео (не MD-транскрипт) для замера Whisper.
