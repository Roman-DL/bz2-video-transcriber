# План: Подготовка md2gdoc к выделению в самостоятельный проект

## Контекст

Папка `docs/reference/md2gdoc/` содержит полную спецификацию (PROJECT-SPEC.md v1.3), архитектуру (ARCHITECTURE.md + 3 модульных документа) и шаблоны (plans/, requirements/). Цель — добавить инфраструктуру для Claude Code (CLAUDE.md, rules, commands) и недостающие операционные документы, чтобы содержимое можно было перенести в отдельный репозиторий и сразу начать разработку.

**Референс:** структура основного проекта `bz2-video-transcribe` — CLAUDE.md, `.claude/rules/`, `.claude/commands/`, docs/.

---

## Целевая структура

```
md2gdoc/
├── CLAUDE.md                        # AI инструкции (< 200 строк)
├── VERSION                          # 0.0.0
├── CHANGELOG.md                     # Начальный changelog
├── .gitignore                       # Python + Node + IDE + secrets
├── pyproject.toml                   # Commitizen config (cz bump)
│
├── .claude/
│   ├── rules/
│   │   ├── converter.md             # MD↔HTML↔GDoc конвертация
│   │   ├── rules-engine.md          # Rules Engine + Sync Manager
│   │   ├── google-drive.md          # Google Drive API client
│   │   ├── api.md                   # FastAPI endpoints + Pydantic models
│   │   └── frontend.md              # React + Vite + Tailwind
│   └── commands/
│       ├── preflight.md             # Pre-flight check
│       ├── finalize.md              # Post-implementation audit
│       └── sync-docs.md             # Documentation audit
│
├── docs/
│   ├── PROJECT-SPEC.md              # [ЕСТЬ] Спецификация v1.3
│   ├── ARCHITECTURE.md              # [ЕСТЬ] Обзор архитектуры
│   ├── overview.md                  # СОЗДАТЬ — 1-page overview
│   ├── configuration.md             # СОЗДАТЬ — настройки и env vars
│   ├── testing.md                   # СОЗДАТЬ — стратегия тестирования
│   ├── deployment.md                # СОЗДАТЬ — развёртывание (Docker)
│   ├── api-reference.md             # СОЗДАТЬ — HTTP API endpoints
│   ├── architecture/
│   │   ├── README.md                # [ЕСТЬ]
│   │   ├── 01-converter.md          # [ЕСТЬ]
│   │   ├── 02-rules-engine.md       # [ЕСТЬ]
│   │   └── 03-google-drive.md       # [ЕСТЬ]
│   ├── decisions/                   # [ЕСТЬ, пустая]
│   ├── plans/
│   │   ├── README.md                # [ЕСТЬ]
│   │   └── PLAN-TEMPLATE.md         # [ЕСТЬ]
│   └── requirements/
│       ├── README.md                # [ЕСТЬ]
│       └── REQUIREMENT-TEMPLATE.md  # [ЕСТЬ]
│
├── backend/                         # (не создаём — только документация)
├── frontend/                        # (не создаём — только документация)
└── config/                          # (не создаём — только документация)
```

---

## Файлы для создания

### 1. `CLAUDE.md` (~180 строк)

Точка входа для AI. Адаптировать структуру из bz2-video-transcribe.

**Секции:**
- **Шапка** — описание проекта (1 строка), ссылка на PROJECT-SPEC.md
- **Инструкции для Claude** — язык (русский общение/документация, английский код), git commits (русский, `{тип}: описание`), версионирование (`cz bump`)
- **Quick Start** — команды для разработки (backend venv, frontend npm, deploy)
- **Архитектура** — ASCII-схема из ARCHITECTURE.md + краткое описание компонентов
- **Ключевые ограничения** — извлечь из PROJECT-SPEC.md и ARCHITECTURE.md:
  1. Polling вместо inotify/kqueue (SMB/NFS надёжность)
  2. Service Account для Google API (НЕ OAuth2)
  3. 3 одновременных конвертации (rate limits)
  4. Конфликты: last-modified wins (НЕ merge)
  5. Image Resolution отложена (MVP: placeholder + warning)
  6. ВСЕГДА Pydantic CamelCaseModel для API
  7. Промпты/конфиг — НЕ хардкодить в коде
- **Документация** — таблица ссылок на все документы
- **Workflow** — `/preflight` → реализация → `/finalize`
- **Структура проекта** — дерево из ARCHITECTURE.md
- **Маршрутизация правил** — куда записывать новые правила (converter, rules-engine, google-drive, api, frontend, ограничения, ADR)
- **После реализации (ОБЯЗАТЕЛЬНО)** — чеклист обновления документации
- **Разработка** — macOS venv, backend, frontend, тестирование
- **Версионирование** — VERSION файл, cz bump, patch/minor/major
- **Текущий статус** — v0.0.0

