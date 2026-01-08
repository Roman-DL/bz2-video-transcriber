"""
File saver service.

Saves processing results to the archive directory structure.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

from app.config import Settings, get_settings, load_events_config
from app.models.schemas import (
    RawTranscript,
    TranscriptChunks,
    VideoMetadata,
    VideoSummary,
)

logger = logging.getLogger(__name__)

# Pipeline version for tracking
PIPELINE_VERSION = "1.0.0"

# Russian month names for date formatting
RUSSIAN_MONTHS = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]


class FileSaver:
    """
    File saver service for archive storage.

    Saves all processing results to the archive directory:
    - transcript_chunks.json - structured chunks for RAG
    - summary.md - markdown summary with YAML frontmatter
    - transcript_raw.txt - raw transcript with timestamps
    - video file - moved from inbox to archive

    Example:
        saver = FileSaver(settings)
        files = await saver.save(metadata, raw_transcript, chunks, summary)
        print(f"Created: {files}")
        # ['transcript_chunks.json', 'summary.md', 'transcript_raw.txt', 'video.mp4']
    """

    def __init__(self, settings: Settings):
        """
        Initialize file saver.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.events_config = load_events_config(settings)

    async def save(
        self,
        metadata: VideoMetadata,
        raw_transcript: RawTranscript,
        chunks: TranscriptChunks,
        summary: VideoSummary,
    ) -> list[str]:
        """
        Save all processing results to archive.

        Creates archive directory structure and saves:
        - transcript_chunks.json
        - summary.md
        - transcript_raw.txt
        - moves video file

        Args:
            metadata: Video metadata
            raw_transcript: Raw transcript from Whisper
            chunks: Semantic chunks
            summary: Video summary

        Returns:
            List of created file names
        """
        archive_path = metadata.archive_path

        logger.info(f"Saving results to: {archive_path}")

        # Create archive directory
        archive_path.mkdir(parents=True, exist_ok=True)

        created_files = []

        # Save transcript chunks JSON
        chunks_path = self._save_chunks_json(
            archive_path, metadata, raw_transcript, chunks
        )
        created_files.append(chunks_path.name)

        # Save summary markdown
        summary_path = self._save_summary_md(
            archive_path, metadata, raw_transcript, summary
        )
        created_files.append(summary_path.name)

        # Save raw transcript
        raw_path = self._save_raw_transcript(archive_path, raw_transcript)
        created_files.append(raw_path.name)

        # Move video file
        video_path = self._move_video(metadata.source_path, archive_path)
        created_files.append(video_path.name)

        logger.info(f"Save complete: {len(created_files)} files created")

        return created_files

    def _save_chunks_json(
        self,
        archive_path: Path,
        metadata: VideoMetadata,
        raw_transcript: RawTranscript,
        chunks: TranscriptChunks,
    ) -> Path:
        """
        Save transcript chunks as JSON for RAG indexing.

        Args:
            archive_path: Archive directory path
            metadata: Video metadata
            raw_transcript: Raw transcript
            chunks: Semantic chunks

        Returns:
            Path to created file
        """
        # Calculate statistics
        total_words = sum(c.word_count for c in chunks.chunks)

        # Get full stream name
        stream_name = self._get_stream_name(metadata.event_type, metadata.stream)

        data = {
            "video_id": metadata.video_id,
            "metadata": {
                "title": metadata.title,
                "speaker": metadata.speaker,
                "date": metadata.date.isoformat(),
                "event_type": metadata.event_type,
                "stream": metadata.stream,
                "stream_name": stream_name,
                "duration_seconds": raw_transcript.duration_seconds,
                "duration_formatted": self._format_duration(
                    raw_transcript.duration_seconds
                ),
                "language": raw_transcript.language,
                "whisper_model": raw_transcript.whisper_model,
                "processed_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            "statistics": {
                "total_chunks": chunks.total_chunks,
                "avg_chunk_words": chunks.avg_chunk_size,
                "total_words": total_words,
            },
            "chunks": [
                {
                    "id": chunk.id,
                    "index": chunk.index,
                    "topic": chunk.topic,
                    "text": chunk.text,
                    "word_count": chunk.word_count,
                }
                for chunk in chunks.chunks
            ],
        }

        file_path = archive_path / "transcript_chunks.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.debug(f"Saved chunks JSON: {file_path}")

        return file_path

    def _save_summary_md(
        self,
        archive_path: Path,
        metadata: VideoMetadata,
        raw_transcript: RawTranscript,
        summary: VideoSummary,
    ) -> Path:
        """
        Save summary as Markdown with YAML frontmatter.

        Args:
            archive_path: Archive directory path
            metadata: Video metadata
            raw_transcript: Raw transcript
            summary: Video summary

        Returns:
            Path to created file
        """
        stream_name = self._get_stream_name(metadata.event_type, metadata.stream)
        date_formatted = self._format_date_russian(metadata.date)
        duration_formatted = self._format_duration(raw_transcript.duration_seconds)

        # Build YAML frontmatter
        frontmatter_lines = [
            "---",
            "# === Identification ===",
            f'video_id: "{metadata.video_id}"',
            f'title: "{metadata.title}"',
            'type: "video_summary"',
            "",
            "# === Source ===",
            f'speaker: "{metadata.speaker}"',
            f'date: "{metadata.date.isoformat()}"',
            f'event_type: "{metadata.event_type}"',
            f'stream: "{metadata.stream}"',
            f'stream_name: "{stream_name}"',
            f'duration: "{duration_formatted}"',
            "",
            "# === Classification for BZ 2.0 ===",
            f'section: "{summary.section}"',
            f'subsection: "{summary.subsection}"',
            f"access_level: {summary.access_level}",
            "tags:",
        ]

        for tag in summary.tags:
            frontmatter_lines.append(f'  - "{tag}"')

        frontmatter_lines.extend([
            "",
            "# === Files ===",
            f'video_file: "{metadata.original_filename}"',
            'transcript_file: "transcript_chunks.json"',
            "",
            "# === Service ===",
            f'created: "{datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")}"',
            f'llm_model: "{self.settings.llm_model}"',
            f'pipeline_version: "{PIPELINE_VERSION}"',
            "---",
        ])

        # Build Markdown body
        body_lines = [
            "",
            f"# {metadata.title}",
            "",
            f"**Спикер:** {metadata.speaker}  ",
            f"**Дата:** {date_formatted}  ",
            f"**Поток:** {stream_name}",
            "",
            "---",
            "",
            "## Краткое содержание",
            "",
            summary.summary,
            "",
            "## Ключевые тезисы",
            "",
        ]

        for point in summary.key_points:
            body_lines.append(f"- {point}")

        body_lines.extend([
            "",
            "## Практические рекомендации",
            "",
        ])

        for i, rec in enumerate(summary.recommendations, 1):
            body_lines.append(f"{i}. {rec}")

        body_lines.extend([
            "",
            "## Для кого полезно",
            "",
            summary.target_audience,
            "",
            "## Вопросы, на которые отвечает видео",
            "",
        ])

        for q in summary.questions_answered:
            body_lines.append(f"- {q}")

        body_lines.append("")

        # Combine and write
        content = "\n".join(frontmatter_lines + body_lines)
        file_path = archive_path / "summary.md"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.debug(f"Saved summary MD: {file_path}")

        return file_path

    def _save_raw_transcript(
        self,
        archive_path: Path,
        raw_transcript: RawTranscript,
    ) -> Path:
        """
        Save raw transcript with timestamps.

        Args:
            archive_path: Archive directory path
            raw_transcript: Raw transcript

        Returns:
            Path to created file
        """
        file_path = archive_path / "transcript_raw.txt"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(raw_transcript.text_with_timestamps)

        logger.debug(f"Saved raw transcript: {file_path}")

        return file_path

    def _move_video(self, source: Path, dest_dir: Path) -> Path:
        """
        Move video file to archive directory.

        Args:
            source: Source video path
            dest_dir: Destination directory

        Returns:
            Path to moved file
        """
        dest_path = dest_dir / source.name

        shutil.move(str(source), str(dest_path))

        logger.debug(f"Moved video: {source} -> {dest_path}")

        return dest_path

    def _get_stream_name(self, event_type: str, stream: str) -> str:
        """
        Get full stream name from events config.

        Args:
            event_type: Event type code (e.g., "ПШ")
            stream: Stream code (e.g., "SV")

        Returns:
            Full stream name (e.g., "Понедельничная Школа — Супервайзеры")
        """
        event_types = self.events_config.get("event_types", {})

        event_info = event_types.get(event_type, {})
        event_name = event_info.get("name", event_type)

        streams = event_info.get("streams", {})
        stream_desc = streams.get(stream, stream)

        return f"{event_name} — {stream_desc}"

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """
        Format duration in seconds as HH:MM:SS.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration string
        """
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    @staticmethod
    def _format_date_russian(d) -> str:
        """
        Format date in Russian (e.g., "7 апреля 2025").

        Args:
            d: Date object

        Returns:
            Formatted date string
        """
        return f"{d.day} {RUSSIAN_MONTHS[d.month]} {d.year}"


