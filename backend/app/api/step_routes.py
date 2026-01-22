"""
Step-by-step API routes with SSE progress tracking.

Allows individual execution of each pipeline stage with real-time progress
updates via Server-Sent Events (SSE).

Each endpoint returns StreamingResponse with progress events and final result.
"""

import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, Awaitable, Callable, TypeVar

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.models.schemas import (
    CleanedTranscript,
    Longread,
    ProcessingStatus,
    RawTranscript,
    SlidesExtractionResult,
    StepChunkRequest,
    StepCleanRequest,
    StepLongreadRequest,
    StepParseRequest,
    StepSaveRequest,
    StepSlidesRequest,
    StepStoryRequest,
    StepSummarizeRequest,
    Story,
    Summary,
    TranscriptChunks,
    VideoMetadata,
)
from app.services.ai_clients import ClaudeClient
from app.services.pipeline import PipelineOrchestrator
from app.services.slides_extractor import SlidesExtractor
from app.utils import get_media_duration
from app.services.progress_estimator import ProgressEstimator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/step", tags=["step-by-step"])

T = TypeVar("T")


def get_orchestrator() -> PipelineOrchestrator:
    """Get pipeline orchestrator instance."""
    return PipelineOrchestrator(get_settings())


# ═══════════════════════════════════════════════════════════════════════════════
# SSE Progress Generator
# ═══════════════════════════════════════════════════════════════════════════════


async def run_with_sse_progress(
    stage: ProcessingStatus,
    estimator: ProgressEstimator,
    estimated_seconds: float,
    message: str,
    operation: Callable[[], Awaitable[T]],
) -> AsyncGenerator[str, None]:
    """
    Run async operation with SSE progress updates.

    Starts a ticker that sends progress updates every second while
    the operation is running. When complete, sends final result.

    Args:
        stage: Processing stage for progress status
        estimator: ProgressEstimator for ticker management
        estimated_seconds: Estimated operation duration
        message: Human-readable progress message
        operation: Async function to execute

    Yields:
        SSE events in format "data: {...}\\n\\n":
        - Progress: {"type": "progress", "status": "...", "progress": 45.5, "message": "...",
                    "estimated_seconds": 100.0, "elapsed_seconds": 45.5}
        - Result: {"type": "result", "data": {...}}
        - Error: {"type": "error", "error": "..."}
    """
    progress_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    result_holder: list[Any] = []
    error_holder: list[Exception] = []
    start_time = time.time()

    async def progress_callback(
        status: ProcessingStatus,
        progress: float,
        msg: str,
        est_seconds: float,
        elapsed_seconds: float,
    ) -> None:
        await progress_queue.put(
            {
                "type": "progress",
                "status": status.value,
                "progress": round(progress, 1),
                "message": msg,
                "estimated_seconds": round(est_seconds, 1),
                "elapsed_seconds": round(elapsed_seconds, 1),
            }
        )

    async def run_operation() -> None:
        try:
            result = await operation()
            result_holder.append(result)
        except Exception as e:
            logger.exception(f"Operation error in {stage.value}")
            error_holder.append(e)
        finally:
            await progress_queue.put({"type": "done"})

    # Start ticker and operation in parallel
    ticker = await estimator.start_ticker(
        stage=stage,
        estimated_seconds=estimated_seconds,
        message=message,
        callback=progress_callback,
    )

    operation_task = asyncio.create_task(run_operation())

    # Yield progress events while operation runs
    try:
        while True:
            try:
                event = await asyncio.wait_for(progress_queue.get(), timeout=2.0)
            except asyncio.TimeoutError:
                # No event received, continue waiting
                continue

            if event["type"] == "done":
                break

            yield f"data: {json.dumps(event)}\n\n"
    finally:
        # Stop ticker with actual elapsed time
        actual_seconds = time.time() - start_time
        await estimator.stop_ticker(
            ticker,
            stage,
            progress_callback,
            "Complete",
            estimated_seconds=estimated_seconds,
            actual_seconds=actual_seconds,
        )

        # Cancel task if still running
        if not operation_task.done():
            operation_task.cancel()
            try:
                await operation_task
            except asyncio.CancelledError:
                pass

    # Send final result or error
    if error_holder:
        yield f"data: {json.dumps({'type': 'error', 'error': str(error_holder[0])})}\n\n"
    elif result_holder:
        result = result_holder[0]
        # Handle different result types
        if hasattr(result, "model_dump"):
            data = result.model_dump(mode='json')
        elif isinstance(result, dict):
            data = result
        elif isinstance(result, list):
            data = result
        else:
            data = str(result)
        yield f"data: {json.dumps({'type': 'result', 'data': data})}\n\n"
    else:
        yield f"data: {json.dumps({'type': 'error', 'error': 'No result'})}\n\n"


