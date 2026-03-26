# Миграция Orchestrator на Stage абстракцию

> Orchestrator должен использовать BaseStage вместо прямых вызовов сервисов — ADR-001 Phase 1

**Статус:** Done (v0.84)
**Дата:** 2026-03-26
**Версии:** v0.84

---

## 1. Проблема

Auto-pipeline (`orchestrator.process()`) вызывает сервисы напрямую, минуя stage абстракцию (`BaseStage`). Stage абстракция существует и используется в step-by-step режиме, но orchestrator её игнорирует.

**Текущая ситуация (три пути выполнения Clean):**
- `CleanStage.execute()` — stage абстракция, имеет pass-through для foreign. **Не используется ничем**
- `orchestrator._do_clean()` — метод для `process()` (full auto). **`process()` не вызывается** — фронтенд использует step endpoints
- `orchestrator.clean()` (строка 335) — step-by-step API endpoint. **Единственный реальный путь** — вызывает `cleaner.clean()` напрямую без проверки language

**Критично:** Фронтенд даже в auto-режиме вызывает step endpoints последовательно (через `usePipelineProcessor` hook), а не `orchestrator.process()`. Поэтому `_do_clean()` — мёртвый код.

**Почему это проблема:**
- Clean pass-through для foreign transcripts написан в `clean_stage.py` и `_do_clean()`, но **не в `orchestrator.clean()`** — единственном реальном пути
- При добавлении логики в stage нужно менять ТРИ места (stage, _do_clean, clean)
- `_do_clean()` и `process()` — мёртвый код, создаёт ложное впечатление работоспособности
- Нарушается ADR-001: "Фаза 1 мигрирует orchestrator на использование Stage абстракции" — так и не выполнена
- ADR-001 обещает "новые шаги добавляются без изменения orchestrator" — сейчас это неправда

---

## 2. Решение

Orchestrator.process() использует StageContext + BaseStage.execute() вместо прямых вызовов сервисов.

### Ключевые идеи

1. **StageContext как единый контейнер данных** — результаты передаются между stages через context, orchestrator не знает внутренности
2. **Orchestrator оркестрирует stages, не сервисы** — вызывает `stage.execute(context)`, не `cleaner.clean()`
3. **Progress ticker интегрируется в BaseStage** — сейчас каждый `_do_*` метод вручную создаёт/останавливает тикер, это можно унифицировать
4. **Step-by-step endpoints тоже используют stages** — единый путь выполнения

### Текущий flow (auto-pipeline)

```
orchestrator.process()
  ├── parse_filename() + metadata enrichment
  ├── _do_transcribe() → whisper_client.transcribe() напрямую
  ├── _do_clean() → cleaner.clean() напрямую [+ дублированный pass-through]
  ├── _do_educational_pipeline()
  │   ├── LongreadGenerator().generate() напрямую
  │   ├── SummaryGenerator().generate() напрямую
  │   ├── chunk_by_h2() напрямую
  │   └── _do_save_educational() → Saver().save() напрямую
  └── _do_leadership_pipeline() (аналогично)
```

### Целевой flow

```
orchestrator.process()
  ├── create stages + StageContext
  ├── for stage in pipeline:
  │     context = context.with_result(stage.name, await stage.execute(context))
  └── return context.get_result("save")
```

---

## 3. Scope

### Что рефакторить

| Метод orchestrator | Заменяется на Stage |
|---|---|
| `parse_filename()` + enrichment | `ParseStage.execute()` (уже существует, нужно дополнить speaker_info/language) |
| `_do_transcribe()` | `TranscribeStage.execute()` (уже существует) |
| `_do_clean()` | `CleanStage.execute()` (уже существует, уже имеет pass-through) |
| `LongreadGenerator().generate()` | `LongreadStage.execute()` (уже существует) |
| `SummaryGenerator().generate()` | `SummarizeStage.execute()` (уже существует) |
| `StoryGenerator().generate()` | `StoryStage.execute()` (уже существует) |
| `chunk_by_h2()` + description | `ChunkStage.execute()` (уже существует) |
| `Saver().save()` | `SaveStage.execute()` (уже существует) |

### Что НЕ менять

- Stage implementations — уже работают, интерфейс не меняется
- Step-by-step API endpoints — продолжают работать через stages
- Frontend — API контракт не меняется
- StageContext, BaseStage — существующие абстракции достаточны

### Что нужно дополнить в stages

- `ParseStage` — добавить enrichment (duration, speaker_info, language) для MD файлов
- `BaseStage` или orchestrator — интеграция progress ticker (сейчас в каждом `_do_*`)
- Возможно обработка slides между clean и longread/story (сейчас в `_do_educational_pipeline`)

---

## 4. Ограничения

| Параметр | Требование | Обоснование |
|----------|------------|-------------|
| Обратная совместимость | API endpoints не меняются | Frontend не должен ломаться |
| Step-by-step режим | Продолжает работать | Пользователи используют оба режима |
| Удалить дубликаты | Clean pass-through только в `CleanStage` | Единая точка логики |
| Не менять stage интерфейс | `BaseStage.execute(context) -> result` | Существующие stages не трогаем |

---

## 5. Тестирование

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| Auto-pipeline с русским транскриптом | Clean выполняется, лонгрид/конспект генерируются |
| Auto-pipeline с английским транскриптом | Clean пропускается (pass-through), лонгрид на русском |
| Step-by-step с русским транскриптом | Без изменений — работает как раньше |
| Step-by-step с английским транскриптом | Clean пропускается, лонгрид на русском |
| Leadership content (story) | Story генерируется вместо longread+summary |
| Progress tracking в UI | Прогресс-бар работает корректно в обоих режимах |

---

## 6. Референсы

- ADR-001: Stage Abstraction для Pipeline — `docs/decisions/001-stage-abstraction.md`
- ADR-011: Разделение режимов обработки — `docs/decisions/011-processing-mode-separation.md`
- Stage документация — `docs/pipeline/stages.md`
- Текущий orchestrator — `backend/app/services/pipeline/orchestrator.py`
- Существующие stages — `backend/app/services/stages/`

---

## Открытые вопросы

- [ ] Progress ticker: встроить в BaseStage или оставить в orchestrator?
- [ ] Slides: оформить как stage или оставить как отдельный вызов?
- [ ] Ветвление educational/leadership: кто решает — orchestrator или stage registry?

---

_Документ для планирования в Claude Code_