if __name__ == "__main__":
    """Run tests when executed directly."""
    import asyncio
    import sys
    import tempfile
    from datetime import date

    # Configure logging for tests
    logging.basicConfig(level=logging.INFO)

    async def run_tests():
        """Run all saver tests."""
        print("\nRunning saver tests...\n")

        settings = get_settings()

        # Test 1: Format duration
        print("Test 1: Format duration...", end=" ")
        try:
            assert FileSaver._format_duration(0) == "00:00:00"
            assert FileSaver._format_duration(61) == "00:01:01"
            assert FileSaver._format_duration(3661) == "01:01:01"
            assert FileSaver._format_duration(5025) == "01:23:45"
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 2: Format date Russian
        print("Test 2: Format date Russian...", end=" ")
        try:
            d = date(2025, 4, 7)
            formatted = FileSaver._format_date_russian(d)
            assert formatted == "7 апреля 2025", f"Got: {formatted}"
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 3: Get stream name
        print("Test 3: Get stream name...", end=" ")
        try:
            saver = FileSaver(settings)
            stream_name = saver._get_stream_name("ПШ", "SV")
            assert "Понедельничная Школа" in stream_name, f"Got: {stream_name}"
            assert "Супервайзеры" in stream_name, f"Got: {stream_name}"
            print("OK")
            print(f"  Stream name: {stream_name}")
        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 4: Full save cycle with temp directory
        print("\nTest 4: Full save cycle...", end=" ")
        try:
            from app.models.schemas import TranscriptChunk, TranscriptSegment

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Create mock video file
                inbox_dir = temp_path / "inbox"
                inbox_dir.mkdir()
                video_file = inbox_dir / "2025.04.07 ПШ.SV Test Video (Test Speaker).mp4"
                video_file.write_text("mock video content")

                # Create archive path
                archive_dir = temp_path / "archive" / "2025" / "04" / "ПШ.SV" / "Test Video (Test Speaker)"

                # Create mock metadata
                metadata = VideoMetadata(
                    date=date(2025, 4, 7),
                    event_type="ПШ",
                    stream="SV",
                    title="Test Video",
                    speaker="Test Speaker",
                    original_filename=video_file.name,
                    video_id="2025-04-07_ПШ-SV_test-video",
                    source_path=video_file,
                    archive_path=archive_dir,
                )

                # Create mock raw transcript
                raw_transcript = RawTranscript(
                    segments=[
                        TranscriptSegment(start=0.0, end=5.0, text="First segment."),
                        TranscriptSegment(start=5.0, end=10.0, text="Second segment."),
                    ],
                    language="ru",
                    duration_seconds=5025.0,
                    whisper_model="large-v3",
                )

                # Create mock chunks
                chunks = TranscriptChunks(
                    chunks=[
                        TranscriptChunk(
                            id="2025-04-07_ПШ-SV_test-video_001",
                            index=1,
                            topic="Introduction",
                            text="This is the introduction text.",
                            word_count=5,
                        ),
                        TranscriptChunk(
                            id="2025-04-07_ПШ-SV_test-video_002",
                            index=2,
                            topic="Main content",
                            text="This is the main content.",
                            word_count=5,
                        ),
                    ]
                )

                # Create mock summary
                summary = VideoSummary(
                    summary="This is a test summary.",
                    key_points=["Point 1", "Point 2"],
                    recommendations=["Recommendation 1"],
                    target_audience="All users",
                    questions_answered=["Question 1?"],
                    section="Обучение",
                    subsection="Тестирование",
                    tags=["test", "demo"],
                    access_level=1,
                )

                # Run save
                saver = FileSaver(settings)
                files = await saver.save(metadata, raw_transcript, chunks, summary)

                # Verify results
                assert len(files) == 4, f"Expected 4 files, got {len(files)}"
                assert "transcript_chunks.json" in files
                assert "summary.md" in files
                assert "transcript_raw.txt" in files
                assert video_file.name in files

                # Verify files exist
                assert (archive_dir / "transcript_chunks.json").exists()
                assert (archive_dir / "summary.md").exists()
                assert (archive_dir / "transcript_raw.txt").exists()
                assert (archive_dir / video_file.name).exists()

                # Verify JSON content
                with open(archive_dir / "transcript_chunks.json", "r", encoding="utf-8") as f:
                    json_data = json.load(f)
                assert json_data["video_id"] == metadata.video_id
                assert len(json_data["chunks"]) == 2

                # Verify summary content
                summary_content = (archive_dir / "summary.md").read_text(encoding="utf-8")
                assert "video_id:" in summary_content
                assert "Test Video" in summary_content
                assert "Краткое содержание" in summary_content

                # Verify raw transcript
                raw_content = (archive_dir / "transcript_raw.txt").read_text(encoding="utf-8")
                assert "[00:00:00]" in raw_content
                assert "First segment." in raw_content

                print("OK")
                print(f"  Created files: {files}")
                print(f"  Archive path: {archive_dir}")

        except Exception as e:
            print(f"FAILED: {e}")
            import traceback
            traceback.print_exc()
            return 1

        print("\n" + "=" * 40)
        print("All tests passed!")
        return 0

    sys.exit(asyncio.run(run_tests()))
