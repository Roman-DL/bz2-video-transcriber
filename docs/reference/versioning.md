# Система версионирования

> Единая SemVer-версия для всего проекта с автоматической генерацией CHANGELOG

**Статус:** Done
**Дата:** 2026-02-22
**Серия:** [ROADMAP.md](ROADMAP.md) — требование #9

---

## 1. Проблема

Проект не имеет единой системы версионирования. Невозможно определить какая версия развёрнута на сервере, нет связи между git-коммитами и релизами, CHANGELOG не ведётся.

**Текущая ситуация:**
- Бот: `"2.0.0"` hardcoded в `src/main.py` (health endpoint)
- Admin API: `"1.0.0"` hardcoded в `src/admin/app.py` (FastAPI title)
- Admin Portal: `"0.0.0"` в `package.json` (заглушка Vite)
- Docker образы: без тегов версий
- Git tags: не используются
- CHANGELOG: не ведётся
- Deploy: `deploy.sh` не отслеживает версии

**Почему это проблема:**
- Невозможно быстро определить версию на сервере (кроме ручной проверки health endpoint бота)
- Нет связи между коммитами и версиями — нельзя откатиться к конкретной версии
- Нет CHANGELOG — трудно вспомнить что менялось
- Три разных номера версий рассинхронизированы (2.0.0, 1.0.0, 0.0.0)
- При отладке на сервере нет способа подтвердить какой код запущен

---

## 2. Решение

### Концепция

Два уровня версионирования:

1. **Версия (SemVer)** — `2.1.0` — осмысленный релиз, меняется при `cz bump`
2. **Номер сборки (build)** — `23` — счётчик деплоев, инкрементируется при каждом `deploy.sh`

Отображение: `2.1.0 (build 23)`. Всегда видно и версию, и конкретную сборку.

```
VERSION (файл) ──────────────────→ "2.1.0"
deploy.sh (.build_number) ──────→ "23"
                                      │
                              "2.1.0 (build 23)"

cz bump (релиз)
    → собирает ВСЕ коммиты с последнего тега
    → определяет major/minor/patch из типов коммитов
    → обновляет VERSION + package.json
    → генерирует CHANGELOG.md (все коммиты с последнего тега)
    → создаёт git commit + git tag vX.Y.Z
```

**Деплой ≠ релиз.** Деплоить можно часто (для тестирования), build number инкрементируется при каждом деплое. Релиз (`cz bump`) — когда `/finalize` рекомендует (или разработчик решает сам). Все коммиты между тегами всегда попадают в CHANGELOG — ничего не теряется.

### Ключевые идеи

1. **Единая версия** — бот, API и фронтенд версионируются вместе. Проект деплоится атомарно (docker compose), один разработчик, компоненты тесно связаны. Раздельные версии — лишний overhead.

2. **SemVer** — коммиты уже используют формат `feat:` / `fix:` / `refactor:`, что идеально ложится на MAJOR.MINOR.PATCH. CalVer не даёт семантики изменений.

3. **Commitizen** — Python-инструмент, одна команда `cz bump` делает bump + changelog + commit + tag. Уже в экосистеме проекта (pip install).

4. **Стартовая версия 2.1.0** — продолжение от текущего бота (2.0.0), следующий minor.

### Commit scopes (разделение по модулям)

Для отслеживания изменений по компонентам — scopes в коммитах:

```
feat(bot): добавлен голосовой поиск
fix(admin): исправлена пагинация таблицы
refactor: обновлена структура конфига
```

| Scope | Что входит |
|-------|-----------|
| `bot` | Telegram бот (хэндлеры, поиск, голосовые, контент) |
| `admin` | Админ-портал (API + фронтенд) |
| без scope | Инфраструктура, конфиг, БД, общее |

Commitizen автоматически включает scope в CHANGELOG:

```markdown
## 2.2.0 (2026-02-25)

### Feat
- **bot**: добавлен голосовой поиск
- **admin**: страница аналитики

### Fix
- **bot**: исправлена обработка голосовых
```

