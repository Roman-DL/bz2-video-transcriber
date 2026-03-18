"""
Filename parser for video files.

Unified format (v0.69+, day optional since v0.71):
    {date} {type}[.{stream}]. {title} ({speaker}).ext
    Date: YYYY.MM.DD or YYYY.MM (day defaults to 1 if omitted)

Examples:
    2025.04.07 ПШ.SV. Группа поддержки (Светлана Дмитрук).mp4
    2025.04.07 ПШ.SV. История (Антоновы Дмитрий и Юлия).mp4
    2025.05.02 ШБМ. Тема (Спикер).mp4
    2026.02 ФСТ. Спонсор, за которым идут (Дмитрук Светлана).mp4
    2025.04.07 МК.Бизнес. Тема (Спикер).mp4

"История" in title position → content_type=LEADERSHIP.
Event type determines regular/offsite via events.yaml lookup.
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
                f"Expected format: '{{YYYY.MM[.DD]}} {{type}}[.{{stream}}]. {{title}} ({{speaker}}).ext'"
            )
        super().__init__(message)


# Unified filename pattern (v0.69+)
# Format: {date} {type}[.{stream}]. {title} ({speaker}).ext
# Groups: (1) date, (2) event group (type[.stream]), (3) title, (4) speaker
EVENT_PATTERN = re.compile(
    r'^(\d{4}\.\d{2}(?:\.\d{2})?)\s+'   # Date: 2025.04.07 or 2025.04
    r'(.+?)\.\s+'                    # Event group: ПШ.SV or Форум TABTeam
    r'(.+?)\s+'                      # Title: Группа поддержки or История
    r'\(([^)]+)\)'                   # Speaker/Names: (Светлана Дмитрук)
    r'(?:\.\w+)?$',                  # Extension: .mp4
    re.UNICODE
)


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
        event_type: Event type code (e.g., "ПШ", "ШБМ")

    Returns:
        EventCategory.REGULAR or EventCategory.OFFSITE based on events.yaml
    """
    try:
        events_config = load_events_config()
        event_types = events_config.get('event_types', {})
        event_info = event_types.get(event_type, {})
        category = event_info.get('category', 'regular')
        return EventCategory(category)
    except Exception:
        return EventCategory.REGULAR if event_type == "ПШ" else EventCategory.OFFSITE


def resolve_event_name(event_type: str, stream: str) -> str:
    """Resolve short display name for an event.

    With stream: "{display_name}.{stream}" (e.g., "ПШ.SV")
    Without stream: display_name (e.g., "ВВК", "Форум TABTeam")
    Fallback: event_type code.

    Args:
        event_type: Event type code (e.g., "ПШ")
        stream: Stream code (e.g., "SV"), can be empty string

    Returns:
        Display name for the event
    """
    try:
        events_config = load_events_config()
        event_info = events_config.get("event_types", {}).get(event_type, {})
        display_name = event_info.get("display_name", event_type)
    except Exception:
        display_name = event_type

    if stream:
        return f"{display_name}.{stream}"
    return display_name


def parse_filename(
    filename: str,
    source_path: Path | None = None,
) -> VideoMetadata:
    """
    Parse media filename and return metadata.

    Unified format (v0.69+):
        {date} {type}[.{stream}]. {title} ({speaker}).ext

    Args:
        filename: Media filename to parse
        source_path: Optional source path (defaults to inbox_dir/filename)

    Returns:
        VideoMetadata with parsed information

    Raises:
        FilenameParseError: If filename doesn't match expected pattern
    """
    settings = get_settings()

    # Determine source path
    if source_path is None:
        source_path = settings.inbox_dir / filename

    # Try unified event pattern
    match = EVENT_PATTERN.match(filename)
    if match:
        return _parse_event(match, filename, source_path, settings)

    # No pattern matched
    raise FilenameParseError(
        filename,
        f"Filename '{filename}' doesn't match expected pattern.\n"
        f"Expected format: '{{YYYY.MM[.DD]}} {{type}}[.{{stream}}]. {{title}} ({{speaker}}).ext'"
    )


