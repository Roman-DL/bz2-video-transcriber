"""
Pipeline orchestrator for video processing.

Coordinates all pipeline stages from parsing to saving.
Supports both full pipeline execution and step-by-step mode for testing.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from app.config import Settings, get_settings
from app.services.progress_estimator import ProgressEstimator
from app.models.schemas import (
    CleanedTranscript,
    ContentType,
    Longread,
    ProcessingResult,
    ProcessingStatus,
    RawTranscript,
    Story,
    Summary,
    TranscriptChunks,
    VideoMetadata,
    VideoSummary,
)
from app.services.ai_clients import OllamaClient, WhisperClient
from app.services.cleaner import TranscriptCleaner
from app.services.longread_generator import LongreadGenerator
from app.services.story_generator import StoryGenerator
from app.services.summary_generator import SummaryGenerator
from app.services.parser import FilenameParseError, parse_filename
from app.services.saver import FileSaver
from app.services.summarizer import VideoSummarizer
from app.services.transcriber import WhisperTranscriber
from app.utils import estimate_duration_from_size, get_media_duration
from app.utils.h2_chunker import chunk_by_h2

from .config_resolver import ConfigResolver
from .fallback_factory import FallbackFactory
from .processing_strategy import ProcessingStrategy
from .progress_manager import ProgressCallback, ProgressManager

logger = logging.getLogger(__name__)


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
        self.processing_strategy = ProcessingStrategy(self.settings)

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

        # Get media duration for progress estimation
        metadata.duration_seconds = get_media_duration(video_path)
        if metadata.duration_seconds is None:
            # Fallback: estimate from file size (different rates for audio/video)
            metadata.duration_seconds = estimate_duration_from_size(video_path)
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

        # Stage 2: Transcribe (requires WhisperClient)
        async with WhisperClient.from_settings(self.settings) as whisper_client:
            transcriber = WhisperTranscriber(whisper_client, self.settings)

            # Stage 2: Transcribe (extracts audio first, then sends to Whisper)
            raw_transcript, audio_path = await self._do_transcribe(
                transcriber, video_path, metadata.duration_seconds, progress_callback
            )

        # Stages 3-6: Require LLM client (OllamaClient for local models)
        async with OllamaClient.from_settings(self.settings) as ai_client:
            # Initialize LLM services
            cleaner = TranscriptCleaner(ai_client, self.settings)
            longread_gen = LongreadGenerator(ai_client, self.settings)
            summary_gen = SummaryGenerator(ai_client, self.settings)
            story_gen = StoryGenerator(ai_client, self.settings)
            saver = FileSaver(self.settings)

            # Stage 3: Clean
            cleaned_transcript = await self._do_clean(
                cleaner, raw_transcript, metadata, progress_callback
            )

            # Stage 4-6: Content-type specific pipeline
            # v0.25+: New order - Longread/Story first, then deterministic chunking
            if metadata.content_type == ContentType.LEADERSHIP:
                # Leadership: Story -> Chunk (deterministic from story markdown)
                chunks, story = await self._do_leadership_pipeline(
                    story_gen,
                    cleaned_transcript,
                    metadata,
                    progress_callback,
                )
                # Stage 7: Save leadership content
                files_created = await self._do_save_leadership(
                    saver,
                    metadata,
                    raw_transcript,
                    cleaned_transcript,
                    chunks,
                    story,
                    audio_path,
                    progress_callback,
                )
            else:
                # Educational: Longread -> Summary -> Chunk (deterministic from longread markdown)
                chunks, longread, summary = await self._do_educational_pipeline(
                    longread_gen,
                    summary_gen,
                    cleaned_transcript,
                    metadata,
                    progress_callback,
                )
                # Stage 7: Save educational content
                files_created = await self._do_save_educational(
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

        async with WhisperClient.from_settings(self.settings) as whisper_client:
            transcriber = WhisperTranscriber(whisper_client, self.settings)
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
        actual_model = model or settings.cleaner_model
        async with self.processing_strategy.create_client(actual_model) as ai_client:
            cleaner = TranscriptCleaner(ai_client, settings)
            return await cleaner.clean(raw_transcript, metadata)

    def chunk(
        self,
        markdown_content: str,
        metadata: VideoMetadata,
    ) -> TranscriptChunks:
        """
        Chunk markdown content by H2 headers.

        v0.25+: Deterministic chunking, no LLM needed.

        Args:
            markdown_content: Longread or Story markdown
            metadata: Video metadata (for chunk IDs)

        Returns:
            TranscriptChunks with H2-based chunks
        """
        return chunk_by_h2(markdown_content, metadata.video_id)

    async def longread(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
        model: str | None = None,
    ) -> Longread:
        """
        Generate longread document from cleaned transcript.

        v0.25+: Now takes CleanedTranscript instead of chunks.

        Args:
            cleaned_transcript: Cleaned transcript
            metadata: Video metadata
            model: Optional model override for generation

        Returns:
            Longread document with sections
        """
        settings = self.config_resolver.with_model(model, "longread")
        actual_model = model or settings.summarizer_model
        async with self.processing_strategy.create_client(actual_model) as ai_client:
            generator = LongreadGenerator(ai_client, settings)
            try:
                return await generator.generate(cleaned_transcript, metadata)
            except Exception as e:
                logger.warning(f"Longread generation failed: {e}, using fallback")
                return self.fallback_factory.create_longread_from_cleaned(metadata, cleaned_transcript)

    async def summarize_from_cleaned(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
        model: str | None = None,
    ) -> Summary:
        """
        Generate summary (конспект) from cleaned transcript.

        v0.24+: Summary is now generated directly from cleaned transcript,
        allowing it to see all original details.

        Args:
            cleaned_transcript: Cleaned transcript
            metadata: Video metadata
            model: Optional model override for generation

        Returns:
            Summary with essence, concepts, tools, quotes, topic_area, access_level
        """
        settings = self.config_resolver.with_model(model, "summarizer")
        actual_model = model or settings.summarizer_model
        async with self.processing_strategy.create_client(actual_model) as ai_client:
            generator = SummaryGenerator(ai_client, settings)
            try:
                return await generator.generate(cleaned_transcript, metadata)
            except Exception as e:
                logger.warning(f"Summary generation failed: {e}, using fallback")
                return self.fallback_factory.create_summary_from_cleaned(cleaned_transcript, metadata)

    async def story(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
        model: str | None = None,
    ) -> Story:
        """
        Generate leadership story (8 blocks) from cleaned transcript.

        For leadership content only (content_type=LEADERSHIP).

        Args:
            cleaned_transcript: Cleaned transcript
            metadata: Video metadata
            model: Optional model override for generation

        Returns:
            Story with 8 blocks
        """
        settings = self.config_resolver.with_model(model, "summarizer")
        actual_model = model or settings.summarizer_model
        async with self.processing_strategy.create_client(actual_model) as ai_client:
            generator = StoryGenerator(ai_client, settings)
            return await generator.generate(cleaned_transcript, metadata)

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
        actual_model = model or settings.summarizer_model
        async with self.processing_strategy.create_client(actual_model) as ai_client:
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
        longread: Longread | None = None,
        summary: Summary | None = None,
        story: Story | None = None,
        audio_path: Path | None = None,
    ) -> list[str]:
        """
        Save all processing results to archive.

        Supports both educational (longread+summary) and leadership (story) content.

        Args:
            metadata: Video metadata
            raw_transcript: Raw transcript
            cleaned_transcript: Cleaned transcript after LLM processing
            chunks: Semantic chunks
            longread: Longread document (for educational content)
            summary: Summary (for educational content)
            story: Story document (for leadership content)
            audio_path: Path to extracted audio file (optional)

        Returns:
            List of created file names
        """
        saver = FileSaver(self.settings)

        # Choose save method based on content type
        if story is not None:
            return await saver.save_leadership(
                metadata, raw_transcript, cleaned_transcript, chunks,
                story, audio_path
            )
        elif longread is not None and summary is not None:
            return await saver.save_educational(
                metadata, raw_transcript, cleaned_transcript, chunks,
                longread, summary, audio_path
            )
        else:
            raise ValueError("Either story or longread+summary must be provided")

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

    async def _do_educational_pipeline(
        self,
        longread_gen: LongreadGenerator,
        summary_gen: SummaryGenerator,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
        callback: ProgressCallback | None,
    ) -> tuple[TranscriptChunks, Longread, Summary]:
        """
        Execute educational content pipeline.

        v0.25+: New pipeline order - Longread -> Summary -> Chunk (deterministic)

        For content_type=EDUCATIONAL only.
        Chunking is now deterministic from longread markdown (H2 headers).
        """
        input_chars = len(cleaned_transcript.text)

        # Phase 1: Longread generation (includes internal outline extraction)
        longread_estimate = self.estimator.estimate_summarize(input_chars) * 1.5
        ticker = None
        if callback:
            ticker = await self.estimator.start_ticker(
                stage=ProcessingStatus.LONGREAD,
                estimated_seconds=longread_estimate,
                message="Generating longread",
                callback=lambda s, p, m: self.progress_manager.update_progress(callback, s, p, m),
            )

        try:
            longread = await longread_gen.generate(cleaned_transcript, metadata)
        except Exception as e:
            if ticker:
                ticker.cancel()
            logger.error(f"Longread generation failed: {e}")
            longread = self.fallback_factory.create_longread_from_cleaned(metadata, cleaned_transcript)

        if callback and ticker:
            await self.estimator.stop_ticker(
                ticker,
                ProcessingStatus.LONGREAD,
                lambda s, p, m: self.progress_manager.update_progress(callback, s, p, m),
                f"Longread: {longread.total_sections} sections, {longread.total_word_count} words",
            )

        # Phase 2: Summary generation from cleaned transcript
        summary_estimate = self.estimator.estimate_summarize(input_chars) * 0.5
        if callback:
            ticker = await self.estimator.start_ticker(
                stage=ProcessingStatus.SUMMARIZING,
                estimated_seconds=summary_estimate,
                message="Generating summary from transcript",
                callback=lambda s, p, m: self.progress_manager.update_progress(callback, s, p, m),
            )

        try:
            summary = await summary_gen.generate(cleaned_transcript, metadata)
        except Exception as e:
            if ticker:
                ticker.cancel()
            logger.error(f"Summary generation failed: {e}")
            summary = self.fallback_factory.create_summary_from_cleaned(cleaned_transcript, metadata)

        if callback and ticker:
            await self.estimator.stop_ticker(
                ticker,
                ProcessingStatus.SUMMARIZING,
                lambda s, p, m: self.progress_manager.update_progress(callback, s, p, m),
                f"Summary: {len(summary.key_concepts)} concepts, {len(summary.quotes)} quotes",
            )

        # Phase 3: Deterministic chunking from longread markdown
        if callback:
            await self.progress_manager.update_progress(
                callback,
                ProcessingStatus.CHUNKING,
                0,
                "Chunking by H2 headers",
            )

        chunks = chunk_by_h2(longread.to_markdown(), metadata.video_id)

        if callback:
            await self.progress_manager.update_progress(
                callback,
                ProcessingStatus.CHUNKING,
                100,
                f"Chunked: {chunks.total_chunks} chunks (deterministic)",
            )

        return chunks, longread, summary

    async def _do_leadership_pipeline(
        self,
        story_gen: StoryGenerator,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
        callback: ProgressCallback | None,
    ) -> tuple[TranscriptChunks, Story]:
        """
        Execute leadership content pipeline.

        v0.25+: New pipeline order - Story -> Chunk (deterministic)

        For content_type=LEADERSHIP only.
        Generates 8-block story, then chunks by H2 headers.
        """
        input_chars = len(cleaned_transcript.text)

        # Phase 1: Story generation
        story_estimate = self.estimator.estimate_summarize(input_chars) * 1.5
        ticker = None
        if callback:
            ticker = await self.estimator.start_ticker(
                stage=ProcessingStatus.LONGREAD,  # Reuse LONGREAD status for story
                estimated_seconds=story_estimate,
                message="Generating leadership story",
                callback=lambda s, p, m: self.progress_manager.update_progress(callback, s, p, m),
            )

        try:
            story = await story_gen.generate(cleaned_transcript, metadata)
        except Exception as e:
            if ticker:
                ticker.cancel()
            logger.error(f"Story generation failed: {e}")
            raise PipelineError(
                ProcessingStatus.LONGREAD, f"Story generation failed: {e}", e
            )

        if callback and ticker:
            await self.estimator.stop_ticker(
                ticker,
                ProcessingStatus.LONGREAD,
                lambda s, p, m: self.progress_manager.update_progress(callback, s, p, m),
                f"Story: {story.total_blocks} blocks, speed={story.speed}",
            )

        # Phase 2: Deterministic chunking from story markdown
        if callback:
            await self.progress_manager.update_progress(
                callback,
                ProcessingStatus.CHUNKING,
                0,
                "Chunking by H2 headers",
            )

        chunks = chunk_by_h2(story.to_markdown(), metadata.video_id)

        if callback:
            await self.progress_manager.update_progress(
                callback,
                ProcessingStatus.CHUNKING,
                100,
                f"Chunked: {chunks.total_chunks} chunks (deterministic)",
            )

        return chunks, story

    async def _do_save_educational(
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
        """Execute save stage for educational content."""
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
            files = await saver.save_educational(
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

    async def _do_save_leadership(
        self,
        saver: FileSaver,
        metadata: VideoMetadata,
        raw_transcript: RawTranscript,
        cleaned_transcript: CleanedTranscript,
        chunks: TranscriptChunks,
        story: Story,
        audio_path: Path | None,
        callback: ProgressCallback | None,
    ) -> list[str]:
        """Execute save stage for leadership content."""
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
            files = await saver.save_leadership(
                metadata, raw_transcript, cleaned_transcript, chunks,
                story, audio_path
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
