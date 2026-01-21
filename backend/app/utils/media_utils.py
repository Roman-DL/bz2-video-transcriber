"""
Media utilities for video/audio file handling.

Provides common functions for media file operations:
- Duration detection via ffprobe
- Size-based duration estimation as fallback
- Media type detection (audio vs video)
"""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Supported media extensions
AUDIO_EXTENSIONS = frozenset({".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"})
VIDEO_EXTENSIONS = frozenset({".mp4", ".mkv", ".avi", ".mov", ".webm"})


def is_audio_file(file_path: Path) -> bool:
    """Check if file is an audio file by extension.

    Args:
        file_path: Path to media file

    Returns:
        True if file has audio extension
    """
    return file_path.suffix.lower() in AUDIO_EXTENSIONS


def is_video_file(file_path: Path) -> bool:
    """Check if file is a video file by extension.

    Args:
        file_path: Path to media file

    Returns:
        True if file has video extension
    """
    return file_path.suffix.lower() in VIDEO_EXTENSIONS


def get_media_duration(media_path: Path) -> float | None:
    """Get media duration using ffprobe.

    Works for both audio and video files.

    Args:
        media_path: Path to media file

    Returns:
        Duration in seconds, or None if ffprobe fails
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(media_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"ffprobe failed for {media_path.name}: {e}")

    return None


def estimate_duration_from_size(file_path: Path) -> float:
    """Estimate media duration from file size.

    Fallback when ffprobe is unavailable. Uses different rates for audio/video:
    - Video: ~5 MB/min (83333 bytes/sec)
    - Audio: ~1 MB/min (16667 bytes/sec for 128kbps MP3)

    Args:
        file_path: Path to media file

    Returns:
        Estimated duration in seconds
    """
    file_size = file_path.stat().st_size

    if is_audio_file(file_path):
        # ~1 MB/min for 128kbps audio
        return file_size / 16667
    else:
        # ~5 MB/min for video
        return file_size / 83333
