# Унификация структуры архивных папок — План реализации

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Перейти с 4-уровневой структуры архива на унифицированную 3-уровневую, добавить `#История` маркер для leadership.

**Architecture:** Изменение затрагивает парсер (формирование archive_path), API endpoint (сканирование), фронтенд (параметры запросов), миграционный скрипт. EventCategory сохраняется. `#` в title потребляется парсером и не протекает дальше.

**Tech Stack:** Python/FastAPI (backend), React/TypeScript (frontend), bash (миграция)

**Spec:** `docs/superpowers/specs/2026-03-18-archive-folder-structure-design.md`

---

## Task 1: Parser — leadership detection и archive_path

**Files:**
- Modify: `backend/app/services/parser.py:261-299`

- [ ] **Step 1: Обновить leadership detection**

В `_parse_event()` (строка 261-265) заменить:
```python
# Было:
if title == "История":
    content_type = ContentType.LEADERSHIP
else:
    content_type = ContentType.EDUCATIONAL

# Стало:
if title.startswith("#История"):
    content_type = ContentType.LEADERSHIP
    title = title[1:]  # Strip '#' — marker consumed by parser
else:
    content_type = ContentType.EDUCATIONAL
```

- [ ] **Step 2: Обновить формирование archive_path**

В `_parse_event()` (строки 273-299) заменить всю секцию:
```python
# Было (4 уровня):
if event_category == EventCategory.REGULAR:
    date_folder = f"{video_date.month:02d}.{video_date.day:02d}"
    topic_folder = f"{stream} {title} ({speaker})" if stream else f"{title} ({speaker})"
    archive_path = (
        settings.archive_dir / str(video_date.year)
        / event_type / date_folder / topic_folder
    )
else:
    topic_folder = f"{stream} {title} ({speaker})" if stream else f"{title} ({speaker})"
    archive_path = (
        settings.archive_dir / str(video_date.year)
        / "Выездные" / event_type / topic_folder
    )

# Стало (3 уровня):
if event_category == EventCategory.REGULAR:
    event_group = event_type
    date_prefix = f"{video_date.month:02d}.{video_date.day:02d}"
    if stream:
        topic_folder = f"{date_prefix} {stream}. {title} ({speaker})"
    else:
        topic_folder = f"{date_prefix} {title} ({speaker})"
else:
    event_group = f"{video_date.month:02d} {event_type}"
    topic_folder = f"{title} ({speaker})"

archive_path = (
    settings.archive_dir / str(video_date.year)
    / event_group / topic_folder
)
```

- [ ] **Step 3: Обновить inline-тесты в parser.py**

Обновить тесты `test_archive_path_regular` (test 13), `test_archive_path_no_stream` (test 14), `test_offsite_educational` (test 5), `test_offsite_leadership` (test 6), `test_date_without_day_offsite` (test 18).

Добавить новые тесты:
```python
def test_leadership_hash_marker():
    """Test: #История marker is consumed by parser."""
    filename = "2026.03.16 ПШ.НП. #История AWT (Прохорова Светлана).mp4"
    metadata = parse_filename(filename)
    assert metadata.content_type == ContentType.LEADERSHIP
    assert metadata.title == "История AWT"  # # stripped
    assert "#" not in str(metadata.archive_path)

def test_educational_with_история_in_title():
    """Test: История without # is EDUCATIONAL."""
    filename = "2026.02 ФСТ. История Herbalife и истоки (Руцман Ида).md"
    metadata = parse_filename(filename)
    assert metadata.content_type == ContentType.EDUCATIONAL
    assert metadata.title == "История Herbalife и истоки"

def test_archive_path_regular_with_stream_separator():
    """Test: Regular archive path uses '. ' separator between stream and title."""
    filename = "2025.08.04 ПШ.НП. Контент (Пепелина Инга).mp4"
    metadata = parse_filename(filename)
    path_str = str(metadata.archive_path)
    assert "/ПШ/" in path_str
    assert "08.04 НП. Контент (Пепелина Инга)" in path_str
```

- [ ] **Step 4: Запустить inline-тесты парсера**

Run: `cd backend && python3 -m app.services.parser`
Expected: All tests passed!

