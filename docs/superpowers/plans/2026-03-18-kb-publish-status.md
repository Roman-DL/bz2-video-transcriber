# KB Publish Status Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Показать в архиве транскрайбера, какие материалы загружены в базу знаний, через файл-маркер `.published`.

**Architecture:** Файл `.published` в папке материала = маркер публикации. Backend проверяет наличие при сканировании, отдаёт поле `published` во фронтенд. Два новых эндпоинта (PUT/DELETE) управляют маркером. Фронтенд показывает бейдж и переключатель.

**Tech Stack:** Python/FastAPI (backend), React/TypeScript/TanStack Query (frontend), Pydantic v2 (модели)

**Spec:** `docs/superpowers/specs/2026-03-18-kb-publish-status-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/models/schemas.py` | Modify | Добавить `published` в `ArchiveItem`, `published_total` в `ArchiveResponse` |
| `backend/app/api/routes.py` | Modify | Проверка `.published` в GET /api/archive, новые PUT/DELETE эндпоинты |
| `frontend/src/api/types.ts` | Modify | Поля `published`, `publishedTotal` в типах |
| `frontend/src/api/hooks/useArchive.ts` | Modify | Мутации для PUT/DELETE published |
| `frontend/src/components/archive/ArchiveCatalog.tsx` | Modify | Бейдж "В БЗ", счётчик в заголовке |
| `frontend/src/components/archive/ArchiveResultsModal.tsx` | Modify | Переключатель статуса БЗ |
| `docs/data-formats.md` | Modify | Документация `.published` |
| `scripts/mark_published.sh` | Create | Скрипт начальной разметки ПШ |

---

### Task 1: Backend модели

**Files:**
- Modify: `backend/app/models/schemas.py:1350-1366`

- [ ] **Step 1: Добавить `published` в `ArchiveItem`**

```python
class ArchiveItem(CamelCaseModel):
    """Single item in archive tree."""

    title: str = Field(..., description="Topic title")
    speaker: str = Field(..., description="Speaker name")
    event_type: str = Field(..., description="Event group code")
    topic_folder: str = Field(..., description="Full topic folder name from disk")
    published: bool = Field(default=False, description="Loaded into knowledge base")
```

- [ ] **Step 2: Добавить `published_total` в `ArchiveResponse`**

```python
class ArchiveResponse(CamelCaseModel):
    """Response for GET /api/archive."""

    tree: dict[str, dict[str, list[ArchiveItem]]] = Field(
        default_factory=dict,
        description="Year -> event_folder -> items",
    )
    total: int = Field(default=0, ge=0, description="Total number of items")
    published_total: int = Field(default=0, ge=0, description="Number of items published to KB")
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/schemas.py
git commit -m "feat: поля published в ArchiveItem и ArchiveResponse"
```

---

### Task 2: Backend — проверка `.published` в GET /api/archive

**Files:**
- Modify: `backend/app/api/routes.py:56-118`

- [ ] **Step 1: Добавить проверку `.published` при сканировании**

В цикле сканирования `topic_dir` внутри `GET /api/archive`, после создания `topic_path`, добавить:

```python
published = (topic_path / ".published").exists()
```

Передать в конструктор `ArchiveItem(..., published=published)`.

- [ ] **Step 2: Считать `published_total`**

Завести счётчик `published_total = 0` рядом с `total = 0`. Инкрементировать при `published == True`:

```python
if published:
    published_total += 1
```

Передать в `ArchiveResponse(tree=tree, total=total, published_total=published_total)`.

**Важно:** также обновить early return для пустого архива (если есть), добавив `published_total=0`.

- [ ] **Step 3: Проверить через curl**

```bash
curl -s http://localhost:8000/api/archive | python3 -m json.tool | head -30
```

Ожидание: каждый item имеет поле `"published": false` (пока маркеров нет), response имеет `"publishedTotal": 0`.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/routes.py
git commit -m "feat: проверка .published при сканировании архива"
```

---

### Task 3: Backend — PUT/DELETE эндпоинты

**Files:**
- Modify: `backend/app/api/routes.py`

- [ ] **Step 1: Добавить импорт `HTTPException` и вспомогательную функцию**

Добавить `HTTPException` в импорт FastAPI (строка 12):

```python
from fastapi import APIRouter, HTTPException
```

Добавить `Path` из pathlib если отсутствует. Затем добавить функцию валидации перед эндпоинтами:

```python
def _resolve_archive_path(
    archive_dir: Path, year: str, event_group: str, topic_folder: str
) -> Path:
    """Resolve and validate archive path, preventing path traversal."""
    target = (archive_dir / year / event_group / topic_folder).resolve()
    archive_resolved = archive_dir.resolve()
    if not str(target).startswith(str(archive_resolved)):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not target.is_dir():
        raise HTTPException(status_code=404, detail="Folder not found")
    return target
