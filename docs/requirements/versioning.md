# Система версионирования и CHANGELOG

> Автоматическое SemVer через Commitizen, build number при деплое, страница /changelog в UI

**Статус:** Done
**Дата:** 2026-02-22
**Версии:** v0.80 — v0.81 (реализовано)

---

## 1. Проблема

Проект ведётся полгода, версия 0.79.0. Версионирование ручное, история изменений не фиксируется.

**Текущая ситуация:**
- Версия хранится только в `frontend/package.json` (`"version": "0.79.0"`)
- Backend содержит hardcoded `version="0.1.0"` в FastAPI app (`backend/app/main.py:53`) — не синхронизирован
- CHANGELOG отсутствует — история только в таблице "Текущий статус" в `CLAUDE.md`
- Git tags не используются — нет привязки версий к коммитам
- Build number отсутствует — невозможно определить какой деплой запущен на сервере
- `scripts/deploy.sh` не содержит версионной логики
- Health endpoint (`GET /health`) возвращает только `{"status": "ok"}` — нет версии

**Почему это проблема:**
- Невозможно определить какая версия на сервере (нет build number, нет версии в health)
- Ручное обновление версии забывается или делается непоследовательно
- Нет CHANGELOG — пользователь не видит что изменилось между версиями
- Нет git tags — невозможно откатиться к конкретной версии
- Backend version `0.1.0` вводит в заблуждение при отладке API

---

## 2. Решение

Commitizen для автоматического SemVer + CHANGELOG, build number через серверный счётчик, UI-страница /changelog с карточками версий.

### Ключевые идеи

1. **`VERSION` файл в корне** — единый Source of Truth для backend и deploy
2. **`frontend/package.json`** — синхронизируется через `cz bump` (version_files), используется Vite при сборке (`npm_package_version`)
3. **Commitizen (`cz bump`)** — автоматический SemVer по conventional commits, генерация CHANGELOG.md, git tags
4. **Build number** — серверный файл `.build_number`, инкремент при каждом деплое
5. **Без scopes** — проект монолитный, единая версия, CHANGELOG группируется по типам (feat/fix), а не по модулям
6. **Порядок в CHANGELOG** — Commitizen prepend'ит новые версии вверху файла, парсер читает сверху вниз — порядок для UI (последняя версия первая) совпадает автоматически

### Архитектура

```
                   cz bump
                     │
                     ▼
VERSION ──────────────────────────────► git tag v0.80.0
  │                  │
  │                  ├──► package.json (synced) → npm build → __APP_VERSION__ ──┐
  │                  ▼                                                          ├► Header.tsx
  │            CHANGELOG.md                                                     │  "v0.80.0 • build 42"
  │                  │                                                          │
  ├──► backend/app/version.py      ──► FastAPI version + /health                │
  ├──► deploy.sh (.build_number) ──► BUILD_NUMBER ──┬► backend env (version.py) │
  │                  │                              └► frontend build-arg ───────┘
  │                  ▼                                  (__BUILD_NUMBER__)
  │         /api/changelog (JSON)
  │                  │
  │                  ▼
  │          /changelog (UI page)
  │
  └──► docker-compose.yml (env) ──► BUILD_NUMBER
```

**Два потока в Header.tsx:**
- **Версия:** `VERSION` → `cz bump` → `package.json` → `npm run build` → `npm_package_version` → `__APP_VERSION__`
- **Build:** `.build_number` → `deploy.sh` → `BUILD_NUMBER` → docker build-arg → `__BUILD_NUMBER__`

---

## 3. Пользовательский сценарий

### Сценарий A: Разработчик выпускает версию

```
1. Разработчик делает коммиты: "feat: поддержка мультиспикерного контента"
2. Запускает: cz bump
3. Commitizen анализирует коммиты с последнего тега:
   - feat → minor bump: 0.79.0 → 0.80.0
4. Автоматически:
   - Обновлён VERSION (0.80.0)
   - Обновлён frontend/package.json (0.80.0)
   - Новая секция в CHANGELOG.md (prepend вверху)
   - Коммит "bump: version 0.79.0 → 0.80.0"
   - Git tag v0.80.0
5. Разработчик запускает: /bin/bash scripts/deploy.sh
6. Deploy.sh: "Deploying v0.80.0 (build 42)"
```