def create_sse_response(generator: AsyncGenerator[str, None]) -> StreamingResponse:
    """Create SSE StreamingResponse with proper headers."""
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Step Endpoints with SSE Progress
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/parse", response_model=VideoMetadata)
async def step_parse(request: StepParseRequest) -> VideoMetadata:
    """
    Parse video filename to extract metadata.

    Synchronous operation (fast) - no SSE needed.

    Args:
        request: StepParseRequest with video_filename

    Returns:
        VideoMetadata with parsed fields

    Raises:
        400: Invalid filename format
        404: Video file not found
    """
    settings = get_settings()
    video_path = settings.inbox_dir / request.video_filename

    if not video_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Video file not found: {request.video_filename}",
        )

    orchestrator = get_orchestrator()

    try:
        metadata = orchestrator.parse(video_path)
        # Add video duration for UI display
        metadata.duration_seconds = get_media_duration(video_path)
        if metadata.duration_seconds is None:
            # Fallback: estimate from file size (~5MB per minute)
            metadata.duration_seconds = video_path.stat().st_size / 83333
        return metadata
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transcribe")
async def step_transcribe(request: StepParseRequest) -> StreamingResponse:
    """
    Transcribe video using Whisper API with SSE progress.

    Extracts audio from video first, then sends to Whisper.
    Returns SSE stream with progress updates and final result containing
    RawTranscript and audio_path.

    Args:
        request: StepParseRequest with video_filename

    Returns:
        StreamingResponse with SSE events:
        - {"type": "progress", "status": "transcribing", "progress": 45.5, "message": "..."}
        - {"type": "result", "data": {"raw_transcript": RawTranscript, "audio_path": "..."}}
        - {"type": "error", "error": "..."}

    Raises:
        404: Video file not found
    """
    settings = get_settings()
    video_path = settings.inbox_dir / request.video_filename

    if not video_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Video file not found: {request.video_filename}",
        )

    orchestrator = get_orchestrator()
    estimator = ProgressEstimator(settings)

    # Get video duration for time estimation
    duration = get_media_duration(video_path)
    if duration is None:
        # Fallback: estimate from file size (~5MB per minute)
        duration = video_path.stat().st_size / 83333

    estimate = estimator.estimate_transcribe(duration)

    async def transcribe_and_wrap():
        """Wrap transcribe result to include audio_path and display_text."""
        settings = get_settings()
        transcript, audio_path = await orchestrator.transcribe(video_path)
        # Choose display format based on settings
        display_text = (
            transcript.text_with_timestamps
            if settings.whisper_include_timestamps
            else transcript.full_text
        )
        return {
            "raw_transcript": transcript.model_dump(mode='json'),
            "audio_path": str(audio_path),
            "display_text": display_text,
        }

    return create_sse_response(
        run_with_sse_progress(
            stage=ProcessingStatus.TRANSCRIBING,
            estimator=estimator,
            estimated_seconds=estimate.estimated_seconds,
            message=f"Transcribing: {request.video_filename}",
            operation=transcribe_and_wrap,
        )
    )