def _parse_event(
    match: re.Match,
    filename: str,
    source_path: Path,
    settings,
) -> VideoMetadata:
    """Parse unified event filename (v0.69+)."""
    date_str, event_group, title, speaker = match.groups()

    # Parse date
    try:
        if len(date_str) == 10:  # YYYY.MM.DD
            video_date = datetime.strptime(date_str, '%Y.%m.%d').date()
        else:  # YYYY.MM (day defaults to 1)
            video_date = datetime.strptime(date_str, '%Y.%m').date()
    except ValueError as e:
        raise FilenameParseError(filename, f"Invalid date format: {e}")

    # Parse event group: "ПШ.SV" → ("ПШ", "SV"), "Форум TABTeam" → ("Форум TABTeam", "")
    if '.' in event_group:
        last_dot = event_group.rindex('.')
        event_type = event_group[:last_dot]
        stream = event_group[last_dot + 1:]
    else:
        event_type = event_group
        stream = ""

    # Validate event type and stream
    validate_event_type_stream(event_type, stream)

    # Determine event category
    event_category = get_event_category(event_type)

    # Leadership detection: "#История" marker → LEADERSHIP
    if title.startswith("#История"):
        content_type = ContentType.LEADERSHIP
        title = title[1:]  # Strip '#' — marker consumed by parser
    else:
        content_type = ContentType.EDUCATIONAL

    # Resolve event_name
    event_name = resolve_event_name(event_type, stream)

    # Generate video ID
    video_id = generate_video_id(video_date, event_type, stream, title)

    # Generate archive path based on event category (3-level structure)
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
        settings.archive_dir
        / str(video_date.year)
        / event_group
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
        content_type=content_type,
        event_category=event_category,
        event_name=event_name,
    )