### Сценарий B: Пользователь смотрит что нового

```
1. Пользователь видит в Header: "v0.80.0 • build 42"
2. Кликает на версию → открывается /changelog
3. Видит карточки версий (последняя сверху):
   - v0.80.0 (22.02.2026) — с бейджами "Новое" / "Исправление"
   - v0.79.0 (20.02.2026)
4. Результат: понимает что изменилось
```

### Сценарий C: Диагностика на сервере

```
1. curl -k https://transcriber.home/health
2. Ответ: {"status": "ok", "version": "0.80.0", "build": 42}
3. Сразу видно версию и номер сборки
```

### Сценарий D: /finalize и рекомендация релиза

```
1. Закончил мелкий fix → /finalize
   → "С последнего тега: 1 fix. Пока рано для релиза."
2. Закончил крупную фичу → /finalize
   → "С v0.80.0: 2 feat, 1 fix (3 коммита).
      Рекомендую релиз: cz bump → v0.81.0. Сделать?"
3. cz bump → CHANGELOG включает ВСЕ 3 коммита
```

---

## 4. UI

### Header — версия как ссылка

```
┌─────────────────────────────────────────────────────────────────────┐
│ [🎬] БЗ Транскрибатор                           [●● Services] [⚙] │
│       v0.80.0 • build 42                                            │
│       ^^^^^^^^^^^^^^^^^^^^^^^^                                      │
│       кликабельная ссылка → /changelog                              │
└─────────────────────────────────────────────────────────────────────┘
```

- Текст версии становится `<button>` с hover-подчёркиванием
- Клик переключает state `page` в App.tsx на `'changelog'`

### Страница /changelog

```
┌─────────────────────────────────────────────────────────────────────┐
│ [🎬] БЗ Транскрибатор                           [●● Services] [⚙] │
│       v0.80.0 • build 42                                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Журнал изменений                                    v0.80.0       │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ v0.80.0                                     22 февраля 2026  │  │
│  │                                                               │  │
│  │  [Новое]  Поддержка мультиспикерного контента в pipeline      │  │
│  │  [Новое]  Адаптивные шапки чанков для линейки                 │  │
│  │  [Исправление]  Исправлены правила frontmatter                │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ v0.79.0                                     20 февраля 2026  │  │
│  │                                                               │  │
│  │  [Новое]  Надёжный деплой с health check                      │  │
│  │  [Новое]  Единый источник default моделей                     │  │
│  │  [Исправление]  Убраны дубли конфигов из docker-compose       │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Бейджи типов изменений

| Тип коммита | Бейдж | Цвет |
|-------------|-------|------|
| feat | Новое | Зелёный фон |
| fix | Исправление | Красный фон |
| refactor | Улучшение | Серый фон |
| docs | Документация | Серый фон |
| perf | Производительность | Серый фон |

### Маппинг заголовков Commitizen → бейджи

Commitizen генерирует `### Feat`, `### Fix` и т.д. (с большой буквы). Парсер маппит:

| Заголовок Commitizen | type в API | Бейдж в UI |
|----------------------|------------|------------|
| `### Feat` | `feat` | Новое |
| `### Fix` | `fix` | Исправление |
| `### Refactor` | `refactor` | Улучшение |
| `### Docs` | `docs` | Документация |
| `### Perf` | `perf` | Производительность |

### Состояния

| Состояние | Описание |
|-----------|----------|
| Загрузка | Spinner при получении данных с `/api/changelog` |
| Данные | Список карточек версий |
| Пусто | "История изменений пока недоступна" (если CHANGELOG.md пуст) |
| Ошибка | "Не удалось загрузить историю изменений" с кнопкой повтора |

### Навигация (без react-router)

State `page` в `App.tsx`: `'dashboard' | 'changelog'`. Header передаёт callback `onNavigateChangelog`. Кнопка "← Назад" на странице changelog возвращает на dashboard.