@router.post("/clean")
async def step_clean(request: StepCleanRequest) -> StreamingResponse:
    """
    Clean raw transcript using glossary and LLM with SSE progress.

    Returns SSE stream with progress updates and final CleanedTranscript.

    Args:
        request: StepCleanRequest with raw_transcript and metadata

    Returns:
        StreamingResponse with SSE events
    """
    settings = get_settings()
    orchestrator = get_orchestrator()
    estimator = ProgressEstimator(settings)

    # Calculate input size for time estimation
    input_chars = len(request.raw_transcript.full_text)
    estimate = estimator.estimate_clean(input_chars)

    return create_sse_response(
        run_with_sse_progress(
            stage=ProcessingStatus.CLEANING,
            estimator=estimator,
            estimated_seconds=estimate.estimated_seconds,
            message=f"Cleaning {input_chars:,} chars",
            operation=lambda: orchestrator.clean(
                raw_transcript=request.raw_transcript,
                metadata=request.metadata,
                model=request.model,
                prompt_overrides=request.prompt_overrides,
            ),
        )
    )


@router.post("/slides")
async def step_slides(request: StepSlidesRequest) -> StreamingResponse:
    """
    Extract text from slides using vision API with SSE progress.

    v0.50+: Processes uploaded slides (images/PDFs) and extracts
    structured text using Claude Vision API.

    Args:
        request: StepSlidesRequest with slides and optional model override

    Returns:
        StreamingResponse with SSE events -> SlidesExtractionResult
    """
    settings = get_settings()
    estimator = ProgressEstimator(settings)

    # Estimate time based on slide count
    slides_count = len(request.slides)
    # Approximately 3 seconds per slide for Haiku
    estimated_seconds = slides_count * 3.0

    async def extract_slides() -> SlidesExtractionResult:
        async with ClaudeClient.from_settings(settings) as client:
            extractor = SlidesExtractor(
                client,
                settings,
                prompt_overrides=request.prompt_overrides,
            )
            return await extractor.extract(
                slides=request.slides,
                model=request.model,
            )

    return create_sse_response(
        run_with_sse_progress(
            stage=ProcessingStatus.SLIDES,
            estimator=estimator,
            estimated_seconds=estimated_seconds,
            message=f"Extracting text from {slides_count} slides",
            operation=extract_slides,
        )
    )


@router.post("/chunk", response_model=TranscriptChunks)
async def step_chunk(request: StepChunkRequest) -> TranscriptChunks:
    """
    Chunk markdown by H2 headers (deterministic).

    v0.25+: No LLM needed - instant operation that parses H2 headers
    from longread/story markdown. No SSE needed as it's instant.

    Args:
        request: StepChunkRequest with markdown_content and metadata

    Returns:
        TranscriptChunks with H2-based chunks
    """
    orchestrator = get_orchestrator()

    chunks = orchestrator.chunk(
        markdown_content=request.markdown_content,
        metadata=request.metadata,
    )

    return chunks


@router.post("/longread")
async def step_longread(request: StepLongreadRequest) -> StreamingResponse:
    """
    Generate longread document from cleaned transcript with SSE progress.

    v0.25+: Now takes CleanedTranscript instead of chunks.
    Creates a structured longread with introduction, sections, and conclusion.

    Args:
        request: StepLongreadRequest with cleaned_transcript and metadata

    Returns:
        StreamingResponse with SSE events -> Longread
    """
    settings = get_settings()
    orchestrator = get_orchestrator()
    estimator = ProgressEstimator(settings)

    # Calculate input size for time estimation
    input_chars = len(request.cleaned_transcript.text)
    estimate = estimator.estimate_summarize(input_chars)
    estimated_seconds = estimate.estimated_seconds * 1.5  # Longread takes longer

    return create_sse_response(
        run_with_sse_progress(
            stage=ProcessingStatus.LONGREAD,
            estimator=estimator,
            estimated_seconds=estimated_seconds,
            message=f"Generating longread from {input_chars:,} chars",
            operation=lambda: orchestrator.longread(
                cleaned_transcript=request.cleaned_transcript,
                metadata=request.metadata,
                model=request.model,
                prompt_overrides=request.prompt_overrides,
                slides_text=request.slides_text,  # v0.50+
            ),
        )
    )


