"""
Fallback object factory for pipeline stages.

Creates minimal valid objects when stage processing fails,
ensuring pipeline can complete with degraded results.
"""

import logging

from app.config import Settings
from app.models.schemas import (
    CleanedTranscript,
    Longread,
    LongreadSection,
    Summary,
    TranscriptChunk,
    TranscriptChunks,
    VideoMetadata,
    VideoSummary,
)

logger = logging.getLogger(__name__)


class FallbackFactory:
    """
    Factory for creating fallback objects when pipeline stages fail.

    All fallback objects contain valid data structure but minimal content,
    allowing the pipeline to complete and save results even on partial failures.

    Example:
        factory = FallbackFactory(settings)
        chunks = factory.create_chunks(cleaned_transcript, metadata)
        longread = factory.create_longread(metadata, chunks)
        summary = factory.create_summary_from_cleaned(cleaned_transcript, metadata)
    """

    def __init__(self, settings: Settings):
        """
        Initialize fallback factory.

        Args:
            settings: Application settings for model names
        """
        self.settings = settings

    def create_chunks(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
    ) -> TranscriptChunks:
        """
        Create fallback chunks when semantic chunking fails.

        Simply splits text into fixed-size chunks (~300 words each).

        Args:
            cleaned_transcript: Cleaned transcript text
            metadata: Video metadata for chunk IDs

        Returns:
            TranscriptChunks with simple word-based splits
        """
        text = cleaned_transcript.text
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

        logger.info(
            f"Created fallback chunks: {len(chunks)} chunks from {len(words)} words"
        )

        return TranscriptChunks(
            chunks=chunks,
            model_name=self.settings.chunker_model,
        )

    def create_summary(self, metadata: VideoMetadata) -> VideoSummary:
        """
        Create minimal fallback summary when summarization fails.

        Args:
            metadata: Video metadata for basic info

        Returns:
            VideoSummary with placeholder content
        """
        logger.info(f"Creating fallback summary for: {metadata.video_id}")

        return VideoSummary(
            summary=f"Видео '{metadata.title}' от {metadata.speaker}",
            key_points=["Саммари недоступно из-за технической ошибки"],
            recommendations=[],
            target_audience="Требует ручной обработки",
            questions_answered=[],
            section="Обучение",  # Legacy field for VideoSummary
            subsection="",
            tags=[metadata.event_type, metadata.stream] if metadata.stream else [metadata.event_type],
            access_level=1,  # VideoSummary uses int (1-4)
            model_name=self.settings.summarizer_model,
        )

    def create_longread(
        self,
        metadata: VideoMetadata,
        chunks: TranscriptChunks,
    ) -> Longread:
        """
        Create fallback longread when generation fails.

        Uses chunks directly as sections without additional processing.

        Args:
            metadata: Video metadata
            chunks: Transcript chunks to use as sections

        Returns:
            Longread with chunks as sections
        """
        logger.info(
            f"Creating fallback longread for: {metadata.video_id} "
            f"from {chunks.total_chunks} chunks"
        )

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
            topic_area=["мотивация"],  # Default topic area
            tags=[metadata.event_type, metadata.stream] if metadata.stream else [metadata.event_type],
            access_level="consultant",
            model_name=self.settings.summarizer_model,
        )

    def create_summary_from_cleaned(
        self,
        cleaned_transcript: CleanedTranscript,
        metadata: VideoMetadata,
    ) -> Summary:
        """
        Create fallback summary from cleaned transcript when summary generation fails.

        Args:
            cleaned_transcript: Cleaned transcript text
            metadata: Video metadata

        Returns:
            Summary with minimal data extracted from transcript
        """
        logger.info(f"Creating fallback summary from cleaned transcript: {metadata.video_id}")

        # Take first 500 chars as essence
        essence = cleaned_transcript.text[:500]
        if len(cleaned_transcript.text) > 500:
            essence = essence.rsplit(" ", 1)[0] + "..."

        return Summary(
            video_id=metadata.video_id,
            title=metadata.title,
            speaker=metadata.speaker,
            date=metadata.date,
            essence=essence,
            key_concepts=[],
            practical_tools=[],
            quotes=[],
            insight="Конспект недоступен из-за технической ошибки",
            actions=[],
            topic_area=["мотивация"],  # Default topic area
            tags=[metadata.event_type, metadata.stream] if metadata.stream else [metadata.event_type],
            access_level="consultant",
            model_name=self.settings.summarizer_model,
        )