**Known limitations:**
- Кнопка «Назад» в браузере не работает (state не интегрирован с browser history). Для одной дополнительной «страницы» приемлемо.
- Дата деплоя не отображается в Header — заменена на build number (полезнее при нескольких деплоях в день). Дата доступна в журнале изменений у релизных версий.

---

## 5. API

### GET /api/changelog

Парсит CHANGELOG.md и возвращает структурированный JSON.

**Pydantic-модели** (наследуют `CamelCaseModel` по правилам проекта):

```python
class ChangelogEntry(CamelCaseModel):
    type: Literal["feat", "fix", "refactor", "docs", "perf"]
    description: str

class ChangelogVersion(CamelCaseModel):
    version: str       # "0.80.0"
    date: str          # "2026-02-22"
    changes: list[ChangelogEntry]

class ChangelogResponse(CamelCaseModel):
    versions: list[ChangelogVersion]
```

### TypeScript-интерфейс (frontend)

```typescript
interface ChangelogEntry {
  type: 'feat' | 'fix' | 'refactor' | 'docs' | 'perf';
  description: string;
}

interface ChangelogVersion {
  version: string;       // "0.80.0"
  date: string;          // "2026-02-22"
  changes: ChangelogEntry[];
}

interface ChangelogResponse {
  versions: ChangelogVersion[];
}
```

### Пример ответа

```json
{
  "versions": [
    {
      "version": "0.80.0",
      "date": "2026-02-22",
      "changes": [
        {"type": "feat", "description": "Поддержка мультиспикерного контента в pipeline"},
        {"type": "fix", "description": "Исправлены правила frontmatter — globs на paths"}
      ]
    }
  ]
}
```

### GET /health (обновлённый)

**Pydantic-модель** (по правилам проекта — API endpoints всегда через Pydantic):

```python
class HealthResponse(CamelCaseModel):
    status: str
    version: str
    build: int
```

```json
{
  "status": "ok",
  "version": "0.80.0",
  "build": 42
}
```

---

## 6. Данные

### Новые файлы

| Файл | Назначение |
|------|-----------|
| `VERSION` | Source of Truth — одна строка с версией (`0.79.0`). Обновляется только через `cz bump` |
| `CHANGELOG.md` | Создаётся как пустой placeholder (`# Changelog`). Наполняется при первом `cz bump` |
| `.cz.toml` | Конфигурация Commitizen: `version_files`, `tag_format`, `update_changelog_on_bump` |
| `backend/app/version.py` | Python-модуль: читает VERSION (fallback для Docker-путей), build из `BUILD_NUMBER` env |
| `frontend/src/pages/ChangelogPage.tsx` | Страница /changelog с карточками версий |
| `backend/app/api/changelog_routes.py` | Роутер: парсинг CHANGELOG.md → JSON |

### Изменения существующих

| Файл | Изменение |
|------|-----------|
| `frontend/package.json` | `version` синхронизируется через `cz bump` (version_files в `.cz.toml`) |
| `frontend/vite.config.ts` | Заменить `__BUILD_TIME__` → `__BUILD_NUMBER__` (из `process.env.BUILD_NUMBER`). Убрать `getBuildTime()`. `__APP_VERSION__` — без изменений (`npm_package_version`) |
| `frontend/src/vite-env.d.ts` | Заменить `__BUILD_TIME__: string` → `__BUILD_NUMBER__: string` |
| `frontend/src/components/layout/Header.tsx` | Версия как кликабельная кнопка → переход на changelog. Отображение: `v{__APP_VERSION__} • build {__BUILD_NUMBER__}` |
| `frontend/src/App.tsx` | State `page: 'dashboard' \| 'changelog'`, условный рендеринг |
| `backend/app/main.py` | `version=` из `version.py`, `/health` с `HealthResponse` (Pydantic) |
| `backend/Dockerfile` | `COPY VERSION .` и `COPY CHANGELOG.md .` перед `COPY app/` |
| `frontend/Dockerfile` | Добавить `ARG BUILD_NUMBER=0` и `ENV BUILD_NUMBER=${BUILD_NUMBER}` перед `RUN npm run build` |
| `docker-compose.yml` | `BUILD_NUMBER=${BUILD_NUMBER:-0}` в environment (backend) + build args (frontend) |
| `scripts/deploy.sh` | Чтение VERSION, инкремент `.build_number` на сервере, `--exclude='.build_number'` в rsync, передача `BUILD_NUMBER` в docker compose (env + build-arg), вывод версии |
| `.gitignore` | +`.build_number` |

