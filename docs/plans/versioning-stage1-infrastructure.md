# Этап 1: Инфраструктура версионирования

## Контекст

Проект на v0.79.0, версионирование ручное. Backend содержит `version="0.1.0"` (не синхронизирован), CHANGELOG отсутствует, git tags не используются, build number отсутствует. Невозможно определить какая версия/сборка на сервере.

**Цель:** Единый `VERSION` файл → Commitizen для автоматического SemVer → build number при деплое → version+build в health endpoint и Header.

**Источник:** [docs/requirements/versioning.md](../requirements/versioning.md) — Этап 1

---

## Новые файлы (4)

### 1. `VERSION` (корень проекта)
```
0.79.0
```
Одна строка — source of truth для backend и deploy.

### 2. `CHANGELOG.md` (корень проекта)
```markdown
# Changelog
```
Пустой placeholder — чтобы `COPY CHANGELOG.md .` в Dockerfile не сломался до первого `cz bump`.

### 3. `.cz.toml` (корень проекта)
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

### 4. `backend/app/version.py`
```python
"""Application version from VERSION file + BUILD_NUMBER from environment."""

import os
from pathlib import Path


def get_version() -> str:
    """Read version from VERSION file.

    Searches at different directory depths:
    - Local:  backend/app/version.py → parents[2] → project root
    - Docker: /app/app/version.py   → parents[1] → /app/ (WORKDIR)
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

---

## Изменения существующих файлов (9)

### 5. [backend/app/models/schemas.py](../../backend/app/models/schemas.py) — добавить HealthResponse

После `CacheVersionResponse` (строка 1383) добавить:

```python
class HealthResponse(CamelCaseModel):
    """Health check endpoint response with version info."""

    status: str = Field(default="ok", description="Service status")
    version: str = Field(..., description="Application version from VERSION file")
    build: int = Field(default=0, ge=0, description="Build number from deploy")
```

### 6. [backend/app/main.py](../../backend/app/main.py) — интеграция version + HealthResponse

**Добавить импорты** (после строки 16):
```python
from app.version import __version__, __build__
from app.models.schemas import HealthResponse
```

**Строка 53** — заменить `version="0.1.0"` → `version=__version__`

**Строки 74-82** — заменить `/health` endpoint:
```python
@app.get("/health")
async def health_check() -> HealthResponse:
    """Health check endpoint with version and build info."""
    return HealthResponse(version=__version__, build=__build__)
```

### 7. [backend/Dockerfile](../../backend/Dockerfile) — COPY VERSION и CHANGELOG

Перед `COPY app/ ./app/` (строка 13) вставить:
```dockerfile
# Copy version and changelog
COPY VERSION .
COPY CHANGELOG.md .
```

### 8. [frontend/vite.config.ts](../../frontend/vite.config.ts) — BUILD_NUMBER вместо BUILD_TIME

- **Удалить** функцию `getBuildTime()` (строки 5-20)
- **Заменить** в `define`:
  ```typescript
  __BUILD_TIME__: JSON.stringify(getBuildTime()),
  ```
  →
  ```typescript
  __BUILD_NUMBER__: JSON.stringify(process.env.BUILD_NUMBER || '0'),
  ```

### 9. [frontend/src/vite-env.d.ts](../../frontend/src/vite-env.d.ts)

Заменить `declare const __BUILD_TIME__: string` → `declare const __BUILD_NUMBER__: string`

### 10. [frontend/src/components/layout/Header.tsx:17](../../frontend/src/components/layout/Header.tsx#L17)

Заменить:
```tsx
v{__APP_VERSION__} • {__BUILD_TIME__}
```
→
```tsx
v{__APP_VERSION__} • build {__BUILD_NUMBER__}
```
Остаётся plain text — кликабельная кнопка будет в Этап 2.

### 11. [frontend/Dockerfile](../../frontend/Dockerfile) — ARG BUILD_NUMBER

После `FROM node:20-alpine AS builder` добавить:
```dockerfile
ARG BUILD_NUMBER=0
ENV BUILD_NUMBER=${BUILD_NUMBER}
```

### 12. [docker-compose.yml](../../docker-compose.yml)

**Backend** (после LOG_LEVEL_AI_CLIENT, строка 39):
```yaml
      # Version
      - BUILD_NUMBER=${BUILD_NUMBER:-0}
