"""
Filename parser for video files.

Supports two formats:

1. Regular events (ПШ - weekly schools):
    {date} {type}[.{stream}] {title} ({speaker}).mp4
    Example: 2025.01.13 ПШ.SV Закрытие ПО (Кухаренко Женя).mp4

2. Offsite events (выездные):
    Leadership: {Фамилия} ({Имя}).mp4 or {Фамилия} ({Имя и Имя}).mp4
    Educational: {Фамилия} — {Название темы}.mp4

    For offsite, event_name comes from parent folder or config.
    Example folder: inbox/2025.01 Форум TABTeam (Москва)/Антоновы (Дмитрий и Юлия).mp4
"""

import logging
import re
from datetime import date, datetime
from pathlib import Path

from app.config import get_settings, load_events_config
from app.models.schemas import ContentType, EventCategory, VideoMetadata

logger = logging.getLogger(__name__)


class FilenameParseError(Exception):
    """Raised when filename doesn't match expected pattern."""

    def __init__(self, filename: str, message: str | None = None):
        self.filename = filename
        if message is None:
            message = (
                f"Filename '{filename}' doesn't match expected pattern. "
                f"Expected format: '{{date}} {{type}}[.{{stream}}] {{title}} ({{speaker}}).mp4'"
            )
        super().__init__(message)


# Regex pattern for regular events (ПШ - weekly schools)
# Groups: (1) date, (2) event_type, (3) stream (optional), (4) title, (5) speaker
REGULAR_EVENT_PATTERN = re.compile(
    r'^(\d{4}\.\d{2}\.\d{2})\s+'  # Date: 2025.04.07
    r'(\w+)(?:\.(\w+))?\s+'        # Type[.Stream]: ПШ.SV or ПШ (stream optional)
    r'(.+?)\s+'                    # Title: Группа поддержки
    r'\(([^)]+)\)'                 # Speaker: (Светлана Дмитрук)
    r'(?:\.\w+)?$',                # Extension: .mp4 (optional in pattern)
    re.UNICODE
)

# Regex pattern for offsite leadership stories
# "Фамилия (Имя)" or "Фамилия (Имя и Имя)" - speaker story
# Groups: (1) surname (title=surname), (2) first_name(s) (speaker=names)
OFFSITE_LEADERSHIP_PATTERN = re.compile(
    r'^([А-ЯЁA-Z][а-яёa-z]+(?:ы|е|о|а)?)\s*'  # Surname: Антоновы, Мекибель
    r'\(([А-ЯЁA-Z][а-яёa-z]+(?:\s+и\s+[А-ЯЁA-Z][а-яёa-z]+)?)\)'  # (Имя) or (Имя и Имя)
    r'(?:\.\w+)?$',  # Extension
    re.UNICODE
)

# Regex pattern for offsite educational content
# "Фамилия — Название темы" - educational topic from speaker
# Groups: (1) surname (speaker), (2) title
OFFSITE_EDUCATIONAL_PATTERN = re.compile(
    r'^([А-ЯЁA-Z][а-яёa-z]+)\s*'  # Surname: Мекибель
    r'[—–-]\s*'  # Em-dash, en-dash, or hyphen with optional spaces
    r'(.+?)'  # Title: Модели работы с МП
    r'(?:\.\w+)?$',  # Extension
    re.UNICODE
)

# Regex pattern for offsite event folder name
# "{MM} {Event Name} ({City})" or "{YYYY.MM} {Event Name} ({City})"
# Groups: (1) month/date prefix, (2) event name, (3) city
OFFSITE_FOLDER_PATTERN = re.compile(
    r'^(\d{4}\.\d{2}|\d{2})\s+'  # Date prefix: "2025.01" or "01"
    r'(.+?)\s*'  # Event name: Форум TABTeam
    r'\(([^)]+)\)$',  # City: (Москва)
    re.UNICODE
)

# Keep old name for backwards compatibility in tests
FILENAME_PATTERN = REGULAR_EVENT_PATTERN


def slugify(text: str) -> str:
    """
    Convert text to slug format.

    - Replace spaces with dashes
    - Remove special characters (keep letters, digits, dashes)
    - Convert to lowercase
    - Cyrillic characters are preserved

    Args:
        text: Input text to slugify

    Returns:
        Slugified text
    """
    # Convert to lowercase
    text = text.lower()

    # Replace spaces with dashes
    text = text.replace(' ', '-')

    # Keep only letters (including cyrillic), digits, and dashes
    text = re.sub(r'[^\w\-]', '', text, flags=re.UNICODE)

    # Replace multiple dashes with single dash
    text = re.sub(r'-+', '-', text)

    # Strip leading/trailing dashes
    text = text.strip('-')

    return text


