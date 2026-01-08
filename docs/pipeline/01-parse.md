# Этап 1: Parse Filename

[Обзор Pipeline](README.md) | [Далее: Transcribe >](02-transcribe.md)

---

## Назначение

Извлечение метаданных из имени файла по установленному паттерну.

## Паттерн имени файла

```
{дата} {тип}.{поток} {тема} ({спикер}).mp4

Пример:
2025.04.07 ПШ.SV Подготовка и проведение Группы поддержки (Светлана Дмитрук).mp4
```

## Regex

```python
FILENAME_PATTERN = r'^(\d{4}\.\d{2}\.\d{2})\s+(\w+)\.(\w+)\s+(.+?)\s+\(([^)]+)\)(?:\.\w+)?$'

# Группы:
# 1: date       (2025.04.07)
# 2: event_type (ПШ)
# 3: stream     (SV)
# 4: title      (Подготовка и проведение Группы поддержки)
# 5: speaker    (Светлана Дмитрук)
```

## Модель данных

```python
@dataclass
class VideoMetadata:
    """Метаданные видео, извлечённые из имени файла."""

    # Из имени файла
    date: date                    # 2025-04-07
    event_type: str               # ПШ
    stream: str                   # SV
    title: str                    # Подготовка и проведение Группы поддержки
    speaker: str                  # Светлана Дмитрук

    # Вычисляемые
    original_filename: str        # Полное имя файла
    video_id: str                 # 2025-04-07_psh-sv_gruppa-podderzhki

    # Пути
    source_path: Path             # /inbox/filename.mp4
    archive_path: Path            # /archive/2025/04/ПШ.SV/Title (Speaker)/
```

## Генерация video_id

```python
def generate_video_id(metadata: VideoMetadata) -> str:
    """
    Генерирует уникальный ID для видео.

    Формат: {date}_{event_type}-{stream}_{slug}
    Пример: 2025-04-07_psh-sv_gruppa-podderzhki
    """
    date_str = metadata.date.isoformat()  # 2025-04-07
    event_stream = f"{metadata.event_type}-{metadata.stream}".lower()  # psh-sv
    slug = slugify(metadata.title)  # gruppa-podderzhki

    return f"{date_str}_{event_stream}_{slug}"
```

## Error Handling

```python
class FilenameParseError(Exception):
    """Имя файла не соответствует паттерну."""
    pass

def parse_filename(filename: str) -> VideoMetadata:
    match = re.match(FILENAME_PATTERN, filename)
    if not match:
        raise FilenameParseError(
            f"Файл '{filename}' не соответствует паттерну. "
            f"Ожидается: '{{дата}} {{тип}}.{{поток}} {{тема}} ({{спикер}}).mp4'"
        )
    # ...
```

---

## Связанные документы

- **Код:** [`backend/app/services/parser.py`](../../backend/app/services/parser.py)
- **Типы мероприятий:** [`config/events.yaml`](../../config/events.yaml)