API-эндпоинт `/api/changelog` парсит CHANGELOG.md и возвращает структурированный JSON с группировкой по модулям — для отображения в админ-портале.

### Архитектура

```
  VERSION (2.1.0)       .build_number на сервере (23)
        │                            │
        └──────────┬─────────────────┘
                   ▼
           src/__version__.py    (version из VERSION)
           deploy.sh             (build из .build_number)
                   │
    ┌──────────────┼──────────────────┐
    ▼              ▼                  ▼
  Python        Vite              deploy.sh
  (health,      (sidebar          "Deploying
   logs,         footer)           v2.1.0
   FastAPI)                        (build 23)"
```

### Триггер релиза

`/finalize` проверяет коммиты с последнего тега и рекомендует релиз:

```
/finalize после мелкого fix:
  → "С последнего тега: 1 fix. Пока рано для релиза."

/finalize после крупной фичи:
  → "С последнего тега v2.1.0: 3 feat, 2 fix (5 коммитов).
     Рекомендую релиз: cz bump → v2.2.0. Сделать?"

cz bump собирает ВСЕ 5 коммитов в CHANGELOG — ничего не теряется.
```

---

## 3. Пользовательский сценарий

### Сценарий A: Разработчик делает релиз

```
1. Разработчик завершает работу над фичами
2. Запускает: cz bump
3. Commitizen анализирует коммиты с последнего тега:
   - 3 feat: → minor bump
   - 2 fix: → patch (перекрывается minor)
   → Версия: 2.1.0 → 2.2.0
4. Автоматически:
   - Обновлён VERSION (2.2.0)
   - Обновлён package.json (2.2.0)
   - Сгенерирован CHANGELOG.md
   - Создан git commit "bump: version 2.1.0 → 2.2.0"
   - Создан git tag v2.2.0
5. Разработчик запускает: ./scripts/deploy.sh
6. На сервере: docker compose build + up
```

### Сценарий B: Обычный деплой (без релиза)

```
1. Написал код → commit → deploy.sh
2. deploy.sh: инкрементирует .build_number (23 → 24)
3. deploy.sh выводит: "Deploying v2.1.0 (build 24)"
4. Sidebar footer: "v2.1.0 (build 24)"
5. Health: {"version": "2.1.0", "build": 24}
6. Следующий деплой:
   - "Deploying v2.1.0 (build 25)"
   - Видно: 24 → 25, значит обновилось
```

### Сценарий C: Проверка версии на сервере

```
1. Админ открывает портал → sidebar footer: "v2.2.0 (build 30)"
2. Или: curl server:8081/health → {"status": "ok", "version": "2.2.0", "build": 30}
3. Или: curl server:8080/api/health → {"status": "ok", "version": "2.2.0", "build": 30}
4. В логах бота при старте: "app_starting version=2.2.0 build=30"
```

### Сценарий D: Hotfix

```
1. Баг на production → быстрый fix
2. git commit -m "fix: описание бага"
3. cz bump → 2.2.0 → 2.2.1 (patch)
4. ./scripts/deploy.sh → "Deploying v2.2.1 (build 31)"
```

### Сценарий E: Просмотр CHANGELOG в портале

```
1. Админ открывает портал → sidebar footer: "v2.2.0 (build 30)"
2. Кликает по версии → страница "Журнал изменений"
3. Видит список релизов: v2.2.0 (25.02.2026), v2.1.0 (22.02.2026)
4. В каждом релизе — группы: Бот, Админ-портал, Общее
5. Быстро находит что менялось в боте vs портале
```

### Сценарий F: /finalize и релиз

```
1. Закончил мелкий fix → /finalize
   → Claude: "С последнего тега: 1 fix. Пока рано для релиза."
2. Закончил ещё fix → /finalize
   → Claude: "С последнего тега: 2 fix. Пока рано."
3. Закончил крупную фичу → /finalize
   → Claude: "С v2.1.0: 2 feat, 2 fix (4 коммита).
      Рекомендую релиз: cz bump → v2.2.0. Сделать?"
4. cz bump → CHANGELOG включает ВСЕ 4 коммита
5. deploy.sh → "Deploying v2.2.0 (build 28)"
```