**Источники:** PROJECT-SPEC.md (ограничения, стек), ARCHITECTURE.md (схема, структура), bz2 CLAUDE.md (формат, workflow).

### 2. `VERSION`

```
0.0.0
```

### 3. `CHANGELOG.md`

```markdown
# Changelog

## v0.0.0 (2026-02-23)

Инициализация проекта. Спецификация и архитектура готовы.
```

### 4. `.gitignore`

Стандартный для Python + Node.js:
- Python: `__pycache__/`, `.venv/`, `*.pyc`, `dist/`, `*.egg-info`
- Node: `node_modules/`, `dist/`
- IDE: `.idea/`, `.vscode/`, `*.swp`
- OS: `.DS_Store`, `Thumbs.db`
- Secrets: `.env`, `.env.local`, `config/service-account.json`
- Data: `data/`, `*.db`

### 5. `pyproject.toml`

Минимальный — только Commitizen config:
```toml
[tool.commitizen]
name = "cz_conventional_commits"
version = "0.0.0"
version_files = ["VERSION", "package.json:version"]
tag_format = "v$version"
update_changelog_on_bump = true
```

### 6. `.claude/rules/converter.md`

```
paths: backend/app/services/converter/**
```

**Содержание** (извлечь из `docs/architecture/01-converter.md`):
- Конвертация MD → HTML: Python-Markdown/mistune
- HTML → GDoc: upload с `mimeType: text/html` + auto-convert
- GDoc → MD (two-way): export HTML → detect callouts → restore links → convert
- Каллауты: emoji-to-type mapping (8 типов), HTML table формат для двусторонней конвертации
- Frontmatter: strip перед конвертацией, сохранять при обратной
- Изображения: MVP — placeholder + warning, НЕ загружать на Drive
- ВСЕГДА поддерживать оба направления конвертации в модуле

### 7. `.claude/rules/rules-engine.md`

```
paths: backend/app/services/rules/**, backend/app/services/sync/**
```

**Содержание** (извлечь из `docs/architecture/02-rules-engine.md`):
- Rule — центральная сущность (name, source_path, target_folder_id, mode, poll_interval, recursive, file_filter)
- Три режима: once, one-way, two-way
- SQLite: 3 таблицы (rules, file_mappings, conversion_log)
- Polling: периодическое сканирование, НЕ inotify
- Change detection: SHA-256 hash для дедупликации
- Рекурсивный поиск: true для once, false для one-way/two-way по умолчанию
- Background worker: max 3 concurrent конвертации
- Конфликт resolution (two-way): last-modified wins

### 8. `.claude/rules/google-drive.md`

```
paths: backend/app/services/google/**
```

**Содержание** (извлечь из `docs/architecture/03-google-drive.md`):
- ВСЕГДА Service Account (НЕ OAuth2)
- 5 операций: create, update, export, check modifications, get folder info
- Rate limits: exponential backoff, max 3 concurrent
- Error handling: 403 (permission), 404 (not found), 429 (rate limit), 500/503 (retry)
- `config/service-account.json` — НИКОГДА не коммитить
- Upload: `mimeType: text/html` → Google auto-converts to Google Doc

### 9. `.claude/rules/api.md`

```
paths: backend/app/api/**, backend/app/models/**, frontend/src/api/**
```

**Содержание** (адаптировать из bz2 api.md):
- CamelCaseModel для всех response-моделей (snake_case Python → camelCase JSON)
- ВСЕГДА Pydantic модели, НЕ dict
- REST endpoints: CRUD для rules, trigger conversion, logs, settings
- `populate_by_name=True`

### 10. `.claude/rules/frontend.md`

```
paths: frontend/src/**
```

**Содержание** (адаптировать из bz2 frontend.md):
- React + Vite + Tailwind
- Tailwind CSS — НЕ inline styles
- API типы из `frontend/src/api/types.ts`
- НЕ fetch/axios напрямую — только через API client

### 11. `.claude/commands/preflight.md`

Адаптация из bz2 `preflight.md`:
- Убрать `docs/pipeline/` (нет pipeline в md2gdoc)
- Шаги: ARCHITECTURE.md → architecture/ → decisions/ → CLAUDE.md → .claude/rules/ → проверить совместимость → оценить документацию
- Формат ответа аналогичный

### 12. `.claude/commands/finalize.md`

Адаптация из bz2 `finalize.md`:
- Убрать pipeline-специфику
- Шаги: понять что изменилось → проверить rules → проверить docs (ARCHITECTURE.md, architecture/, ADR, CLAUDE.md) → рекомендация релиза → проверить размер CLAUDE.md
- Формат ответа аналогичный