@router.post("/summarize")
async def step_summarize(request: StepSummarizeRequest) -> StreamingResponse:
    """
    Generate summary (конспект) from cleaned transcript with SSE progress.

    Updated in v0.24: Now takes CleanedTranscript instead of Longread.
    Summary is generated directly from the cleaned transcript.

    Args:
        request: StepSummarizeRequest with cleaned_transcript and metadata

    Returns:
        StreamingResponse with SSE events -> Summary
    """
    settings = get_settings()
    orchestrator = get_orchestrator()
    estimator = ProgressEstimator(settings)

    # Calculate input size for time estimation
    input_chars = len(request.cleaned_transcript.text)
    estimate = estimator.estimate_summarize(input_chars)
    estimated_seconds = estimate.estimated_seconds * 0.5  # Summary is faster

    return create_sse_response(
        run_with_sse_progress(
            stage=ProcessingStatus.SUMMARIZING,
            estimator=estimator,
            estimated_seconds=estimated_seconds,
            message=f"Generating summary from transcript ({input_chars:,} chars)",
            operation=lambda: orchestrator.summarize_from_cleaned(
                cleaned_transcript=request.cleaned_transcript,
                metadata=request.metadata,
                model=request.model,
                prompt_overrides=request.prompt_overrides,
            ),
        )
    )


@router.post("/story")
async def step_story(request: StepStoryRequest) -> StreamingResponse:
    """
    Generate leadership story (8 blocks) from cleaned transcript with SSE progress.

    For content_type=LEADERSHIP only. Creates a structured story with 8 fixed blocks.

    Args:
        request: StepStoryRequest with cleaned_transcript and metadata

    Returns:
        StreamingResponse with SSE events -> Story
    """
    settings = get_settings()
    orchestrator = get_orchestrator()
    estimator = ProgressEstimator(settings)

    # Calculate input size for time estimation
    input_chars = len(request.cleaned_transcript.text)
    estimate = estimator.estimate_summarize(input_chars)
    estimated_seconds = estimate.estimated_seconds * 1.2  # Story is slightly longer

    return create_sse_response(
        run_with_sse_progress(
            stage=ProcessingStatus.STORY,
            estimator=estimator,
            estimated_seconds=estimated_seconds,
            message=f"Generating story from {input_chars:,} chars",
            operation=lambda: orchestrator.story(
                cleaned_transcript=request.cleaned_transcript,
                metadata=request.metadata,
                model=request.model,
                prompt_overrides=request.prompt_overrides,
            ),
        )
    )


@router.post("/save", response_model=list[str])
async def step_save(request: StepSaveRequest) -> list[str]:
    """
    Save all processing results to archive.

    Updated in v0.23: Supports both educational (longread+summary) and leadership (story).
    Fast operation - no SSE needed.

    Args:
        request: StepSaveRequest with all pipeline outputs

    Returns:
        List of created file names

    Raises:
        500: Save error
    """
    orchestrator = get_orchestrator()

    # Convert audio_path string to Path if provided
    audio_path = Path(request.audio_path) if request.audio_path else None

    try:
        files = await orchestrator.save(
            metadata=request.metadata,
            raw_transcript=request.raw_transcript,
            cleaned_transcript=request.cleaned_transcript,
            chunks=request.chunks,
            longread=request.longread,
            summary=request.summary,
            story=request.story,
            audio_path=audio_path,
        )
        return files
    except Exception as e:
        logger.exception("Save error")
        raise HTTPException(status_code=500, detail=str(e))