if __name__ == "__main__":
    """Run tests when executed directly."""
    from datetime import date
    from pathlib import Path

    from app.config import get_settings

    print("\nRunning FallbackFactory tests...\n")

    settings = get_settings()
    factory = FallbackFactory(settings)

    # Create mock data
    mock_cleaned = CleanedTranscript(
        text=" ".join(["word"] * 650),  # 650 words -> 3 chunks
        original_length=1000,
        cleaned_length=650 * 5,
    )

    mock_metadata = VideoMetadata(
        date=date(2025, 1, 9),
        event_type="ПШ",
        stream="SV",
        title="Test Video",
        speaker="Test Speaker",
        original_filename="test.mp4",
        video_id="test-video-id",
        source_path=Path("/test/test.mp4"),
        archive_path=Path("/archive/test"),
    )

    # Test 1: Create chunks
    print("Test 1: Create fallback chunks...", end=" ")
    chunks = factory.create_chunks(mock_cleaned, mock_metadata)
    assert chunks.total_chunks == 3, f"Expected 3 chunks, got {chunks.total_chunks}"
    assert chunks.chunks[0].id == "test-video-id_001"
    assert chunks.chunks[0].topic == "Часть 1"
    assert chunks.chunks[0].word_count == 300
    assert chunks.chunks[2].word_count == 50  # Remaining words
    print("OK")
    print(f"  Chunks: {chunks.total_chunks}, sizes: {[c.word_count for c in chunks.chunks]}")

    # Test 2: Create summary
    print("Test 2: Create fallback summary...", end=" ")
    summary = factory.create_summary(mock_metadata)
    assert "Test Video" in summary.summary
    assert summary.section == "Обучение"
    assert "ПШ" in summary.tags
    assert summary.access_level == 1
    print("OK")
    print(f"  Summary: {summary.summary}")

    # Test 3: Create longread
    print("Test 3: Create fallback longread...", end=" ")
    longread = factory.create_longread(mock_metadata, chunks)
    assert longread.video_id == "test-video-id"
    assert longread.total_sections == 3
    assert longread.sections[0].title == "Часть 1"
    assert longread.topic_area == ["мотивация"]  # Default topic_area
    assert longread.access_level == "consultant"
    print("OK")
    print(f"  Sections: {longread.total_sections}, topic_area: {longread.topic_area}")

    # Test 4: Create summary from cleaned transcript (v0.24+)
    print("Test 4: Create summary from cleaned transcript...", end=" ")
    summary_from_cleaned = factory.create_summary_from_cleaned(mock_cleaned, mock_metadata)
    assert summary_from_cleaned.video_id == "test-video-id"
    assert summary_from_cleaned.topic_area == ["мотивация"]
    assert summary_from_cleaned.access_level == "consultant"
    assert len(summary_from_cleaned.essence) > 0
    print("OK")
    print(f"  Essence length: {len(summary_from_cleaned.essence)}")

    # Test 5: Metadata without stream
    print("Test 5: Metadata without stream...", end=" ")
    mock_metadata_no_stream = VideoMetadata(
        date=date(2025, 1, 9),
        event_type="ПШ",
        stream=None,
        title="Test Video",
        speaker="Test Speaker",
        original_filename="test.mp4",
        video_id="test-video-id",
        source_path=Path("/test/test.mp4"),
        archive_path=Path("/archive/test"),
    )
    summary_no_stream = factory.create_summary(mock_metadata_no_stream)
    assert summary_no_stream.tags == ["ПШ"]
    longread_no_stream = factory.create_longread(mock_metadata_no_stream, chunks)
    assert longread_no_stream.tags == ["ПШ"]
    print("OK")

    print("\n" + "=" * 40)
    print("All FallbackFactory tests passed!")
