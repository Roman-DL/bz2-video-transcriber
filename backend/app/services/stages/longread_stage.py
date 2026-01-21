"""
Longread stage for generating longread documents from cleaned transcript.

Creates an edited version of the transcript for those who didn't watch the video.

v0.25+: Now depends on clean instead of chunk (new pipeline order).
"""

import logging

from app.config import Settings
from app.models.schemas import (
    CleanedTranscript,
    ContentType,
    Longread,
    LongreadSection,
    ProcessingStatus,
    VideoMetadata,
)
from app.services.ai_clients import BaseAIClient
from app.services.longread_generator import LongreadGenerator
from app.services.stages.base import BaseStage, StageContext, StageError


logger = logging.getLogger(__name__)


class LongreadStage(BaseStage):
    """Generate longread document from cleaned transcript.

    A longread is an edited version of the transcript that preserves
    the speaker's voice and logic while improving readability.

    v0.25+: Now depends on clean instead of chunk.

    Input (from context):
        - parse: VideoMetadata
        - clean: CleanedTranscript

    Output:
        Longread document with sections

    Example:
        stage = LongreadStage(ai_client, settings)
        longread = await stage.execute(context)
    """

    name = "longread"
    depends_on = ["parse", "clean"]
    status = ProcessingStatus.LONGREAD

    def __init__(self, ai_client: BaseAIClient, settings: Settings):
        """Initialize longread stage.

        Args:
            ai_client: AI client for LLM calls
            settings: Application settings
        """
        self.ai_client = ai_client
        self.settings = settings
        self.generator = LongreadGenerator(ai_client, settings)

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

    async def execute(self, context: StageContext) -> Longread:
        """Generate longread from cleaned transcript.

        v0.25+: Now uses clean result instead of chunk.

        Args:
            context: Context with parse and clean results

        Returns:
            Longread document

        Raises:
            StageError: If generation fails (with fallback)
        """
        self.validate_context(context)

        metadata: VideoMetadata = context.get_result("parse")
        cleaned: CleanedTranscript = context.get_result("clean")

        try:
            return await self.generator.generate(cleaned, metadata)
        except Exception as e:
            logger.warning(f"Longread generation failed: {e}, using fallback")
            return self._create_fallback_longread(metadata, cleaned)

    def _create_fallback_longread(
        self,
        metadata: VideoMetadata,
        cleaned: CleanedTranscript,
    ) -> Longread:
        """Create fallback longread when generation fails.

        Creates a single-section longread from cleaned text.

        Args:
            metadata: Video metadata
            cleaned: Cleaned transcript

        Returns:
            Longread with single section
        """
        sections = [
            LongreadSection(
                index=1,
                title=metadata.title,
                content=cleaned.text,
                source_chunks=[1],
                word_count=cleaned.word_count,
            )
        ]

        return Longread(
            video_id=metadata.video_id,
            title=metadata.title,
            speaker=metadata.speaker,
            date=metadata.date,
            event_type=metadata.event_type,
            stream=metadata.stream,
            introduction="",
            sections=sections,
            conclusion="",
            topic_area=["мотивация"],
            tags=[metadata.event_type, metadata.stream] if metadata.stream else [metadata.event_type],
            access_level="consultant",
            model_name=self.settings.summarizer_model,
        )

    def estimate_time(self, input_size: int) -> float:
        """Estimate longread generation time.

        Args:
            input_size: Transcript length in characters

        Returns:
            Estimated time in seconds
        """
        # Longread generation is slower due to map-reduce over sections
        return 30.0 + input_size / 300
