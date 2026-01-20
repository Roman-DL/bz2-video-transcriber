"""
Cache API routes for stage result versioning.

Provides endpoints for:
- GET /api/cache/{video_id} - Get cache information for a video
- POST /api/cache/rerun - Re-run a pipeline stage
- POST /api/cache/version - Set current version for a stage
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.models.cache import (
    CacheInfo,
    CacheStageName,
    RerunRequest,
    RerunResponse,
)
from app.models.schemas import (
    CleanedTranscript,
    Longread,
    ProcessingStatus,
    RawTranscript,
    Summary,
    TranscriptChunks,
)
from app.services.pipeline import PipelineOrchestrator, StageResultCache
from app.services.progress_estimator import ProgressEstimator
from app.api.step_routes import run_with_sse_progress, create_sse_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cache", tags=["cache"])


def get_settings_instance():
    """Get settings instance."""
    return get_settings()


def get_orchestrator() -> PipelineOrchestrator:
    """Get pipeline orchestrator instance."""
    return PipelineOrchestrator(get_settings())


def get_cache() -> StageResultCache:
    """Get cache service instance."""
    return StageResultCache(get_settings())


def resolve_archive_path(video_id: str) -> Path | None:
    """Resolve video_id to archive path.

    Searches for existing archive directory matching the video_id.

    Args:
        video_id: Video identifier (e.g., "2025-01-09_ПШ-SV_topic")

    Returns:
        Path to archive directory or None if not found
    """
    settings = get_settings()
    archive_dir = settings.archive_dir

    # video_id format: YYYY-MM-DD_TYPE-STREAM_title
    # Archive path: archive/YYYY/MM.DD TYPE.STREAM/Title

    # Search in archive directory
    for year_dir in archive_dir.iterdir():
        if not year_dir.is_dir():
            continue
        for event_dir in year_dir.iterdir():
            if not event_dir.is_dir():
                continue
            for video_dir in event_dir.iterdir():
                if not video_dir.is_dir():
                    continue
                # Check if pipeline_results.json exists and matches video_id
                results_file = video_dir / "pipeline_results.json"
                if results_file.exists():
                    import json
                    try:
                        with open(results_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if data.get("metadata", {}).get("video_id") == video_id:
                            return video_dir
                    except Exception:
                        continue

    return None


@router.get("/{video_id}", response_model=CacheInfo)
async def get_cache_info(video_id: str) -> CacheInfo:
    """
    Get cache information for a video.

    Returns list of cached stages with versions and metadata.

    Args:
        video_id: Video identifier

    Returns:
        CacheInfo with stage versions

    Raises:
        404: Video not found in archive
    """
    archive_path = resolve_archive_path(video_id)

    if archive_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"Video not found: {video_id}",
        )

    cache = get_cache()
    return await cache.get_info(archive_path)


@router.post("/rerun", response_class=StreamingResponse)
async def rerun_stage(request: RerunRequest) -> StreamingResponse:
    """
    Re-run a pipeline stage with optional model override.

    Creates new version of the stage result and stores in cache.
    Returns SSE stream with progress updates.

    Args:
        request: RerunRequest with video_id, stage, and optional model

    Returns:
        StreamingResponse with SSE events:
        - {"type": "progress", ...}
        - {"type": "result", "data": RerunResponse}
        - {"type": "error", "error": "..."}

    Raises:
        404: Video not found
        400: Missing required input (previous stage not cached)
    """
    archive_path = resolve_archive_path(request.video_id)

    if archive_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"Video not found: {request.video_id}",
        )

    settings = get_settings_instance()
    orchestrator = get_orchestrator()
    cache = get_cache()
    estimator = ProgressEstimator(settings)

    # Load metadata from pipeline_results.json
    import json
    results_file = archive_path / "pipeline_results.json"
    with open(results_file, "r", encoding="utf-8") as f:
        pipeline_data = json.load(f)

    # Convert metadata to VideoMetadata
    from app.models.schemas import VideoMetadata
    from datetime import date

    meta_data = pipeline_data["metadata"]
    metadata = VideoMetadata(
        date=date.fromisoformat(meta_data["date"]),
        event_type=meta_data["event_type"],
        stream=meta_data["stream"],
        title=meta_data["title"],
        speaker=meta_data["speaker"],
        original_filename=meta_data["original_filename"],
        video_id=meta_data["video_id"],
        source_path=Path(meta_data["source_path"]),
        archive_path=Path(meta_data["archive_path"]),
        duration_seconds=meta_data.get("duration_seconds"),
    )

    # Map stage to ProcessingStatus and estimate
    stage_mapping = {
        CacheStageName.CLEANING: (ProcessingStatus.CLEANING, "clean"),
        CacheStageName.CHUNKING: (ProcessingStatus.CHUNKING, "chunk"),
        CacheStageName.LONGREAD: (ProcessingStatus.LONGREAD, "longread"),
        CacheStageName.SUMMARY: (ProcessingStatus.SUMMARIZING, "summarize"),
    }

    if request.stage not in stage_mapping:
        raise HTTPException(
            status_code=400,
            detail=f"Stage {request.stage.value} cannot be re-run",
        )

    processing_status, method_name = stage_mapping[request.stage]

    # Load input data based on stage
    async def run_rerun():
        """Execute rerun and cache result."""
        nonlocal metadata

        if request.stage == CacheStageName.CLEANING:
            # Input: RawTranscript
            raw_data = pipeline_data.get("raw_transcript")
            if not raw_data:
                raise ValueError("Raw transcript not found in pipeline results")

            raw_transcript = RawTranscript.model_validate(raw_data)
            input_hash = cache.compute_hash(raw_transcript)

            result = await orchestrator.clean(
                raw_transcript=raw_transcript,
                metadata=metadata,
                model=request.model,
            )

            model_name = request.model or settings.cleaner_model

        elif request.stage == CacheStageName.CHUNKING:
            # Input: CleanedTranscript
            cleaned_data = pipeline_data.get("cleaned_transcript")
            if not cleaned_data:
                raise ValueError("Cleaned transcript not found in pipeline results")

            cleaned_transcript = CleanedTranscript.model_validate(cleaned_data)
            input_hash = cache.compute_hash(cleaned_transcript)

            result = await orchestrator.chunk(
                cleaned_transcript=cleaned_transcript,
                metadata=metadata,
                model=request.model,
            )

            model_name = request.model or settings.chunker_model

        elif request.stage == CacheStageName.LONGREAD:
            # Input: TranscriptChunks
            chunks_data = pipeline_data.get("chunks")
            if not chunks_data:
                raise ValueError("Chunks not found in pipeline results")

            chunks = TranscriptChunks.model_validate(chunks_data)
            input_hash = cache.compute_hash(chunks)

            result = await orchestrator.longread(
                chunks=chunks,
                metadata=metadata,
                model=request.model,
            )

            model_name = request.model or settings.longread_model

        elif request.stage == CacheStageName.SUMMARY:
            # Input: Longread
            longread_data = pipeline_data.get("longread")
            if not longread_data:
                raise ValueError("Longread not found in pipeline results")

            longread = Longread.model_validate(longread_data)
            input_hash = cache.compute_hash(longread)

            result = await orchestrator.summarize_from_longread(
                longread=longread,
                metadata=metadata,
                model=request.model,
            )

            model_name = request.model or settings.summarizer_model

        else:
            raise ValueError(f"Unknown stage: {request.stage}")

        # Save to cache
        entry = await cache.save(
            archive_path=archive_path,
            stage=request.stage,
            result=result,
            model_name=model_name,
            input_hash=input_hash,
        )

        return RerunResponse(
            video_id=request.video_id,
            stage=request.stage.value,
            new_version=entry.version,
            model_name=model_name,
        )

    # Estimate time based on input size
    cleaned_data = pipeline_data.get("cleaned_transcript", {})
    input_chars = len(cleaned_data.get("text", "")) or 10000

    if request.stage == CacheStageName.CLEANING:
        estimate = estimator.estimate_clean(input_chars)
    elif request.stage == CacheStageName.CHUNKING:
        estimate = estimator.estimate_chunk(input_chars)
    else:
        estimate = estimator.estimate_summarize(input_chars)

    return create_sse_response(
        run_with_sse_progress(
            stage=processing_status,
            estimator=estimator,
            estimated_seconds=estimate.estimated_seconds,
            message=f"Re-running {request.stage.value}",
            operation=run_rerun,
        )
    )


class SetVersionRequest(RerunRequest):
    """Request to set current version."""

    version: int


@router.post("/version")
async def set_current_version(
    video_id: str,
    stage: CacheStageName,
    version: int,
) -> dict:
    """
    Set specific version as current for a stage.

    Args:
        video_id: Video identifier
        stage: Stage name
        version: Version number to activate

    Returns:
        Success status

    Raises:
        404: Video or version not found
    """
    archive_path = resolve_archive_path(video_id)

    if archive_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"Video not found: {video_id}",
        )

    cache = get_cache()
    result = await cache.set_current_version(archive_path, stage, version)

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Version {version} not found for stage {stage.value}",
        )

    return {"status": "ok", "stage": stage.value, "version": version}


@router.get("/{video_id}/{stage}")
async def get_cached_result(
    video_id: str,
    stage: CacheStageName,
    version: int | None = None,
) -> dict:
    """
    Get cached result for a stage.

    Args:
        video_id: Video identifier
        stage: Stage name
        version: Version number (None = current)

    Returns:
        Cached result data

    Raises:
        404: Video or cache not found
    """
    archive_path = resolve_archive_path(video_id)

    if archive_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"Video not found: {video_id}",
        )

    cache = get_cache()
    result = await cache.load(archive_path, stage, version)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Cache not found for {stage.value}" +
                   (f" v{version}" if version else ""),
        )

    return result