---

## 4. UI

### Sidebar footer (Admin Portal)

```
┌──────────────────────┐
│ ☰ Админ-портал       │
│                      │
│ 📊 Материалы         │
│ 👥 Пользователи      │
│ ⚙️ Настройки         │
│ 📈 Аналитика         │
│                      │
│                      │
│                      │
│ ─────────────────    │
│ v2.1.0 (build 23)   │
└──────────────────────┘
```

- Мелкий текст `text-muted-foreground` внизу sidebar
- Клик по версии → переход на страницу CHANGELOG

### Страница CHANGELOG (Admin Portal)

Доступ: клик по версии в sidebar footer → `/changelog`

```
┌─────────────────────────────────────────────────┐
│ Журнал изменений                                │
│                                                 │
│ ┌─────────────────────────────────────────────┐ │
│ │ v2.2.0 — 25 февраля 2026                   │ │
│ │                                             │ │
│ │ 🤖 Бот                                     │ │
│ │   • Добавлен голосовой поиск                │ │
│ │   • Исправлена обработка голосовых          │ │
│ │                                             │ │
│ │ 🖥️ Админ-портал                            │ │
│ │   • Страница аналитики                      │ │
│ │                                             │ │
│ │ 🔧 Общее                                   │ │
│ │   • Обновлена структура конфига             │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ ┌─────────────────────────────────────────────┐ │
│ │ v2.1.0 — 22 февраля 2026                   │ │
│ │                                             │ │
│ │ 🤖 Бот                                     │ │
│ │   • Начальная версия: поиск, навигация      │ │
│ │   ...                                       │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

- Каждая версия — карточка (`Card`) с заголовком `v{version} — {дата}`
- Внутри — группировка по модулям (Бот / Админ-портал / Общее)
- Типы коммитов (feat/fix) не показываются — только описания
- Новые версии вверху

---

## 5. API

### Health endpoints (изменения)

**Bot health** (порт 8081) — уже возвращает version, заменить hardcode + добавить build:

```
GET /health
→ {"status": "ok", "uptime_seconds": 3600, "version": "2.1.0", "build": 23}
```

**Admin API health** (порт 8080) — добавить version и build:

```
GET /api/health
→ {"status": "ok", "version": "2.1.0", "build": 23}
```

**FastAPI OpenAPI** — версия в Swagger UI:

```python
app = FastAPI(title="BZ2 Admin API", version=__version__)
```

### CHANGELOG endpoint

```
GET /api/changelog
→ {
    "versions": [
      {
        "version": "2.2.0",
        "date": "2026-02-25",
        "modules": {
          "bot": ["Добавлен голосовой поиск", "Исправлена обработка голосовых"],
          "admin": ["Страница аналитики"],
          "other": ["Обновлена структура конфига"]
        }
      },
      ...
    ]
  }