def generate_video_id(d: date, event_type: str, stream: str, title: str) -> str:
    """
    Generate unique video ID.

    Format: {date}_{event_type}[-{stream}]_{slug}
    Examples:
        2025-04-07_ПШ-SV_группа-поддержки (with stream)
        2025-04-07_ПШ_группа-поддержки (without stream)

    Args:
        d: Video date
        event_type: Event type code (e.g., ПШ)
        stream: Stream code (e.g., SV), can be empty string
        title: Video title

    Returns:
        Unique video ID
    """
    date_str = d.isoformat()  # 2025-04-07
    type_stream = f"{event_type}-{stream}" if stream else event_type
    title_slug = slugify(title)

    return f"{date_str}_{type_stream}_{title_slug}"


def validate_event_type_stream(event_type: str, stream: str) -> None:
    """
    Validate event_type and stream against events.yaml configuration.

    Issues warnings if not found but doesn't raise errors.

    Args:
        event_type: Event type code to validate
        stream: Stream code to validate (can be empty)
    """
    try:
        events_config = load_events_config()
        event_types = events_config.get('event_types', {})

        if event_type not in event_types:
            logger.warning(
                f"Unknown event type '{event_type}'. "
                f"Known types: {list(event_types.keys())}"
            )
            return

        # Skip stream validation if stream is empty
        if not stream:
            return

        event_streams = event_types[event_type].get('streams', {})
        if stream not in event_streams:
            logger.warning(
                f"Unknown stream '{stream}' for event type '{event_type}'. "
                f"Known streams: {list(event_streams.keys())}"
            )
    except Exception as e:
        logger.warning(f"Could not validate event type/stream: {e}")


def get_event_category(event_type: str) -> EventCategory:
    """
    Determine event category from event type code.

    Args:
        event_type: Event type code (e.g., "ПШ", "ВЫЕЗД")

    Returns:
        EventCategory.REGULAR for weekly schools (ПШ),
        EventCategory.OFFSITE for other events
    """
    try:
        events_config = load_events_config()
        event_types = events_config.get('event_types', {})
        event_info = event_types.get(event_type, {})
        category = event_info.get('category', 'regular')
        return EventCategory(category)
    except Exception:
        # Default: ПШ is regular, everything else is offsite
        return EventCategory.REGULAR if event_type == "ПШ" else EventCategory.OFFSITE


def parse_offsite_folder(folder_name: str) -> tuple[str, str | None]:
    """
    Parse offsite event folder name to extract event name and date.

    Args:
        folder_name: Folder name like "2025.01 Форум TABTeam (Москва)" or "01 Форум TABTeam (Москва)"

    Returns:
        Tuple of (event_name with city, date_prefix or None)
        Example: ("Форум TABTeam (Москва)", "2025.01")
    """
    match = OFFSITE_FOLDER_PATTERN.match(folder_name)
    if match:
        date_prefix, event_name, city = match.groups()
        return f"{event_name} ({city})", date_prefix
    return folder_name, None


def detect_content_type_from_filename(filename: str) -> tuple[ContentType, str, str] | None:
    """
    Detect content type from offsite filename pattern.

    Args:
        filename: Filename without path, e.g. "Антоновы (Дмитрий и Юлия).mp4"

    Returns:
        Tuple of (content_type, title, speaker) if matched, None otherwise
    """
    # Try leadership pattern: Фамилия (Имя) or Фамилия (Имя и Имя)
    match = OFFSITE_LEADERSHIP_PATTERN.match(filename)
    if match:
        surname, first_names = match.groups()
        # Title is just the surname (family name), speaker is full name
        return ContentType.LEADERSHIP, surname, first_names

    # Try educational pattern: Фамилия — Название
    match = OFFSITE_EDUCATIONAL_PATTERN.match(filename)
    if match:
        surname, title = match.groups()
        return ContentType.EDUCATIONAL, title.strip(), surname

    return None


