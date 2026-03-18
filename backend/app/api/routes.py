"""
HTTP API routes for video processing pipeline.

Provides endpoints for:
- Listing inbox files
- Archive structure and results
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.models.schemas import (
    ArchiveItem,
    ArchiveResponse,
    PipelineResults,
    PipelineResultsResponse,
)

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
        # Transcript formats (v0.64+: MD from MacWhisper)
        ".md",
    }
    files = [
        f.name
        for f in settings.inbox_dir.iterdir()
        if f.is_file() and f.suffix.lower() in extensions
    ]

    return sorted(files)


@router.get("/archive")
async def list_archive() -> ArchiveResponse:
    """
    List archive folder structure.

    Archive structure (3 levels):
    - Regular: archive/{year}/{event_type}/{date_prefix topic (speaker)}/
    - Offsite: archive/{year}/{MM event_type}/{topic (speaker)}/

    Returns:
        ArchiveResponse with tree structure: year -> event_group -> items
    """
    settings = get_settings()
    archive_dir = settings.archive_dir

    if not archive_dir.exists():
        return ArchiveResponse(tree={}, total=0, published_total=0)

    tree: dict[str, dict[str, list[ArchiveItem]]] = {}
    total = 0
    published_total = 0

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

                published = (topic_dir / ".published").exists()

                tree[year][event_group].append(
                    ArchiveItem(
                        title=title,
                        speaker=speaker,
                        event_type=event_group,
                        topic_folder=folder_name,
                        published=published,
                    )
                )
                total += 1
                if published:
                    published_total += 1

    return ArchiveResponse(tree=tree, total=total, published_total=published_total)


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


@router.put("/archive/published")
async def set_published(year: str, event_group: str, topic_folder: str):
    """Mark archive material as published to knowledge base."""
    settings = get_settings()
    target = _resolve_archive_path(
        Path(settings.archive_dir), year, event_group, topic_folder
    )
    (target / ".published").touch()
    return {"status": "ok"}


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