### .cz.toml

```toml
[tool.commitizen]
name = "cz_conventional_commits"
version = "0.79.0"
tag_format = "v$version"
update_changelog_on_bump = true
changelog_incremental = true
version_files = [
    "VERSION",
    "frontend/package.json:version",
]
```

> **Примечание:** `version` в `.cz.toml` стартует с `0.79.0` (текущая). Первый `cz bump` обновит до `0.80.0`.

### backend/app/version.py

```python
"""Application version from VERSION file + BUILD_NUMBER from environment."""

import os
from pathlib import Path


def get_version() -> str:
    """Read version from VERSION file.

    Searches for VERSION file at different directory depths to support
    both local development and Docker container environments:
    - Local:  backend/app/version.py → 3 parents up → project root
    - Docker: /app/app/version.py   → 2 parents up → /app/ (WORKDIR)
    """
    for parents_up in (2, 1, 0):
        candidate = Path(__file__).parents[parents_up] / "VERSION"
        if candidate.exists():
            return candidate.read_text().strip()
    return "0.0.0-dev"


def get_build_number() -> int:
    """Read build number from BUILD_NUMBER environment variable."""
    return int(os.environ.get("BUILD_NUMBER", "0"))


__version__ = get_version()
__build__ = get_build_number()
```

### Формат CHANGELOG.md (генерация Commitizen)

Commitizen (`cz_conventional_commits`) генерирует markdown в таком формате:

```markdown
## 0.80.0 (2026-02-22)

### Feat

- поддержка мультиспикерного контента в pipeline
- адаптивные шапки чанков для линейки

### Fix

- исправлены правила frontmatter — globs на paths
```

Парсер в `changelog_routes.py` разбирает этот формат:
1. Разбивает по `## version (date)` — заголовки версий
2. Внутри каждой версии — `### Type` заголовки для группировки
3. Bullet items (`- описание`) → `ChangelogEntry`
4. Маппинг: `Feat` → `feat`, `Fix` → `fix` и т.д. (lowercase)

### Механизм BUILD_NUMBER в deploy.sh

```bash
# 1. Инкремент .build_number на сервере
BUILD_NUM=$(remote "cat ${DEPLOY_PATH}/.build_number 2>/dev/null || echo 0")
BUILD_NUM=$((BUILD_NUM + 1))
remote "echo $BUILD_NUM > ${DEPLOY_PATH}/.build_number"

# 2. Build с передачей BUILD_NUMBER (frontend получает как build-arg)
remote_sudo "cd ${DEPLOY_PATH} && BUILD_NUMBER=$BUILD_NUM docker compose build"

# 3. Up с передачей BUILD_NUMBER (backend получает как env)
remote_sudo "cd ${DEPLOY_PATH} && BUILD_NUMBER=$BUILD_NUM docker compose up -d"
```

**Два пути передачи BUILD_NUMBER:**
- **Backend (runtime):** `docker-compose.yml` → `environment: BUILD_NUMBER` → `os.environ.get("BUILD_NUMBER")` в `version.py`
- **Frontend (build-time):** `docker-compose.yml` → `build: args: BUILD_NUMBER` → `ARG` в Dockerfile → `ENV` → `process.env.BUILD_NUMBER` в vite.config.ts → `__BUILD_NUMBER__` (вшивается в бандл)

### docker-compose.yml (изменения)

```yaml
services:
  bz2-transcriber:
    environment:
      - BUILD_NUMBER=${BUILD_NUMBER:-0}   # runtime — version.py читает из env

  bz2-frontend:
    build:
      context: ./frontend
      args:
        BUILD_NUMBER: ${BUILD_NUMBER:-0}  # build-time — вшивается в бандл
```

### frontend/Dockerfile (изменения)

