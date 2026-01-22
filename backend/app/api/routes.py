"""
HTTP API routes for video processing pipeline.

Provides endpoints for:
- Listing inbox files
- Archive structure and results
"""

import json
import logging

from fastapi import APIRouter

from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["pipeline"])


@router.get("/inbox", response_model=list[str])
async def list_inbox_files() -> list[str]:
    """
    List video and audio files in inbox directory.

    Returns:
        List of media filenames (video: mp4, mkv, avi, mov, webm; audio: mp3, wav, m4a, flac, aac, ogg)
    """
    settings = get_settings()

    if not settings.inbox_dir.exists():
        return []

    extensions = {
        # Video formats
        ".mp4", ".mkv", ".avi", ".mov", ".webm",
        # Audio formats (for offsite events)
        ".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg",
    }
    files = [
        f.name
        for f in settings.inbox_dir.iterdir()
        if f.is_file() and f.suffix.lower() in extensions
    ]

    return sorted(files)


@router.get("/archive")
async def list_archive() -> dict:
    """
    List archive folder structure.

    Archive structure (4 levels):
    - Regular: archive/{year}/{event_type}/{MM.DD}/{topic_folder}/
    - Offsite: archive/{year}/Выездные/{event_name}/{topic_folder}/

    Returns:
        Tree structure: year -> event_folder -> items
        Each item contains: title, speaker, event_type, mid_folder
    """
    settings = get_settings()
    archive_dir = settings.archive_dir

    if not archive_dir.exists():
        return {"tree": {}, "total": 0}

    tree: dict = {}
    total = 0

    # Scan 4 levels: archive/{year}/{event_type}/{mid_folder}/{topic_folder}/
    for year_dir in sorted(archive_dir.iterdir(), reverse=True):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue

        year = year_dir.name
        tree[year] = {}

        for event_type_dir in sorted(year_dir.iterdir(), reverse=True):
            if not event_type_dir.is_dir():
                continue

            event_type = event_type_dir.name  # "ПШ", "Выездные"

            for mid_dir in sorted(event_type_dir.iterdir(), reverse=True):
                if not mid_dir.is_dir():
                    continue

                mid_folder = mid_dir.name  # "01.22" or "Форум Табтим"
                # Display key: "01.22 ПШ" or "Форум Табтим"
                event_folder = f"{mid_folder} {event_type}" if event_type != "Выездные" else mid_folder
                tree[year][event_folder] = []

                for topic_dir in sorted(mid_dir.iterdir()):
                    if not topic_dir.is_dir():
                        continue

                    # Parse topic folder: "[stream] title (speaker)" or "title (speaker)"
                    folder_name = topic_dir.name
                    speaker = None
                    title = folder_name

                    # Extract speaker from parentheses at the end
                    if "(" in folder_name and folder_name.endswith(")"):
                        idx = folder_name.rfind("(")
                        speaker = folder_name[idx + 1 : -1]
                        title = folder_name[:idx].strip()

                    tree[year][event_folder].append({
                        "title": title,
                        "speaker": speaker,
                        "event_type": event_type,
                        "mid_folder": mid_folder,
                    })
                    total += 1

    return {"tree": tree, "total": total}


@router.get("/archive/results")
async def get_archive_results(
    year: str,
    event_type: str,
    mid_folder: str,
    topic_folder: str,
) -> dict:
    """
    Get pipeline results for archived video.

    Reads pipeline_results.json from the archive folder if it exists.

    Args:
        year: Year folder (e.g., "2026")
        event_type: Event type folder (e.g., "ПШ", "Выездные")
        mid_folder: Date or event name folder (e.g., "01.22", "Форум Табтим")
        topic_folder: Topic folder (e.g., "SV Тестовая запись (Тест)")

    Returns:
        - {"available": true, "data": {...}} if file exists
        - {"available": false, "message": "..."} if file missing or read error
    """
    settings = get_settings()
    archive_path = settings.archive_dir / year / event_type / mid_folder / topic_folder
    results_file = archive_path / "pipeline_results.json"

    if not results_file.exists():
        logger.debug(f"Pipeline results not found: {results_file}")
        return {
            "available": False,
            "message": "Результаты обработки недоступны для этого файла",
        }

    try:
        with open(results_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to read pipeline results: {results_file}, error: {e}")
        return {
            "available": False,
            "message": "Ошибка чтения файла результатов",
        }

    return {"available": True, "data": data}