```

- Читает `CHANGELOG.md` из файловой системы
- Парсит markdown: версии → типы → записи со scopes
- Перегруппировывает по модулям (`bot`, `admin`, `other`)
- Описания без type-prefix (показываем «Добавлен голосовой поиск», не «feat: добавлен...»)

---

## 6. Данные

### Новые файлы

| Файл | Назначение |
|------|------------|
| `VERSION` | Single Source of Truth — одна строка с версией (в git) |
| `src/__version__.py` | Python-модуль, читает VERSION |
| `CHANGELOG.md` | Автогенерация через commitizen |
| `pyproject.toml` | Конфигурация commitizen (`version_files`, `tag_format`) |
| `requirements-dev.txt` | Dev-зависимости (`-r requirements.txt` + commitizen) |

### Изменения существующих

| Файл | Изменение |
|------|-----------|
| `src/main.py` | `"2.0.0"` → `__version__`, `__build__` из `src/__version__.py` |
| `src/admin/app.py` | `"1.0.0"` → `__version__`, `__build__` из `src/__version__.py` |
| `admin-portal/package.json` | `"0.0.0"` → `"2.1.0"` (синхронизируется через commitizen) |
| `admin-portal/vite.config.ts` | Добавить `define: { __APP_VERSION__: ..., __APP_BUILD__: ... }` |
| `admin-portal/src/vite-env.d.ts` | Объявить `__APP_VERSION__`, `__APP_BUILD__` |
| `admin-portal/src/components/layout/app-sidebar.tsx` | Footer-секцию с версией (клик → CHANGELOG) |
| `deploy/Dockerfile.frontend` | `ARG BUILD_NUMBER` для передачи в Vite build |
| `docker-compose.yml` | `environment: BUILD_NUMBER` для Python-контейнеров |
| `scripts/deploy.sh` | Инкремент `.build_number`, `--exclude`, build-arg, вывод версии |
| `.gitignore` | +`.build_number` |
| `src/admin/routers/changelog.py` | Новый роутер: парсинг CHANGELOG.md → JSON |
| `admin-portal/src/pages/changelog/` | Новая страница: отображение CHANGELOG |
| `CLAUDE.md` | Конвенция commit scopes (секция «Ключевые ограничения» или git commits) |

---

## 7. Ограничения

| Параметр | Лимит | Обоснование |
|----------|-------|-------------|
| Стартовая версия | 2.1.0 | Продолжение от бота 2.0.0 (ядро проекта) |
| Формат тегов | `vX.Y.Z` | Стандарт commitizen |
| CHANGELOG язык | Русский (описания коммитов) | Коммиты на русском, commitizen корректно работает с кириллицей |
| Commitizen type prefixes | Английские (feat, fix, refactor) | Commitizen парсит только prefix до двоеточия |
| VERSION файл | Только одна строка, без пробелов | Парсинг через `.strip()`. Файл в git (Source of Truth) |
| `.build_number` | Только на сервере, в `.gitignore` | Счётчик деплоев, не часть кодовой базы |
| Первый тег | `v2.1.0` создаётся вручную | `cz bump` используется начиная со следующего релиза |
| Commitizen | Dev-зависимость (`requirements-dev.txt`) | Не нужен в production Docker-образах |
| Commit scopes | `bot`, `admin`, без scope | Минимальный набор для разделения в CHANGELOG. Расширять при необходимости |

---

## 8. План реализации

### Этап 1: Инфраструктура версии

- [ ] Создать `VERSION` файл (`2.1.0`)
- [ ] Создать `src/__version__.py` (читает VERSION; build из `BUILD_NUMBER` env var)
- [ ] Создать `pyproject.toml` с конфигурацией commitizen:
  ```toml
  [tool.commitizen]
  version = "2.1.0"
  version_files = [
      "VERSION",
      "admin-portal/package.json:version",
  ]
  tag_format = "v$version"
  update_changelog_on_bump = true
  ```
- [ ] Создать `requirements-dev.txt` (`-r requirements.txt` + commitizen)
- [ ] Добавить `.build_number` в `.gitignore`
- [ ] Обновить конвенцию коммитов в `CLAUDE.md`: добавить scopes (`bot`, `admin`)

### Этап 2: Замена hardcodes (Python)

- [ ] `src/main.py`: health endpoint → `__version__` + `__build__`
- [ ] `src/main.py`: startup log → `__version__` + `__build__`
- [ ] `src/admin/app.py`: FastAPI version → `__version__`
- [ ] `src/admin/app.py`: health endpoint → добавить `version` + `build`
- [ ] `src/admin/routers/changelog.py`: эндпоинт парсинга CHANGELOG.md → JSON (группировка по модулям)
- [ ] Зарегистрировать роутер в `src/admin/app.py`

### Этап 3: Frontend

- [ ] `admin-portal/vite.config.ts`: `define: { __APP_VERSION__: ..., __APP_BUILD__: ... }`
- [ ] `admin-portal/package.json`: обновить version → `2.1.0`
- [ ] TypeScript: объявить `__APP_VERSION__`, `__APP_BUILD__` в `vite-env.d.ts`
- [ ] Создать footer-секцию в sidebar (`app-sidebar.tsx`) с `v{version} (build {N})`
  - Сейчас sidebar не имеет footer — `"БЗ 2.0"` в заголовке это название, не версия
  - Клик по версии → навигация на `/changelog`
- [ ] Создать страницу `/changelog`: карточки версий, группировка по модулям
- [ ] Добавить маршрут в React Router

### Этап 4: Deploy интеграция

- [ ] `deploy.sh`: добавить `--exclude='.build_number'` в rsync (иначе `--delete` удалит его)
- [ ] `deploy.sh`: инкрементировать `.build_number` на сервере **ПЕРЕД** `docker compose build`
- [ ] `deploy.sh`: читать `VERSION` и `.build_number`, выводить `"Deploying v{version} (build {N})"`
- [ ] `deploy.sh`: передать `BUILD_NUMBER` в `docker compose build --build-arg`
- [ ] `Dockerfile.frontend`: `ARG BUILD_NUMBER=0` → передать в Vite build через env
- [ ] `docker-compose.yml`: `environment: BUILD_NUMBER` для Python-контейнеров (runtime)

### Этап 5: Интеграция с /finalize

- [ ] Добавить в `/finalize` проверку коммитов с последнего тега
- [ ] Логика рекомендации: предлагать релиз при значительных изменениях

### Этап 6: Первый релиз

- [ ] Создать начальный `CHANGELOG.md` (вручную — описание текущего состояния)
- [ ] Создать git tag `v2.1.0` вручную (`git tag v2.1.0`)
- [ ] `cz bump --dry-run` — проверка что следующий bump работает корректно
- [ ] Проверить: health endpoints, sidebar, логи, deploy.sh

---

## 9. Тестирование

| Сценарий | Ожидаемый результат |
|----------|---------------------|
| `cat VERSION` | `2.1.0` |
| `BUILD_NUMBER=23 python -c "from src.__version__ import __version__, __build__; print(f'{__version__} build {__build__}')"` | `2.1.0 build 23` |
| `curl localhost:8081/health` | `{"version": "2.1.0", "build": 23, ...}` |
| `curl localhost:8080/api/health` | `{"version": "2.1.0", "build": 23}` |
| Sidebar footer в портале | `v2.1.0 (build 23)` |
| `cz bump --dry-run` | Показывает следующую версию |
| `git tag -l` | `v2.1.0` |
| Startup log бота | `version=2.1.0 build=23` |
| VERSION файл отсутствует | `__version__` = `"0.0.0-dev"` |
| `BUILD_NUMBER` не задан | `__build__` = `0` |
| `deploy.sh` | `Deploying v2.1.0 (build 23)` |
| `curl localhost:8080/api/changelog` | JSON с версиями, модулями, описаниями |
| Клик по версии в sidebar | Переход на `/changelog` |
| Страница CHANGELOG | Карточки версий с группировкой Бот / Админ-портал / Общее |
| Коммит `feat(bot): тест` → `cz bump` | В CHANGELOG запись в группе «Бот» |

---

## 10. Референсы

- [Commitizen documentation](https://commitizen-tools.github.io/commitizen/)
- [SemVer specification](https://semver.org/)
- `src/main.py` — текущий health endpoint с hardcoded version
- `src/admin/app.py` — текущий FastAPI app с hardcoded version
- `admin-portal/package.json` — текущая заглушка 0.0.0

---

## Решённые вопросы

| Вопрос                        | Решение                                         | Обоснование                                                                                                   |
| ----------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Единая или раздельные версии? | Единая                                          | Атомарный деплой, один разработчик, тесная связь компонентов                                                  |
| SemVer или CalVer?            | SemVer                                          | Коммиты уже используют conventional format (feat/fix), семантика полезнее даты                                |
| Стартовая версия?             | 2.1.0                                           | Продолжение от бота 2.0.0 — ядра проекта                                                                      |
| Инструмент автоматизации?     | Commitizen (Python)                             | В экосистеме проекта, поддерживает version_files, одна команда cz bump                                        |
| Single Source of Truth?       | Файл `VERSION`                                  | Простейший формат, читается из Python и Node.js                                                               |
| CHANGELOG формат?             | Авто через commitizen                           | Zero effort, коммиты уже в правильном формате                                                                 |
| Pre-release версии?           | Нет                                             | Не нужен формат `2.1.0-beta.1`, простые номера достаточно                                                     |
| Кто определяет версию?        | Commitizen автоматически                        | `feat:` → MINOR, `fix:` → PATCH, детерминированно из коммитов. Разработчик решает только *когда* делать релиз |
| CHANGELOG и рост?             | Не проблема                                     | Новое вверху, в контекст AI не грузится (работает с git log). Для человека — быстрый обзор последних релизов  |
| Деплой ≠ релиз?               | Да, разные операции                             | Деплой — часто (тестирование), релиз (`cz bump`) — когда набралась осмысленная единица                        |
| Build number формат?          | Счётчик деплоев (`.build_number` на сервере)    | Привязан к деплоям (нагляднее коммитов), всегда растёт, легко сравнить                                        |
| Когда делать релиз?           | `/finalize` подсказывает                        | Проверяет коммиты с последнего тега, рекомендует при значительных изменениях. Решение за разработчиком        |
| Потеряются ли коммиты?        | Нет, `cz bump` берёт ВСЕ с последнего тега      | Неважно когда релиз — все коммиты между тегами попадают в CHANGELOG                                           |
| Deploy.sh и версия?           | Да, выводить `Deploying v{version} (build {N})` | Сразу видно что деплоится                                                                                     |
| Docker image tags?            | Нет, не нужны пока нет registry                 | Образы собираются локально, `docker compose build` пересобирает latest                                        |
| Commitizen — prod или dev?    | Dev-зависимость (`requirements-dev.txt`)         | Нужен только для bump/changelog на машине разработчика, не в Docker                                           |
| Первый тег?                   | Вручную `git tag v2.1.0`                         | `cz bump` работает начиная со следующего релиза, первый тег — точка отсчёта                                   |
| CHANGELOG на русском?         | Да                                               | Коммиты на русском, commitizen корректно работает с кириллицей                                                |
| rsync и `.build_number`?      | `--exclude='.build_number'` в deploy.sh          | `rsync --delete` удалит файл на сервере если его нет в репозитории                                            |
| Дата деплоя в sidebar?        | Пока нет, возможно позже                         | Build number важнее при активной разработке, дата — на длинной дистанции                                       |
| Как разделять модули в CHANGELOG? | Commit scopes (`bot`, `admin`) + API-парсинг   | Commitizen автоматически включает scope, API перегруппировывает для фронтенда                                  |
| Где показывать CHANGELOG?     | Страница в админ-портале, клик по версии в sidebar | Естественная точка входа — версия в sidebar footer                                                             |
| Type-prefix в UI?             | Не показывать (feat/fix)                         | Пользователю важно «что изменилось», не тип коммита. Type-prefix остаётся в git и CHANGELOG.md               |

## Открытые вопросы

Нет открытых вопросов.

---

## История изменений

| Дата | Версия | Изменения |
|------|--------|-----------|
| 2026-02-22 | 1.0 | Первоначальная версия: исследование + требования |
| 2026-02-22 | 1.1 | Build = счётчик деплоев, интеграция с /finalize, закрыты все вопросы |
| 2026-02-22 | 1.2 | Ревью: детализация Этапа 4 (deploy flow, rsync, Docker build-arg), `requirements-dev.txt`, конфигурация commitizen, первый тег вручную, sidebar footer уточнение |
| 2026-02-22 | 1.3 | CHANGELOG-страница в админ-портале, commit scopes (bot/admin), API-эндпоинт парсинга, группировка по модулям |

---

_Документ для планирования в Claude Code_

---

## Pre-flight: Система версионирования

### Архитектурный контекст

**Релевантные компоненты:**
- **src/main.py** — health endpoint бота (строка 31: `"2.0.0"` hardcode, строка 63: `version="2.0.0"` в логе)
- **src/admin/app.py** — FastAPI app (строка 28: `version="1.0.0"` hardcode), health endpoint (строка 76-79: без version/build)
- **admin-portal/package.json** — `"version": "0.0.0"` (строка 4)
- **admin-portal/vite.config.ts** — нет `define` секции, нужно добавить
- **admin-portal/src/vite-env.d.ts** — нет объявлений `__APP_VERSION__` / `__APP_BUILD__`
- **admin-portal/src/components/layout/app-sidebar.tsx** — уже есть `SidebarFooter` с кнопкой Settings. Версию добавить ниже кнопки Settings (перед закрытием `SidebarFooter`)
- **scripts/deploy.sh** — нет `.build_number` логики, нет `--exclude`, нет build-arg
- **docker-compose.yml** — нет `BUILD_NUMBER` env var, нет build-arg для frontend
- **deploy/Dockerfile.python** — не копирует `VERSION` файл (нужно добавить `COPY VERSION .`)
- **deploy/Dockerfile.frontend** — нет `ARG BUILD_NUMBER`
- **src/admin/routers/__init__.py** — пустой docstring, роутеры регистрируются в `app.py` напрямую
- **admin-portal/src/App.tsx** — нужно добавить маршрут `/changelog`

**Релевантные ADR:**
- ADR-001 (Technology Stack) — выбор Python-стека, не конфликтует
- ADR-003 (Admin Portal Stack) — Vite + React + shadcn/ui, `define` в vite.config.ts — стандартный паттерн Vite
- Релевантных ADR нет — версионирование не противоречит принятым решениям

**Ограничения из CLAUDE.md:**
- «НИКОГДА не усложнять архитектуру» — Commitizen + VERSION файл — минимальная сложность, ✅
- «ВСЕГДА использовать популярные библиотеки» — Commitizen, 7.6k stars на GitHub, ✅
- «ВСЕГДА добавлять логирование» — startup log уже есть, нужно обновить version param, ✅
- Конфликтов с ограничениями нет

**Rules (.claude/rules/):**
- `admin-api.md`: учтён — thin routers, `Depends(get_current_user)` на changelog endpoint. Порядок routes: `/api/changelog` — отдельный роутер, не sub-path, конфликтов нет
- `admin-portal.md`: учтён — Vite define, sidebar footer, React Router маршрут, direct fetch для changelog (не Refine CRUD)
- `infrastructure.md`: учтён — `settings.py` без изменений, `VERSION` читается в `__version__.py`
- `bot.md`: не затрагивается (health endpoint в `main.py`, не в handlers)
- `search.md`: не затрагивается
- `content.md`: не затрагивается
- `users.md`: не затрагивается

### Рекомендации по интеграции

**Этап 1 — Инфраструктура:**
- `VERSION` — корень проекта, одна строка `2.1.0`
- `src/__version__.py` — читает `VERSION` через `pathlib.Path`, fallback `"0.0.0-dev"`. Build из `os.environ.get("BUILD_NUMBER", "0")`
- `pyproject.toml` — новый файл (сейчас НЕТ в проекте), конфиг commitizen
- `requirements-dev.txt` — новый файл, `-r requirements.txt` + `commitizen`
- `.gitignore` — добавить `.build_number`
- `deploy/Dockerfile.python` — добавить `COPY VERSION .` перед `COPY config/`

**Этап 2 — Python hardcodes:**
- `src/main.py:31` → `from src.__version__ import __version__, __build__`, использовать в health и логе
- `src/admin/app.py:28` → `version=__version__`, health endpoint → добавить `version` + `build`
- `src/admin/routers/changelog.py` — новый роутер, парсинг CHANGELOG.md (regex), группировка по scopes → JSON

**Этап 3 — Frontend:**
- `vite.config.ts` → добавить `define: { __APP_VERSION__: JSON.stringify(...)`, __APP_BUILD__: ... }`
  - VERSION читать из `../VERSION` через `fs.readFileSync`
  - BUILD_NUMBER из `process.env.BUILD_NUMBER || "0"`
- `vite-env.d.ts` → объявить `__APP_VERSION__: string`, `__APP_BUILD__: string`
- `app-sidebar.tsx` → внутри `SidebarFooter`, после `SidebarMenu` с Settings, добавить `<Link to="/changelog">` с версией
- `admin-portal/src/pages/changelog/index.tsx` — новая страница, fetch `/api/changelog`, Card для каждой версии
- `App.tsx` → маршрут `/changelog`

**Этап 4 — Deploy:**
- `deploy.sh` → `--exclude='.build_number'` в rsync, инкремент `.build_number` на сервере через SSH перед build, read VERSION, передать `BUILD_NUMBER` через `--build-arg` и `docker compose` env
- `docker-compose.yml` → `BUILD_NUMBER` env var для Python-контейнеров (runtime), build-arg для frontend
- `Dockerfile.frontend` → `ARG BUILD_NUMBER=0`, `ENV VITE_APP_BUILD=${BUILD_NUMBER}` перед `npm run build`

**Важные нюансы:**
1. `Dockerfile.python` не копирует `VERSION` — нужно добавить `COPY VERSION .`, иначе `__version__.py` не найдёт файл в контейнере
2. `CHANGELOG.md` тоже нужно копировать в Python-образ для changelog endpoint — `COPY CHANGELOG.md .`
3. Sidebar footer: `SidebarFooter` уже используется для Settings. Версию разместить как `<p>` текст ниже Settings кнопки, с `group-data-[collapsible=icon]:hidden` для скрытия в collapsed mode
4. Frontend `__APP_VERSION__` — Vite `define` подставляет на этапе build. В dev — читает из `VERSION` файла через fs. В Docker — из скопированного `VERSION`

### Оценка совместимости

**Вписывается в текущую архитектуру.** Изменения затрагивают только:
- Замена hardcoded строк на динамические значения
- Добавление одного нового API-эндпоинта (changelog)
- Добавление одной новой страницы фронтенда
- Изменение deploy-скрипта (инкремент build number)

Архитектурных изменений нет. Новых зависимостей в production нет (commitizen — dev only).

**Потенциальные проблемы:**
- `CHANGELOG.md` парсинг regex — Commitizen генерирует стабильный формат, но при ручной правке может сломаться. Рекомендация: defensive парсинг с fallback на пустой массив
- Первый запуск `cz bump` до создания тега `v2.1.0` — сначала нужно вручную `git tag v2.1.0`

### Вероятные обновления документации

- **ARCHITECTURE.md** (обзор) — да: добавить файл `VERSION` в структуру проекта, `src/__version__.py`, `CHANGELOG.md`
- **architecture/12-deployment.md** — обновить: добавить `.build_number`, BUILD_NUMBER env, описание deploy flow с версией
- **architecture/11-admin-portal.md** — обновить: новая страница `/changelog`, version footer в sidebar, новый роутер
- **ADR** — нет: подход стандартный, не требует обоснования
- **CLAUDE.md** — да: добавить commit scopes (`bot`, `admin`) в секцию «Инструкции для Claude → Git commits»

> Окончательный список определит `/finalize` после реализации

### Готов к реализации

**Да.** План детальный, все затрагиваемые файлы идентифицированы, конфликтов с архитектурой нет. Можно приступать к Этапу 1.
