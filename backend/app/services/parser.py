"""
Filename parser for video files.

Parses video filenames in format:
    {date} {type}[.{stream}] {title} ({speaker}).mp4

Stream (часть) is optional.

Examples:
    2025.04.07 ПШ.SV Группа поддержки (Светлана Дмитрук).mp4
    2025.04.07 ПШ Группа поддержки (Светлана Дмитрук).mp4
"""

import logging
import re
from datetime import date, datetime
from pathlib import Path

from app.config import get_settings, load_events_config
from app.models.schemas import VideoMetadata

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


# Regex pattern for parsing video filenames
# Groups: (1) date, (2) event_type, (3) stream (optional), (4) title, (5) speaker
FILENAME_PATTERN = re.compile(
    r'^(\d{4}\.\d{2}\.\d{2})\s+'  # Date: 2025.04.07
    r'(\w+)(?:\.(\w+))?\s+'        # Type[.Stream]: ПШ.SV or ПШ (stream optional)
    r'(.+?)\s+'                    # Title: Группа поддержки
    r'\(([^)]+)\)'                 # Speaker: (Светлана Дмитрук)
    r'(?:\.\w+)?$',                # Extension: .mp4 (optional in pattern)
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


def parse_filename(
    filename: str,
    source_path: Path | None = None
) -> VideoMetadata:
    """
    Parse video filename and return metadata.

    Args:
        filename: Video filename to parse
        source_path: Optional source path (defaults to inbox_dir/filename)

    Returns:
        VideoMetadata with parsed information

    Raises:
        FilenameParseError: If filename doesn't match expected pattern
    """
    # Match filename against pattern
    match = FILENAME_PATTERN.match(filename)
    if not match:
        raise FilenameParseError(filename)

    # Extract groups
    date_str, event_type, stream, title, speaker = match.groups()

    # stream can be None if not specified, convert to empty string
    stream = stream or ""

    # Parse date
    try:
        video_date = datetime.strptime(date_str, '%Y.%m.%d').date()
    except ValueError as e:
        raise FilenameParseError(filename, f"Invalid date format: {e}")

    # Validate event type and stream (soft validation - warnings only)
    validate_event_type_stream(event_type, stream)

    # Generate video ID
    video_id = generate_video_id(video_date, event_type, stream, title)

    # Get settings for paths
    settings = get_settings()

    # Determine source path
    if source_path is None:
        source_path = settings.inbox_dir / filename

    # Generate archive path
    # Format: archive/{year}/{date event_type}/{[stream] title (speaker)}/
    # Level 1: year (2025)
    # Level 2: date + event_type (12.22 ПШ)
    # Level 3: [stream] title (speaker) - e.g., "SV Тема (Спикер)" or "Тема (Спикер)"
    event_folder = f"{video_date.month:02d}.{video_date.day:02d} {event_type}"
    topic_folder = f"{stream} {title} ({speaker})" if stream else f"{title} ({speaker})"

    archive_path = (
        settings.archive_dir
        / str(video_date.year)
        / event_folder
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
        """Test 8: Archive path with stream."""
        print("Test 8: Archive path with stream...", end=" ")

        filename = "2025.12.22 ПШ.SV Тестовая запись (Тест).mp4"
        metadata = parse_filename(filename)

        path_str = str(metadata.archive_path)
        assert "2025" in path_str, f"Year not in path: {path_str}"
        assert "12.22 ПШ" in path_str, f"Event folder not in path: {path_str}"
        assert "SV Тестовая запись (Тест)" in path_str, f"Topic folder not in path: {path_str}"

        print("OK")

    def test_archive_path_without_stream():
        """Test 9: Archive path without stream."""
        print("Test 9: Archive path without stream...", end=" ")

        filename = "2025.12.22 ПШ Тестовая запись (Тест).mp4"
        metadata = parse_filename(filename)

        path_str = str(metadata.archive_path)
        assert "2025" in path_str, f"Year not in path: {path_str}"
        assert "12.22 ПШ" in path_str, f"Event folder not in path: {path_str}"
        assert "Тестовая запись (Тест)" in path_str, f"Topic folder not in path: {path_str}"
        # Should NOT have stream prefix
        assert "SV " not in path_str, f"Should not have stream prefix: {path_str}"

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
