"""
Summarize stage for generating summaries from cleaned transcript.

Creates a condensed summary (конспект) for navigation and quick reference.

v0.24+: Generates from CleanedTranscript (not Longread).
v0.29+: Removed fallback - raises StageError on failure.
"""

import logging

from app.config import Settings
from app.models.schemas import (
    CleanedTranscript,
    ContentType,
    ProcessingStatus,
    Summary,
    VideoMetadata,
)
from app.services.stages.base import BaseStage, StageContext, StageError
from app.services.summary_generator import SummaryGenerator


logger = logging.getLogger(__name__)


class SummarizeStage(BaseStage):
    """Generate summary (конспект) from cleaned transcript.

    A summary is a navigation document for those who ALREADY watched/read
    the content. It helps recall key points quickly.

    v0.24+: Now generates from CleanedTranscript instead of Longread.
    This allows the summary to see all original details from the transcript.

    Input (from context):
        - parse: VideoMetadata
        - clean: CleanedTranscript

    Output:
        Summary with essence, concepts, tools, quotes, topic_area, access_level

    Example:
        stage = SummarizeStage(settings, config_resolver, processing_strategy)
        summary = await stage.execute(context)
    """

    name = "summarize"
    depends_on = ["parse", "clean"]  # v0.24: Changed from ["parse", "longread"]
    status = ProcessingStatus.SUMMARIZING

    def __init__(self, settings: Settings, config_resolver=None, processing_strategy=None):
        """Initialize summarize stage.

        Args:
            settings: Application settings
            config_resolver: ConfigResolver for model overrides
            processing_strategy: ProcessingStrategy for AI client creation
        """
        self.settings = settings
        self.config_resolver = config_resolver
        self.processing_strategy = processing_strategy

    def should_skip(self, context: StageContext) -> bool:
        """Check if stage should be skipped.

        Returns True for leadership content (use StoryStage instead).

        Args:
            context: Stage context with parse results

        Returns:
            True if content_type is LEADERSHIP
        """
        metadata: VideoMetadata | None = context.get_result("parse")
        if metadata is None:
            return False

        return metadata.content_type == ContentType.LEADERSHIP

    async def execute(self, context: StageContext) -> Summary:
        """Generate summary from cleaned transcript.

        v0.29+: Removed fallback - raises StageError on failure.

        Args:
            context: Context with parse and clean results

        Returns:
            Summary document

        Raises:
            StageError: If generation fails
        """
        self.validate_context(context)

        metadata: VideoMetadata = context.get_result("parse")
        cleaned_transcript: CleanedTranscript = context.get_result("clean")

        # Get slides text if available
        slides_text = None
        if context.has_result("slides"):
            slides_result = context.get_result("slides")
            slides_text = slides_result.extracted_text if slides_result else None

        try:
            model = context.get_metadata("model_overrides", {}).get("summarize")
            prompt_overrides = context.get_metadata("prompt_overrides", {}).get("summarize")
            settings = self.config_resolver.with_model(model, "summarizer") if self.config_resolver else self.settings
            actual_model = model or settings.summarizer_model
            async with self.processing_strategy.create_client(actual_model) as ai_client:
                generator = SummaryGenerator(ai_client, settings, prompt_overrides)
                return await generator.generate(cleaned_transcript, metadata, slides_text)
        except Exception as e:
            raise StageError(self.name, f"Summary generation failed: {e}", e)

    def estimate_time(self, input_size: int) -> float:
        """Estimate summary generation time.

        Args:
            input_size: Cleaned transcript length in characters

        Returns:
            Estimated time in seconds
        """
        # Summary from cleaned transcript takes about the same time as from longread
        return 15.0 + input_size / 500
