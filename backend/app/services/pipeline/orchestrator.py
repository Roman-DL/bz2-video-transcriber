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

from app.config import Settings, get_settings
from app.services.progress_estimator import ProgressEstimator
from app.models.schemas import (
    CleanedTranscript,
    Longread,
    ProcessingResult,
    ProcessingStatus,
    RawTranscript,
    Summary,
    TextPart,
    TranscriptChunks,
    TranscriptOutline,
    VideoMetadata,
    VideoSummary,
)
from app.services.ai_client import AIClient
from app.services.chunker import DEFAULT_LARGE_TEXT_THRESHOLD, SemanticChunker
from app.services.cleaner import TranscriptCleaner
from app.services.longread_generator import LongreadGenerator
from app.services.outline_extractor import OutlineExtractor
from app.services.summary_generator import SummaryGenerator
from app.services.text_splitter import TextSplitter
from app.services.parser import FilenameParseError, parse_filename
from app.services.saver import FileSaver
from app.services.summarizer import VideoSummarizer
from app.services.transcriber import WhisperTranscriber

from .config_resolver import ConfigResolver
from .fallback_factory import FallbackFactory
from .progress_manager import ProgressCallback, ProgressManager

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

    def __init__(self, settings: Settings | None = None):
        """
        Initialize pipeline orchestrator.

        Args:
            settings: Application settings (uses defaults if None)
        """
        self.settings = settings or get_settings()
        self.estimator = ProgressEstimator(self.settings)
        self.progress_manager = ProgressManager()
        self.fallback_factory = FallbackFactory(self.settings)
        self.config_resolver = ConfigResolver(self.settings)

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
        await self.progress_manager.update_progress(
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

        await self.progress_manager.update_progress(
            progress_callback,
            ProcessingStatus.PARSING,
            100,
            f"Parsed: {metadata.video_id} ({metadata.duration_seconds:.0f}s)",
        )

        # Stages 2-6: Require AI client
        async with AIClient(self.settings) as ai_client:
            # Initialize services
            transcriber = WhisperTranscriber(ai_client, self.settings)
            cleaner = TranscriptCleaner(ai_client, self.settings)
            chunker = SemanticChunker(ai_client, self.settings)
            longread_gen = LongreadGenerator(ai_client, self.settings)
            summary_gen = SummaryGenerator(ai_client, self.settings)
            saver = FileSaver(self.settings)

            # Stage 2: Transcribe (extracts audio first, then sends to Whisper)
            raw_transcript, audio_path = await self._do_transcribe(
                transcriber, video_path, metadata.duration_seconds, progress_callback
            )

            # Stage 3: Clean
            cleaned_transcript = await self._do_clean(
                cleaner, raw_transcript, metadata, progress_callback
            )

            # Stage 4-6: Chunk -> Longread -> Summary (sequential with shared outline)
            chunks, longread, summary = await self._do_chunk_longread_summarize(
                chunker,
                longread_gen,
                summary_gen,
                cleaned_transcript,
                metadata,
                progress_callback,
                ai_client,
            )

            # Stage 7: Save (includes audio.mp3, longread.md, summary.md)
            files_created = await self._do_save(
                saver,
                metadata,
                raw_transcript,
                cleaned_transcript,
                chunks,
                longread,
                summary,
                audio_path,
                progress_callback,
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
        model: str | None = None,
    ) -> CleanedTranscript:
        """
        Clean raw transcript using glossary and LLM.

        Args:
            raw_transcript: Raw transcript from Whisper
            metadata: Video metadata
            model: Optional model override for cleaning

        Returns:
            CleanedTranscript with cleaned text
        """
        settings = self.config_resolver.with_model(model, "cleaner")
        async with AIClient(settings) as ai_client:
            cleaner = TranscriptCleaner(ai_client, settings)
            return await cleaner.clean(raw_transcript, metadata)

    async def chunk(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
        model: str | None = None,
    ) -> TranscriptChunks:
        """
        Split cleaned transcript into semantic chunks.

        Args:
            cleaned_transcript: Cleaned transcript
            metadata: Video metadata (for chunk IDs)
            model: Optional model override for chunking

        Returns:
            TranscriptChunks with semantic chunks
        """
        settings = self.config_resolver.with_model(model, "chunker")
        async with AIClient(settings) as ai_client:
            chunker = SemanticChunker(ai_client, settings)
            return await chunker.chunk(cleaned_transcript, metadata)

    async def longread(
        self,
        chunks: TranscriptChunks,
        metadata: VideoMetadata,
        outline: TranscriptOutline | None = None,
        model: str | None = None,
    ) -> Longread:
        """
        Generate longread document from transcript chunks.

        Args:
            chunks: Transcript chunks from chunking stage
            metadata: Video metadata
            outline: Optional transcript outline for context
            model: Optional model override for generation

        Returns:
            Longread document with sections
        """
        settings = self.config_resolver.with_model(model, "longread")
        async with AIClient(settings) as ai_client:
            generator = LongreadGenerator(ai_client, settings)
            try:
                return await generator.generate(chunks, metadata, outline)
            except Exception as e:
                logger.warning(f"Longread generation failed: {e}, using fallback")
                return self.fallback_factory.create_longread(metadata, chunks)

    async def summarize_from_longread(
        self,
        longread: Longread,
        metadata: VideoMetadata,
        model: str | None = None,
    ) -> Summary:
        """
        Generate summary (конспект) from longread document.

        Args:
            longread: Longread document
            metadata: Video metadata
            model: Optional model override for generation

        Returns:
            Summary with essence, concepts, tools, quotes
        """
        settings = self.config_resolver.with_model(model, "summarizer")
        async with AIClient(settings) as ai_client:
            generator = SummaryGenerator(ai_client, settings)
            try:
                return await generator.generate(longread, metadata)
            except Exception as e:
                logger.warning(f"Summary generation failed: {e}, using fallback")
                return self.fallback_factory.create_summary_from_longread(longread, metadata)

    async def summarize(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
        prompt_name: str = "summarizer",
        model: str | None = None,
    ) -> VideoSummary:
        """
        Create structured summary from cleaned transcript.

        For step-by-step mode: automatically extracts outline for large texts.
        Uses full transcript for small texts (<10K chars).

        Args:
            cleaned_transcript: Cleaned transcript
            metadata: Video metadata
            prompt_name: Name of prompt file (without .md) from config/prompts/
            model: Optional model override for summarization

        Returns:
            VideoSummary with structured content
        """
        settings = self.config_resolver.with_model(model, "summarizer")
        async with AIClient(settings) as ai_client:
            # Extract outline for large texts (step-by-step mode)
            _, outline = await self._extract_outline(cleaned_transcript, ai_client)

            summarizer = VideoSummarizer(ai_client, settings)
            if prompt_name != "summarizer":
                summarizer.set_prompt(prompt_name)

            return await summarizer.summarize(outline, metadata, cleaned_transcript)

    async def save(
        self,
        metadata: VideoMetadata,
        raw_transcript: RawTranscript,
        cleaned_transcript: CleanedTranscript,
        chunks: TranscriptChunks,
        longread: Longread,
        summary: Summary,
        audio_path: Path | None = None,
    ) -> list[str]:
        """
        Save all processing results to archive.

        Args:
            metadata: Video metadata
            raw_transcript: Raw transcript
            cleaned_transcript: Cleaned transcript after LLM processing
            chunks: Semantic chunks
            longread: Longread document
            summary: Summary (конспект)
            audio_path: Path to extracted audio file (optional)

        Returns:
            List of created file names
        """
        saver = FileSaver(self.settings)
        return await saver.save(
            metadata, raw_transcript, cleaned_transcript, chunks,
            longread, summary, audio_path
        )

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
                callback=lambda s, p, m: self.progress_manager.update_progress(callback, s, p, m),
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
                lambda s, p, m: self.progress_manager.update_progress(callback, s, p, m),
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
                callback=lambda s, p, m: self.progress_manager.update_progress(callback, s, p, m),
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
                lambda s, p, m: self.progress_manager.update_progress(callback, s, p, m),
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

        For small texts (<= DEFAULT_LARGE_TEXT_THRESHOLD), returns None outline.
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

        if input_chars <= DEFAULT_LARGE_TEXT_THRESHOLD:
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

    async def _do_chunk_longread_summarize(
        self,
        chunker: SemanticChunker,
        longread_gen: LongreadGenerator,
        summary_gen: SummaryGenerator,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
        callback: ProgressCallback | None,
        ai_client: AIClient,
    ) -> tuple[TranscriptChunks, Longread, Summary]:
        """
        Execute outline extraction, chunking, longread generation, and summarization.

        Pipeline: Outline -> Chunk -> Longread -> Summary

        The outline is extracted once and used by both chunker and longread generator.
        """
        input_chars = len(cleaned_transcript.text)

        # Phase 1: Extract outline for large texts
        text_parts, outline = await self._extract_outline(
            cleaned_transcript, ai_client, callback
        )

        # Phase 2: Chunking
        chunk_estimate = self.estimator.estimate_chunk(input_chars)
        ticker = None
        if callback:
            ticker = await self.estimator.start_ticker(
                stage=ProcessingStatus.CHUNKING,
                estimated_seconds=chunk_estimate.estimated_seconds,
                message="Chunking transcript",
                callback=lambda s, p, m: self.progress_manager.update_progress(callback, s, p, m),
            )

        try:
            chunks = await chunker.chunk_with_outline(
                cleaned_transcript, metadata, text_parts, outline
            )
        except Exception as e:
            if ticker:
                ticker.cancel()
            logger.warning(f"Chunking failed: {e}, using fallback")
            chunks = self.fallback_factory.create_chunks(cleaned_transcript, metadata)

        if callback and ticker:
            await self.estimator.stop_ticker(
                ticker,
                ProcessingStatus.CHUNKING,
                lambda s, p, m: self.progress_manager.update_progress(callback, s, p, m),
                f"Chunked: {chunks.total_chunks} chunks",
            )

        # Phase 3: Longread generation
        longread_estimate = self.estimator.estimate_summarize(input_chars) * 1.5
        if callback:
            ticker = await self.estimator.start_ticker(
                stage=ProcessingStatus.LONGREAD,
                estimated_seconds=longread_estimate,
                message="Generating longread",
                callback=lambda s, p, m: self.progress_manager.update_progress(callback, s, p, m),
            )

        try:
            longread = await longread_gen.generate(chunks, metadata, outline)
        except Exception as e:
            if ticker:
                ticker.cancel()
            logger.error(f"Longread generation failed: {e}")
            longread = self.fallback_factory.create_longread(metadata, chunks)

        if callback and ticker:
            await self.estimator.stop_ticker(
                ticker,
                ProcessingStatus.LONGREAD,
                lambda s, p, m: self.progress_manager.update_progress(callback, s, p, m),
                f"Longread: {longread.total_sections} sections, {longread.total_word_count} words",
            )

        # Phase 4: Summary generation from longread
        summary_estimate = self.estimator.estimate_summarize(input_chars) * 0.5
        if callback:
            ticker = await self.estimator.start_ticker(
                stage=ProcessingStatus.SUMMARIZING,
                estimated_seconds=summary_estimate,
                message="Generating summary from longread",
                callback=lambda s, p, m: self.progress_manager.update_progress(callback, s, p, m),
            )

        try:
            summary = await summary_gen.generate(longread, metadata)
        except Exception as e:
            if ticker:
                ticker.cancel()
            logger.error(f"Summary generation failed: {e}")
            summary = self.fallback_factory.create_summary_from_longread(longread, metadata)

        if callback and ticker:
            await self.estimator.stop_ticker(
                ticker,
                ProcessingStatus.SUMMARIZING,
                lambda s, p, m: self.progress_manager.update_progress(callback, s, p, m),
                f"Summary: {len(summary.key_concepts)} concepts, {len(summary.quotes)} quotes",
            )

        return chunks, longread, summary

    async def _do_save(
        self,
        saver: FileSaver,
        metadata: VideoMetadata,
        raw_transcript: RawTranscript,
        cleaned_transcript: CleanedTranscript,
        chunks: TranscriptChunks,
        longread: Longread,
        summary: Summary,
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
                callback=lambda s, p, m: self.progress_manager.update_progress(callback, s, p, m),
            )

        try:
            files = await saver.save(
                metadata, raw_transcript, cleaned_transcript, chunks,
                longread, summary, audio_path
            )
        except Exception as e:
            if ticker:
                ticker.cancel()
            raise PipelineError(ProcessingStatus.SAVING, f"Save failed: {e}", e)

        # Stop ticker and send 100%
        if callback:
            await self.estimator.stop_ticker(
                ticker,
                ProcessingStatus.SAVING,
                lambda s, p, m: self.progress_manager.update_progress(callback, s, p, m),
                f"Saved {len(files)} files",
            )

        return files

    # ═══════════════════════════════════════════════════════════════════════════
    # Legacy compatibility (deprecated)
    # ═══════════════════════════════════════════════════════════════════════════

    # These methods are kept for backward compatibility but delegate to new classes

    def _get_settings_with_model(self, model: str | None, stage: str) -> Settings:
        """Deprecated: Use config_resolver.with_model() instead."""
        return self.config_resolver.with_model(model, stage)  # type: ignore

    async def _update_progress(
        self,
        callback: ProgressCallback | None,
        status: ProcessingStatus,
        stage_progress: float,
        message: str,
    ) -> None:
        """Deprecated: Use progress_manager.update_progress() instead."""
        await self.progress_manager.update_progress(callback, status, stage_progress, message)

    def _calculate_overall_progress(
        self,
        current_stage: ProcessingStatus,
        stage_progress: float = 100,
    ) -> float:
        """Deprecated: Use progress_manager.calculate_overall_progress() instead."""
        return self.progress_manager.calculate_overall_progress(current_stage, stage_progress)

    def _create_fallback_chunks(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
    ) -> TranscriptChunks:
        """Deprecated: Use fallback_factory.create_chunks() instead."""
        return self.fallback_factory.create_chunks(cleaned_transcript, metadata)

    def _create_fallback_summary(self, metadata: VideoMetadata) -> VideoSummary:
        """Deprecated: Use fallback_factory.create_summary() instead."""
        return self.fallback_factory.create_summary(metadata)

    def _create_fallback_longread(
        self,
        metadata: VideoMetadata,
        chunks: TranscriptChunks,
    ) -> Longread:
        """Deprecated: Use fallback_factory.create_longread() instead."""
        return self.fallback_factory.create_longread(metadata, chunks)

    def _create_fallback_summary_from_longread(
        self,
        longread: Longread,
        metadata: VideoMetadata,
    ) -> Summary:
        """Deprecated: Use fallback_factory.create_summary_from_longread() instead."""
        return self.fallback_factory.create_summary_from_longread(longread, metadata)

    # Expose STAGE_WEIGHTS for backward compatibility
    @property
    def STAGE_WEIGHTS(self) -> dict:
        """Deprecated: Use progress_manager.STAGE_WEIGHTS instead."""
        return self.progress_manager.STAGE_WEIGHTS
