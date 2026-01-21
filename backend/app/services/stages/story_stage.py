"""
Story generation stage for leadership content.

Generates 8-block story document from cleaned transcript.
Only executes for content_type=LEADERSHIP, skipped for EDUCATIONAL.
"""

import logging
from typing import Any

from app.config import Settings
from app.models.schemas import (
    CleanedTranscript,
    ContentType,
    Story,
    VideoMetadata,
)
from app.services.ai_clients import BaseAIClient
from app.services.stages.base import BaseStage, StageContext, StageError
from app.services.story_generator import StoryGenerator

logger = logging.getLogger(__name__)


class StoryStage(BaseStage):
    """
    Story generation stage for leadership content.

    Produces:
        - Story: 8-block structured document

    Dependencies:
        - clean: CleanedTranscript
        - parse: VideoMetadata (for content_type check)

    Skip conditions:
        - content_type != LEADERSHIP

    Example:
        stage = StoryStage(ai_client, settings)
        context = context.with_result("clean", cleaned_transcript)
        context = context.with_result("parse", metadata)

        if not stage.should_skip(context):
            story = await stage.execute(context)
    """

    name = "story"
    depends_on = ["clean", "parse"]
    optional = False

    def __init__(self, ai_client: BaseAIClient, settings: Settings):
        """
        Initialize story stage.

        Args:
            ai_client: AI client for LLM calls
            settings: Application settings
        """
        self.generator = StoryGenerator(ai_client, settings)
        self.settings = settings

    def should_skip(self, context: StageContext) -> bool:
        """
        Check if stage should be skipped.

        Returns True for educational content (use LongreadStage instead).

        Args:
            context: Stage context with parse results

        Returns:
            True if content_type is not LEADERSHIP
        """
        metadata: VideoMetadata | None = context.get_result("parse")
        if metadata is None:
            return True

        return metadata.content_type != ContentType.LEADERSHIP

    async def execute(self, context: StageContext) -> Story:
        """
        Execute story generation.

        Args:
            context: Context with clean and parse results

        Returns:
            Story with 8 blocks

        Raises:
            StageError: If generation fails
        """
        cleaned: CleanedTranscript | None = context.get_result("clean")
        metadata: VideoMetadata | None = context.get_result("parse")

        if cleaned is None or metadata is None:
            raise StageError(
                self.name,
                "Missing required results: clean and parse",
            )

        logger.info(f"Generating story for: {metadata.speaker}")

        try:
            story = await self.generator.generate(cleaned, metadata)

            logger.info(
                f"Story generated: {story.total_blocks} blocks, "
                f"speed={story.speed}"
            )

            return story

        except Exception as e:
            raise StageError(
                self.name,
                f"Story generation failed: {e}",
            ) from e

    def estimate_time(self, input_size: int) -> float:
        """
        Estimate execution time.

        Story generation is a single LLM call.

        Args:
            input_size: Not used

        Returns:
            Estimated time in seconds
        """
        return 60.0  # Single comprehensive generation