### 13. `.claude/commands/sync-docs.md`

Адаптация из bz2 `sync-docs.md`:
- Карта покрытия: код → architecture/ → rules/ → requirements/
- Приоритеты долга: критический → значительный → умеренный
- Стратегия субагентов для большого проекта
- Формат отчёта аналогичный

### 14. `docs/overview.md`

1-page обзор системы (~50 строк):
- Что делает: Markdown → Google Docs конвертация и синхронизация
- Три режима работы (кратко, 1 строка каждый)
- Технологический стек
- Ссылки на PROJECT-SPEC.md (подробности) и ARCHITECTURE.md (техническая архитектура)

**НЕ дублировать** содержание PROJECT-SPEC.md или ARCHITECTURE.md — только краткий обзор со ссылками.

### 15. `docs/configuration.md`

Референс по настройкам:
- Environment variables (из PROJECT-SPEC.md): `GOOGLE_SERVICE_ACCOUNT_PATH`, `POLL_INTERVAL_DEFAULT`, `MAX_CONCURRENT_CONVERSIONS`, `DB_PATH`
- Google Service Account setup — как создать, где разместить JSON key
- SQLite database — расположение, инициализация
- Frontend config — API base URL
- Docker env vars

**Источник:** PROJECT-SPEC.md (appendix с деталями), architecture/03-google-drive.md (Service Account).

### 16. `docs/testing.md`

Стратегия тестирования:
- Unit tests: converter (MD→HTML→GDoc mapping), rules engine (CRUD, change detection)
- Integration tests: Google Drive API (с реальным Service Account)
- E2E: создание правила → мониторинг → конвертация → проверка Google Doc
- Локальная разработка: mock Google API, тестовые MD файлы
- Как запускать: `pytest backend/tests/`

### 17. `docs/deployment.md`

Развёртывание:
- Docker Compose — сервисы (backend, frontend, nginx/traefik)
- Целевая среда: TrueNAS (Docker)
- Volumes: `/mnt/.../` для исходных файлов, `data/` для SQLite
- Service Account JSON — как пробросить в контейнер
- Health check endpoint
- Шаги первого деплоя

### 18. `docs/api-reference.md`

HTTP API endpoints (извлечь из architecture/02-rules-engine.md + PROJECT-SPEC.md):
- Rules CRUD: `GET/POST/PUT/DELETE /api/rules`
- Trigger: `POST /api/rules/{id}/trigger`
- Logs: `GET /api/logs`
- Settings: `GET/PUT /api/settings`
- Health: `GET /health`
- Convert (quick): `POST /api/convert`

**НЕ дублировать** детали из architecture/ — только перечисление endpoints с кратким описанием, request/response schemas.

---

## Порядок создания

1. `CLAUDE.md` — определяет конвенции для всех остальных файлов
2. `VERSION`, `CHANGELOG.md`, `.gitignore`, `pyproject.toml` — корневые файлы
3. `.claude/rules/` — 5 файлов (converter, rules-engine, google-drive, api, frontend)
4. `.claude/commands/` — 3 файла (preflight, finalize, sync-docs)
5. `docs/` — 5 файлов (overview, configuration, testing, deployment, api-reference)

---

## Принципы

- **Не дублировать** — docs/overview.md и docs/api-reference.md ссылаются на PROJECT-SPEC.md и architecture/, не копируют
- **Извлекать, не придумывать** — ограничения и правила берём из существующих документов (PROJECT-SPEC.md, ARCHITECTURE.md, architecture/)
- **Готово к разработке** — после переноса в новый репозиторий, Claude Code может сразу начать реализацию MVP (v0.1)
- **Те же конвенции** — язык, workflow, формат rules/commands идентичны bz2-video-transcribe

---

## Верификация

После создания всех файлов:
1. Проверить что `CLAUDE.md` < 200 строк и все ссылки на docs/ корректны
2. Проверить что `.claude/rules/` файлы имеют правильный `paths:` frontmatter
3. Проверить что docs/ не дублирует architecture/ и PROJECT-SPEC.md
4. Просмотреть целевую структуру — все файлы на месте
5. Убедиться что `.gitignore` включает `config/service-account.json`

---

## Что НЕ создаём

- Код приложения (backend/, frontend/, config/)
- `docs/logging.md` — преждевременно до реализации
- `docs/data-formats.md` — преждевременно до реализации
- `.claude/commands/refactor-claude.md` — добавим когда CLAUDE.md вырастет
- `docs/DOCUMENTATION_GUIDELINES.md` — используем те же конвенции что в bz2
