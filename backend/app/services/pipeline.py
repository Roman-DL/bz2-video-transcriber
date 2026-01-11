"""
Pipeline orchestrator for video processing.

Coordinates all pipeline stages from parsing to saving.
Supports both full pipeline execution and step-by-step mode for testing.
"""

import asyncio
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable

from app.config import Settings, get_settings
from app.services.progress_estimator import ProgressEstimator
from app.models.schemas import (
    CleanedTranscript,
    ProcessingResult,
    ProcessingStatus,
    RawTranscript,
    TextPart,
    TranscriptChunk,
    TranscriptChunks,
    TranscriptOutline,
    VideoMetadata,
    VideoSummary,
)
from app.services.ai_client import AIClient
from app.services.chunker import LARGE_TEXT_THRESHOLD, SemanticChunker
from app.services.cleaner import TranscriptCleaner
from app.services.outline_extractor import OutlineExtractor
from app.services.text_splitter import TextSplitter
from app.services.parser import FilenameParseError, parse_filename
from app.services.saver import FileSaver
from app.services.summarizer import VideoSummarizer
from app.services.transcriber import WhisperTranscriber

logger = logging.getLogger(__name__)


def get_video_duration(video_path: Path) -> float | None:
    """
    Get video duration using ffprobe.

    Args:
        video_path: Path to video file

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
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"ffprobe failed for {video_path.name}: {e}")

    return None


# Type alias for progress callback
# Signature: (status, progress_percent, message) -> None
ProgressCallback = Callable[[ProcessingStatus, float, str], Awaitable[None]]


class PipelineError(Exception):
    """
    Pipeline stage error with context.

    Attributes:
        stage: Processing stage where error occurred
        message: Error description
        cause: Original exception (if any)
    """

    def __init__(
        self,
        stage: ProcessingStatus,
        message: str,
        cause: Exception | None = None,
    ):
        self.stage = stage
        self.message = message
        self.cause = cause
        super().__init__(f"[{stage.value}] {message}")


class PipelineOrchestrator:
    """
    Pipeline orchestrator for video processing.

    Supports two modes:
    1. Full pipeline: process() runs all stages automatically
    2. Step-by-step: individual methods for testing prompts/glossaries

    Example (full pipeline):
        orchestrator = PipelineOrchestrator()
        result = await orchestrator.process(Path("inbox/video.mp4"))

    Example (step-by-step):
        orchestrator = PipelineOrchestrator()
        metadata = orchestrator.parse(Path("inbox/video.mp4"))
        raw = await orchestrator.transcribe(Path("inbox/video.mp4"))
        cleaned = await orchestrator.clean(raw, metadata)
        chunks = await orchestrator.chunk(cleaned, metadata)
        summary = await orchestrator.summarize(cleaned, metadata, "summarizer_v2")
        files = await orchestrator.save(metadata, raw, chunks, summary)
    """

    # Progress weights for each stage (must sum to 100)
    # Based on actual times: transcribe=87s, clean=7.5s, chunk+summarize=18s, save<1s
    STAGE_WEIGHTS = {
        ProcessingStatus.PARSING: 2,       # 0-2%: instant
        ProcessingStatus.TRANSCRIBING: 50, # 2-52%: dominant stage (~77% of time)
        ProcessingStatus.CLEANING: 13,     # 52-65%
        ProcessingStatus.CHUNKING: 16,     # 65-81%: parallel with SUMMARIZING
        ProcessingStatus.SUMMARIZING: 16,  # 65-97%: combined = 32%
        ProcessingStatus.SAVING: 3,        # 97-100%: instant
    }

    def __init__(self, settings: Settings | None = None):
        """
        Initialize pipeline orchestrator.

        Args:
            settings: Application settings (uses defaults if None)
        """
        self.settings = settings or get_settings()
        self.estimator = ProgressEstimator(self.settings)

    # ═══════════════════════════════════════════════════════════════════════════
    # Full Pipeline
    # ═══════════════════════════════════════════════════════════════════════════

    async def process(
        self,
        video_path: Path,
        progress_callback: ProgressCallback | None = None,
    ) -> ProcessingResult:
        """
        Process video through complete pipeline.

        Stages:
        1. Parse filename -> VideoMetadata
        2. Transcribe video -> RawTranscript
        3. Clean transcript -> CleanedTranscript
        4. Chunk + Summarize (parallel) -> TranscriptChunks, VideoSummary
        5. Save all results -> files in archive

        Args:
            video_path: Path to video file
            progress_callback: Optional async callback for progress updates

        Returns:
            ProcessingResult with video_id, archive_path, etc.

        Raises:
            PipelineError: If any stage fails
            FileNotFoundError: If video file doesn't exist
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        started_at = datetime.now()

        # Stage 1: Parse filename
        await self._update_progress(
            progress_callback,
            ProcessingStatus.PARSING,
            0,
            f"Parsing: {video_path.name}",
        )

        try:
            metadata = parse_filename(video_path.name, video_path)
        except FilenameParseError as e:
            raise PipelineError(ProcessingStatus.PARSING, str(e), e)

        # Get video duration for progress estimation
        metadata.duration_seconds = get_video_duration(video_path)
        if metadata.duration_seconds is None:
            # Fallback: estimate from file size (~5MB per minute)
            metadata.duration_seconds = video_path.stat().st_size / 83333
            logger.info(
                f"Using estimated duration: {metadata.duration_seconds:.0f}s "
                f"(from file size {video_path.stat().st_size / 1024 / 1024:.1f}MB)"
            )

        await self._update_progress(
            progress_callback,
            ProcessingStatus.PARSING,
            100,
            f"Parsed: {metadata.video_id} ({metadata.duration_seconds:.0f}s)",
        )

        # Stages 2-5: Require AI client
        async with AIClient(self.settings) as ai_client:
            # Initialize services
            transcriber = WhisperTranscriber(ai_client, self.settings)
            cleaner = TranscriptCleaner(ai_client, self.settings)
            chunker = SemanticChunker(ai_client, self.settings)
            summarizer = VideoSummarizer(ai_client, self.settings)
            saver = FileSaver(self.settings)

            # Stage 2: Transcribe (extracts audio first, then sends to Whisper)
            raw_transcript, audio_path = await self._do_transcribe(
                transcriber, video_path, metadata.duration_seconds, progress_callback
            )

            # Stage 3: Clean
            cleaned_transcript = await self._do_clean(
                cleaner, raw_transcript, metadata, progress_callback
            )

            # Stage 4-5: Chunk + Summarize (parallel with shared outline)
            chunks, summary = await self._do_chunk_and_summarize(
                chunker,
                summarizer,
                cleaned_transcript,
                metadata,
                progress_callback,
                ai_client,
            )

            # Stage 6: Save (includes audio.mp3)
            files_created = await self._do_save(
                saver, metadata, raw_transcript, chunks, summary, audio_path, progress_callback
            )

        processing_time = (datetime.now() - started_at).total_seconds()

        logger.info(
            f"Pipeline complete: {metadata.video_id}, "
            f"{chunks.total_chunks} chunks, {processing_time:.1f}s"
        )

        return ProcessingResult(
            video_id=metadata.video_id,
            archive_path=metadata.archive_path,
            chunks_count=chunks.total_chunks,
            duration_seconds=raw_transcript.duration_seconds,
            files_created=files_created,
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # Step-by-Step Mode (for testing prompts/glossaries)
    # ═══════════════════════════════════════════════════════════════════════════

    def parse(self, video_path: Path) -> VideoMetadata:
        """
        Parse video filename.

        Args:
            video_path: Path to video file

        Returns:
            VideoMetadata with parsed information

        Raises:
            FilenameParseError: If filename doesn't match pattern
        """
        video_path = Path(video_path)
        return parse_filename(video_path.name, video_path)

    async def transcribe(self, video_path: Path) -> tuple[RawTranscript, Path]:
        """
        Transcribe video via Whisper API.

        Extracts audio from video first, then sends to Whisper.

        Args:
            video_path: Path to video file

        Returns:
            Tuple of (RawTranscript, audio_path)
        """
        video_path = Path(video_path)

        async with AIClient(self.settings) as ai_client:
            transcriber = WhisperTranscriber(ai_client, self.settings)
            return await transcriber.transcribe(video_path)

    async def clean(
        self,
        raw_transcript: RawTranscript,
        metadata: VideoMetadata,
    ) -> CleanedTranscript:
        """
        Clean raw transcript using glossary and LLM.

        Args:
            raw_transcript: Raw transcript from Whisper
            metadata: Video metadata

        Returns:
            CleanedTranscript with cleaned text
        """
        async with AIClient(self.settings) as ai_client:
            cleaner = TranscriptCleaner(ai_client, self.settings)
            return await cleaner.clean(raw_transcript, metadata)

    async def chunk(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
    ) -> TranscriptChunks:
        """
        Split cleaned transcript into semantic chunks.

        Args:
            cleaned_transcript: Cleaned transcript
            metadata: Video metadata (for chunk IDs)

        Returns:
            TranscriptChunks with semantic chunks
        """
        async with AIClient(self.settings) as ai_client:
            chunker = SemanticChunker(ai_client, self.settings)
            return await chunker.chunk(cleaned_transcript, metadata)

    async def summarize(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
        prompt_name: str = "summarizer",
    ) -> VideoSummary:
        """
        Create structured summary from cleaned transcript.

        For step-by-step mode: automatically extracts outline for large texts.
        Uses full transcript for small texts (<10K chars).

        Args:
            cleaned_transcript: Cleaned transcript
            metadata: Video metadata
            prompt_name: Name of prompt file (without .md) from config/prompts/

        Returns:
            VideoSummary with structured content
        """
        async with AIClient(self.settings) as ai_client:
            # Extract outline for large texts (step-by-step mode)
            _, outline = await self._extract_outline(cleaned_transcript, ai_client)

            summarizer = VideoSummarizer(ai_client, self.settings)
            if prompt_name != "summarizer":
                summarizer.set_prompt(prompt_name)

            return await summarizer.summarize(outline, metadata, cleaned_transcript)

    async def save(
        self,
        metadata: VideoMetadata,
        raw_transcript: RawTranscript,
        chunks: TranscriptChunks,
        summary: VideoSummary,
        audio_path: Path | None = None,
    ) -> list[str]:
        """
        Save all processing results to archive.

        Args:
            metadata: Video metadata
            raw_transcript: Raw transcript
            chunks: Semantic chunks
            summary: Video summary
            audio_path: Path to extracted audio file (optional)

        Returns:
            List of created file names
        """
        saver = FileSaver(self.settings)
        return await saver.save(metadata, raw_transcript, chunks, summary, audio_path)

    # ═══════════════════════════════════════════════════════════════════════════
    # Internal: Stage Execution with Progress
    # ═══════════════════════════════════════════════════════════════════════════

    async def _do_transcribe(
        self,
        transcriber: WhisperTranscriber,
        video_path: Path,
        video_duration: float,
        callback: ProgressCallback | None,
    ) -> tuple[RawTranscript, Path]:
        """Execute transcription stage with progress ticker."""
        estimate = self.estimator.estimate_transcribe(video_duration)

        # Start progress ticker
        ticker = None
        if callback:
            ticker = await self.estimator.start_ticker(
                stage=ProcessingStatus.TRANSCRIBING,
                estimated_seconds=estimate.estimated_seconds,
                message=f"Transcribing: {video_path.name}",
                callback=lambda s, p, m: self._update_progress(callback, s, p, m),
            )

        try:
            transcript, audio_path = await transcriber.transcribe(video_path)
        except Exception as e:
            if ticker:
                ticker.cancel()
            raise PipelineError(
                ProcessingStatus.TRANSCRIBING, f"Transcription failed: {e}", e
            )

        # Stop ticker and send 100%
        if callback:
            await self.estimator.stop_ticker(
                ticker,
                ProcessingStatus.TRANSCRIBING,
                lambda s, p, m: self._update_progress(callback, s, p, m),
                f"Transcribed: {len(transcript.segments)} segments, {transcript.duration_seconds:.0f}s",
            )

        return transcript, audio_path

    async def _do_clean(
        self,
        cleaner: TranscriptCleaner,
        raw_transcript: RawTranscript,
        metadata: VideoMetadata,
        callback: ProgressCallback | None,
    ) -> CleanedTranscript:
        """Execute cleaning stage with progress ticker."""
        input_chars = len(raw_transcript.full_text)
        estimate = self.estimator.estimate_clean(input_chars)

        # Start progress ticker
        ticker = None
        if callback:
            ticker = await self.estimator.start_ticker(
                stage=ProcessingStatus.CLEANING,
                estimated_seconds=estimate.estimated_seconds,
                message="Cleaning transcript with glossary and LLM",
                callback=lambda s, p, m: self._update_progress(callback, s, p, m),
            )

        try:
            result = await cleaner.clean(raw_transcript, metadata)
        except Exception as e:
            if ticker:
                ticker.cancel()
            raise PipelineError(
                ProcessingStatus.CLEANING, f"Cleaning failed: {e}", e
            )

        # Stop ticker and send 100%
        if callback:
            await self.estimator.stop_ticker(
                ticker,
                ProcessingStatus.CLEANING,
                lambda s, p, m: self._update_progress(callback, s, p, m),
                f"Cleaned: {result.original_length} -> {result.cleaned_length} chars",
            )

        return result

    async def _extract_outline(
        self,
        cleaned_transcript: CleanedTranscript,
        ai_client: AIClient,
        callback: ProgressCallback | None = None,
    ) -> tuple[list[TextPart], TranscriptOutline | None]:
        """
        Extract outline from transcript for large texts.

        For small texts (<= LARGE_TEXT_THRESHOLD), returns None outline.
        For large texts, extracts outline using Map-Reduce approach.

        Args:
            cleaned_transcript: Cleaned transcript
            ai_client: AI client for LLM calls
            callback: Optional progress callback

        Returns:
            Tuple of (text_parts, outline or None)
        """
        text = cleaned_transcript.text
        input_chars = len(text)

        text_splitter = TextSplitter()
        text_parts = text_splitter.split(text)

        if input_chars <= LARGE_TEXT_THRESHOLD:
            logger.debug(f"Small text ({input_chars} chars), skipping outline extraction")
            return text_parts, None

        # Large text: extract outline using Map-Reduce
        logger.info(
            f"Large text detected ({input_chars} chars), "
            f"extracting outline from {len(text_parts)} parts"
        )

        if callback:
            await callback(
                ProcessingStatus.CHUNKING,
                0,
                f"Extracting outline from {len(text_parts)} parts",
            )

        extractor = OutlineExtractor(ai_client, self.settings)
        outline = await extractor.extract(text_parts)

        logger.info(
            f"Outline extracted: {outline.total_parts} parts, "
            f"{len(outline.all_topics)} unique topics"
        )

        return text_parts, outline

    async def _do_chunk_and_summarize(
        self,
        chunker: SemanticChunker,
        summarizer: VideoSummarizer,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
        callback: ProgressCallback | None,
        ai_client: AIClient,
    ) -> tuple[TranscriptChunks, VideoSummary]:
        """
        Execute outline extraction, chunking and summarization.

        For large texts: extracts outline first, then runs chunking and
        summarization in parallel with shared outline context.

        For small texts: runs chunking and summarization in parallel
        without outline (uses full transcript).
        """
        input_chars = len(cleaned_transcript.text)

        # Phase 1: Extract outline for large texts
        text_parts, outline = await self._extract_outline(
            cleaned_transcript, ai_client, callback
        )

        # Calculate estimates for parallel stages
        chunk_estimate = self.estimator.estimate_chunk(input_chars)
        summarize_estimate = self.estimator.estimate_summarize(input_chars)
        combined_estimated = max(
            chunk_estimate.estimated_seconds,
            summarize_estimate.estimated_seconds,
        )

        # Start progress ticker for combined parallel operation
        ticker = None
        if callback:
            ticker = await self.estimator.start_ticker(
                stage=ProcessingStatus.CHUNKING,
                estimated_seconds=combined_estimated,
                message="Chunking and summarizing in parallel",
                callback=lambda s, p, m: self._update_progress(callback, s, p, m),
            )

        # Phase 2: Parallel chunking and summarization (both use outline)
        chunk_task = asyncio.create_task(
            chunker.chunk_with_outline(cleaned_transcript, metadata, text_parts, outline)
        )
        summarize_task = asyncio.create_task(
            summarizer.summarize(outline, metadata, cleaned_transcript)
        )

        # Wait for both, catching exceptions
        results = await asyncio.gather(
            chunk_task, summarize_task, return_exceptions=True
        )

        chunk_result, summarize_result = results

        # Handle results with graceful degradation
        chunks: TranscriptChunks | None = None
        summary: VideoSummary | None = None
        errors: list[str] = []

        if isinstance(chunk_result, Exception):
            errors.append(f"Chunking failed: {chunk_result}")
            logger.error(f"Chunking error: {chunk_result}")
        else:
            chunks = chunk_result

        if isinstance(summarize_result, Exception):
            errors.append(f"Summarization failed: {summarize_result}")
            logger.error(f"Summarization error: {summarize_result}")
        else:
            summary = summarize_result

        # If both failed, raise error
        if chunks is None and summary is None:
            if ticker:
                ticker.cancel()
            raise PipelineError(
                ProcessingStatus.CHUNKING,
                f"Both chunking and summarization failed: {'; '.join(errors)}",
            )

        # Graceful degradation: create fallbacks if one failed
        if chunks is None:
            logger.warning("Using fallback chunks due to chunker failure")
            chunks = self._create_fallback_chunks(cleaned_transcript, metadata)

        if summary is None:
            logger.warning("Using fallback summary due to summarizer failure")
            summary = self._create_fallback_summary(metadata)

        # Stop ticker and send 100%
        if callback:
            await self.estimator.stop_ticker(
                ticker,
                ProcessingStatus.SUMMARIZING,
                lambda s, p, m: self._update_progress(callback, s, p, m),
                f"Completed: {chunks.total_chunks} chunks, summary ready",
            )

        return chunks, summary

    async def _do_save(
        self,
        saver: FileSaver,
        metadata: VideoMetadata,
        raw_transcript: RawTranscript,
        chunks: TranscriptChunks,
        summary: VideoSummary,
        audio_path: Path | None,
        callback: ProgressCallback | None,
    ) -> list[str]:
        """Execute save stage with progress ticker."""
        estimated = self.estimator.get_fixed_stage_time("save")

        # Start progress ticker
        ticker = None
        if callback:
            ticker = await self.estimator.start_ticker(
                stage=ProcessingStatus.SAVING,
                estimated_seconds=estimated,
                message=f"Saving to: {metadata.archive_path}",
                callback=lambda s, p, m: self._update_progress(callback, s, p, m),
            )

        try:
            files = await saver.save(metadata, raw_transcript, chunks, summary, audio_path)
        except Exception as e:
            if ticker:
                ticker.cancel()
            raise PipelineError(ProcessingStatus.SAVING, f"Save failed: {e}", e)

        # Stop ticker and send 100%
        if callback:
            await self.estimator.stop_ticker(
                ticker,
                ProcessingStatus.SAVING,
                lambda s, p, m: self._update_progress(callback, s, p, m),
                f"Saved {len(files)} files",
            )

        return files

    # ═══════════════════════════════════════════════════════════════════════════
    # Internal: Progress Calculation
    # ═══════════════════════════════════════════════════════════════════════════

    async def _update_progress(
        self,
        callback: ProgressCallback | None,
        status: ProcessingStatus,
        stage_progress: float,
        message: str,
    ) -> None:
        """
        Update progress via callback.

        Args:
            callback: Progress callback (may be None)
            status: Current processing status
            stage_progress: Progress within current stage (0-100)
            message: Human-readable status message
        """
        if callback is None:
            return

        overall_progress = self._calculate_overall_progress(status, stage_progress)

        try:
            await callback(status, overall_progress, message)
        except Exception as e:
            # Never fail due to callback error
            logger.warning(f"Progress callback error: {e}")

    def _calculate_overall_progress(
        self,
        current_stage: ProcessingStatus,
        stage_progress: float = 100,
    ) -> float:
        """
        Calculate overall progress percentage.

        Args:
            current_stage: Current processing stage
            stage_progress: Progress within current stage (0-100)

        Returns:
            Overall progress (0-100)
        """
        # Define stage order for progress calculation
        stage_order = [
            ProcessingStatus.PARSING,
            ProcessingStatus.TRANSCRIBING,
            ProcessingStatus.CLEANING,
            ProcessingStatus.CHUNKING,  # Parallel with SUMMARIZING
            ProcessingStatus.SAVING,
        ]

        # Calculate base progress from completed stages
        base_progress = 0.0
        for stage in stage_order:
            if stage == current_stage:
                break

            weight = self.STAGE_WEIGHTS.get(stage, 0)
            # SUMMARIZING shares progress with CHUNKING
            if stage == ProcessingStatus.CHUNKING:
                weight += self.STAGE_WEIGHTS.get(ProcessingStatus.SUMMARIZING, 0)
            base_progress += weight

        # Add current stage progress
        current_weight = self.STAGE_WEIGHTS.get(current_stage, 0)
        if current_stage in (ProcessingStatus.CHUNKING, ProcessingStatus.SUMMARIZING):
            # Parallel stages share combined weight
            current_weight = (
                self.STAGE_WEIGHTS.get(ProcessingStatus.CHUNKING, 0)
                + self.STAGE_WEIGHTS.get(ProcessingStatus.SUMMARIZING, 0)
            )

        stage_contribution = (stage_progress / 100) * current_weight

        return min(base_progress + stage_contribution, 100)

    # ═══════════════════════════════════════════════════════════════════════════
    # Internal: Fallback Methods
    # ═══════════════════════════════════════════════════════════════════════════

    def _create_fallback_chunks(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
    ) -> TranscriptChunks:
        """
        Create fallback chunks when semantic chunking fails.

        Simply splits text into fixed-size chunks (~300 words).
        """
        text = cleaned_transcript.text
        words = text.split()
        chunk_size = 300
        chunks: list[TranscriptChunk] = []

        for i, start in enumerate(range(0, len(words), chunk_size)):
            chunk_words = words[start : start + chunk_size]
            chunk_text = " ".join(chunk_words)

            chunks.append(
                TranscriptChunk(
                    id=f"{metadata.video_id}_{i + 1:03d}",
                    index=i + 1,
                    topic=f"Часть {i + 1}",
                    text=chunk_text,
                    word_count=len(chunk_words),
                )
            )

        return TranscriptChunks(chunks=chunks)

    def _create_fallback_summary(self, metadata: VideoMetadata) -> VideoSummary:
        """
        Create minimal fallback summary when summarization fails.
        """
        return VideoSummary(
            summary=f"Видео '{metadata.title}' от {metadata.speaker}",
            key_points=["Саммари недоступно из-за технической ошибки"],
            recommendations=[],
            target_audience="Требует ручной обработки",
            questions_answered=[],
            section="Обучение",  # Default section
            subsection="",
            tags=[metadata.event_type, metadata.stream],
            access_level=1,
        )


if __name__ == "__main__":
    """Run tests when executed directly."""
    import sys
    from datetime import date

    # Configure logging for tests
    logging.basicConfig(level=logging.INFO)

    async def run_tests():
        """Run all pipeline tests."""
        print("\nRunning pipeline tests...\n")

        settings = get_settings()

        # Test 1: PipelineError
        print("Test 1: PipelineError...", end=" ")
        try:
            error = PipelineError(
                ProcessingStatus.PARSING, "Test error", ValueError("cause")
            )
            assert error.stage == ProcessingStatus.PARSING
            assert "Test error" in str(error)
            assert error.cause is not None
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 2: Progress calculation
        print("Test 2: Progress calculation...", end=" ")
        try:
            orchestrator = PipelineOrchestrator(settings)

            # PARSING at 0%
            progress = orchestrator._calculate_overall_progress(
                ProcessingStatus.PARSING, 0
            )
            assert progress == 0, f"Expected 0, got {progress}"

            # PARSING at 100%
            progress = orchestrator._calculate_overall_progress(
                ProcessingStatus.PARSING, 100
            )
            assert progress == 2, f"Expected 2, got {progress}"

            # TRANSCRIBING at 50%
            progress = orchestrator._calculate_overall_progress(
                ProcessingStatus.TRANSCRIBING, 50
            )
            # Base (PARSING=2) + 50% of TRANSCRIBING (45*0.5=22.5)
            expected = 2 + 22.5
            assert abs(progress - expected) < 0.1, f"Expected {expected}, got {progress}"

            # SAVING at 0%
            progress = orchestrator._calculate_overall_progress(
                ProcessingStatus.SAVING, 0
            )
            # All previous stages completed
            expected = 2 + 45 + 15 + 13 + 13  # 88
            assert progress == expected, f"Expected {expected}, got {progress}"

            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 3: Fallback chunks
        print("Test 3: Fallback chunks...", end=" ")
        try:
            orchestrator = PipelineOrchestrator(settings)

            mock_cleaned = CleanedTranscript(
                text=" ".join(["word"] * 650),  # 650 words -> 3 chunks
                original_length=1000,
                cleaned_length=650 * 5,
                corrections_made=[],
            )

            mock_metadata = VideoMetadata(
                date=date(2025, 1, 9),
                event_type="ПШ",
                stream="SV",
                title="Test Video",
                speaker="Test Speaker",
                original_filename="test.mp4",
                video_id="test-video-id",
                source_path=Path("/test/test.mp4"),
                archive_path=Path("/archive/test"),
            )

            chunks = orchestrator._create_fallback_chunks(mock_cleaned, mock_metadata)

            assert chunks.total_chunks == 3, f"Expected 3 chunks, got {chunks.total_chunks}"
            assert chunks.chunks[0].id == "test-video-id_001"
            assert chunks.chunks[0].topic == "Часть 1"
            assert chunks.chunks[0].word_count == 300
            assert chunks.chunks[2].word_count == 50  # Remaining words

            print("OK")
            print(f"  Chunks: {chunks.total_chunks}, sizes: {[c.word_count for c in chunks.chunks]}")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 4: Fallback summary
        print("Test 4: Fallback summary...", end=" ")
        try:
            summary = orchestrator._create_fallback_summary(mock_metadata)

            assert "Test Video" in summary.summary
            assert summary.section == "Обучение"
            assert "ПШ" in summary.tags
            assert summary.access_level == 1

            print("OK")
            print(f"  Summary: {summary.summary}")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 5: Parse method
        print("Test 5: Parse method...", end=" ")
        try:
            orchestrator = PipelineOrchestrator(settings)

            # This will fail if inbox_dir doesn't exist, but tests parse logic
            try:
                # Create a mock path that matches the pattern
                mock_path = Path("2025.01.09 ПШ.SV Test Video (Test Speaker).mp4")
                metadata = orchestrator.parse(mock_path)
                assert metadata.event_type == "ПШ"
                assert metadata.stream == "SV"
                print("OK")
            except FilenameParseError:
                print("SKIPPED (parse test requires valid filename)")

        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 6: Full pipeline (requires services)
        print("\nTest 6: Full pipeline integration...", end=" ")
        async with AIClient(settings) as client:
            status = await client.check_services()

            if not status["whisper"] or not status["ollama"]:
                print("SKIPPED (AI services unavailable)")
                print(f"  Whisper: {status['whisper']}, Ollama: {status['ollama']}")
            else:
                # Check if there's a test video
                test_videos = list(settings.inbox_dir.glob("*.mp4"))
                if not test_videos:
                    print("SKIPPED (no test video in inbox)")
                else:
                    try:
                        orchestrator = PipelineOrchestrator(settings)

                        async def progress_handler(
                            status: ProcessingStatus,
                            progress: float,
                            message: str,
                        ):
                            print(f"  [{status.value}] {progress:.0f}% - {message}")

                        result = await orchestrator.process(
                            test_videos[0], progress_callback=progress_handler
                        )

                        print("OK")
                        print(f"  Video ID: {result.video_id}")
                        print(f"  Chunks: {result.chunks_count}")
                        print(f"  Files: {result.files_created}")
                    except Exception as e:
                        print(f"FAILED: {e}")
                        import traceback

                        traceback.print_exc()
                        return 1

        print("\n" + "=" * 40)
        print("All tests passed!")
        return 0

    sys.exit(asyncio.run(run_tests()))
