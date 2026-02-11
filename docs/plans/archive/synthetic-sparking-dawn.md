# Аудит согласованности документации

## Контекст

Проверка что цикл "планирование → реализация → актуализация документов" настроен без пробелов: все документы упомянуты в нужных местах, ссылки не битые, rules покрывают реальный код.

---

## 1. Цепочка планирования: CLAUDE.md vs /preflight

### Что читается при планировании

| Документ | CLAUDE.md "При планировании" | /preflight | Расхождение |
|----------|:---:|:---:|---|
| docs/ARCHITECTURE.md | + | + | — |
| docs/architecture/ | + | + | — |
| docs/pipeline/ | + | + | — |
| docs/decisions/ | + | + | — |
| .claude/rules/ | + | + | — |
| CLAUDE.md (ограничения) | — | + | **Пробел в CLAUDE.md** |
| docs/requirements/ | — | — | Оба не упоминают |

### Вывод

Ядро согласовано. Единственное расхождение — /preflight явно читает CLAUDE.md (секцию ограничений), а секция "При планировании" в CLAUDE.md себя не упоминает. Это некритично — CLAUDE.md и так подгружается в контекст автоматически.

**Проблема P1:** `docs/requirements/` не упомянут ни в CLAUDE.md Plan Mode, ни в /preflight. Если есть активные требования — они не попадут в контекст планирования.

---

## 2. Цепочка финализации: CLAUDE.md vs /finalize vs /sync-docs

### Что проверяется после реализации

| Область | CLAUDE.md "После реализации" | /finalize | /sync-docs |
|---------|:---:|:---:|:---:|
| docs/ARCHITECTURE.md | + | + | + |
| docs/architecture/ | + | + | + |
| docs/pipeline/ | + | + | + |
| docs/decisions/ | + | + | + |
| .claude/rules/ | + | + | + |
| CLAUDE.md (ограничения, структура) | + | + | + |
| Размер CLAUDE.md (>250 строк) | — | + | — |
| docs/requirements/ | — | — | + |
| docs/plans/ (зависшие) | — | — | + |
| Карта покрытия код↔docs | — | — | + |

### Вывод

Основные 6 областей покрыты всеми тремя. /sync-docs уникально проверяет requirements и plans. Разделение ролей корректное:
- "После реализации" — быстрый чеклист (автоматический)
- /finalize — детальная проверка после фичи
- /sync-docs — полный аудит проекта

**Проблем нет.** Система трёхуровневая и каждый уровень расширяет предыдущий.

---

## 3. Карта покрытия .claude/rules/

### Globs из файлов правил

| Файл | Globs |
|------|-------|
| pipeline.md | `backend/app/services/pipeline/**`, `backend/app/services/stages/**` |
| ai-clients.md | `backend/app/services/ai_clients/**`, `backend/app/services/cleaner.py`, `*_generator.py`, `slides_extractor.py` |
| api.md | `backend/app/api/**`, `backend/app/models/schemas.py`, `frontend/src/api/**` |
| content.md | `backend/app/services/parser.py`, `backend/app/services/saver.py`, `*longread*`, `*story*`, `config/events.yaml` |
| infrastructure.md | `backend/app/utils/**`, `backend/app/config.py`, `config/**`, `docker-compose.yml`, `scripts/**` |

### Покрытие по модулям

