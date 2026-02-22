# План: создание требования на систему версионирования

## Контекст

Проект bz2-video-transcribe версионируется вручную: версия в `frontend/package.json` (0.79.0), отображается в Header через Vite define. Backend hardcoded `0.1.0`, CHANGELOG отсутствует, git tags не используются, build number нет. Пользователь реализовал хорошую систему в другом проекте (BZ2-Bot) — `docs/reference/versioning.md` — и хочет адаптировать подход для этого проекта.

**Задача:** Создать документ `docs/requirements/versioning.md` и обновить индекс `docs/requirements/README.md`.

## Что создаётся

Документ требований по шаблону `REQUIREMENT-TEMPLATE.md` (10 разделов), адаптированный под особенности bz2-video-transcribe:

### Ключевые отличия от BZ2-Bot

| Аспект | BZ2-Bot | bz2-video-transcribe |
|--------|---------|---------------------|
| Scopes | `bot`, `admin` | Без scopes (монолит) |
| Стартовая версия | 2.1.0 | 0.80.0 (продолжение от 0.79.0) |
| Структура | `src/`, `admin-portal/` | `backend/app/`, `frontend/` |
| Версия в UI | Sidebar footer | Header (уже есть — делаем кликабельным) |
| CHANGELOG группировка | По модулям (Бот/Админ) | По типам (feat/fix) с бейджами |
| Маршрутизация | React Router | State в App.tsx (нет react-router) |
| VERSION Python | `src/__version__.py` | `backend/app/version.py` |
| Dockerfile | `COPY VERSION .` в Dockerfile.python | `COPY VERSION .` в `backend/Dockerfile` до `COPY app/` |

### Содержимое документа

Документ включает:

1. **Проблема** — ручное версионирование, нет CHANGELOG, backend `0.1.0` не синхронизирован
2. **Решение** — VERSION файл + Commitizen + build number + CHANGELOG API + UI страница
3. **Сценарии** — A: cz bump, B: просмотр CHANGELOG, C: диагностика сервера, D: /finalize
4. **UI** — версия в Header как ссылка → страница /changelog с карточками, бейджи "Новое"/"Исправление"
5. **API** — `GET /api/changelog` (парсинг CHANGELOG.md → JSON), обновлённый `GET /health`
6. **Данные** — новые файлы (VERSION, .cz.toml, version.py, ChangelogPage), изменения существующих
7. **Ограничения** — без scopes, русский CHANGELOG, VERSION read-only, начало с v0.80.0
8. **План** — 2 этапа: инфраструктура (v0.80), UI changelog (v0.81)
9. **Тестирование** — таблица проверочных сценариев
10. **Референсы** — BZ2-Bot, Commitizen docs

### Ключевые технические решения

- **VERSION файл** (корень проекта) → `frontend/vite.config.ts` читает через `fs.readFileSync`, `backend/app/version.py` через `pathlib.Path`
- **`backend/Dockerfile`**: добавить `COPY VERSION .` перед `COPY app/`
- **`frontend/Dockerfile`**: VERSION уже попадает через `COPY . .` при build
- **`docker-compose.yml`**: `BUILD_NUMBER=${BUILD_NUMBER:-0}` как environment для backend, build arg для frontend
- **`deploy.sh`**: чтение VERSION, инкремент `.build_number` на сервере через SSH, передача BUILD_NUMBER, exclude `.build_number` из rsync
- **Навигация**: state в App.tsx (`page: 'dashboard' | 'changelog'`), без react-router
- **CHANGELOG парсинг**: regex по формату Commitizen, endpoint в `backend/app/api/changelog_routes.py`
- **Порядок в CHANGELOG**: Commitizen по умолчанию prepend'ит новые версии вверху файла — парсер читает сверху вниз, порядок для UI (последняя версия первая) совпадает автоматически. Ручное ведение не нужно.

## Файлы для создания/изменения

| Файл | Действие |
|------|----------|
| `docs/requirements/versioning.md` | **Создать** — полный документ требований |
| `docs/requirements/README.md` | **Обновить** — добавить запись в таблицу "Активные" |

## Верификация

- Проверить что документ следует шаблону `REQUIREMENT-TEMPLATE.md`
- Проверить что все ссылки на файлы соответствуют реальной структуре проекта
- Проверить что README.md корректно обновлён