```

**Frontend** — заменить `build: ./frontend` (строка 47):
```yaml
    build:
      context: ./frontend
      args:
        BUILD_NUMBER: "${BUILD_NUMBER:-0}"
```

### 13. [scripts/deploy.sh](../../scripts/deploy.sh) — версия + build number

**a)** После `PROJECT_DIR` (строка 18) — чтение VERSION:
```bash
VERSION=$(cat "$PROJECT_DIR/VERSION" 2>/dev/null || echo "0.0.0")
```

**b)** Строка 67 — обновить сообщение:
```bash
echo "==> Deploying bz2-video-transcriber v${VERSION}..."
```

**c)** В rsync excludes — добавить:
```bash
    --exclude '.build_number' \
```

**d)** Новый шаг между "Create .env" и "Pull base images":
```bash
# --- Step 2.5: Increment build number ---

echo ""
echo "==> Incrementing build number..."
BUILD_NUM=$(remote "cat ${DEPLOY_PATH}/.build_number 2>/dev/null || echo 0")
BUILD_NUM=$((BUILD_NUM + 1))
remote "echo $BUILD_NUM > ${DEPLOY_PATH}/.build_number"
echo "    Version: v${VERSION} (build ${BUILD_NUM})"
```

**e)** Строка 136 — передать BUILD_NUMBER в build:
```bash
if remote_sudo "cd ${DEPLOY_PATH} && BUILD_NUMBER=$BUILD_NUM docker compose build 2>&1" > "$BUILD_LOG" 2>&1; then
```

**f)** Строка 152 — передать BUILD_NUMBER в up:
```bash
remote_sudo "cd ${DEPLOY_PATH} && BUILD_NUMBER=$BUILD_NUM docker compose up -d"
```

**g)** Финальный вывод (строка 180):
```bash
echo "==> Deploy complete! v${VERSION} (build ${BUILD_NUM})"
```

---

## .gitignore — добавить .build_number

После секции "Project specific" (строка 51, после `*.tmp`):
```
# Build
.build_number
```

---

## Ручные шаги после коммита

1. **Создать git tag** (точка отсчёта, обязательно перед `cz bump`):
   ```bash
   git tag v0.79.0
   ```

2. **Первый `cz bump`** → v0.80.0:
   ```bash
   cz bump
   ```
   Обновит VERSION, package.json, CHANGELOG.md, создаст tag v0.80.0.

---

## Верификация

| Тест | Команда | Ожидание |
|------|---------|----------|
| VERSION файл | `cat VERSION` | `0.79.0` |
| version.py локально | `cd backend && python3 -c "from app.version import __version__; print(__version__)"` | `0.79.0` |
| Синтаксис Python | `python3 -m py_compile backend/app/version.py` | Без ошибок |
| TypeScript | `cd frontend && npx tsc --noEmit` | Без ошибок |
| .gitignore | `grep build_number .gitignore` | `.build_number` |
| Health (после деплоя) | `curl -k https://transcriber.home/health` | `{"status":"ok","version":"0.80.0","build":1}` |
| Header (браузер) | — | `v0.80.0 • build 1` |
| Deploy вывод | — | `Deploying v0.80.0...` → `Deploy complete! v0.80.0 (build 1)` |

---

## Документация (после реализации → /finalize)

- **ARCHITECTURE.md** — нет: версионирование не меняет архитектуру компонентов
- **ADR** — нет: решения описаны в requirements/versioning.md
- **CLAUDE.md** — обновить секцию "Текущий статус" (v0.80)
- **docs/deployment.md** — возможно: добавить инфо о BUILD_NUMBER и VERSION
