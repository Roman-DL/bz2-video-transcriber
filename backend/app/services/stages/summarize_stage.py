"""
Summarize stage for generating summaries from longread.

Creates a condensed summary (конспект) for navigation and quick reference.
"""

import logging

from app.config import Settings
from app.models.schemas import (
    ContentType,
    Longread,
    ProcessingStatus,
    Summary,
    VideoMetadata,
)
from app.services.ai_clients import BaseAIClient
from app.services.stages.base import BaseStage, StageContext, StageError
from app.services.summary_generator import SummaryGenerator


logger = logging.getLogger(__name__)


class SummarizeStage(BaseStage):
    """Generate summary (конспект) from longread document.

    A summary is a navigation document for those who ALREADY watched/read
    the content. It helps recall key points quickly.

    Input (from context):
        - parse: VideoMetadata
        - longread: Longread document

    Output:
        Summary with essence, concepts, tools, quotes

    Example:
        stage = SummarizeStage(ai_client, settings)
        summary = await stage.execute(context)
    """

    name = "summarize"
    depends_on = ["parse", "longread"]
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
        """Generate summary from longread.

        Args:
            context: Context with parse and longread results

        Returns:
            Summary document

        Raises:
            StageError: If generation fails (with fallback)
        """
        self.validate_context(context)

        metadata: VideoMetadata = context.get_result("parse")
        longread: Longread = context.get_result("longread")

        try:
            return await self.generator.generate(longread, metadata)
        except Exception as e:
            logger.warning(f"Summary generation failed: {e}, using fallback")
            return self._create_fallback_summary(longread, metadata)

    def _create_fallback_summary(
        self,
        longread: Longread,
        metadata: VideoMetadata,
    ) -> Summary:
        """Create fallback summary when generation fails.

        Args:
            longread: Longread document
            metadata: Video metadata

        Returns:
            Minimal summary with basic information
        """
        return Summary(
            video_id=metadata.video_id,
            title=metadata.title,
            speaker=metadata.speaker,
            date=metadata.date,
            essence=longread.introduction or f"Тема: {metadata.title}",
            key_concepts=[s.title for s in longread.sections[:5]],
            practical_tools=[],
            quotes=[],
            insight="Конспект недоступен из-за технической ошибки",
            actions=[],
            topic_area=longread.topic_area,
            tags=longread.tags,
            access_level=longread.access_level,
            model_name=self.settings.summarizer_model,
        )

    def estimate_time(self, input_size: int) -> float:
        """Estimate summary generation time.

        Args:
            input_size: Longread length in characters

        Returns:
            Estimated time in seconds
        """
        # Summary generation is relatively quick from longread
        return 15.0 + input_size / 500
