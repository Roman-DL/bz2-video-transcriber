"""
Step-by-step API routes for pipeline testing.

Allows individual execution of each pipeline stage for:
- Testing different prompts/glossaries
- Debugging specific stages
- Manual pipeline control

Each endpoint directly calls PipelineOrchestrator methods.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.models.schemas import (
    CleanedTranscript,
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
from app.services.pipeline import PipelineOrchestrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/step", tags=["step-by-step"])


def get_orchestrator() -> PipelineOrchestrator:
    """Get pipeline orchestrator instance."""
    return PipelineOrchestrator(get_settings())


@router.post("/parse", response_model=VideoMetadata)
async def step_parse(request: StepParseRequest) -> VideoMetadata:
    """
    Parse video filename to extract metadata.

    Synchronous operation (fast).

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


@router.post("/transcribe", response_model=RawTranscript)
async def step_transcribe(request: StepParseRequest) -> RawTranscript:
    """
    Transcribe video using Whisper API.

    This is a long-running operation (depends on video length).
    Consider using the full pipeline with WebSocket for progress tracking.

    Args:
        request: StepParseRequest with video_filename

    Returns:
        RawTranscript with segments and metadata

    Raises:
        404: Video file not found
        500: Transcription error
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
        raw_transcript = await orchestrator.transcribe(video_path)
        return raw_transcript
    except Exception as e:
        logger.exception(f"Transcription error: {request.video_filename}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clean", response_model=CleanedTranscript)
async def step_clean(request: StepCleanRequest) -> CleanedTranscript:
    """
    Clean raw transcript using glossary and LLM.

    Args:
        request: StepCleanRequest with raw_transcript and metadata

    Returns:
        CleanedTranscript with cleaned text

    Raises:
        500: Cleaning error
    """
    orchestrator = get_orchestrator()

    try:
        cleaned = await orchestrator.clean(
            raw_transcript=request.raw_transcript,
            metadata=request.metadata,
        )
        return cleaned
    except Exception as e:
        logger.exception("Cleaning error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chunk", response_model=TranscriptChunks)
async def step_chunk(request: StepChunkRequest) -> TranscriptChunks:
    """
    Split cleaned transcript into semantic chunks.

    Args:
        request: StepChunkRequest with cleaned_transcript and metadata

    Returns:
        TranscriptChunks with semantic chunks

    Raises:
        500: Chunking error
    """
    orchestrator = get_orchestrator()

    try:
        chunks = await orchestrator.chunk(
            cleaned_transcript=request.cleaned_transcript,
            metadata=request.metadata,
        )
        return chunks
    except Exception as e:
        logger.exception("Chunking error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summarize", response_model=VideoSummary)
async def step_summarize(request: StepSummarizeRequest) -> VideoSummary:
    """
    Create structured summary from cleaned transcript.

    Supports different prompt files for A/B testing.

    Args:
        request: StepSummarizeRequest with cleaned_transcript, metadata, and prompt_name

    Returns:
        VideoSummary with structured content

    Raises:
        500: Summarization error

    Example:
        Test different prompts by changing prompt_name:
        - "summarizer" (default)
        - "summarizer_v2"
        - "summarizer_detailed"
    """
    orchestrator = get_orchestrator()

    try:
        summary = await orchestrator.summarize(
            cleaned_transcript=request.cleaned_transcript,
            metadata=request.metadata,
            prompt_name=request.prompt_name,
        )
        return summary
    except Exception as e:
        logger.exception(f"Summarization error with prompt {request.prompt_name}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save", response_model=list[str])
async def step_save(request: StepSaveRequest) -> list[str]:
    """
    Save all processing results to archive.

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
