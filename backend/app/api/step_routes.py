"""
Step-by-step API routes with SSE progress tracking.

Allows individual execution of each pipeline stage with real-time progress
updates via Server-Sent Events (SSE).

Each endpoint returns StreamingResponse with progress events and final result.
"""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, Awaitable, Callable, TypeVar

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.models.schemas import (
    CleanedTranscript,
    ProcessingStatus,
    RawTranscript,
    StepChunkRequest,
    StepCleanRequest,
    StepParseRequest,
    StepSaveRequest,
    StepSummarizeRequest,
    TranscriptChunks,
    VideoMetadata,
    VideoSummary,
)
from app.services.pipeline import PipelineOrchestrator, get_video_duration
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
        - Progress: {"type": "progress", "status": "...", "progress": 45.5, "message": "..."}
        - Result: {"type": "result", "data": {...}}
        - Error: {"type": "error", "error": "..."}
    """
    progress_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    result_holder: list[Any] = []
    error_holder: list[Exception] = []

    async def progress_callback(
        status: ProcessingStatus, progress: float, msg: str
    ) -> None:
        await progress_queue.put(
            {
                "type": "progress",
                "status": status.value,
                "progress": round(progress, 1),
                "message": msg,
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
        # Stop ticker
        await estimator.stop_ticker(ticker, stage, progress_callback, "Complete")

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
        # Handle Pydantic models
        if hasattr(result, "model_dump"):
            data = result.model_dump()
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
        return metadata
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transcribe")
async def step_transcribe(request: StepParseRequest) -> StreamingResponse:
    """
    Transcribe video using Whisper API with SSE progress.

    Returns SSE stream with progress updates and final RawTranscript.

    Args:
        request: StepParseRequest with video_filename

    Returns:
        StreamingResponse with SSE events:
        - {"type": "progress", "status": "transcribing", "progress": 45.5, "message": "..."}
        - {"type": "result", "data": RawTranscript}
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
    duration = get_video_duration(video_path)
    if duration is None:
        # Fallback: estimate from file size (~5MB per minute)
        duration = video_path.stat().st_size / 83333

    estimate = estimator.estimate_transcribe(duration)

    return create_sse_response(
        run_with_sse_progress(
            stage=ProcessingStatus.TRANSCRIBING,
            estimator=estimator,
            estimated_seconds=estimate.estimated_seconds,
            message=f"Transcribing: {request.video_filename}",
            operation=lambda: orchestrator.transcribe(video_path),
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
            ),
        )
    )


@router.post("/chunk")
async def step_chunk(request: StepChunkRequest) -> StreamingResponse:
    """
    Split cleaned transcript into semantic chunks with SSE progress.

    Returns SSE stream with progress updates and final TranscriptChunks.

    Args:
        request: StepChunkRequest with cleaned_transcript and metadata

    Returns:
        StreamingResponse with SSE events
    """
    settings = get_settings()
    orchestrator = get_orchestrator()
    estimator = ProgressEstimator(settings)

    # Calculate input size for time estimation
    input_chars = len(request.cleaned_transcript.text)
    estimate = estimator.estimate_chunk(input_chars)

    return create_sse_response(
        run_with_sse_progress(
            stage=ProcessingStatus.CHUNKING,
            estimator=estimator,
            estimated_seconds=estimate.estimated_seconds,
            message=f"Chunking {input_chars:,} chars",
            operation=lambda: orchestrator.chunk(
                cleaned_transcript=request.cleaned_transcript,
                metadata=request.metadata,
            ),
        )
    )


@router.post("/summarize")
async def step_summarize(request: StepSummarizeRequest) -> StreamingResponse:
    """
    Create structured summary from cleaned transcript with SSE progress.

    Supports different prompt files for A/B testing.

    Args:
        request: StepSummarizeRequest with cleaned_transcript, metadata, and prompt_name

    Returns:
        StreamingResponse with SSE events

    Example:
        Test different prompts by changing prompt_name:
        - "summarizer" (default)
        - "summarizer_v2"
        - "summarizer_detailed"
    """
    settings = get_settings()
    orchestrator = get_orchestrator()
    estimator = ProgressEstimator(settings)

    # Calculate input size for time estimation
    input_chars = len(request.cleaned_transcript.text)
    estimate = estimator.estimate_summarize(input_chars)

    return create_sse_response(
        run_with_sse_progress(
            stage=ProcessingStatus.SUMMARIZING,
            estimator=estimator,
            estimated_seconds=estimate.estimated_seconds,
            message=f"Summarizing {input_chars:,} chars",
            operation=lambda: orchestrator.summarize(
                cleaned_transcript=request.cleaned_transcript,
                metadata=request.metadata,
                prompt_name=request.prompt_name,
            ),
        )
    )


@router.post("/save", response_model=list[str])
async def step_save(request: StepSaveRequest) -> list[str]:
    """
    Save all processing results to archive.

    Fast operation - no SSE needed.

    Args:
        request: StepSaveRequest with all pipeline outputs

    Returns:
        List of created file names

    Raises:
        500: Save error
    """
    orchestrator = get_orchestrator()

    try:
        files = await orchestrator.save(
            metadata=request.metadata,
            raw_transcript=request.raw_transcript,
            chunks=request.chunks,
            summary=request.summary,
        )
        return files
    except Exception as e:
        logger.exception("Save error")
        raise HTTPException(status_code=500, detail=str(e))