```dockerfile
FROM node:20-alpine AS builder

ARG BUILD_NUMBER=0
ENV BUILD_NUMBER=${BUILD_NUMBER}

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# ... rest unchanged
```

---

## 7. Ограничения

| Параметр | Лимит | Обоснование |
|----------|-------|-------------|
| Без scopes | `feat: описание` (не `feat(backend): описание`) | Монолитный проект, единая версия |
| Язык CHANGELOG | Русский | Коммиты на русском (по CLAUDE.md), Commitizen корректно работает с кириллицей |
| VERSION — read-only | Обновляется только через `cz bump` | Ручное редактирование сломает синхронизацию |
| Build number — серверный | `.build_number` на сервере, не в git | Инкремент при каждом деплое, не при коммите |
| Текущая версия 0.79.0 | Продолжаем, первый `cz bump` создаст v0.80.0 | Не пересоздаём историю версий |
| CHANGELOG ретроспективно | Этап 3: записи v0.29–v0.79 из git log + CLAUDE.md | Коммиты уже в conventional format, данных достаточно для качественной ретроспективы |
| Без react-router | Навигация через state в App.tsx | Одна дополнительная «страница», не стоит добавлять зависимость |
| Browser back не работает | State не интегрирован с history API | Приемлемо для одной доп. страницы, кнопка «← Назад» есть в UI |
| Commitizen — глобальный dev-инструмент | Установка через `pipx install commitizen`, не нужен в Docker | Только для bump/changelog на машине разработчика |
| Первый тег | `v0.79.0` создаётся вручную **перед** первым `cz bump` | `cz bump` работает начиная со следующего релиза |
| Header: build вместо даты | `v0.80.0 • build 42` вместо `v0.80.0 • 22.02.26 15:30` | Build number полезнее при нескольких деплоях в день; дата — в журнале изменений у релизных версий |
| BUILD_NUMBER — два пути | Backend: runtime env; Frontend: build-arg (вшивается в бандл) | Backend читает при каждом запросе, frontend — статически при сборке |

---

## 8. План реализации

### Этап 1: Инфраструктура версионирования (v0.80)

Commitizen, VERSION файл, синхронизация backend/frontend, deploy интеграция.

- [ ] Создать `VERSION` файл в корне (`0.79.0`)
- [ ] Создать `CHANGELOG.md` — пустой placeholder (`# Changelog\n`) для корректной работы Dockerfile
- [ ] Создать `.cz.toml` с конфигурацией Commitizen
- [ ] Создать `backend/app/version.py` — чтение VERSION (с fallback для Docker) + BUILD_NUMBER
- [ ] Обновить `backend/app/main.py:53` — `version=__version__` из `version.py`
- [ ] Обновить `GET /health` — `HealthResponse` (Pydantic) с version + build
- [ ] Обновить `backend/Dockerfile` — `COPY VERSION .` и `COPY CHANGELOG.md .` перед `COPY app/`
- [ ] Обновить `frontend/vite.config.ts` — заменить `__BUILD_TIME__` → `__BUILD_NUMBER__` (из `process.env.BUILD_NUMBER`), убрать `getBuildTime()`
- [ ] Обновить `frontend/src/vite-env.d.ts` — заменить `__BUILD_TIME__` → `__BUILD_NUMBER__`
- [ ] Обновить `frontend/Dockerfile` — добавить `ARG BUILD_NUMBER=0` и `ENV BUILD_NUMBER=${BUILD_NUMBER}`
- [ ] Обновить `docker-compose.yml` — `BUILD_NUMBER` в environment (backend) + build args (frontend)
- [ ] Обновить `scripts/deploy.sh` — чтение VERSION, инкремент `.build_number`, `--exclude`, передача `BUILD_NUMBER` в docker compose (env + build-arg), вывод версии
- [ ] Добавить `.build_number` в `.gitignore`
- [ ] Создать git tag `v0.79.0` вручную (точка отсчёта, **обязательно перед** `cz bump`)
- [ ] Первый `cz bump` → v0.80.0, обновление CHANGELOG.md

### Этап 2: API changelog + UI (v0.81)

Endpoint для отдачи CHANGELOG, страница /changelog, кликабельная версия в Header.