- [ ] **Step 5: Коммит**

```bash
git add backend/app/services/parser.py
git commit -m "feat: 3-уровневая структура архива и #История маркер в парсере"
```

---

## Task 2: Backend API — сканирование архива (3 уровня)

**Files:**
- Modify: `backend/app/api/routes.py:56-170`

- [ ] **Step 1: Обновить `list_archive()` — 3-уровневое сканирование**

Заменить строки 56-126:
```python
@router.get("/archive")
async def list_archive() -> ArchiveResponse:
    """
    List archive folder structure.

    Archive structure (3 levels):
    - Regular: archive/{year}/{event_type}/{date_prefix topic (speaker)}/
    - Offsite: archive/{year}/{MM event_type}/{topic (speaker)}/

    Returns:
        ArchiveResponse with tree structure: year -> event_folder -> items
    """
    settings = get_settings()
    archive_dir = settings.archive_dir

    if not archive_dir.exists():
        return ArchiveResponse(tree={}, total=0)

    tree: dict[str, dict[str, list[ArchiveItem]]] = {}
    total = 0

    # Scan 3 levels: archive/{year}/{event_group}/{topic_folder}/
    for year_dir in sorted(archive_dir.iterdir(), reverse=True):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue

        year = year_dir.name
        tree[year] = {}

        for event_group_dir in sorted(year_dir.iterdir(), reverse=True):
            if not event_group_dir.is_dir():
                continue

            event_group = event_group_dir.name  # "ПШ" or "02 ФСТ"

            tree[year][event_group] = []

            for topic_dir in sorted(event_group_dir.iterdir()):
                if not topic_dir.is_dir():
                    continue

                # Parse topic folder: "title (speaker)" or "08.04 SV. title (speaker)"
                folder_name = topic_dir.name
                speaker = ""
                title = folder_name

                # Extract speaker from parentheses at the end
                if "(" in folder_name and folder_name.endswith(")"):
                    idx = folder_name.rfind("(")
                    speaker = folder_name[idx + 1 : -1]
                    title = folder_name[:idx].strip()

                tree[year][event_group].append(
                    ArchiveItem(
                        title=title,
                        speaker=speaker,
                        event_type=event_group,
                        topic_folder=folder_name,
                    )
                )
                total += 1

    return ArchiveResponse(tree=tree, total=total)
```

- [ ] **Step 2: Обновить `get_archive_results()` — 3 параметра вместо 4**

Заменить строки 129-170:
```python
@router.get("/archive/results")
async def get_archive_results(
    year: str,
    event_group: str,
    topic_folder: str,
) -> PipelineResultsResponse:
    """
    Get pipeline results for archived video.

    Args:
        year: Year folder (e.g., "2026")
        event_group: Event group folder (e.g., "ПШ", "02 ФСТ")
        topic_folder: Topic folder (e.g., "08.04 НП. Контент (Пепелина Инга)")

    Returns:
        PipelineResultsResponse with available flag and data/message
    """
    settings = get_settings()
    archive_path = settings.archive_dir / year / event_group / topic_folder
    results_file = archive_path / "pipeline_results.json"

    if not results_file.exists():
        logger.debug(f"Pipeline results not found: {results_file}")
        return PipelineResultsResponse(
            available=False,
            message="Результаты обработки недоступны для этого файла",
        )

    try:
        with open(results_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to read pipeline results: {results_file}, error: {e}")
        return PipelineResultsResponse(
            available=False,
            message="Ошибка чтения файла результатов",
        )

    return PipelineResultsResponse(
        available=True,
        data=PipelineResults.model_validate(data),
    )
```

- [ ] **Step 3: Обновить модель ArchiveItem в schemas.py**

Заменить `mid_folder` на `topic_folder` (полное имя папки для API-вызовов):
```python
# Было:
class ArchiveItem(CamelCaseModel):
    title: str
    speaker: str | None = None
    event_type: str
    mid_folder: str

# Стало:
class ArchiveItem(CamelCaseModel):
    title: str
    speaker: str | None = None
    event_type: str
    topic_folder: str
```

Обновить docstring `VideoMetadata` — описание archive path.

