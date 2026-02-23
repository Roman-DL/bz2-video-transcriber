# md2gdoc

Markdown → Google Docs конвертация и двусторонняя синхронизация. [Полная спецификация](docs/PROJECT-SPEC.md).

## Инструкции для Claude

- **Язык общения:** Русский
- **Язык кода:** Английский (имена переменных, функций, комментарии в коде)
- **Язык документации:** Русский
- **Git commits:** Русский, формат "{тип}: описание" (docs, feat, fix, refactor)
- **Версионирование:** `cz bump` для релиза (обновляет VERSION, package.json, CHANGELOG.md, git tag). Предлагай при завершении значимых фич.

## Документирование кода

- **Docstrings в коде** — обязательны для публичных методов (Google-style)
- **Внешняя документация** — только архитектура, интеграция, решения
- **Не дублируй код в docs** — ИИ читает код напрямую

## Quick Start

```bash
# Backend
cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev

# Docker deploy (TrueNAS)
docker-compose up -d

# Health check
curl http://localhost:8000/health
```

## Архитектура

```
Admin Panel (React) → Backend (FastAPI) → Rules Engine (SQLite)
                                        → Sync Manager (Polling)
                                        → Converter (MD↔HTML↔GDoc)
                                        → Google Drive Client (Service Account)
```

> Подробности: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) и [docs/architecture/](docs/architecture/).

## Ключевые ограничения

<!--
Что AI НЕ должен делать. ОБЯЗАТЕЛЬНО обновлять после каждой проблемы!
Формулировки: "НИКОГДА не...", "ВСЕГДА проверяй..."
-->

1. **Polling вместо inotify/kqueue** — SMB/NFS mount не поддерживает filesystem events надёжно
2. **Service Account для Google API** — НЕ OAuth2, JSON-ключ в `config/service-account.json`
3. **Max 3 одновременных конвертации** — Google API rate limits (300 req/min)
4. **Конфликты (two-way): last-modified wins** — НЕ merge, НЕ manual resolution
5. **Image Resolution отложена** — MVP: placeholder + warning, НЕ загружать на Drive
6. **API endpoints — ВСЕГДА Pydantic модели** (`CamelCaseModel`), не `dict` — Python `snake_case` → JSON `camelCase`
7. **Промпты/конфиг — НЕ хардкодить в коде** — ВСЕГДА через файлы в `config/`

---

## Документация

| Тема | Документ |
|------|----------|
| Обзор системы | [docs/overview.md](docs/overview.md) |
| Спецификация | [docs/PROJECT-SPEC.md](docs/PROJECT-SPEC.md) |
| Архитектура | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Модульная архитектура | [docs/architecture/](docs/architecture/) |
| Конфигурация | [docs/configuration.md](docs/configuration.md) |
| API сервисов | [docs/api-reference.md](docs/api-reference.md) |
| Развёртывание | [docs/deployment.md](docs/deployment.md) |
| Тестирование | [docs/testing.md](docs/testing.md) |
| Требования | [docs/requirements/](docs/requirements/) |
| ADR (решения) | [docs/decisions/](docs/decisions/) |
| Процесс разработки | [docs/WORKFLOW.md](docs/WORKFLOW.md) |
| Чеклисты изменений | [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) |
| Гайдлайны документации | [docs/DOCUMENTATION_GUIDELINES.md](docs/DOCUMENTATION_GUIDELINES.md) |
| Справочник команд | [docs/COMMANDS-REFERENCE.md](docs/COMMANDS-REFERENCE.md) |

---

## Workflow

> Полный процесс: [docs/WORKFLOW.md](docs/WORKFLOW.md) | Команды: [docs/COMMANDS-REFERENCE.md](docs/COMMANDS-REFERENCE.md)

