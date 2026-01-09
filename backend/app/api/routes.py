"""
HTTP API routes for video processing pipeline.

Provides endpoints for:
- Starting full pipeline processing
- Querying job status
- Listing inbox files
"""

import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.config import get_settings
from app.models.schemas import (
    ProcessingJob,
    ProcessingResult,
    ProcessingStatus,
    ProcessRequest,
)
from app.services.job_manager import get_job_manager
from app.services.pipeline import PipelineError, PipelineOrchestrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["pipeline"])


async def run_pipeline(job_id: str, video_path: Path) -> None:
    """
    Background task to run pipeline processing.

    Args:
        job_id: Job identifier for progress updates
        video_path: Path to video file
    """
    job_manager = get_job_manager()
    settings = get_settings()
    orchestrator = PipelineOrchestrator(settings)

    async def progress_callback(
        status: ProcessingStatus,
        progress: float,
        message: str,
    ) -> None:
        """Forward progress to job manager."""
        await job_manager.update_progress(job_id, status, progress, message)

    try:
        result = await orchestrator.process(
            video_path=video_path,
            progress_callback=progress_callback,
        )
        await job_manager.complete_job(job_id, result)

    except PipelineError as e:
        await job_manager.fail_job(job_id, f"[{e.stage.value}] {e.message}")
    except Exception as e:
        logger.exception(f"Pipeline error for job {job_id}")
        await job_manager.fail_job(job_id, str(e))


@router.post("/process", response_model=ProcessingJob)
async def start_processing(
    request: ProcessRequest,
    background_tasks: BackgroundTasks,
) -> ProcessingJob:
    """
    Start video processing pipeline.

    Creates a new processing job and starts background processing.
    Use WebSocket /ws/{job_id} to receive real-time progress updates.

    Args:
        request: ProcessRequest with video_filename

    Returns:
        ProcessingJob with job_id for tracking

    Raises:
        404: Video file not found in inbox
    """
    settings = get_settings()
    video_path = settings.inbox_dir / request.video_filename

    if not video_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Video file not found: {request.video_filename}",
        )

    job_manager = get_job_manager()
    job = job_manager.create_job(video_path)

    background_tasks.add_task(run_pipeline, job.job_id, video_path)

    logger.info(f"Started processing job {job.job_id}: {request.video_filename}")
    return job


@router.get("/jobs/{job_id}", response_model=ProcessingJob)
async def get_job_status(job_id: str) -> ProcessingJob:
    """
    Get processing job status.

    Args:
        job_id: Job identifier

    Returns:
        ProcessingJob with current status

    Raises:
        404: Job not found
    """
    job_manager = get_job_manager()
    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}",
        )

    return job


@router.get("/jobs", response_model=list[ProcessingJob])
async def list_jobs() -> list[ProcessingJob]:
    """
    List all processing jobs.

    Returns:
        List of all ProcessingJob objects
    """
    job_manager = get_job_manager()
    return job_manager.list_jobs()


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