**Важно:** `topic_folder` нужен потому что для regular-событий имя папки содержит дату и поток (`08.04 SV. Контент (Пепелина Инга)`), и фронтенд не может его восстановить из `title + speaker`.

- [ ] **Step 4: Обновить комментарий в cache_routes.py**

В `backend/app/api/cache_routes.py` строка ~69 — обновить комментарий с описанием пути на 3-уровневый формат.

- [ ] **Step 5: Коммит**

```bash
git add backend/app/api/routes.py backend/app/models/schemas.py backend/app/api/cache_routes.py
git commit -m "feat: API архива — 3-уровневое сканирование, убрана mid_folder"
```

---

## Task 3: Frontend — адаптация к 3-уровневому API

**Files:**
- Modify: `frontend/src/api/types.ts:358-376`
- Modify: `frontend/src/api/hooks/useArchive.ts:20-44`
- Modify: `frontend/src/App.tsx:27-66`
- Modify: `frontend/src/components/archive/ArchiveResultsModal.tsx:109-114`
- Modify: `frontend/src/components/archive/ArchiveCatalog.tsx`

- [ ] **Step 1: Обновить типы в types.ts**

```typescript
// Заменить midFolder на topicFolder (полное имя папки с диска)
export interface ArchiveItem {
  title: string;
  speaker: string | null;
  eventType: string;
  topicFolder: string;
}

// Обновить ArchiveItemWithPath — убрать midFolder, переименовать eventFolder→eventGroup
export interface ArchiveItemWithPath extends ArchiveItem {
  year: string;
  eventGroup: string;
}
```

Примечание: `topicFolder` перемещён в `ArchiveItem` (приходит из API), поэтому `ArchiveItemWithPath` больше не нуждается в нём отдельно.

- [ ] **Step 2: Обновить useArchive.ts**

```typescript
export function useArchiveResults(
  year: string | null,
  eventGroup: string | null,
  topicFolder: string | null
) {
  return useQuery({
    queryKey: ['archive-results', year, eventGroup, topicFolder],
    queryFn: async () => {
      const { data } = await apiClient.get<PipelineResultsResponse>(
        '/api/archive/results',
        {
          params: {
            year,
            event_group: eventGroup,
            topic_folder: topicFolder,
          },
        }
      );
      return data;
    },
    enabled: !!(year && eventGroup && topicFolder),
  });
}
```

- [ ] **Step 3: Обновить metadataToArchiveItem в App.tsx**

```typescript
function metadataToArchiveItem(metadata: VideoMetadata): ArchiveItemWithPath {
  const year = metadata.date.split('-')[0];
  const isOffsite = metadata.eventCategory === 'offsite';

  let eventGroup: string;
  let topicFolder: string;

  if (isOffsite) {
    const month = metadata.date.split('-')[1];
    eventGroup = `${month} ${metadata.eventType}`;
    topicFolder = metadata.speaker
      ? `${metadata.title} (${metadata.speaker})`
      : metadata.title;
  } else {
    eventGroup = metadata.eventType;
    const [, month, day] = metadata.date.split('-');
    const datePrefix = `${month}.${day}`;
    if (metadata.stream) {
      topicFolder = `${datePrefix} ${metadata.stream}. ${metadata.title} (${metadata.speaker})`;
    } else {
      topicFolder = `${datePrefix} ${metadata.title} (${metadata.speaker})`;
    }
  }

  return {
    title: metadata.title,
    speaker: metadata.speaker,
    eventType: eventGroup,
    year,
    eventGroup,
    topicFolder,
  };
}
```

- [ ] **Step 4: Обновить ArchiveResultsModal.tsx**

В `frontend/src/components/archive/ArchiveResultsModal.tsx` строки 109-114 — обновить вызов `useArchiveResults`:
```typescript
// Было (4 параметра):
const { data, isLoading, isError } = useArchiveResults(
    item?.year ?? null,
    item?.eventType ?? null,
    item?.midFolder ?? null,
    item?.topicFolder ?? null
);

// Стало (3 параметра):
const { data, isLoading, isError } = useArchiveResults(
    item?.year ?? null,
    item?.eventGroup ?? null,
    item?.topicFolder ?? null
);
```

