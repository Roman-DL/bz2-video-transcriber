# Этап 1: Parse Filename

[Обзор Pipeline](README.md) | [Далее: Transcribe >](02-transcribe.md)

---

## Назначение

Извлечение метаданных из имени файла по установленному паттерну.

## Паттерн имени файла

```
{дата} {тип}.{поток} {тема} ({спикер}).{ext}

Пример:
2025.04.07 ПШ.SV Группа поддержки (Светлана Дмитрук).mp4
```

**Поддерживаемые форматы:** `.mp4`, `.mkv` и другие видеофайлы.

## Regex

```python
FILENAME_PATTERN = re.compile(
    r'^(\d{4}\.\d{2}\.\d{2})\s+'  # Date: 2025.04.07
    r'(\w+)\.(\w+)\s+'             # Type.Stream: ПШ.SV
    r'(.+?)\s+'                    # Title: Группа поддержки
    r'\(([^)]+)\)'                 # Speaker: (Светлана Дмитрук)
    r'(?:\.\w+)?$',                # Extension: .mp4 (опционально)
    re.UNICODE                     # Поддержка кириллицы в \w
)

# Группы:
# 1: date       (2025.04.07)
# 2: event_type (ПШ)
# 3: stream     (SV)
# 4: title      (Группа поддержки)
# 5: speaker    (Светлана Дмитрук)
```

## Модель данных

```python
class VideoMetadata(BaseModel):
    """Metadata extracted from video filename."""

    # Из имени файла
    date: date                    # 2025-04-07
    event_type: str               # ПШ
    stream: str                   # SV
    title: str                    # Группа поддержки
    speaker: str                  # Светлана Дмитрук

    # Вычисляемые
    original_filename: str        # Полное имя файла
    video_id: str                 # 2025-04-07_ПШ-SV_группа-поддержки

    # Пути
    source_path: Path             # /inbox/filename.mp4
    archive_path: Path            # /archive/2025/04/ПШ.SV/Группа поддержки (Светлана Дмитрук)/

    @computed_field
    @property
    def stream_full(self) -> str:
        """Full stream name: ПШ.SV"""
        return f"{self.event_type}.{self.stream}"
```

**Файл модели:** [`backend/app/models/schemas.py`](../../backend/app/models/schemas.py)

## Функция slugify

Преобразует текст в slug-формат для video_id:

```python
def slugify(text: str) -> str:
    """
    Convert text to slug format.

    - Преобразует в lowercase
    - Заменяет пробелы на дефисы
    - Удаляет спецсимволы (сохраняет буквы, цифры, дефисы)
    - Кириллица сохраняется

    Примеры:
        "Группа поддержки" → "группа-поддержки"
        "Test 123" → "test-123"
        "Multiple   Spaces" → "multiple-spaces"
    """
```

## Генерация video_id

```python
def generate_video_id(d: date, event_type: str, stream: str, title: str) -> str:
    """
    Generate unique video ID.

    Формат: {date}_{event_type}-{stream}_{slug}
    Пример: 2025-04-07_ПШ-SV_группа-поддержки

    Args:
        d: Дата видео
        event_type: Код типа события (ПШ)
        stream: Код потока (SV)
        title: Название видео

    Returns:
        Уникальный ID видео
    """
    date_str = d.isoformat()        # 2025-04-07
    type_stream = f"{event_type}-{stream}"  # ПШ-SV (регистр сохраняется)
    title_slug = slugify(title)     # группа-поддержки

    return f"{date_str}_{type_stream}_{title_slug}"
```

## Валидация типа события

```python
def validate_event_type_stream(event_type: str, stream: str) -> None:
    """
    Validate event_type and stream against events.yaml configuration.

    Выводит предупреждения если тип или поток не найдены,
    но не выбрасывает исключения.

    Args:
        event_type: Код типа события для проверки
        stream: Код потока для проверки
    """
```

## Парсинг имени файла

```python
def parse_filename(
    filename: str,
    source_path: Path | None = None
) -> VideoMetadata:
    """
    Parse video filename and return metadata.

    Args:
        filename: Имя файла для парсинга
        source_path: Опциональный путь (по умолчанию inbox_dir/filename)

    Returns:
        VideoMetadata с извлечённой информацией

    Raises:
        FilenameParseError: Если имя файла не соответствует паттерну
    """
```

## Error Handling

```python
class FilenameParseError(Exception):
    """Raised when filename doesn't match expected pattern."""

    def __init__(self, filename: str, message: str | None = None):
        self.filename = filename
        if message is None:
            message = (
                f"Filename '{filename}' doesn't match expected pattern. "
                f"Expected format: '{{date}} {{type}}.{{stream}} {{title}} ({{speaker}}).mp4'"
            )
        super().__init__(message)
```

## Тестирование

Встроенные тесты запускаются командой:

```bash
python -m backend.app.services.parser
```

**Тесты:**
1. Парсинг стандартного имени файла
2. Генерация video_id с кириллицей
3. Обработка некорректного имени файла
4. Поддержка расширения `.mkv`
5. Функция `slugify()`

---

## Связанные документы

- **Код:** [`backend/app/services/parser.py`](../../backend/app/services/parser.py)
- **Модели:** [`backend/app/models/schemas.py`](../../backend/app/models/schemas.py)
- **Типы мероприятий:** [`config/events.yaml`](../../config/events.yaml)
