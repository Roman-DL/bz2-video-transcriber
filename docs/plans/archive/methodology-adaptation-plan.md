# План: Адаптация bz2-video-transcribe под методологию claude-dev-framework

## Контекст

Проект bz2-video-transcribe создавался ДО методологии и имеет зрелую документацию: 13 ADR, 14 pipeline docs, мета-система Diátaxis+, CLAUDE.md на 785 строк. Задача — адаптировать под процессы методологии минимальными изменениями.

**Ключевое ограничение:** Полная реструктуризация docs/ (переименование папок, фиксация ссылок) требует доступа к коду проекта. Поэтому работа разделена:

- **Часть A (здесь):** Подготовить файлы в `workspace/bz2-video-transcribe/` — CLAUDE.md, .claude/commands/, .claude/rules/, план миграции
- **Часть B (в реальном проекте):** Пользователь переносит файлы и выполняет реструктуризацию docs/ с доступом к коду

**Рабочая директория:** `workspace/bz2-video-transcribe/`
**Эталон:** `project-template/`
**Пример:** `workspace/bz2-bot/`

### Существующая `.claude/` (сохраняем)

- `skills/frontend-design/SKILL.md` — скилл для дизайна UI
- `settings.local.json` — permissions для bash-команд
- `plans/` — 37 авто-генерированных файлов Claude Code (внутреннее состояние)

---

## Часть A: Что делаем ЗДЕСЬ (claude-dev-framework)

### A1. Добавить `.claude/commands/` (4 файла)

Скопировать из `project-template/.claude/commands/` и адаптировать:

| Файл | Адаптация |
|------|-----------|
| `preflight.md` | Пути: `docs/decisions/` (не `adr/`), добавить `docs/pipeline/` |
| `finalize.md` | Добавить `docs/pipeline/` в чеклист проверки |
| `sync-docs.md` | Без изменений |
| `refactor-claude.md` | Без изменений |

**Источники для копирования:**
- `project-template/.claude/commands/preflight.md`
- `project-template/.claude/commands/finalize.md`
- `project-template/.claude/commands/sync-docs.md`
- `project-template/.claude/commands/refactor-claude.md`

### A2. Добавить `.claude/rules/` (5 файлов)

Извлечь из текущего CLAUDE.md (785 строк) в директивы:

| Файл | Globs | Источник из CLAUDE.md |
|------|-------|----------------------|
| `pipeline.md` | `backend/app/services/pipeline/**`, `backend/app/services/stages/**` | §Pipeline Package, §Stage Result Cache, §Stage Abstraction, §Shared Utils, §Slides (pipeline) |
| `ai-clients.md` | `backend/app/services/ai_clients/**`, `backend/app/services/cleaner.py`, `*_generator.py`, `slides_extractor.py` | §AI Clients, §AI Services |
| `api.md` | `backend/app/api/**`, `backend/app/models/schemas.py`, `frontend/src/api/**` | §Extended Metrics, §Prompts API, CamelCase |
| `content.md` | `backend/app/services/parser.py`, `backend/app/services/saver.py`, `*longread*`, `*story*`, `config/events.yaml` | §Content Types, §Slides (контент) |
| `infrastructure.md` | `backend/app/utils/**`, `backend/app/config.py`, `config/**`, `docker-compose.yml`, `scripts/**` | §Logging, §Development, §Deployment, промпты |

Каждый rule-файл: 20-35 строк, формат директив ("ВСЕГДА...", "НЕ..."), код-примеры минимальные.

### A3. Переписать CLAUDE.md (785 → ~260 строк)

**Оставить без изменений:**
- Заголовок + описание (3 строки)
- Инструкции для Claude (8)
- Документирование кода (6)
- Quick Start (13)
- Архитектура — диаграмма pipeline (10)

**Добавить новое (из шаблона методологии):**
- Ключевые ограничения (~18) — docker-compose не работает, Claude default (ADR-007), Pydantic не dict, Chunk детерминистический, sshpass для сервера
- Документация — таблица с обновлёнными ссылками (~20), уже с `docs/decisions/` вместо `docs/decisions/`
- Workflow — планирование / крупная фича / быстрая доработка / баг (~20)
- После реализации (ОБЯЗАТЕЛЬНО) — чеклист (~15)
- Маршрутизация правил — таблица куда сохранять (~15)
- Текущий статус (~6)

**Оставить кратко:**
- Структура проекта (15) — обновить пути (decisions/, architecture/)
- Разработка (10) — macOS note, ссылка на CONTRIBUTING
- Версионирование (8)

**Удалить** (вынесено в .claude/rules/): Pipeline Package, Stage Result Cache, Prompts API, Slides Extraction, Content Types, Extended Metrics, Stage Abstraction, Shared Utils, AI Clients, AI Services, Logging, Testing on Server.

### A4. Создать план миграции документации

Файл: `.claude/plans/methodology-adaptation-plan.md`

Детальный план для выполнения в реальном проекте (Часть B ниже). Включает все команды, маппинг файлов, чеклист верификации.

---

## Часть B: План миграции для реального проекта (содержимое A4)

Этот раздел станет основой для `docs/plans/methodology-adaptation.md`.

### B1. Переименовать директории

| Было | Стало | Действие |
|------|-------|----------|
| `docs/decisions/` | `docs/decisions/` | `mv` — 13 ADR файлов, содержимое не меняется |
| `docs/requirements/` | `docs/requirements/` | `mv` — пустая (DS_Store) |
| `docs/template prompts/` | `docs/template-prompts/` | `mv` — убрать пробел |

