"""
HTTP API routes for video processing pipeline.

Provides endpoints for:
- Listing inbox files
"""

import logging

from fastapi import APIRouter

from app.config import get_settings

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