- [ ] Создать `backend/app/api/changelog_routes.py` — парсер CHANGELOG.md + endpoint
- [ ] Pydantic модели (наследуют `CamelCaseModel`): `ChangelogEntry`, `ChangelogVersion`, `ChangelogResponse`
- [ ] Зарегистрировать роутер в `backend/app/main.py`
- [ ] Создать `frontend/src/pages/ChangelogPage.tsx` — карточки версий с бейджами
- [ ] Обновить `frontend/src/App.tsx` — state `page`, условный рендеринг
- [ ] Обновить `frontend/src/components/layout/Header.tsx` — версия как кликабельная кнопка

### Этап 3: Ретроспективный CHANGELOG

Наполнение CHANGELOG.md записями предыдущих версий (v0.29–v0.79) на основе git-истории и артефактов проекта. Выполняется после Этапа 1 (когда CHANGELOG.md уже создан через `cz bump` с первой записью v0.80.0).

**Источники данных (по приоритету):**
1. `git log --oneline` — коммиты в conventional format (`feat:`, `fix:`, `refactor:`) с указанием версий в скобках
2. Таблица «Текущий статус» в `CLAUDE.md` — краткие описания версий v0.29–v0.79
3. `docs/decisions/` — ADR с привязкой к версиям (ADR-020 → v0.77, ADR-021 → v0.78, ADR-022 → v0.79)
4. Коммиты `docs:` и `chore: bump version` — для определения дат релизов

**Формат:** Соблюдать формат Commitizen (парсер уже написан на Этапе 2):
```markdown
## 0.79.0 (2026-02-XX)

### Feat

- поддержка мультиспикерного контента в pipeline
- адаптивные шапки чанков для линейки

### Fix

- frontmatter rules файлов — globs → paths
```

**Задачи:**
- [ ] Собрать маппинг версий → коммитов из git log (коммиты с `(v0.XX)` в описании + `chore: bump version`)
- [ ] Определить даты версий из коммитов `chore: bump` или первого `feat:` коммита версии
- [ ] Сформировать записи для каждой версии: сгруппировать коммиты по типам (Feat/Fix/Refactor)
- [ ] Записать в CHANGELOG.md **ниже** записи v0.80.0 (новые вверху — Commitizen convention)
- [ ] Проверить: `/api/changelog` возвращает все версии, `/changelog` UI отображает карточки
- [ ] Заморозить таблицу «Текущий статус» в CLAUDE.md — добавить ссылку «Полная история: CHANGELOG.md»

**Границы:**
- Версии до v0.29 не включаются (нет conventional commits, мало информации)
- Пропуски в нумерации (v0.30–v0.50, v0.52–v0.58, v0.66) — нормально, это были промежуточные коммиты без явного релиза
- Описания берутся из коммитов as-is; если коммит на английском — перевести на русский для единообразия

---

## 9. Тестирование

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| `cat VERSION` | `0.80.0` |
| `python3 -c "from app.version import __version__; print(__version__)"` | `0.80.0` |
| `docker exec bz2-transcriber python -c "from app.version import __version__; print(__version__)"` | `0.80.0` (проверка Docker-путей) |
| `cz bump --dry-run` | Показывает следующую версию |
| `cz bump` (после feat) | Minor bump, обновлён VERSION + package.json + CHANGELOG.md + git tag |
| `curl -k https://transcriber.home/health` | `{"status": "ok", "version": "0.80.0", "build": 42}` |
| `curl -k https://transcriber.home/api/changelog` | JSON с массивом версий |
| Вывод deploy.sh | "Deploying v0.80.0 (build 42)" |
| Header в браузере | `v0.80.0 • build 42` (версия + build number, без даты) |
| Клик по версии в Header | Открывается страница changelog |
| Страница /changelog | Карточки с бейджами, последняя версия сверху |
| Пустой CHANGELOG | "История изменений пока недоступна" |
| `git tag -l` | Содержит `v0.80.0` |
| `.build_number` на сервере | Инкрементируется при каждом деплое |
| FastAPI /docs | Корректная версия в заголовке |
| `frontend/package.json` version | Совпадает с `VERSION` |

---

## 10. Референсы

