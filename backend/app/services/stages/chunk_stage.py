"""
Chunk stage for semantic transcript chunking.

Splits cleaned transcript into semantic chunks for RAG retrieval.
For large texts, extracts outline first using Map-Reduce approach.
"""

import logging

from app.config import Settings
from app.models.schemas import (
    CleanedTranscript,
    ProcessingStatus,
    TextPart,
    TranscriptChunk,
    TranscriptChunks,
    TranscriptOutline,
    VideoMetadata,
)
from app.services.ai_clients import BaseAIClient
from app.services.chunker import DEFAULT_LARGE_TEXT_THRESHOLD, SemanticChunker
from app.services.outline_extractor import OutlineExtractor
from app.services.stages.base import BaseStage, StageContext, StageError
from app.services.text_splitter import TextSplitter


logger = logging.getLogger(__name__)


class ChunkStage(BaseStage):
    """Split cleaned transcript into semantic chunks.

    For large texts (> DEFAULT_LARGE_TEXT_THRESHOLD), extracts outline first
    using Map-Reduce approach for better context.

    Input (from context):
        - parse: VideoMetadata
        - clean: CleanedTranscript

    Output:
        Tuple of (TranscriptChunks, TranscriptOutline | None, list[TextPart])
        - chunks: Semantic chunks for RAG
        - outline: Optional outline for longread generation
        - text_parts: Text parts for downstream processing

    Example:
        stage = ChunkStage(ai_client, settings)
        chunks, outline, text_parts = await stage.execute(context)
    """

    name = "chunk"
    depends_on = ["parse", "clean"]
    status = ProcessingStatus.CHUNKING

    def __init__(self, ai_client: BaseAIClient, settings: Settings):
        """Initialize chunk stage.

        Args:
            ai_client: AI client for LLM calls
            settings: Application settings
        """
        self.ai_client = ai_client
        self.settings = settings
        self.chunker = SemanticChunker(ai_client, settings)
        self.text_splitter = TextSplitter()
        self.outline_extractor = OutlineExtractor(ai_client, settings)

    async def execute(
        self, context: StageContext
    ) -> tuple[TranscriptChunks, TranscriptOutline | None, list[TextPart]]:
        """Chunk cleaned transcript.

        Args:
            context: Context with parse and clean results

        Returns:
            Tuple of (chunks, outline, text_parts)

        Raises:
            StageError: If chunking fails
        """
        self.validate_context(context)

        metadata: VideoMetadata = context.get_result("parse")
        cleaned: CleanedTranscript = context.get_result("clean")

        try:
            # Split text into parts
            text_parts = self.text_splitter.split(cleaned.text)

            # Extract outline for large texts
            outline = await self._extract_outline_if_needed(cleaned, text_parts)

            # Perform chunking
            if outline:
                chunks = await self.chunker.chunk_with_outline(
                    cleaned, metadata, text_parts, outline
                )
            else:
                chunks = await self.chunker.chunk(cleaned, metadata)

            return chunks, outline, text_parts

        except Exception as e:
            logger.warning(f"Chunking failed: {e}, using fallback")
            chunks = self._create_fallback_chunks(cleaned, metadata)
            text_parts = self.text_splitter.split(cleaned.text)
            return chunks, None, text_parts

    async def _extract_outline_if_needed(
        self,
        cleaned: CleanedTranscript,
        text_parts: list[TextPart],
    ) -> TranscriptOutline | None:
        """Extract outline for large texts.

        Args:
            cleaned: Cleaned transcript
            text_parts: Text parts from splitter

        Returns:
            Outline if text is large enough, None otherwise
        """
        input_chars = len(cleaned.text)

        if input_chars <= DEFAULT_LARGE_TEXT_THRESHOLD:
            logger.debug(f"Small text ({input_chars} chars), skipping outline extraction")
            return None

        logger.info(
            f"Large text detected ({input_chars} chars), "
            f"extracting outline from {len(text_parts)} parts"
        )

        outline = await self.outline_extractor.extract(text_parts)

        logger.info(
            f"Outline extracted: {outline.total_parts} parts, "
            f"{len(outline.all_topics)} unique topics"
        )

        return outline

    def _create_fallback_chunks(
        self,
        cleaned: CleanedTranscript,
        metadata: VideoMetadata,
    ) -> TranscriptChunks:
        """Create fallback chunks when semantic chunking fails.

        Simply splits text into fixed-size chunks (~300 words).

        Args:
            cleaned: Cleaned transcript
            metadata: Video metadata

        Returns:
            TranscriptChunks with simple word-based chunks
        """
        text = cleaned.text
        words = text.split()
        chunk_size = 300
        chunks: list[TranscriptChunk] = []

        for i, start in enumerate(range(0, len(words), chunk_size)):
            chunk_words = words[start : start + chunk_size]
            chunk_text = " ".join(chunk_words)

            chunks.append(
                TranscriptChunk(
                    id=f"{metadata.video_id}_{i + 1:03d}",
                    index=i + 1,
                    topic=f"Часть {i + 1}",
                    text=chunk_text,
                    word_count=len(chunk_words),
                )
            )

        return TranscriptChunks(
            chunks=chunks,
            model_name=self.settings.chunker_model,
        )

    def estimate_time(self, input_size: int) -> float:
        """Estimate chunking time.

        Args:
            input_size: Transcript length in characters

        Returns:
            Estimated time in seconds
        """
        # Base time + time per 1000 characters
        # Large texts need outline extraction which adds time
        base_time = 10.0
        if input_size > DEFAULT_LARGE_TEXT_THRESHOLD:
            # Add outline extraction time
            base_time += 20.0
        return base_time + input_size / 500