if __name__ == "__main__":
    """Run tests when executed directly."""
    import sys

    # Configure logging for tests
    logging.basicConfig(level=logging.WARNING)

    def test_regular_with_stream():
        """Test 1: Regular event with stream."""
        print("Test 1: Regular event with stream...", end=" ")

        filename = "2025.04.07 ПШ.SV. Группа поддержки (Светлана Дмитрук).mp4"
        metadata = parse_filename(filename)

        assert metadata.date == date(2025, 4, 7), f"Date mismatch: {metadata.date}"
        assert metadata.event_type == "ПШ", f"Event type mismatch: {metadata.event_type}"
        assert metadata.stream == "SV", f"Stream mismatch: {metadata.stream}"
        assert metadata.title == "Группа поддержки", f"Title mismatch: {metadata.title}"
        assert metadata.speaker == "Светлана Дмитрук", f"Speaker mismatch: {metadata.speaker}"
        assert metadata.content_type == ContentType.EDUCATIONAL, f"Content type mismatch: {metadata.content_type}"
        assert metadata.event_category == EventCategory.REGULAR, f"Category mismatch: {metadata.event_category}"
        assert metadata.event_name == "ПШ.SV", f"Event name mismatch: {metadata.event_name}"
        assert metadata.original_filename == filename

        print("OK")

    def test_regular_without_stream():
        """Test 2: Regular event without stream."""
        print("Test 2: Regular event without stream...", end=" ")

        filename = "2025.04.07 Тема. Название (Спикер).mp4"
        metadata = parse_filename(filename)

        assert metadata.event_type == "Тема", f"Event type mismatch: {metadata.event_type}"
        assert metadata.stream == "", f"Stream should be empty: {metadata.stream}"
        assert metadata.title == "Название", f"Title mismatch: {metadata.title}"
        assert metadata.speaker == "Спикер", f"Speaker mismatch: {metadata.speaker}"
        assert metadata.event_name == "Тема", f"Event name mismatch: {metadata.event_name}"

        print("OK")

    def test_leadership_regular():
        """Test 3: Leadership on regular event (#История)."""
        print("Test 3: Leadership regular (#История)...", end=" ")

        filename = "2025.04.07 ПШ.SV. #История (Антоновы Дмитрий и Юлия).mp4"
        metadata = parse_filename(filename)

        assert metadata.content_type == ContentType.LEADERSHIP, f"Expected leadership, got {metadata.content_type}"
        assert metadata.event_type == "ПШ", f"Event type mismatch: {metadata.event_type}"
        assert metadata.stream == "SV", f"Stream mismatch: {metadata.stream}"
        assert metadata.title == "История", f"Title mismatch: {metadata.title}"
        assert metadata.speaker == "Антоновы Дмитрий и Юлия", f"Speaker mismatch: {metadata.speaker}"
        assert metadata.event_name == "ПШ.SV", f"Event name mismatch: {metadata.event_name}"

        print("OK")

    def test_leadership_different_surnames():
        """Test 4: Leadership with different surnames."""
        print("Test 4: Leadership different surnames...", end=" ")

        filename = "2025.04.07 ПШ.SV. #История (Иванов Дмитрий и Петрова Юлия).mp4"
        metadata = parse_filename(filename)

        assert metadata.content_type == ContentType.LEADERSHIP, f"Expected leadership"
        assert metadata.speaker == "Иванов Дмитрий и Петрова Юлия", f"Speaker mismatch: {metadata.speaker}"

        print("OK")

    def test_offsite_educational():
        """Test 5: Offsite educational event."""
        print("Test 5: Offsite educational...", end=" ")

        filename = "2025.05.02 ШБМ. Тема (Спикер).mp4"
        metadata = parse_filename(filename)

        assert metadata.event_type == "ШБМ", f"Event type mismatch: {metadata.event_type}"
        assert metadata.stream == "", f"Stream should be empty: {metadata.stream}"
        assert metadata.title == "Тема", f"Title mismatch: {metadata.title}"
        assert metadata.content_type == ContentType.EDUCATIONAL, f"Content type mismatch: {metadata.content_type}"
        assert metadata.event_category == EventCategory.OFFSITE, f"Category mismatch: {metadata.event_category}"
        assert metadata.event_name == "ШБМ", f"Event name mismatch: {metadata.event_name}"

        # Check 3-level archive path: {year}/{MM event_type}/{topic}/
        path_str = str(metadata.archive_path)
        assert "Выездные" not in path_str, f"Выездные should not be in path: {path_str}"
        assert "/05 ШБМ/" in path_str, f"'05 ШБМ' not in path: {path_str}"

        print("OK")

    def test_offsite_leadership():
        """Test 6: Offsite leadership event."""
        print("Test 6: Offsite leadership...", end=" ")

        filename = "2025.05.02 ШБМ. #История (Иванов Дмитрий).mp4"
        metadata = parse_filename(filename)

        assert metadata.content_type == ContentType.LEADERSHIP, f"Expected leadership"
        assert metadata.event_category == EventCategory.OFFSITE, f"Expected offsite"
        assert metadata.event_name == "ШБМ", f"Event name mismatch: {metadata.event_name}"

        print("OK")

    def test_multi_word_event_type():
        """Test 7: Multi-word event type (Форум TABTeam)."""
        print("Test 7: Multi-word event type...", end=" ")

        filename = "2025.05.02 Форум TABTeam. Тема (Спикер).mp4"
        metadata = parse_filename(filename)

        assert metadata.event_type == "Форум TABTeam", f"Event type mismatch: {metadata.event_type}"
        assert metadata.stream == "", f"Stream should be empty: {metadata.stream}"
        assert metadata.title == "Тема", f"Title mismatch: {metadata.title}"
        assert metadata.event_name == "Форум TABTeam", f"Event name mismatch: {metadata.event_name}"
        assert metadata.event_category == EventCategory.OFFSITE, f"Expected offsite"

        print("OK")

    def test_cyrillic_stream():
        """Test 8: Stream with cyrillic (МК.Бизнес)."""
        print("Test 8: Cyrillic stream...", end=" ")

        filename = "2025.04.07 МК.Бизнес. Тема (Спикер).mp4"
        metadata = parse_filename(filename)

        assert metadata.event_type == "МК", f"Event type mismatch: {metadata.event_type}"
        assert metadata.stream == "Бизнес", f"Stream mismatch: {metadata.stream}"
        assert metadata.event_name == "МК.Бизнес", f"Event name mismatch: {metadata.event_name}"

        print("OK")

    def test_video_id_generation():
        """Test 9: Video ID generation."""
        print("Test 9: Video ID generation...", end=" ")

        video_id = generate_video_id(date(2025, 4, 7), "ПШ", "SV", "Группа поддержки")
        expected = "2025-04-07_ПШ-SV_группа-поддержки"
        assert video_id == expected, f"Video ID mismatch: {video_id} != {expected}"

        video_id2 = generate_video_id(date(2025, 4, 7), "ПШ", "", "Группа поддержки")
        expected2 = "2025-04-07_ПШ_группа-поддержки"
        assert video_id2 == expected2, f"Video ID mismatch: {video_id2} != {expected2}"

        print("OK")

    def test_invalid_filename():
        """Test 10: Invalid filename error."""
        print("Test 10: Invalid filename error...", end=" ")

        try:
            parse_filename("invalid_filename.mp4")
            assert False, "Should have raised FilenameParseError"
        except FilenameParseError as e:
            assert "invalid_filename.mp4" in str(e)

        print("OK")

    def test_slugify():
        """Test 11: Slugify function."""
        print("Test 11: Slugify function...", end=" ")

        assert slugify("Группа поддержки") == "группа-поддержки"
        assert slugify("Test 123") == "test-123"
        assert slugify("  Multiple   Spaces  ") == "multiple-spaces"
        assert slugify("Special!@#$Chars") == "specialchars"

        print("OK")

    def test_mkv_extension():
        """Test 12: MKV extension support."""
        print("Test 12: MKV extension...", end=" ")

        filename = "2025.04.07 ПШ.SV. Группа поддержки (Светлана Дмитрук).mkv"
        metadata = parse_filename(filename)
        assert metadata.event_type == "ПШ"
        assert metadata.original_filename == filename

        print("OK")

    def test_archive_path_regular():
        """Test 13: Archive path for regular event (3-level)."""
        print("Test 13: Archive path regular...", end=" ")

        filename = "2025.12.22 ПШ.SV. Тестовая запись (Тест).mp4"
        metadata = parse_filename(filename)

        path_str = str(metadata.archive_path)
        assert "2025" in path_str, f"Year not in path: {path_str}"
        assert "/ПШ/" in path_str, f"Event type not in path: {path_str}"
        assert "12.22 SV. Тестовая запись (Тест)" in path_str, f"Topic folder not in path: {path_str}"

        print("OK")

    def test_archive_path_no_stream():
        """Test 14: Archive path without stream (3-level)."""
        print("Test 14: Archive path no stream...", end=" ")

        filename = "2025.12.22 ПШ. Тестовая запись (Тест).mp4"
        metadata = parse_filename(filename)

        path_str = str(metadata.archive_path)
        assert "/ПШ/" in path_str, f"Event type not in path: {path_str}"
        assert "12.22 Тестовая запись (Тест)" in path_str, f"Topic folder not in path: {path_str}"
        assert "SV " not in path_str, f"Should not have stream prefix: {path_str}"

        print("OK")

    def test_resolve_event_name():
        """Test 15: resolve_event_name for various types."""
        print("Test 15: resolve_event_name...", end=" ")

        assert resolve_event_name("ПШ", "SV") == "ПШ.SV", f"Got: {resolve_event_name('ПШ', 'SV')}"
        assert resolve_event_name("ПШ", "") == "ПШ", f"Got: {resolve_event_name('ПШ', '')}"
        assert resolve_event_name("ВВК", "") == "ВВК", f"Got: {resolve_event_name('ВВК', '')}"
        assert resolve_event_name("Форум TABTeam", "") == "Форум TABTeam", \
            f"Got: {resolve_event_name('Форум TABTeam', '')}"
        assert resolve_event_name("ШБМ", "") == "ШБМ", f"Got: {resolve_event_name('ШБМ', '')}"
        assert resolve_event_name("МК", "Бизнес") == "МК.Бизнес", f"Got: {resolve_event_name('МК', 'Бизнес')}"

        # Unknown type falls back to event_type
        assert resolve_event_name("UNKNOWN", "") == "UNKNOWN"
        assert resolve_event_name("UNKNOWN", "X") == "UNKNOWN.X"

        print("OK")

    def test_multi_word_event_leadership():
        """Test 16: Multi-word event type with leadership."""
        print("Test 16: Multi-word event leadership...", end=" ")

        filename = "2025.05.02 Форум TABTeam. #История (Иванов Дмитрий).mp4"
        metadata = parse_filename(filename)

        assert metadata.event_type == "Форум TABTeam", f"Event type mismatch: {metadata.event_type}"
        assert metadata.content_type == ContentType.LEADERSHIP, f"Expected leadership"
        assert metadata.title == "История", f"Title mismatch: {metadata.title}"
        assert metadata.event_name == "Форум TABTeam", f"Event name mismatch: {metadata.event_name}"

        print("OK")

    def test_md_extension():
        """Test 17: MD extension support."""
        print("Test 17: MD extension...", end=" ")

        filename = "2025.04.07 ПШ.SV. Группа поддержки (Светлана Дмитрук).md"
        metadata = parse_filename(filename)
        assert metadata.event_type == "ПШ"
        assert metadata.stream == "SV"

        print("OK")

    def test_date_without_day_offsite():
        """Test 18: Offsite event without day in date."""
        print("Test 18: Date without day (offsite)...", end=" ")

        filename = "2026.02 ФСТ. Спонсор, за которым идут (Дмитрук Светлана).mp4"
        metadata = parse_filename(filename)

        assert metadata.date == date(2026, 2, 1), f"Date mismatch: {metadata.date}"
        assert metadata.event_type == "ФСТ", f"Event type mismatch: {metadata.event_type}"
        assert metadata.title == "Спонсор, за которым идут", f"Title mismatch: {metadata.title}"
        assert metadata.speaker == "Дмитрук Светлана", f"Speaker mismatch: {metadata.speaker}"
        assert metadata.content_type == ContentType.EDUCATIONAL, f"Content type mismatch"
        assert metadata.event_category == EventCategory.OFFSITE, f"Category mismatch"
        path_str = str(metadata.archive_path)
        assert "/02 ФСТ/" in path_str, f"'02 ФСТ' not in path: {path_str}"
        assert "Выездные" not in path_str, f"Выездные should not be in path: {path_str}"

        print("OK")

    def test_date_without_day_leadership():
        """Test 19: Offsite leadership without day in date."""
        print("Test 19: Date without day (leadership)...", end=" ")

        filename = "2026.02 ШБМ. #История (Иванов Дмитрий).mp4"
        metadata = parse_filename(filename)

        assert metadata.date == date(2026, 2, 1), f"Date mismatch: {metadata.date}"
        assert metadata.content_type == ContentType.LEADERSHIP, f"Expected leadership"
        assert metadata.event_category == EventCategory.OFFSITE, f"Expected offsite"

        print("OK")

    def test_leadership_hash_marker():
        """Test 20: #История marker is consumed by parser."""
        print("Test 20: Leadership hash marker...", end=" ")

        filename = "2026.03.16 ПШ.НП. #История AWT (Прохорова Светлана).mp4"
        metadata = parse_filename(filename)
        assert metadata.content_type == ContentType.LEADERSHIP
        assert metadata.title == "История AWT"  # # stripped
        assert "#" not in str(metadata.archive_path)

        print("OK")

    def test_educational_with_история_in_title():
        """Test 21: История without # is EDUCATIONAL."""
        print("Test 21: Educational with История in title...", end=" ")

        filename = "2026.02 ФСТ. История Herbalife и истоки (Руцман Ида).md"
        metadata = parse_filename(filename)
        assert metadata.content_type == ContentType.EDUCATIONAL
        assert metadata.title == "История Herbalife и истоки"

        print("OK")

    def test_archive_path_regular_with_stream_separator():
        """Test 22: Regular archive path uses '. ' separator between stream and title."""
        print("Test 22: Archive path regular with stream separator...", end=" ")

        filename = "2025.08.04 ПШ.НП. Контент (Пепелина Инга).mp4"
        metadata = parse_filename(filename)
        path_str = str(metadata.archive_path)
        assert "/ПШ/" in path_str
        assert "08.04 НП. Контент (Пепелина Инга)" in path_str

        print("OK")

    # Run all tests
    print("\nRunning parser tests...\n")

    tests = [
        test_regular_with_stream,
        test_regular_without_stream,
        test_leadership_regular,
        test_leadership_different_surnames,
        test_offsite_educational,
        test_offsite_leadership,
        test_multi_word_event_type,
        test_cyrillic_stream,
        test_video_id_generation,
        test_invalid_filename,
        test_slugify,
        test_mkv_extension,
        test_archive_path_regular,
        test_archive_path_no_stream,
        test_resolve_event_name,
        test_multi_word_event_leadership,
        test_md_extension,
        test_date_without_day_offsite,
        test_date_without_day_leadership,
        test_leadership_hash_marker,
        test_educational_with_история_in_title,
        test_archive_path_regular_with_stream_separator,
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
