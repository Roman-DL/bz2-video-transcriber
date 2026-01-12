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

# Compatible versions for pipeline_results.json
COMPATIBLE_VERSIONS = ["1.0.0"]

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["pipeline"])


@router.get("/inbox", response_model=list[str])
async def list_inbox_files() -> list[str]:
    """
    List video files in inbox directory.

    Returns:
        List of video filenames (mp4, mkv, avi, mov)
    """
    settings = get_settings()

    if not settings.inbox_dir.exists():
        return []

    extensions = {".mp4", ".mkv", ".avi", ".mov", ".webm"}
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

    Archive structure: archive/{year}/{MM.DD event_type}/{[stream] title (speaker)}/

    Returns:
        Tree structure: year -> event_folder -> items
    """
    settings = get_settings()
    archive_dir = settings.archive_dir

    if not archive_dir.exists():
        return {"tree": {}, "total": 0}

    tree: dict = {}
    total = 0

    # Scan: archive/{year}/{event_folder}/{topic_folder}/
    for year_dir in sorted(archive_dir.iterdir(), reverse=True):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue

        year = year_dir.name
        tree[year] = {}

        for event_dir in sorted(year_dir.iterdir(), reverse=True):
            if not event_dir.is_dir():
                continue

            event_folder = event_dir.name  # e.g., "12.22 ПШ"
            tree[year][event_folder] = []

            for topic_dir in sorted(event_dir.iterdir()):
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

                tree[year][event_folder].append({"title": title, "speaker": speaker})
                total += 1

    return {"tree": tree, "total": total}


@router.get("/archive/results")
async def get_archive_results(year: str, event_folder: str, topic_folder: str) -> dict:
    """
    Get pipeline results for archived video.

    Reads pipeline_results.json from the archive folder if it exists
    and the version is compatible.

    Args:
        year: Year folder (e.g., "2025")
        event_folder: Event folder (e.g., "12.22 ПШ")
        topic_folder: Topic folder (e.g., "SV Закрытие ПО (Кухаренко Женя)")

    Returns:
        - {"available": true, "data": {...}} if file exists and version compatible
        - {"available": false, "message": "..."} if file missing or version incompatible
    """
    settings = get_settings()
    archive_path = settings.archive_dir / year / event_folder / topic_folder
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

    # Check version compatibility
    version = data.get("version", "unknown")
    if version not in COMPATIBLE_VERSIONS:
        logger.info(f"Incompatible version {version} in {results_file}")
        return {
            "available": False,
            "message": f"Формат устарел (v{version}). Поддерживаются версии: {', '.join(COMPATIBLE_VERSIONS)}",
        }

    return {"available": True, "data": data}