| Модуль | Покрытие | Rule |
|--------|:---:|------|
| backend/app/services/pipeline/ | **100%** | pipeline.md |
| backend/app/services/stages/ | **100%** | pipeline.md |
| backend/app/services/ai_clients/ | **100%** | ai-clients.md |
| backend/app/api/ | **100%** | api.md |
| backend/app/utils/ | **100%** | infrastructure.md |
| config/ | **100%** | infrastructure.md, content.md |
| scripts/ | **100%** | infrastructure.md |
| **backend/app/services/ (корень)** | **~50%** | Частично |
| **frontend/src/components/** | **0%** | — |
| **frontend/src/hooks/** | **0%** | — |
| **frontend/src/contexts/** | **0%** | — |
| **frontend/src/utils/** | **0%** | — |
| **backend/app/models/cache.py** | **0%** | schemas.py покрыт, cache.py нет |

### Backend-сервисы без rules (6 файлов)

| Файл | Описание | Подходящий rule |
|------|----------|-----------------|
| transcriber.py | Обёртка Whisper | ai-clients.md |
| audio_extractor.py | Извлечение аудио из видео | pipeline.md |
| summarizer.py | Обёртка суммаризации | ai-clients.md |
| outline_extractor.py | Извлечение структуры | ai-clients.md |
| text_splitter.py | Разбиение текста | infrastructure.md (utils) |
| progress_estimator.py | Оценка прогресса | pipeline.md |

### Frontend без rules (34 компонента)

34 .tsx файла в `frontend/src/components/`, плюс `hooks/`, `contexts/`, `utils/` — ни один не покрыт правилами.

**Проблема P2:** Frontend полностью не покрыт rules. Правила из api.md (formatUtils, CamelCase) упоминаются в тексте правила, но glob не включает `frontend/src/components/**` и `frontend/src/utils/**`.

**Проблема P3:** 6 backend-сервисов не покрыты ни одним правилом. Особенно важны transcriber.py и summarizer.py — это AI-клиенты.

**Замечание:** Глобы `*longread*` и `*story*` в content.md слишком широкие (матчат файлы в любой директории), но на практике это не вызывает проблем — ложных срабатываний в проекте нет.

---

## 4. Ссылки в таблице "Документация" CLAUDE.md

### Все ли перечисленные документы существуют?

**Да, все 19 записей таблицы ведут на существующие файлы/директории.**

### Документы вне таблицы

| Документ | Существует | В таблице CLAUDE.md |
|----------|:---:|:---:|
| docs/web-ui.md | + | — |
| docs/reference/ (5 файлов) | + | — |
| docs/research/ | + | — |
| docs/template-prompts/ (8 файлов) | + | — |
| docs/audit/ (2 файла) | + | — |
| docs/plans/ (39 архивных планов) | + | — |
| docs/README.md (индекс) | + | — |

**Проблема P4:** 6 директорий/документов не в таблице. Из них реально важны для AI-контекста:
- `docs/reference/` — стандарты именования, фреймворки
- `docs/web-ui.md` — описание UI

Остальные (research, template-prompts, audit, plans) — вспомогательные, их отсутствие в таблице допустимо.

### docs/architecture/ — пустая директория

В таблице есть "Модульная архитектура → docs/architecture/", но в директории только README.md с пометкой "модули добавлять по мере появления". Фактически модульных документов нет. Это не баг — это задолженность, зафиксированная в самом README.

---

## 5. WORKFLOW.md и COMMANDS-REFERENCE.md

### Команды

| Команда | .claude/commands/ | COMMANDS-REFERENCE | WORKFLOW.md | Описание совпадает |
|---------|:---:|:---:|:---:|:---:|
| /preflight | + | + | + | + |
| /finalize | + | + | + | + |
| /sync-docs | + | + | + | + |
| /refactor-claude | + | + | — | + |

### Ссылки

**WORKFLOW.md:** 3 ссылки — все валидные (CLAUDE.md, ARCHITECTURE.md, COMMANDS-REFERENCE.md)

**COMMANDS-REFERENCE.md:** 7 ссылок — все валидные (4 команды в .claude/commands/, CLAUDE.md, WORKFLOW.md, CONTRIBUTING.md)

**Проблем нет.** Документация команд полностью согласована, описания в справочнике точно соответствуют содержимому файлов команд.

---

## Итоговая сводка

| # | Проблема | Серьёзность | Предлагаемое действие |
|---|----------|:-----------:|----------------------|
| P1 | docs/requirements/ не в контексте планирования | Низкая | Добавить в CLAUDE.md "При планировании" если есть активные требования |
| P2 | Frontend (34 компонента) без rules | Средняя | Создать `.claude/rules/frontend.md` с globs `frontend/src/components/**,frontend/src/utils/**,frontend/src/hooks/**,frontend/src/contexts/**` |
| P3 | 6 backend-сервисов без rules | Низкая | Расширить globs в ai-clients.md: добавить `transcriber.py`, `summarizer.py`, `outline_extractor.py`; в pipeline.md: `audio_extractor.py`, `progress_estimator.py`; в infrastructure.md: `text_splitter.py` |
| P4 | docs/web-ui.md и docs/reference/ не в таблице CLAUDE.md | Низкая | Добавить 2 строки в таблицу |

### Что работает хорошо

- Ядро планирования (5 источников) полностью согласовано между CLAUDE.md и /preflight
- Трёхуровневая финализация ("После реализации" → /finalize → /sync-docs) логична и непротиворечива
- Все 19 документов из таблицы CLAUDE.md существуют, битых ссылок нет
- WORKFLOW.md и COMMANDS-REFERENCE.md полностью синхронизированы с .claude/commands/
- Backend pipeline, stages, ai_clients, api, utils, config — все покрыты rules на 100%

---

## План исправлений

### Шаг 1. Создать `.claude/rules/frontend.md` (P2)

```markdown
---
globs: frontend/src/components/**,frontend/src/utils/**,frontend/src/hooks/**,frontend/src/contexts/**
---

# Rules: Frontend

## Компоненты
- ВСЕГДА использовать `formatUtils` для форматирования: `formatTime()`, `formatCost()`, `formatTokens()`
- НЕ форматировать метрики вручную в компонентах

## API интеграция
- Типы из `frontend/src/api/types.ts` — единственный источник правды для TypeScript типов
- API хуки в `frontend/src/api/` — использовать готовые, НЕ делать fetch напрямую

## Стилизация
- Tailwind CSS для стилей — НЕ использовать inline styles или CSS modules
```

### Шаг 2. Расширить globs в существующих rules (P3)

**ai-clients.md** — добавить `backend/app/services/transcriber.py`, `backend/app/services/summarizer.py`, `backend/app/services/outline_extractor.py`

**pipeline.md** — добавить `backend/app/services/audio_extractor.py`, `backend/app/services/progress_estimator.py`

**infrastructure.md** — добавить `backend/app/services/text_splitter.py`

### Шаг 3. Добавить docs/web-ui.md и docs/reference/ в таблицу CLAUDE.md (P4)

### Шаг 4. Опционально: добавить docs/requirements/ в секцию "При планировании" (P1)

---

## Верификация

После исправлений:
1. Проверить что новые globs в rules матчатся: `claude --print-rules` или проверить вручную
2. Убедиться что все ссылки в обновлённой таблице CLAUDE.md валидны
3. Пересчитать строки CLAUDE.md — не превышает ли 300