```

- [ ] **Step 2: Добавить PUT /api/archive/published**

```python
@router.put("/archive/published")
async def set_published(year: str, event_group: str, topic_folder: str):
    """Mark archive material as published to knowledge base."""
    settings = get_settings()
    target = _resolve_archive_path(
        Path(settings.archive_dir), year, event_group, topic_folder
    )
    (target / ".published").touch()
    return {"status": "ok"}
```

- [ ] **Step 3: Добавить DELETE /api/archive/published**

```python
@router.delete("/archive/published")
async def unset_published(year: str, event_group: str, topic_folder: str):
    """Remove published marker from archive material."""
    settings = get_settings()
    target = _resolve_archive_path(
        Path(settings.archive_dir), year, event_group, topic_folder
    )
    marker = target / ".published"
    if marker.exists():
        marker.unlink()
    return {"status": "ok"}
```

- [ ] **Step 4: Проверить через curl**

```bash
# Установить маркер
curl -X PUT "http://localhost:8000/api/archive/published?year=2025&event_group=ПШ&topic_folder=03.10%20НП.%20Закрытие%20сделки%20на%20ЭО%20и%20ПО%20(Товстая%20Наталья)"

# Проверить что .published создан
ls -la "/path/to/archive/2025/ПШ/03.10 НП. Закрытие сделки на ЭО и ПО (Товстая Наталья)/.published"

# Снять маркер
curl -X DELETE "http://localhost:8000/api/archive/published?year=2025&event_group=ПШ&topic_folder=03.10%20НП.%20Закрытие%20сделки%20на%20ЭО%20и%20ПО%20(Товстая%20Наталья)"

# Проверить path traversal
curl -X PUT "http://localhost:8000/api/archive/published?year=..&event_group=..&topic_folder=etc"
# Ожидание: 400 Bad Request
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes.py
git commit -m "feat: PUT/DELETE /api/archive/published эндпоинты"
```

---

### Task 4: Frontend типы и хуки

**Files:**
- Modify: `frontend/src/api/types.ts:358-369`
- Modify: `frontend/src/api/hooks/useArchive.ts`

- [ ] **Step 1: Обновить TypeScript типы**

В `types.ts` добавить `published` в `ArchiveItem`:

```typescript
export interface ArchiveItem {
  title: string;
  speaker: string | null;
  eventType: string;
  topicFolder: string;
  published: boolean;
}
```

Добавить `publishedTotal` в `ArchiveResponse`:

```typescript
export interface ArchiveResponse {
  tree: Record<string, Record<string, ArchiveItem[]>>;
  total: number;
  publishedTotal: number;
}
```

- [ ] **Step 2: Добавить мутации в useArchive.ts**

Добавить хуки для PUT и DELETE. Использовать `apiClient` (axios), как в существующих хуках:

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';

interface PublishedParams {
  year: string;
  eventGroup: string;
  topicFolder: string;
}

export function useSetPublished() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: PublishedParams) => {
      const { data } = await apiClient.put('/api/archive/published', null, {
        params: {
          year: params.year,
          event_group: params.eventGroup,
          topic_folder: params.topicFolder,
        },
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['archive'] });
    },
  });
}

export function useUnsetPublished() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: PublishedParams) => {
      const { data } = await apiClient.delete('/api/archive/published', {
        params: {
          year: params.year,
          event_group: params.eventGroup,
          topic_folder: params.topicFolder,
        },
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['archive'] });
    },
  });
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/api/hooks/useArchive.ts
git commit -m "feat: типы и хуки для published статуса"
```

---

### Task 5: Frontend — бейдж и счётчик в ArchiveCatalog

**Files:**
- Modify: `frontend/src/components/archive/ArchiveCatalog.tsx`

- [ ] **Step 1: Добавить счётчик в заголовок**

В `ArchiveCatalog.tsx:68-72`, заменить содержимое `<span>` с количеством видео. Использовать `data.publishedTotal` (из оригинального ответа, не из `filteredData`):

```tsx
{data && (
  <span className="text-xs font-medium text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
    {filteredData?.total ?? data.total} видео{data.publishedTotal > 0 && ` · ${data.publishedTotal} в БЗ`}
  </span>
)}
```

- [ ] **Step 2: Добавить бейдж "В БЗ" к элементам**

В `EventSection` (`ArchiveCatalog.tsx:211-232`), внутри `<button>` каждого item, после блока speaker добавить бейдж. Ориентир — строка 228 (закрывающий `</span>` speaker):

```tsx
<span className="text-gray-600 hover:text-blue-600 truncate transition-colors">
  {item.title}
</span>
{item.speaker && (
  <span className="text-xs text-gray-400 ml-1 flex-shrink-0">
    ({item.speaker})
  </span>
)}
{item.published && (
  <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700 flex-shrink-0">
    В БЗ
  </span>
)}
```

- [ ] **Step 3: Визуальная проверка**

