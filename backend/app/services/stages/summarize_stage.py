"""
Summarize stage for generating summaries from cleaned transcript.

Creates a condensed summary (конспект) for navigation and quick reference.

v0.24+: Generates from CleanedTranscript (not Longread).
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
from app.services.ai_clients import BaseAIClient
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
        stage = SummarizeStage(ai_client, settings)
        summary = await stage.execute(context)
    """

    name = "summarize"
    depends_on = ["parse", "clean"]  # v0.24: Changed from ["parse", "longread"]
    status = ProcessingStatus.SUMMARIZING

    def __init__(self, ai_client: BaseAIClient, settings: Settings):
        """Initialize summarize stage.

        Args:
            ai_client: AI client for LLM calls
            settings: Application settings
        """
        self.ai_client = ai_client
        self.settings = settings
        self.generator = SummaryGenerator(ai_client, settings)

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

        Args:
            context: Context with parse and clean results

        Returns:
            Summary document

        Raises:
            StageError: If generation fails (with fallback)
        """
        self.validate_context(context)

        metadata: VideoMetadata = context.get_result("parse")
        cleaned_transcript: CleanedTranscript = context.get_result("clean")

        try:
            return await self.generator.generate(cleaned_transcript, metadata)
        except Exception as e:
            logger.warning(f"Summary generation failed: {e}, using fallback")
            return self._create_fallback_summary(cleaned_transcript, metadata)

    def _create_fallback_summary(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
    ) -> Summary:
        """Create fallback summary when generation fails.

        Args:
            cleaned_transcript: Cleaned transcript
            metadata: Video metadata

        Returns:
            Minimal summary with basic information
        """
        # Take first 500 chars as essence
        essence = cleaned_transcript.text[:500]
        if len(cleaned_transcript.text) > 500:
            essence = essence.rsplit(" ", 1)[0] + "..."

        return Summary(
            video_id=metadata.video_id,
            title=metadata.title,
            speaker=metadata.speaker,
            date=metadata.date,
            essence=essence,
            key_concepts=[],
            practical_tools=[],
            quotes=[],
            insight="Конспект недоступен из-за технической ошибки",
            actions=[],
            topic_area=["мотивация"],  # Default
            tags=[metadata.event_type, metadata.stream] if metadata.stream else [metadata.event_type],
            access_level="consultant",
            model_name=self.settings.summarizer_model,
        )

    def estimate_time(self, input_size: int) -> float:
        """Estimate summary generation time.

        Args:
            input_size: Cleaned transcript length in characters

        Returns:
            Estimated time in seconds
        """
        # Summary from cleaned transcript takes about the same time as from longread
        return 15.0 + input_size / 500
