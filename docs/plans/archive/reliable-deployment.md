# План: Надёжный деплой bz2-video-transcriber

## Контекст

Деплой регулярно ломается из-за трёх проблем:
1. **`--no-cache`** — каждый деплой пересобирает образы с нуля, заново скачивая `python:3.12-slim`, `node:20-alpine` из Docker Hub
2. **Docker Hub недоступен** — TLS handshake timeout при pull базовых образов (сервер за прокси, нестабильная сеть)
3. **Нет обработки ошибок** — если build упал, непонятно что произошло

Цель: деплой одной командой, который не падает из-за временных сетевых проблем и использует Docker layer cache.

## Решение

### 1. Переписать `scripts/deploy.sh`

**Ключевые изменения:**

- **Убрать `--no-cache`** — Docker layer cache работает корректно с текущими Dockerfile (requirements.txt/package.json копируются первыми)
- **Pre-pull базовых образов с retry** — перед build проверяем наличие базовых образов; если нет — тянем с 3 попытками (10s пауза)
- **Флаг `--pull`** — опциональное обновление базовых образов (`./scripts/deploy.sh --pull`)
- **Health check после деплоя** — проверка `https://transcriber.home/health` (5 попыток, 5s пауза)
- **Вывод build-лога при ошибке** — если build упал, показываем последние 30 строк
- **Helper-функции** для SSH команд — `remote()` и `remote_sudo()` чтобы убрать дублирование

**Структура нового скрипта:**

```
1. Загрузка credentials из .env.local
2. Валидация переменных
3. Парсинг аргументов (--pull)
4. rsync исходников (без изменений)
5. Создание .env на сервере (без изменений)
6. [если --pull] Pull базовых образов с retry
7. [если нет образов] Автоматический pull отсутствующих образов
8. docker compose build (БЕЗ --no-cache)
9. docker compose up -d
10. Health check verification
11. Итоговый статус
```

### 2. Создать `frontend/.dockerignore`

Frontend не имеет `.dockerignore` → `COPY . .` копирует лишние файлы (README, .eslintrc и т.п.), увеличивая build context. Создать по аналогии с `backend/.dockerignore`.

### 3. ADR-021: Reliable Deployment

Зафиксировать решение: почему убрали `--no-cache`, стратегия работы с базовыми образами.

### 4. Обновить документацию

- `.claude/rules/infrastructure.md` — секция "Деплой" (добавить `--pull`, правило "НИКОГДА --no-cache")
- `docs/deployment.md` — секция "Автоматический деплой" (обновить пример скрипта, добавить troubleshooting)

## Затрагиваемые файлы

| Файл | Действие | Описание |
|------|----------|----------|
| `scripts/deploy.sh` | **переписать** | Основные изменения: убрать --no-cache, добавить pre-pull, retry, health check |
| `frontend/.dockerignore` | **создать** | Исключить node_modules, dist, .git, *.md, docs |
| `docs/decisions/021-reliable-deployment.md` | **создать** | ADR с обоснованием решений |
| `docs/decisions/README.md` | **обновить** | Добавить ADR-021 в индекс |
| `.claude/rules/infrastructure.md` | **обновить** | Секция "Деплой" — новые правила |
| `docs/deployment.md` | **обновить** | Секция "Автоматический деплой" + troubleshooting |

## Не затрагиваем

- `backend/Dockerfile` — структура слоёв уже оптимальна
- `frontend/Dockerfile` — структура корректна, `.dockerignore` решит проблему context
- `docker-compose.yml` — без изменений

## Верификация

1. **Синтаксис скрипта:** `bash -n scripts/deploy.sh`
2. **Реальный деплой:** `/bin/bash scripts/deploy.sh` — должен использовать кэш, не тянуть образы
3. **Деплой с pull:** `/bin/bash scripts/deploy.sh --pull` — обновить базовые образы
4. **Health check:** скрипт должен сам проверить `https://transcriber.home/health` и показать результат
5. **Тест ошибки build:** если build упадёт, скрипт покажет хвост лога и чёткое сообщение