Открыть UI, убедиться что:
- Счётчик "· X в БЗ" появляется в заголовке (будет 0 пока нет маркеров)
- После ручного `touch .published` в папке материала — бейдж появляется (дождаться 30s refetch или обновить)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/archive/ArchiveCatalog.tsx
git commit -m "feat: бейдж В БЗ и счётчик в архиве"
```

---

### Task 6: Frontend — переключатель статуса в ArchiveResultsModal

**Files:**
- Modify: `frontend/src/components/archive/ArchiveResultsModal.tsx`

- [ ] **Step 1: Добавить переключатель статуса**

Импортировать хуки (использовать `@/` alias как в остальных импортах файла):

```typescript
import { useArchiveResults, useSetPublished, useUnsetPublished } from '@/api/hooks/useArchive';
```

В компоненте `ArchiveResultsModal` (строка ~105) добавить мутации:

```typescript
const setPublished = useSetPublished();
const unsetPublished = useUnsetPublished();
```

Кнопку-переключатель разместить между `<Modal>` и контентом (после строки 143 `<Modal isOpen={isOpen} onClose={onClose} title={title} size="2xl">`), перед блоком `{isLoading && ...}`. Примечание: `ArchiveItemWithPath` наследует `published` от `ArchiveItem`, поэтому `item.published` доступен:

```tsx
{item && (
  item.published ? (
    <button
      onClick={() =>
        unsetPublished.mutate({
          year: item.year,
          eventGroup: item.eventGroup,
          topicFolder: item.topicFolder,
        })
      }
      disabled={unsetPublished.isPending}
      className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-700 hover:bg-red-100 hover:text-red-700 transition-colors"
      title="Снять метку загрузки в БЗ"
    >
      {unsetPublished.isPending ? "..." : "✓ В БЗ"}
    </button>
  ) : (
    <button
      onClick={() =>
        setPublished.mutate({
          year: item.year,
          eventGroup: item.eventGroup,
          topicFolder: item.topicFolder,
        })
      }
      disabled={setPublished.isPending}
      className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-500 hover:bg-green-100 hover:text-green-700 transition-colors"
      title="Отметить как загружен в БЗ"
    >
      {setPublished.isPending ? "..." : "Отметить в БЗ"}
    </button>
  )
)}
```

- [ ] **Step 2: Визуальная проверка**

Открыть модалку материала:
- Для неопубликованного — видна серая кнопка "Отметить в БЗ"
- Нажать → кнопка становится зелёной "✓ В БЗ", бейдж появляется в дереве
- Нажать снова → метка снимается

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/archive/ArchiveResultsModal.tsx
git commit -m "feat: переключатель статуса БЗ в модалке"
```

---

### Task 7: Скрипт миграции и документация

**Files:**
- Create: `scripts/mark_published.sh`
- Modify: `docs/data-formats.md`

- [ ] **Step 1: Создать скрипт миграции**

```bash
#!/bin/bash
# Создать .published во всех папках материалов типа ПШ (уже загружены в БЗ)
set -euo pipefail

ARCHIVE_DIR="${1:-/mnt/main/work/bz2/video/archive}"

if [ ! -d "$ARCHIVE_DIR" ]; then
    echo "ERROR: Archive directory not found: $ARCHIVE_DIR"
    exit 1
fi

count=0
for year_dir in "$ARCHIVE_DIR"/*/; do
    psh_dir="${year_dir}ПШ"
    if [ -d "$psh_dir" ]; then
        for topic_dir in "$psh_dir"/*/; do
            if [ -d "$topic_dir" ]; then
                touch "${topic_dir}.published"
                echo "  ${topic_dir}"
                count=$((count + 1))
            fi
        done
    fi
done

echo ""
echo "Done: marked $count materials as published"
```

- [ ] **Step 2: Сделать скрипт исполняемым**

```bash
chmod +x scripts/mark_published.sh
```

- [ ] **Step 3: Обновить docs/data-formats.md**

В секции описания структуры архивной папки (после списка файлов) добавить `.published`:

```markdown
└── .published              # Маркер: материал загружен в базу знаний (пустой файл)
```

- [ ] **Step 4: Commit**

```bash
git add scripts/mark_published.sh docs/data-formats.md
git commit -m "feat: скрипт миграции ПШ и документация .published"
```

---

### Task 8: Деплой и запуск миграции

- [ ] **Step 1: Деплой на сервер**

```bash
/bin/bash scripts/deploy.sh
```

- [ ] **Step 2: Запустить скрипт миграции на сервере**

Через sshpass (credentials из `.env.local`):

```bash
source .env.local
sshpass -p "$DEPLOY_PASSWORD" ssh "$DEPLOY_USER@$DEPLOY_HOST" \
  "bash /path/to/scripts/mark_published.sh"
```

- [ ] **Step 3: Проверить результат в UI**

Открыть https://transcriber.home — убедиться что:
- Все материалы ПШ имеют бейдж "В БЗ"
- Счётчик "X в БЗ" корректен
- Переключатель работает в модалке
