"""
Clean stage for transcript cleaning using glossary and LLM.

Applies terminology corrections and improves transcript readability.
"""

import logging

from app.config import Settings
from app.models.schemas import CleanedTranscript, ProcessingStatus, RawTranscript, TokensUsed, VideoMetadata
from app.services.cleaner import TranscriptCleaner
from app.services.stages.base import BaseStage, StageContext, StageError

logger = logging.getLogger(__name__)


class CleanStage(BaseStage):
    """Clean raw transcript using glossary and LLM.

    Input (from context):
        - parse: VideoMetadata
        - transcribe: Tuple of (RawTranscript, audio_path)

    Output:
        CleanedTranscript with corrections applied

    Example:
        stage = CleanStage(settings, config_resolver, processing_strategy)
        context = context.with_result("transcribe", (raw_transcript, audio_path))
        cleaned = await stage.execute(context)
    """

    name = "clean"
    depends_on = ["parse", "transcribe"]
    status = ProcessingStatus.CLEANING

    def __init__(self, settings: Settings, config_resolver=None, processing_strategy=None):
        """Initialize clean stage.

        Args:
            settings: Application settings
            config_resolver: ConfigResolver for model overrides
            processing_strategy: ProcessingStrategy for AI client creation
        """
        self.settings = settings
        self.config_resolver = config_resolver
        self.processing_strategy = processing_strategy

    async def execute(self, context: StageContext) -> CleanedTranscript:
        """Clean raw transcript.

        Args:
            context: Context with parse and transcribe results

        Returns:
            CleanedTranscript with corrections applied

        Raises:
            StageError: If cleaning fails
        """
        self.validate_context(context)

        metadata: VideoMetadata = context.get_result("parse")
        raw_transcript, _ = context.get_result("transcribe")

        # Foreign transcripts: skip glossary cleaning, pass-through original text
        if metadata.language == "foreign":
            logger.info("skip_clean_foreign", language=metadata.language)
            return CleanedTranscript(
                text=raw_transcript.text,
                tokens_used=TokensUsed(input=0, output=0),
            )

        try:
            model = context.get_metadata("model_overrides", {}).get("clean")
            prompt_overrides = context.get_metadata("prompt_overrides", {}).get("clean")
            settings = self.config_resolver.with_model(model, "cleaner") if self.config_resolver else self.settings
            actual_model = model or settings.cleaner_model
            async with self.processing_strategy.create_client(actual_model) as ai_client:
                cleaner = TranscriptCleaner(ai_client, settings, prompt_overrides)
                return await cleaner.clean(raw_transcript, metadata)
        except Exception as e:
            raise StageError(self.name, f"Cleaning failed: {e}", e)

    def estimate_time(self, input_size: int) -> float:
        """Estimate cleaning time.

        Args:
            input_size: Transcript length in characters

        Returns:
            Estimated time in seconds
        """
        # Roughly 1 second per 1000 characters for LLM processing
        return max(5.0, input_size / 1000)
