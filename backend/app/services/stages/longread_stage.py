"""
Longread stage for generating longread documents from cleaned transcript.

Creates an edited version of the transcript for those who didn't watch the video.

v0.25+: Now depends on clean instead of chunk (new pipeline order).
v0.29+: Removed fallback - raises StageError on failure.
"""

import logging

from app.config import Settings
from app.models.schemas import (
    CleanedTranscript,
    ContentType,
    Longread,
    ProcessingStatus,
    VideoMetadata,
)
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
        stage = LongreadStage(settings, config_resolver, processing_strategy)
        longread = await stage.execute(context)
    """

    name = "longread"
    depends_on = ["parse", "clean"]
    status = ProcessingStatus.LONGREAD

    def __init__(self, settings: Settings, config_resolver=None, processing_strategy=None):
        """Initialize longread stage.

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

    async def execute(self, context: StageContext) -> Longread:
        """Generate longread from cleaned transcript.

        v0.25+: Now uses clean result instead of chunk.
        v0.29+: Removed fallback - raises StageError on failure.

        Args:
            context: Context with parse and clean results

        Returns:
            Longread document

        Raises:
            StageError: If generation fails
        """
        self.validate_context(context)

        metadata: VideoMetadata = context.get_result("parse")
        cleaned: CleanedTranscript = context.get_result("clean")

        # Get slides text if available
        slides_text = None
        if context.has_result("slides"):
            slides_result = context.get_result("slides")
            slides_text = slides_result.extracted_text if slides_result else None

        try:
            model = context.get_metadata("model_overrides", {}).get("longread")
            prompt_overrides = context.get_metadata("prompt_overrides", {}).get("longread")
            settings = self.config_resolver.with_model(model, "longread") if self.config_resolver else self.settings
            actual_model = model or settings.longread_model
            async with self.processing_strategy.create_client(actual_model) as ai_client:
                generator = LongreadGenerator(ai_client, settings, prompt_overrides)
                return await generator.generate(cleaned, metadata, slides_text)
        except Exception as e:
            raise StageError(self.name, f"Longread generation failed: {e}", e)

    def estimate_time(self, input_size: int) -> float:
        """Estimate longread generation time.

        Args:
            input_size: Transcript length in characters

        Returns:
            Estimated time in seconds
        """
        # Longread generation is slower due to map-reduce over sections
        return 30.0 + input_size / 300