def parse_filename(
    filename: str,
    source_path: Path | None = None,
    event_name: str | None = None,
) -> VideoMetadata:
    """
    Parse video filename and return metadata.

    Supports two formats:
    1. Regular events (ПШ): "{date} {type}[.{stream}] {title} ({speaker}).mp4"
    2. Offsite events: "{Фамилия} ({Имя}).mp4" or "{Фамилия} — {Название}.mp4"

    For offsite events, event_name should be provided (from parent folder or config).

    Args:
        filename: Video filename to parse
        source_path: Optional source path (defaults to inbox_dir/filename)
        event_name: For offsite events, the event name (e.g., "Форум TABTeam (Москва)")

    Returns:
        VideoMetadata with parsed information

    Raises:
        FilenameParseError: If filename doesn't match any expected pattern
    """
    settings = get_settings()

    # Determine source path
    if source_path is None:
        source_path = settings.inbox_dir / filename

    # Try regular event pattern first (has date prefix)
    match = REGULAR_EVENT_PATTERN.match(filename)
    if match:
        return _parse_regular_event(match, filename, source_path, settings)

    # Try offsite patterns (no date prefix)
    offsite_result = detect_content_type_from_filename(filename)
    if offsite_result:
        content_type, title, speaker = offsite_result
        return _parse_offsite_event(
            filename, source_path, settings, content_type, title, speaker, event_name
        )

    # No pattern matched
    raise FilenameParseError(
        filename,
        f"Filename '{filename}' doesn't match any expected pattern.\n"
        f"Expected formats:\n"
        f"  - Regular: '{{date}} {{type}}[.{{stream}}] {{title}} ({{speaker}}).mp4'\n"
        f"  - Offsite leadership: '{{Фамилия}} ({{Имя}}).mp4'\n"
        f"  - Offsite educational: '{{Фамилия}} — {{Название}}.mp4'"
    )


def _parse_regular_event(
    match: re.Match,
    filename: str,
    source_path: Path,
    settings,
) -> VideoMetadata:
    """Parse regular event filename (ПШ - weekly schools)."""
    date_str, event_type, stream, title, speaker = match.groups()
    stream = stream or ""

    # Parse date
    try:
        video_date = datetime.strptime(date_str, '%Y.%m.%d').date()
    except ValueError as e:
        raise FilenameParseError(filename, f"Invalid date format: {e}")

    # Validate event type and stream
    validate_event_type_stream(event_type, stream)

    # Determine event category
    event_category = get_event_category(event_type)

    # Generate video ID
    video_id = generate_video_id(video_date, event_type, stream, title)

    # Generate archive path based on event category
    # Regular (ПШ): archive/{year}/ПШ/{MM.DD}/{[stream] title (speaker)}/
    # Offsite: archive/{year}/Выездные/{event_name}/{title (speaker)}/
    if event_category == EventCategory.REGULAR:
        date_folder = f"{video_date.month:02d}.{video_date.day:02d}"
        topic_folder = f"{stream} {title} ({speaker})" if stream else f"{title} ({speaker})"
        archive_path = (
            settings.archive_dir
            / str(video_date.year)
            / event_type
            / date_folder
            / topic_folder
        )
    else:
        # For dated offsite events (rare)
        topic_folder = f"{stream} {title} ({speaker})" if stream else f"{title} ({speaker})"
        archive_path = (
            settings.archive_dir
            / str(video_date.year)
            / "Выездные"
            / event_type
            / topic_folder
        )

    return VideoMetadata(
        date=video_date,
        event_type=event_type,
        stream=stream,
        title=title,
        speaker=speaker,
        original_filename=filename,
        video_id=video_id,
        source_path=source_path,
        archive_path=archive_path,
        content_type=ContentType.EDUCATIONAL,  # Regular events are always educational
        event_category=event_category,
    )


def _parse_offsite_event(
    filename: str,
    source_path: Path,
    settings,
    content_type: ContentType,
    title: str,
    speaker: str,
    event_name: str | None,
) -> VideoMetadata:
    """Parse offsite event filename (выездные)."""
    # For offsite events, try to get event_name from parent folder if not provided
    if event_name is None:
        parent_folder = source_path.parent.name
        if parent_folder != "inbox":
            event_name, date_prefix = parse_offsite_folder(parent_folder)
        else:
            raise FilenameParseError(
                filename,
                f"Offsite event file '{filename}' requires event_name. "
                f"Either provide event_name parameter or place file in event folder "
                f"(e.g., 'inbox/2025.01 Форум TABTeam (Москва)/{filename}')"
            )

    # Use current date for offsite events (actual date should come from event)
    video_date = date.today()

    # Generate video ID: slug of event_name + title
    event_slug = slugify(event_name) if event_name else "выездные"
    video_id = f"{video_date.isoformat()}_{event_slug}_{slugify(title)}"

    # For leadership: folder is "Фамилия (Имя)"
    # For educational: folder is "Тема (Спикер)"
    if content_type == ContentType.LEADERSHIP:
        topic_folder = f"{title} ({speaker})"
    else:
        topic_folder = f"{title} ({speaker})"

    archive_path = (
        settings.archive_dir
        / str(video_date.year)
        / "Выездные"
        / event_name
        / topic_folder
    )

    return VideoMetadata(
        date=video_date,
        event_type="ВЫЕЗД",
        stream="",
        title=title,
        speaker=speaker,
        original_filename=filename,
        video_id=video_id,
        source_path=source_path,
        archive_path=archive_path,
        content_type=content_type,
        event_category=EventCategory.OFFSITE,
        event_name=event_name,
    )


