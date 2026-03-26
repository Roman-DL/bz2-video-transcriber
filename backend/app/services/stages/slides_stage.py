"""
Slides extraction stage for processing uploaded slides.

Extracts text from slides (images/PDFs) using Claude Vision API.
Optional stage — skipped when no slides are provided.

v0.84+: Now a proper stage in the pipeline (was a separate endpoint).
"""

import logging

from app.config import Settings
from app.models.schemas import ProcessingStatus, SlidesExtractionResult
from app.services.slides_extractor import SlidesExtractor
from app.services.stages.base import BaseStage, StageContext, StageError

logger = logging.getLogger(__name__)


class SlidesStage(BaseStage):
    """Extract text from slides using vision API.

    Optional stage that appears between clean and longread/story.
    Skipped when no slides_input is provided in context metadata.

    Input (from context):
        - clean: CleanedTranscript (dependency)
        - slides_input in metadata: list of SlideInput objects

    Output:
        SlidesExtractionResult with extracted text

    Example:
        stage = SlidesStage(settings, config_resolver, processing_strategy)
        if not stage.should_skip(context):
            result = await stage.execute(context)
    """

    name = "slides"
    depends_on = ["clean"]
    optional = True
    status = ProcessingStatus.SLIDES

    def __init__(self, settings: Settings, config_resolver=None, processing_strategy=None):
        """Initialize slides stage.

        Args:
            settings: Application settings
            config_resolver: ConfigResolver for model overrides
            processing_strategy: ProcessingStrategy for AI client creation
        """
        self.settings = settings
        self.config_resolver = config_resolver
        self.processing_strategy = processing_strategy

    def should_skip(self, context: StageContext) -> bool:
        """Skip when no slides are provided.

        Args:
            context: Stage context with metadata

        Returns:
            True if no slides_input in metadata
        """
        slides_input = context.get_metadata("slides_input")
        return not slides_input

    async def execute(self, context: StageContext) -> SlidesExtractionResult:
        """Extract text from slides.

        Args:
            context: Context with slides_input in metadata

        Returns:
            SlidesExtractionResult with extracted text

        Raises:
            StageError: If extraction fails
        """
        slides_input = context.get_metadata("slides_input")
        if not slides_input:
            raise StageError(self.name, "No slides_input in context metadata")

        try:
            model = context.get_metadata("model_overrides", {}).get("slides")
            prompt_overrides = context.get_metadata("prompt_overrides", {}).get("slides")
            settings = self.config_resolver.with_model(model, "slides") if self.config_resolver else self.settings
            actual_model = model or settings.slides_model
            async with self.processing_strategy.create_client(actual_model) as ai_client:
                extractor = SlidesExtractor(ai_client, settings, prompt_overrides)
                return await extractor.extract(
                    slides=slides_input,
                    model=actual_model,
                )
        except Exception as e:
            raise StageError(self.name, f"Slides extraction failed: {e}", e)

    def estimate_time(self, input_size: int) -> float:
        """Estimate extraction time.

        Args:
            input_size: Number of slides

        Returns:
            Estimated time in seconds
        """
        return max(5.0, input_size * 3.0)
