"""
Chunk stage for deterministic H2-based chunking.

v0.25+: Completely rewritten for deterministic chunking from longread/story markdown.
No longer uses LLM - parses H2 headers from generated documents.

Pipeline order changed:
    Before: Clean -> Chunk (LLM) -> Longread -> Summary
    After:  Clean -> Longread -> Summary -> Chunk (H2 parsing)
"""

import logging

from app.config import Settings
from app.models.schemas import (
    ContentType,
    Longread,
    ProcessingStatus,
    Story,
    TranscriptChunks,
    VideoMetadata,
)
from app.services.stages.base import BaseStage, StageContext, StageError
from app.utils.h2_chunker import chunk_by_h2

logger = logging.getLogger(__name__)


class ChunkStage(BaseStage):
    """Deterministic chunking from longread/story markdown.

    v0.25+: No LLM dependency - parses H2 headers from generated documents.
    Creates semantic chunks for RAG retrieval.

    Pipeline dependency:
        - Educational: depends on longread
        - Leadership: depends on story

    Input (from context):
        - parse: VideoMetadata (for video_id and content_type)
        - longread: Longread (for educational content)
        - story: Story (for leadership content)

    Output:
        TranscriptChunks with deterministic H2-based chunks

    Example:
        stage = ChunkStage(settings)
        chunks = await stage.execute(context)
    """

    name = "chunk"
    depends_on = ["parse", "longread", "story"]
    status = ProcessingStatus.CHUNKING

    def __init__(self, settings: Settings):
        """Initialize chunk stage.

        v0.25+: No AI client needed - deterministic chunking.

        Args:
            settings: Application settings
        """
        self.settings = settings

    async def execute(self, context: StageContext) -> TranscriptChunks:
        """Chunk from longread or story markdown.

        Args:
            context: Context with parse and longread/story results

        Returns:
            TranscriptChunks from H2 headers

        Raises:
            StageError: If no source document found
        """
        self.validate_context(context)

        metadata: VideoMetadata = context.get_result("parse")

        # Get markdown from appropriate source
        markdown = self._get_source_markdown(context, metadata)

        if not markdown:
            raise StageError("No longread or story found for chunking")

        # Deterministic H2 chunking
        chunks = chunk_by_h2(markdown, metadata.video_id)

        logger.info(
            f"Chunked by H2: {chunks.total_chunks} chunks, "
            f"avg {chunks.avg_chunk_size} words"
        )

        return chunks

    def _get_source_markdown(
        self, context: StageContext, metadata: VideoMetadata
    ) -> str | None:
        """Get markdown from appropriate source based on content type.

        Args:
            context: Stage context
            metadata: Video metadata with content_type

        Returns:
            Markdown string or None if not found
        """
        # Educational content → longread
        if metadata.content_type == ContentType.EDUCATIONAL:
            if context.has_result("longread"):
                longread: Longread = context.get_result("longread")
                return longread.to_markdown()

        # Leadership content → story
        elif metadata.content_type == ContentType.LEADERSHIP:
            if context.has_result("story"):
                story: Story = context.get_result("story")
                return story.to_markdown()

        # Fallback: try both
        if context.has_result("longread"):
            longread = context.get_result("longread")
            return longread.to_markdown()

        if context.has_result("story"):
            story = context.get_result("story")
            return story.to_markdown()

        return None

    def estimate_time(self, input_size: int) -> float:
        """Estimate chunking time.

        v0.25+: Deterministic chunking is nearly instant.

        Args:
            input_size: Ignored (instant operation)

        Returns:
            Estimated time in seconds (< 1s)
        """
        return 0.1  # Nearly instant - just string parsing


# Embedded tests
if __name__ == "__main__":
    import sys
    from datetime import date
    from pathlib import Path
    from unittest.mock import MagicMock

    print("\n" + "=" * 60)
    print("ChunkStage Tests (v0.25+)")
    print("=" * 60 + "\n")

    errors = 0

    # Test 1: Initialization (no AI client)
    print("Test 1: Initialization (no AI client)...", end=" ")
    try:
        settings = MagicMock()
        stage = ChunkStage(settings)
        assert stage.name == "chunk"
        assert "longread" in stage.depends_on
        assert "story" in stage.depends_on
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors += 1

    # Test 2: Educational content chunking
    print("Test 2: Educational content chunking...", end=" ")
    try:
        settings = MagicMock()
        stage = ChunkStage(settings)

        # Mock context
        context = MagicMock()
        context.get_result.side_effect = lambda key: {
            "parse": MagicMock(
                video_id="test-123",
                content_type=ContentType.EDUCATIONAL,
            ),
            "longread": MagicMock(
                to_markdown=lambda: """---
type: "лонгрид"
---

# Заголовок

## Введение
Текст введения.

## Основная часть
Текст основной части.

## Заключение
Текст заключения.
"""
            ),
        }.get(key)
        context.has_result.side_effect = lambda key: key in ["parse", "longread"]

        import asyncio
        chunks = asyncio.run(stage.execute(context))

        assert chunks.total_chunks == 3
        assert chunks.model_name == "deterministic"
        print("OK")
        print(f"  Chunks: {[c.topic for c in chunks.chunks]}")
    except Exception as e:
        print(f"FAILED: {e}")
        errors += 1

    # Test 3: Leadership content chunking
    print("Test 3: Leadership content chunking...", end=" ")
    try:
        settings = MagicMock()
        stage = ChunkStage(settings)

        # Mock context
        context = MagicMock()
        context.get_result.side_effect = lambda key: {
            "parse": MagicMock(
                video_id="story-456",
                content_type=ContentType.LEADERSHIP,
            ),
            "story": MagicMock(
                to_markdown=lambda: """---
type: "leadership-story"
---

# История

## 1️⃣ Кто они
Описание персонажей.

## 2️⃣ Проблема
Описание проблемы.
"""
            ),
        }.get(key)
        context.has_result.side_effect = lambda key: key in ["parse", "story"]

        import asyncio
        chunks = asyncio.run(stage.execute(context))

        assert chunks.total_chunks == 2
        # Emoji should be stripped
        assert chunks.chunks[0].topic == "Кто они"
        assert chunks.chunks[1].topic == "Проблема"
        print("OK")
        print(f"  Chunks: {[c.topic for c in chunks.chunks]}")
    except Exception as e:
        print(f"FAILED: {e}")
        errors += 1

    # Test 4: Estimate time (instant)
    print("Test 4: Estimate time (instant)...", end=" ")
    try:
        settings = MagicMock()
        stage = ChunkStage(settings)
        time_estimate = stage.estimate_time(100000)  # Large input
        assert time_estimate < 1.0  # Should be instant
        print("OK")
        print(f"  Estimate: {time_estimate}s")
    except Exception as e:
        print(f"FAILED: {e}")
        errors += 1

    # Summary
    print("\n" + "=" * 60)
    if errors == 0:
        print("All tests passed!")
        sys.exit(0)
    else:
        print(f"{errors} test(s) failed!")
        sys.exit(1)