if __name__ == "__main__":
    """Run tests when executed directly."""
    import sys

    # Configure logging for tests
    logging.basicConfig(level=logging.WARNING)

    def test_standard_filename():
        """Test 1: Standard filename parsing."""
        print("Test 1: Standard filename parsing...", end=" ")

        filename = "2025.04.07 ПШ.SV Группа поддержки (Светлана Дмитрук).mp4"
        metadata = parse_filename(filename)

        assert metadata.date == date(2025, 4, 7), f"Date mismatch: {metadata.date}"
        assert metadata.event_type == "ПШ", f"Event type mismatch: {metadata.event_type}"
        assert metadata.stream == "SV", f"Stream mismatch: {metadata.stream}"
        assert metadata.title == "Группа поддержки", f"Title mismatch: {metadata.title}"
        assert metadata.speaker == "Светлана Дмитрук", f"Speaker mismatch: {metadata.speaker}"
        assert metadata.original_filename == filename

        print("OK")

    def test_video_id_generation():
        """Test 2: Video ID generation with cyrillic."""
        print("Test 2: Video ID generation...", end=" ")

        video_id = generate_video_id(
            date(2025, 4, 7),
            "ПШ",
            "SV",
            "Группа поддержки"
        )

        expected = "2025-04-07_ПШ-SV_группа-поддержки"
        assert video_id == expected, f"Video ID mismatch: {video_id} != {expected}"

        print("OK")

    def test_invalid_filename():
        """Test 3: Invalid filename error."""
        print("Test 3: Invalid filename error...", end=" ")

        try:
            parse_filename("invalid_filename.mp4")
            assert False, "Should have raised FilenameParseError"
        except FilenameParseError as e:
            assert "invalid_filename.mp4" in str(e)

        print("OK")

    def test_mkv_extension():
        """Test 4: MKV extension support."""
        print("Test 4: MKV extension...", end=" ")

        filename = "2025.04.07 ПШ.SV Группа поддержки (Светлана Дмитрук).mkv"
        metadata = parse_filename(filename)

        assert metadata.event_type == "ПШ"
        assert metadata.original_filename == filename

        print("OK")

    def test_slugify():
        """Test slugify function."""
        print("Test 5: Slugify function...", end=" ")

        assert slugify("Группа поддержки") == "группа-поддержки"
        assert slugify("Test 123") == "test-123"
        assert slugify("  Multiple   Spaces  ") == "multiple-spaces"
        assert slugify("Special!@#$Chars") == "specialchars"

        print("OK")

    def test_filename_without_stream():
        """Test 6: Filename without stream part."""
        print("Test 6: Filename without stream...", end=" ")

        filename = "2025.04.07 ПШ Группа поддержки (Светлана Дмитрук).mp4"
        metadata = parse_filename(filename)

        assert metadata.date == date(2025, 4, 7), f"Date mismatch: {metadata.date}"
        assert metadata.event_type == "ПШ", f"Event type mismatch: {metadata.event_type}"
        assert metadata.stream == "", f"Stream should be empty: {metadata.stream}"
        assert metadata.title == "Группа поддержки", f"Title mismatch: {metadata.title}"
        assert metadata.speaker == "Светлана Дмитрук", f"Speaker mismatch: {metadata.speaker}"
        assert metadata.stream_full == "ПШ", f"stream_full should be just event_type: {metadata.stream_full}"

        print("OK")

    def test_video_id_without_stream():
        """Test 7: Video ID generation without stream."""
        print("Test 7: Video ID without stream...", end=" ")

        video_id = generate_video_id(
            date(2025, 4, 7),
            "ПШ",
            "",  # Empty stream
            "Группа поддержки"
        )

        expected = "2025-04-07_ПШ_группа-поддержки"
        assert video_id == expected, f"Video ID mismatch: {video_id} != {expected}"

        print("OK")

    def test_archive_path_with_stream():
        """Test 8: Archive path with stream - new structure archive/{year}/ПШ/{MM.DD}/{Title}."""
        print("Test 8: Archive path with stream...", end=" ")

        filename = "2025.12.22 ПШ.SV Тестовая запись (Тест).mp4"
        metadata = parse_filename(filename)

        path_str = str(metadata.archive_path)
        assert "2025" in path_str, f"Year not in path: {path_str}"
        assert "/ПШ/" in path_str, f"Event type folder not in path: {path_str}"
        assert "12.22" in path_str, f"Date folder not in path: {path_str}"
        assert "SV Тестовая запись (Тест)" in path_str, f"Topic folder not in path: {path_str}"

        print("OK")

    def test_archive_path_without_stream():
        """Test 9: Archive path without stream - new structure."""
        print("Test 9: Archive path without stream...", end=" ")

        filename = "2025.12.22 ПШ Тестовая запись (Тест).mp4"
        metadata = parse_filename(filename)

        path_str = str(metadata.archive_path)
        assert "2025" in path_str, f"Year not in path: {path_str}"
        assert "/ПШ/" in path_str, f"Event type folder not in path: {path_str}"
        assert "12.22" in path_str, f"Date folder not in path: {path_str}"
        assert "Тестовая запись (Тест)" in path_str, f"Topic folder not in path: {path_str}"
        # Should NOT have stream prefix
        assert "SV " not in path_str, f"Should not have stream prefix: {path_str}"

        print("OK")

    def test_content_type_regular():
        """Test 10: Regular events have content_type=educational."""
        print("Test 10: Content type for regular events...", end=" ")

        filename = "2025.01.13 ПШ.SV Закрытие ПО (Кухаренко).mp4"
        metadata = parse_filename(filename)

        assert metadata.content_type == ContentType.EDUCATIONAL, \
            f"Expected educational, got {metadata.content_type}"
        assert metadata.event_category == EventCategory.REGULAR, \
            f"Expected regular, got {metadata.event_category}"

        print("OK")

    def test_offsite_leadership_pattern():
        """Test 11: Offsite leadership pattern - 'Фамилия (Имя)'."""
        print("Test 11: Offsite leadership pattern...", end=" ")

        result = detect_content_type_from_filename("Антоновы (Дмитрий и Юлия).mp4")
        assert result is not None, "Should match leadership pattern"
        content_type, title, speaker = result
        assert content_type == ContentType.LEADERSHIP, f"Expected leadership, got {content_type}"
        assert title == "Антоновы", f"Title should be surname: {title}"
        assert speaker == "Дмитрий и Юлия", f"Speaker should be first names: {speaker}"

        print("OK")

    def test_offsite_educational_pattern():
        """Test 12: Offsite educational pattern - 'Фамилия — Название'."""
        print("Test 12: Offsite educational pattern...", end=" ")

        result = detect_content_type_from_filename("Мекибель — Модели работы с МП.mp4")
        assert result is not None, "Should match educational pattern"
        content_type, title, speaker = result
        assert content_type == ContentType.EDUCATIONAL, f"Expected educational, got {content_type}"
        assert title == "Модели работы с МП", f"Title mismatch: {title}"
        assert speaker == "Мекибель", f"Speaker should be surname: {speaker}"

        print("OK")

    def test_offsite_folder_pattern():
        """Test 13: Offsite event folder parsing."""
        print("Test 13: Offsite folder pattern...", end=" ")

        event_name, date_prefix = parse_offsite_folder("2025.01 Форум TABTeam (Москва)")
        assert event_name == "Форум TABTeam (Москва)", f"Event name mismatch: {event_name}"
        assert date_prefix == "2025.01", f"Date prefix mismatch: {date_prefix}"

        event_name2, date_prefix2 = parse_offsite_folder("01 Форум TABTeam (Москва)")
        assert event_name2 == "Форум TABTeam (Москва)", f"Event name mismatch: {event_name2}"
        assert date_prefix2 == "01", f"Date prefix mismatch: {date_prefix2}"

        print("OK")

    # Run all tests
    print("\nRunning parser tests...\n")

    tests = [
        test_standard_filename,
        test_video_id_generation,
        test_invalid_filename,
        test_mkv_extension,
        test_slugify,
        test_filename_without_stream,
        test_video_id_without_stream,
        test_archive_path_with_stream,
        test_archive_path_without_stream,
        test_content_type_regular,
        test_offsite_leadership_pattern,
        test_offsite_educational_pattern,
        test_offsite_folder_pattern,
    ]

    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {e}")
            failed += 1

    print(f"\n{'All tests passed!' if failed == 0 else f'{failed} test(s) failed.'}")
    sys.exit(failed)