- [docs/reference/versioning.md](../reference/versioning.md) — аналогичная система в BZ2-Bot (референсная реализация)
- [Commitizen documentation](https://commitizen-tools.github.io/commitizen/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- `frontend/src/components/layout/Header.tsx` — текущее отображение версии
- `backend/app/main.py` — FastAPI app с hardcoded version

---

## Решённые вопросы

| Вопрос | Решение | Обоснование |
|--------|---------|-------------|
| Scopes в коммитах? | Без scopes | Монолитный проект, единая версия, один разработчик |
| SemVer или CalVer? | SemVer | Коммиты уже в формате conventional (feat/fix), семантика полезнее даты |
| Инструмент? | Commitizen | Python-экосистема, одна команда `cz bump`, auto CHANGELOG |
| Source of Truth? | Файл `VERSION` | Простейший формат, читается из Python. Frontend — через package.json (synced) |
| Порядок в CHANGELOG? | Новые версии вверху (prepend) | Commitizen по умолчанию prepend'ит, парсер читает сверху вниз — порядок для UI совпадает |
| Build number? | Счётчик деплоев (`.build_number` на сервере) | Привязан к деплоям, всегда растёт, легко сравнить |
| Навигация? | State в App.tsx | Одна дополнительная «страница», react-router — overkill |
| Где версия в UI? | Header (как сейчас) + клик → /changelog | Естественная точка входа |
| Ретроспективный CHANGELOG? | Да, Этап 3 (отдельный) | Git log + CLAUDE.md таблица + ADR. Версии v0.29–v0.79, формат Commitizen |
| Деплой ≠ релиз? | Да | Деплой — часто, `cz bump` — по рекомендации /finalize |
| vite.config.ts менять? | Да, но минимально | `__APP_VERSION__` — без изменений (`npm_package_version`). Заменить `__BUILD_TIME__` → `__BUILD_NUMBER__` (из `process.env.BUILD_NUMBER`). Убрать `getBuildTime()` |
| version.py и Docker-пути? | Fallback-поиск VERSION (parents 2→1→0) | Локально: 3-й parent = project root; Docker: 2-й parent = WORKDIR `/app/`; код ищет VERSION на каждом уровне |
| Дата или build в Header? | Build number | При нескольких деплоях в день build number информативнее даты. Дата доступна в журнале изменений у релизных версий |
| BUILD_NUMBER во frontend? | Да, через docker build-arg | Backend: runtime env (version.py). Frontend: build-arg → ENV → vite define → вшивается в бандл при сборке |
| CHANGELOG.md до первого bump? | Пустой placeholder в git | Dockerfile `COPY CHANGELOG.md .` не сломается на первом деплое |
| /health — Pydantic? | Да, `HealthResponse(CamelCaseModel)` | CLAUDE.md: «API endpoints — ВСЕГДА Pydantic модели» |
| Commitizen — как установить? | `pipx install commitizen` (глобально) | Dev-инструмент разработчика, не нужен в venv проекта или Docker |
| Browser back на /changelog? | Known limitation | State не интегрирован с history API; кнопка «← Назад» в UI достаточна для одной страницы |

## Открытые вопросы

Нет открытых вопросов.

---

## История изменений

| Дата | Версия | Изменения |
|------|--------|-----------|
| 2026-02-22 | 1.0 | Первоначальная версия |
| 2026-02-22 | 1.1 | Ревью: Docker-пути version.py (fallback), CHANGELOG placeholder, HealthResponse Pydantic, BUILD_NUMBER mechanism, CamelCaseModel для changelog, формат Commitizen, browser back limitation, pipx |
| 2026-02-22 | 1.2 | Header: build number вместо даты, BUILD_NUMBER передаётся и во frontend (docker build-arg), vite.config.ts: `__BUILD_TIME__` → `__BUILD_NUMBER__`, frontend/Dockerfile: ARG BUILD_NUMBER |
| 2026-02-22 | 1.3 | Этап 3: ретроспективный CHANGELOG (v0.29–v0.79) из git log + CLAUDE.md + ADR, с конкретным планом и источниками данных |

---

_Документ для планирования в Claude Code_
