"""
Longread stage for generating longread documents from chunks.

Creates an edited version of the transcript for those who didn't watch the video.
"""

import logging

from app.config import Settings
from app.models.schemas import (
    Longread,
    LongreadSection,
    ProcessingStatus,
    TranscriptChunks,
    TranscriptOutline,
    VideoMetadata,
)
from app.services.ai_client import AIClient
from app.services.longread_generator import LongreadGenerator
from app.services.stages.base import BaseStage, StageContext, StageError


logger = logging.getLogger(__name__)


class LongreadStage(BaseStage):
    """Generate longread document from transcript chunks.

    A longread is an edited version of the transcript that preserves
    the speaker's voice and logic while improving readability.

    Input (from context):
        - parse: VideoMetadata
        - chunk: Tuple of (TranscriptChunks, TranscriptOutline | None, list[TextPart])

    Output:
        Longread document with sections

    Example:
        stage = LongreadStage(ai_client, settings)
        longread = await stage.execute(context)
    """

    name = "longread"
    depends_on = ["parse", "chunk"]
    status = ProcessingStatus.LONGREAD

    def __init__(self, ai_client: AIClient, settings: Settings):
        """Initialize longread stage.

        Args:
            ai_client: AI client for LLM calls
            settings: Application settings
        """
        self.ai_client = ai_client
        self.settings = settings
        self.generator = LongreadGenerator(ai_client, settings)

    async def execute(self, context: StageContext) -> Longread:
        """Generate longread from transcript chunks.

        Args:
            context: Context with parse and chunk results

        Returns:
            Longread document

        Raises:
            StageError: If generation fails (with fallback)
        """
        self.validate_context(context)

        metadata: VideoMetadata = context.get_result("parse")
        chunks, outline, _ = context.get_result("chunk")

        try:
            return await self.generator.generate(chunks, metadata, outline)
        except Exception as e:
            logger.warning(f"Longread generation failed: {e}, using fallback")
            return self._create_fallback_longread(metadata, chunks)

    def _create_fallback_longread(
        self,
        metadata: VideoMetadata,
        chunks: TranscriptChunks,
    ) -> Longread:
        """Create fallback longread when generation fails.

        Uses chunks directly as sections.

        Args:
            metadata: Video metadata
            chunks: Transcript chunks

        Returns:
            Longread with chunks as sections
        """
        sections = [
            LongreadSection(
                index=chunk.index,
                title=chunk.topic,
                content=chunk.text,
                source_chunks=[chunk.index],
                word_count=chunk.word_count,
            )
            for chunk in chunks.chunks
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
            section="Обучение",
            subsection="",
            tags=[metadata.event_type, metadata.stream] if metadata.stream else [metadata.event_type],
            access_level=1,
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
