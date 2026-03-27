"""
Pipeline orchestrator for video processing.

Coordinates all pipeline stages from parsing to saving.
Supports both full pipeline execution and step-by-step mode for testing.

v0.84+: Uses BaseStage.execute() instead of direct service calls (ADR-001 Phase 1).
"""

import logging
from datetime import datetime
from pathlib import Path

from app.config import Settings, get_settings
from app.services.progress_estimator import ProgressEstimator
from app.models.schemas import (
    CleanedTranscript,
    Longread,
    ProcessingResult,
    ProcessingStatus,
    PromptOverrides,
    RawTranscript,
    SaveResult,
    SlidesExtractionResult,
    Story,
    Summary,
    TranscriptChunks,
    VideoMetadata,
)
from app.services.stages import (
    StageContext,
    CleanStage,
    ChunkStage,
    LongreadStage,
    ParseStage,
    SaveStage,
    SlidesStage,
    SummarizeStage,
    StoryStage,
    TranscribeStage,
)
from app.services.stages.base import BaseStage, StageError
from app.utils.h2_chunker import chunk_by_h2

from .config_resolver import ConfigResolver
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

    v0.84+: All execution paths go through BaseStage.execute().

    Supports two modes:
    1. Full pipeline: process() runs all stages automatically
    2. Step-by-step: individual methods for testing prompts/glossaries

    Example (full pipeline):
        orchestrator = PipelineOrchestrator()
        result = await orchestrator.process(Path("inbox/video.mp4"))

    Example (step-by-step):
        orchestrator = PipelineOrchestrator()
        metadata = await orchestrator.parse(Path("inbox/video.mp4"))
        raw = await orchestrator.transcribe(Path("inbox/video.mp4"))
        cleaned = await orchestrator.clean(raw, metadata)
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
        Process video through complete pipeline using stage loop.

        v0.84+: Uses BaseStage.execute() for all stages (ADR-001 Phase 1).

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

        stages = self._build_pipeline()
        context = StageContext(metadata={"video_path": str(video_path)})

        for stage in stages:
            if stage.should_skip(context):
                logger.info(f"Skipping stage: {stage.name}")
                continue
            result = await self._execute_with_progress(stage, context, progress_callback)
            context = context.with_result(stage.name, result)

        processing_time = (datetime.now() - started_at).total_seconds()

        return self._build_processing_result(context, processing_time)

    def _build_pipeline(self) -> list[BaseStage]:
        """Build ordered list of pipeline stages."""
        return [
            ParseStage(self.settings),
            TranscribeStage(self.settings),
            CleanStage(self.settings, self.config_resolver, self.processing_strategy),
            SlidesStage(self.settings, self.config_resolver, self.processing_strategy),
            LongreadStage(self.settings, self.config_resolver, self.processing_strategy),
            SummarizeStage(self.settings, self.config_resolver, self.processing_strategy),
            StoryStage(self.settings, self.config_resolver, self.processing_strategy),
            ChunkStage(self.settings),
            SaveStage(self.settings),
        ]

    async def _execute_with_progress(
        self,
        stage: BaseStage,
        context: StageContext,
        callback: ProgressCallback | None,
    ):
        """Execute a stage with progress ticker."""
        status = stage.status
        if not status:
            # No progress tracking for this stage
            try:
                return await stage.execute(context)
            except StageError as e:
                raise PipelineError(
                    ProcessingStatus.FAILED, e.message, e.cause
                )

        # Start progress ticker
        ticker = None
        if callback:
            estimated = self._estimate_stage_time(stage, context)
            ticker = await self.estimator.start_ticker(
                stage=status,
                estimated_seconds=estimated,
                message=f"Processing: {stage.name}",
                callback=lambda s, p, m: self.progress_manager.update_progress(callback, s, p, m),
            )

        try:
            result = await stage.execute(context)
        except StageError as e:
            if ticker:
                ticker.cancel()
            raise PipelineError(status, e.message, e.cause)
        except Exception as e:
            if ticker:
                ticker.cancel()
            raise PipelineError(status, f"{stage.name} failed: {e}", e)

        # Stop ticker
        if callback and ticker:
            await self.estimator.stop_ticker(
                ticker,
                status,
                lambda s, p, m: self.progress_manager.update_progress(callback, s, p, m),
                f"Completed: {stage.name}",
            )

        return result

    def _estimate_stage_time(self, stage: BaseStage, context: StageContext) -> float:
        """Estimate execution time for a stage."""
        if stage.name == "transcribe" and context.has_result("parse"):
            metadata = context.get_result("parse")
            return self.estimator.estimate_transcribe(metadata.duration_seconds).estimated_seconds

        if stage.name == "clean" and context.has_result("transcribe"):
            raw_transcript, _ = context.get_result("transcribe")
            return self.estimator.estimate_clean(len(raw_transcript.full_text)).estimated_seconds

        if stage.name in ("longread", "story") and context.has_result("clean"):
            cleaned = context.get_result("clean")
            return self.estimator.estimate_longread(len(cleaned.text)).estimated_seconds

        if stage.name == "summarize" and context.has_result("clean"):
            cleaned = context.get_result("clean")
            return self.estimator.estimate_summarize(len(cleaned.text)).estimated_seconds

        if stage.name == "save":
            return self.estimator.get_fixed_stage_time("save")

        return stage.estimate_time(0)

    def _build_processing_result(
        self, context: StageContext, processing_time: float
    ) -> ProcessingResult:
        """Build ProcessingResult from completed context."""
        metadata: VideoMetadata = context.get_result("parse")
        raw_transcript: RawTranscript = context.get_result("transcribe")[0]
        chunks: TranscriptChunks = context.get_result("chunk")
        save_result: SaveResult = context.get_result("save")

        logger.info(
            f"Pipeline complete: {metadata.video_id}, "
            f"{chunks.total_chunks} chunks, {processing_time:.1f}s"
        )

        return ProcessingResult(
            video_id=metadata.video_id,
            archive_path=metadata.archive_path,
            chunks_count=chunks.total_chunks,
            duration_seconds=raw_transcript.duration_seconds,
            files_created=save_result.files,
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # Step-by-Step Mode (for testing prompts/glossaries)
    # ═══════════════════════════════════════════════════════════════════════════

    async def parse(self, video_path: Path) -> VideoMetadata:
        """
        Parse video filename and enrich metadata.

        v0.84+: Delegates to ParseStage (includes MD enrichment).

        Args:
            video_path: Path to video file

        Returns:
            VideoMetadata with parsed information
        """
        video_path = Path(video_path)
        context = StageContext(metadata={"video_path": str(video_path)})
        stage = ParseStage(self.settings)
        return await stage.execute(context)

    async def transcribe(self, video_path: Path) -> tuple[RawTranscript, Path | None]:
        """
        Transcribe video via Whisper API, or load MD transcript.

        v0.84+: Delegates to TranscribeStage.

        Args:
            video_path: Path to video/audio/md file

        Returns:
            Tuple of (RawTranscript, audio_path or None for MD)
        """
        video_path = Path(video_path)
        metadata = await self.parse(video_path)
        context = StageContext(
            results={"parse": metadata},
            metadata={"video_path": str(video_path)},
        )
        stage = TranscribeStage(self.settings)
        return await stage.execute(context)

    async def clean(
        self,
        raw_transcript: RawTranscript,
        metadata: VideoMetadata,
        model: str | None = None,
        prompt_overrides: PromptOverrides | None = None,
    ) -> CleanedTranscript:
        """
        Clean raw transcript using glossary and LLM.

        v0.84+: Delegates to CleanStage.

        Args:
            raw_transcript: Raw transcript from Whisper
            metadata: Video metadata
            model: Optional model override for cleaning
            prompt_overrides: Optional prompt file overrides

        Returns:
            CleanedTranscript with cleaned text
        """
        context = StageContext(
            results={"parse": metadata, "transcribe": (raw_transcript, None)},
            metadata={
                "model_overrides": {"clean": model} if model else {},
                "prompt_overrides": {"clean": prompt_overrides} if prompt_overrides else {},
            },
        )
        stage = CleanStage(self.settings, self.config_resolver, self.processing_strategy)
        return await stage.execute(context)

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
        prompt_overrides: PromptOverrides | None = None,
        slides_text: str | None = None,
    ) -> Longread:
        """
        Generate longread document from cleaned transcript.

        v0.84+: Delegates to LongreadStage.

        Args:
            cleaned_transcript: Cleaned transcript
            metadata: Video metadata
            model: Optional model override for generation
            prompt_overrides: Optional prompt file overrides
            slides_text: Optional extracted text from slides

        Returns:
            Longread document with sections
        """
        results = {"parse": metadata, "clean": cleaned_transcript}
        meta = {
            "model_overrides": {"longread": model} if model else {},
            "prompt_overrides": {"longread": prompt_overrides} if prompt_overrides else {},
        }

        # Inject slides as a fake result if slides_text provided
        if slides_text:
            results["slides"] = SlidesExtractionResult(
                extracted_text=slides_text,
                slides_count=0,
                chars_count=len(slides_text),
                words_count=len(slides_text.split()),
                tables_count=0,
                model="step-by-step",
            )

        context = StageContext(results=results, metadata=meta)
        stage = LongreadStage(self.settings, self.config_resolver, self.processing_strategy)
        return await stage.execute(context)

    async def summarize_from_cleaned(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
        model: str | None = None,
        prompt_overrides: PromptOverrides | None = None,
        slides_text: str | None = None,
        language_override: str | None = None,
    ) -> Summary:
        """
        Generate summary (конспект) from cleaned transcript.

        v0.84+: Delegates to SummarizeStage.
        v0.85+: language_override controls prompt language context
                (e.g. "ru" when orchestration passes pre-translated longread).

        Args:
            cleaned_transcript: Cleaned transcript
            metadata: Video metadata
            model: Optional model override for generation
            prompt_overrides: Optional prompt file overrides
            slides_text: Optional extracted text from slides
            language_override: Override language for prompt (v0.85+)

        Returns:
            Summary with essence, concepts, tools, quotes, topic_area, access_level
        """
        results = {"parse": metadata, "clean": cleaned_transcript}
        meta = {
            "model_overrides": {"summarize": model} if model else {},
            "prompt_overrides": {"summarize": prompt_overrides} if prompt_overrides else {},
            "language_override": language_override,
        }

        if slides_text:
            results["slides"] = SlidesExtractionResult(
                extracted_text=slides_text,
                slides_count=0,
                chars_count=len(slides_text),
                words_count=len(slides_text.split()),
                tables_count=0,
                model="step-by-step",
            )

        context = StageContext(results=results, metadata=meta)
        stage = SummarizeStage(self.settings, self.config_resolver, self.processing_strategy)
        return await stage.execute(context)

    async def story(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
        model: str | None = None,
        prompt_overrides: PromptOverrides | None = None,
        slides_text: str | None = None,
    ) -> Story:
        """
        Generate leadership story (8 blocks) from cleaned transcript.

        v0.84+: Delegates to StoryStage.

        Args:
            cleaned_transcript: Cleaned transcript
            metadata: Video metadata
            model: Optional model override for generation
            prompt_overrides: Optional prompt file overrides
            slides_text: Optional extracted text from slides

        Returns:
            Story with 8 blocks
        """
        results = {"parse": metadata, "clean": cleaned_transcript}
        meta = {
            "model_overrides": {"story": model} if model else {},
            "prompt_overrides": {"story": prompt_overrides} if prompt_overrides else {},
        }

        if slides_text:
            results["slides"] = SlidesExtractionResult(
                extracted_text=slides_text,
                slides_count=0,
                chars_count=len(slides_text),
                words_count=len(slides_text.split()),
                tables_count=0,
                model="step-by-step",
            )

        context = StageContext(results=results, metadata=meta)
        stage = StoryStage(self.settings, self.config_resolver, self.processing_strategy)
        return await stage.execute(context)

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
        slides_extraction: SlidesExtractionResult | None = None,
    ) -> SaveResult:
        """
        Save all processing results to archive.

        v0.84+: Delegates to SaveStage.

        Args:
            metadata: Video metadata
            raw_transcript: Raw transcript
            cleaned_transcript: Cleaned transcript after LLM processing
            chunks: Semantic chunks
            longread: Longread document (for educational content)
            summary: Summary (for educational content)
            story: Story document (for leadership content)
            audio_path: Path to extracted audio file (optional)
            slides_extraction: Slides extraction result (optional)

        Returns:
            SaveResult with created files and description metrics
        """
        results = {
            "parse": metadata,
            "transcribe": (raw_transcript, audio_path),
            "clean": cleaned_transcript,
            "chunk": chunks,
        }

        if story is not None:
            results["story"] = story
        if longread is not None:
            results["longread"] = longread
        if summary is not None:
            results["summarize"] = summary
        if slides_extraction is not None:
            results["slides"] = slides_extraction

        context = StageContext(results=results)
        stage = SaveStage(self.settings)
        return await stage.execute(context)
