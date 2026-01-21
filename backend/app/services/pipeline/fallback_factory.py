"""
Fallback object factory for pipeline stages.

Creates minimal valid objects when stage processing fails,
ensuring pipeline can complete with degraded results.

v0.25+: Simplified for new pipeline architecture.
        Chunks are now deterministic from H2 headers.
"""

import logging

from app.config import Settings
from app.models.schemas import (
    CleanedTranscript,
    Longread,
    LongreadSection,
    Summary,
    VideoMetadata,
    VideoSummary,
)

logger = logging.getLogger(__name__)


class FallbackFactory:
    """
    Factory for creating fallback objects when pipeline stages fail.

    All fallback objects contain valid data structure but minimal content,
    allowing the pipeline to complete and save results even on partial failures.

    v0.25+: Simplified - chunks are now deterministic from H2 headers.

    Example:
        factory = FallbackFactory(settings)
        longread = factory.create_longread_from_cleaned(metadata, cleaned_transcript)
        summary = factory.create_summary_from_cleaned(cleaned_transcript, metadata)
    """

    def __init__(self, settings: Settings):
        """
        Initialize fallback factory.

        Args:
            settings: Application settings for model names
        """
        self.settings = settings

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

    def create_longread_from_cleaned(
        self,
        metadata: VideoMetadata,
        cleaned_transcript: CleanedTranscript,
    ) -> Longread:
        """
        Create fallback longread from cleaned transcript when generation fails.

        Args:
            metadata: Video metadata
            cleaned_transcript: Cleaned transcript

        Returns:
            Longread with single section containing full text
        """
        logger.info(
            f"Creating fallback longread for: {metadata.video_id} "
            f"from cleaned transcript ({cleaned_transcript.word_count} words)"
        )

        sections = [
            LongreadSection(
                index=1,
                title=metadata.title,
                content=cleaned_transcript.text,
                source_chunks=[1],
                word_count=cleaned_transcript.word_count,
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

    print("\nRunning FallbackFactory tests (v0.25+)...\n")

    settings = get_settings()
    factory = FallbackFactory(settings)

    # Create mock data
    mock_cleaned = CleanedTranscript(
        text=" ".join(["word"] * 650),
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

    # Test 1: Create summary (legacy)
    print("Test 1: Create fallback summary (legacy)...", end=" ")
    summary = factory.create_summary(mock_metadata)
    assert "Test Video" in summary.summary
    assert summary.section == "Обучение"
    assert "ПШ" in summary.tags
    assert summary.access_level == 1
    print("OK")

    # Test 2: Create longread from cleaned
    print("Test 2: Create longread from cleaned...", end=" ")
    longread = factory.create_longread_from_cleaned(mock_metadata, mock_cleaned)
    assert longread.video_id == "test-video-id"
    assert longread.total_sections == 1
    assert longread.sections[0].title == "Test Video"
    assert longread.topic_area == ["мотивация"]
    assert longread.access_level == "consultant"
    print("OK")

    # Test 3: Create summary from cleaned
    print("Test 3: Create summary from cleaned...", end=" ")
    summary_from_cleaned = factory.create_summary_from_cleaned(mock_cleaned, mock_metadata)
    assert summary_from_cleaned.video_id == "test-video-id"
    assert summary_from_cleaned.topic_area == ["мотивация"]
    assert summary_from_cleaned.access_level == "consultant"
    assert len(summary_from_cleaned.essence) > 0
    print("OK")

    # Test 4: Metadata without stream
    print("Test 4: Metadata without stream...", end=" ")
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
    longread_no_stream = factory.create_longread_from_cleaned(mock_metadata_no_stream, mock_cleaned)
    assert longread_no_stream.tags == ["ПШ"]
    print("OK")

    print("\n" + "=" * 40)
    print("All FallbackFactory tests passed!")