- **Крупная фича:** `/preflight` → план → реализация → `/finalize`
- **UI экран:** `/frontend-design` → Pencil макет → итерации → код
- **Быстрая доработка:** реализация → секция "После реализации" ниже
- **Баг:** простой → исправить; сложный → план; архитектурный → ограничение сюда

**При планировании** изучи: `docs/ARCHITECTURE.md`, `docs/architecture/`, `docs/decisions/`, `.claude/rules/`

---

## После реализации (ОБЯЗАТЕЛЬНО)

После каждого завершённого блока работы проверь:

1. **Архитектура изменилась?** → обнови `docs/ARCHITECTURE.md` (обзор)
2. **Реализован модуль/подсистема?** → создай или обнови `docs/architecture/{module}.md`, обнови индекс `docs/architecture/README.md`
3. **Новый паттерн или значимое решение?** → предложи создать ADR в `docs/decisions/`
4. **Структура проекта изменилась?** → обнови секцию "Структура проекта" ниже
5. **Правила `.claude/rules/`:**
   - Новый модуль → нужен новый файл правил или `paths:` в существующем?
   - Изменился паттерн → обновить правило или откатить код?
   - Устаревшее правило → удалить
6. **Edge case или ошибка AI?** → добавь ограничение в секцию выше

> Для полного аудита документации — `/sync-docs`

---

## Структура проекта

```
backend/app/api/              # FastAPI endpoints
backend/app/models/           # Pydantic models
backend/app/services/
  converter/                  # MD↔HTML↔GDoc конвертация
  google/                     # Google Drive API client
  rules/                      # Rules Engine CRUD
  sync/                       # Sync Manager (polling)
backend/app/utils/            # Shared utilities
frontend/src/                 # React + Vite + Tailwind
frontend/designs/             # Pencil макеты (.pen) — UI прототипы
config/service-account.json   # Google API credentials (НЕ коммитить!)
data/md2gdoc.db               # SQLite database
```

---

## Маршрутизация правил

| Тип | Куда | Пример |
|-----|------|--------|
| Правило конвертера | `.claude/rules/converter.md` | "Каллауты — HTML таблица 2×1" |
| Правило Rules Engine | `.claude/rules/rules-engine.md` | "SHA-256 для дедупликации" |
| Правило Google Drive | `.claude/rules/google-drive.md` | "Service Account, НЕ OAuth2" |
| Правило API/моделей | `.claude/rules/api.md` | "CamelCaseModel обязателен" |
| Правило frontend | `.claude/rules/frontend.md` | "Tailwind, НЕ inline styles" |
| Общее ограничение | Секция "Ключевые ограничения" выше | "НИКОГДА не..." |
| Архитектурное решение | `docs/decisions/ADR-NNN.md` | "Почему polling, а не inotify" |
| Описание системы | `docs/ARCHITECTURE.md` | "Добавлен новый компонент" |
| Описание подсистемы | `docs/architecture/{module}.md` | "Как устроен converter" |

---

## Разработка

**macOS:** Системный Python защищён — используй `python3 -m venv .venv`. Проверка синтаксиса без venv: `python3 -m py_compile backend/app/...`

**Backend:** `cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

**Frontend:** `cd frontend && npm install && npm run dev`

**Тестирование:** см. [docs/testing.md](docs/testing.md)

---

## Версионирование

Source of truth: `VERSION` файл в корне. Синхронизация через `cz bump` (Commitizen).

> **TODO:** При инициализации frontend создать `frontend/package.json` с `"version": "0.0.0"` — `pyproject.toml` ожидает этот файл для синхронизации версий.

- **patch** (0.1.x) — баг-фиксы, мелкие правки
- **minor** (0.x.0) — новые фичи, заметные улучшения
- **major** (x.0.0) — ломающие изменения, крупные переработки

---

## Текущий статус

**Версия:** v0.0.0 • [История изменений](CHANGELOG.md)

---

_Entry point для AI. При проблемах — добавь ограничение. Держи < 200 строк. Если > 180 — запусти `/refactor-claude`._