- [ ] **Step 5: Обновить ArchiveCatalog.tsx**

В `ArchiveCatalog.tsx` — обновить `handleItemClick` для формирования `ArchiveItemWithPath`:
```typescript
// topicFolder теперь приходит из API в item.topicFolder (не нужно реконструировать)
const archiveItem: ArchiveItemWithPath = {
    ...item,
    year,
    eventGroup,
};
```

Заменить все ссылки `midFolder` → убрать, `eventFolder` → `eventGroup`.

- [ ] **Step 6: Проверить сборку фронтенда**

Run: `cd frontend && npm run build`
Expected: Build succeeds without errors

- [ ] **Step 7: Коммит**

```bash
git add frontend/src/
git commit -m "feat: фронтенд — 3-уровневая структура архива"
```

---

## Task 4: Миграционный скрипт

**Files:**
- Create: `scripts/migrate_archive_v2.py`

- [ ] **Step 1: Написать скрипт миграции**

Скрипт должен:
1. Подключиться к серверу через sshpass (credentials из `.env.local`)
2. Найти все 4-уровневые папки в archive/
3. Для каждой — построить новый 3-уровневый путь
4. Сохранить JSON-маппинг old→new для rollback
5. Выполнить переименование (mv)
6. Обновить `metadata.archivePath` в каждом `pipeline_results.json`
7. Удалить пустые папки (MM.DD, Выездные)

Логика маппинга:
```python
# Regular: archive/2025/ПШ/08.04/SV Контент (Пепелина Инга)/
#       → archive/2025/ПШ/08.04 SV. Контент (Пепелина Инга)/
# Offsite: archive/2026/Выездные/ФСТ/Тема (Спикер)/
#        → archive/2026/02 ФСТ/Тема (Спикер)/   (месяц из даты в pipeline_results.json)
```

**Fallback для offsite:** если `pipeline_results.json` отсутствует или повреждён — пропустить папку и вывести warning в лог. Месяц для offsite берётся из `metadata.date` в JSON.

- [ ] **Step 2: Запустить скрипт в dry-run режиме**

Run: `python3 scripts/migrate_archive_v2.py --dry-run`
Expected: Список планируемых перемещений без фактических изменений

- [ ] **Step 3: Коммит**

```bash
git add scripts/migrate_archive_v2.py
git commit -m "feat: миграционный скрипт архива v1→v2 (4 уровня → 3)"
```

---

## Task 5: Документация

**Files:**
- Modify: `docs/data-formats.md`
- Modify: `docs/pipeline/01-parse.md`
- Modify: `docs/pipeline/07-save.md`
- Modify: `docs/pipeline/09-api.md`
- Modify: `.claude/rules/content.md`
- Modify: `config/events.yaml` (комментарии)
- Modify: `CLAUDE.md` (если упоминается структура)

- [ ] **Step 1: Обновить docs/data-formats.md**

Заменить описание 4-уровневой структуры на 3-уровневую. Обновить примеры путей.

- [ ] **Step 2: Обновить docs/pipeline/01-parse.md**

Обновить описание формирования archive_path и `#История` маркера.

- [ ] **Step 3: Обновить docs/pipeline/07-save.md и 09-api.md**

Обновить описание save stage и `/api/archive` endpoint.

- [ ] **Step 4: Обновить .claude/rules/content.md и config/events.yaml**

Убрать упоминания «Выездные» из правил и комментариев.

- [ ] **Step 5: Коммит**

```bash
git add docs/ .claude/rules/content.md config/events.yaml
git commit -m "docs: обновлена документация под 3-уровневую структуру архива"
```

---

## Task 6: Деплой и миграция на сервере

- [ ] **Step 1: Деплой нового кода**

Run: `/bin/bash scripts/deploy.sh`

- [ ] **Step 2: Запустить миграцию на сервере**

Запустить `migrate_archive_v2.py` на сервере для переименования 18 существующих папок.

- [ ] **Step 3: Проверить дерево архива в UI**

Открыть https://transcriber.home и проверить, что дерево отображает 3-уровневую структуру корректно.
