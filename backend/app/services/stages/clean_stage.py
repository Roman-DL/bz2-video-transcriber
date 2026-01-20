"""
Clean stage for transcript cleaning using glossary and LLM.

Applies terminology corrections and improves transcript readability.
"""

from app.config import Settings
from app.models.schemas import CleanedTranscript, ProcessingStatus, RawTranscript, VideoMetadata
from app.services.ai_client import AIClient
from app.services.cleaner import TranscriptCleaner
from app.services.stages.base import BaseStage, StageContext, StageError


class CleanStage(BaseStage):
    """Clean raw transcript using glossary and LLM.

    Input (from context):
        - parse: VideoMetadata
        - transcribe: Tuple of (RawTranscript, audio_path)

    Output:
        CleanedTranscript with corrections applied

    Example:
        stage = CleanStage(ai_client, settings)
        context = context.with_result("transcribe", (raw_transcript, audio_path))
        cleaned = await stage.execute(context)
    """

    name = "clean"
    depends_on = ["parse", "transcribe"]
    status = ProcessingStatus.CLEANING

    def __init__(self, ai_client: AIClient, settings: Settings):
        """Initialize clean stage.

        Args:
            ai_client: AI client for LLM calls
            settings: Application settings
        """
        self.ai_client = ai_client
        self.settings = settings
        self.cleaner = TranscriptCleaner(ai_client, settings)

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

        try:
            return await self.cleaner.clean(raw_transcript, metadata)
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