### B2. Создать новые директории и индексы

| Директория | Что создать |
|-----------|-------------|
| `docs/decisions/` | `README.md` — индекс 13 ADR |
| `docs/requirements/` | `README.md` + `REQUIREMENT-TEMPLATE.md` |
| `docs/plans/` | `README.md` + `PLAN-TEMPLATE.md` |
| `docs/architecture/` | `README.md` — индекс, ссылки на `pipeline/` как основную подсистему |

### B3. Адаптировать docs/ARCHITECTURE.md → docs/ARCHITECTURE.md

- Переименовать в UPPERCASE
- Сократить до < 150 строк (обзор)
- Добавить ссылки на `docs/architecture/` и `docs/pipeline/`

### B4. Миграция docs/reference/

**Сохранить ценное:**

| Источник | Назначение |
|----------|-----------|
| `docs/reference/diataxis-framework.md` | → `docs/reference/diataxis-framework.md` |
| `docs/reference/standards/frontmatter.md` | → `docs/reference/standards/frontmatter.md` |
| `docs/reference/standards/naming.md` | → `docs/reference/standards/naming.md` |

**Архивировать остальное:**

| Источник | Назначение | Причина |
|----------|-----------|---------|
| `docs/reference/agents/*.md` | → `docs/archive/meta/agents/` | Заменено /preflight + /finalize |
| `docs/reference/workflows/*.md` | → `docs/archive/meta/workflows/` | Заменено WORKFLOW.md + commands |
| `docs/reference/artifacts/*.md` | → `docs/archive/meta/artifacts/` | Историческое |
| `docs/reference/research/*.md` | → `docs/archive/meta/research/` | Историческое |
| `docs/reference/MOC - *.md` | → `docs/archive/meta/` | Заменено методологией |

**Архивировать generic SKILL-файлы:**
- `docs/reference/SKILL - backend-patterns.md` → `docs/archive/reference/` (Node.js, не для проекта)
- `docs/reference/SKILL - frontend-pattern.md` → `docs/archive/reference/` (generic, заменено rules/)

Удалить пустую `docs/reference/` после миграции.

### B5. Создать файлы методологии

| Файл | Описание |
|------|---------|
| `docs/WORKFLOW.md` | Процесс работы с Claude Code (из шаблона) |
| `docs/DOC-STRUCTURE.md` | Описание структуры документации (из шаблона) |
| `docs/COMMANDS-REFERENCE.md` | Справка по slash-командам (из шаблона) |

### B6. Фиксация ссылок (глобальная замена)

| Было | Стало |
|------|-------|
| `docs/decisions/` | `docs/decisions/` |
| `../decisions/` | `../decisions/` |
| `docs/ARCHITECTURE.md` | `docs/ARCHITECTURE.md` |
| `../ARCHITECTURE.md` | `../ARCHITECTURE.md` |
| `docs/requirements/` | `docs/requirements/` |
| `docs/reference/diataxis-framework.md` | `docs/reference/diataxis-framework.md` |
| `docs/reference/standards/` | `docs/reference/standards/` |

**Критичные файлы:**
- `docs/pipeline/README.md` — 6 ссылок на `../decisions/`
- `docs/README.md` — навигация
- `docs/CONTRIBUTING.md`
- `docs/audit/architecture-summary.md`
- Все pipeline docs с ADR-ссылками

### B7. Обновить docs/README.md

Навигационная таблица с новыми путями + новые документы методологии.

---

## Что НЕ трогаем

| Что | Почему |
|-----|--------|
| `.claude/plans/` (37 файлов) | Внутреннее состояние Claude Code |
| `.claude/skills/frontend-design/` | Рабочий скилл |
| `.claude/settings.local.json` | Настройки permissions |
| `docs/pipeline/*.md` (14 файлов) | Зрелая документация, core asset |
| Содержимое 13 ADR | Иммутабельные решения |
| `docs/overview.md`, `configuration.md`, `api-reference.md`, `data-formats.md` | Рабочие документы |
| `docs/deployment.md`, `logging.md`, `testing.md`, `model-testing.md`, `web-ui.md` | Рабочие документы |
| `docs/CONTRIBUTING.md`, `DOCUMENTATION_GUIDELINES.md` | Только обновить ссылки (Часть B) |
| `docs/audit/` | Аудит-снэпшоты |
| `docs/archive/` | Только добавляем |

---

## Верификация

### После Части A (здесь)

```bash
wc -l workspace/bz2-video-transcribe/CLAUDE.md    # < 300
ls workspace/bz2-video-transcribe/.claude/commands/ # 4 файла
ls workspace/bz2-video-transcribe/.claude/rules/    # 5 файлов
ls workspace/bz2-video-transcribe/.claude/skills/   # frontend-design (сохранён)
```

### После Части B (в реальном проекте)

```bash
# Структура
ls docs/decisions/       # README + 13 ADR
ls docs/requirements/    # README + template
ls docs/plans/           # README + template + methodology-adaptation.md
ls docs/architecture/    # README
ls docs/ARCHITECTURE.md docs/WORKFLOW.md docs/DOC-STRUCTURE.md docs/COMMANDS-REFERENCE.md

# Ссылки (0 вхождений вне archive/)
grep -r "docs/decisions/" --include="*.md" . | grep -v archive/
grep -r "docs/reference/" --include="*.md" . | grep -v archive/
grep -r "docs/requirements/" --include="*.md" . | grep -v archive/

# Отсутствие docs/reference/
ls docs/reference/ 2>&1 | grep "No such"
```
