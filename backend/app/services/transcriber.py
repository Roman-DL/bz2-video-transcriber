"""
Whisper transcription service.

Transcribes video/audio files via Whisper HTTP API.
"""

import logging
import time
from pathlib import Path

from app.config import Settings, get_settings
from app.models.schemas import RawTranscript, TranscriptSegment
from app.services.ai_client import AIClient

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("app.perf")


class WhisperTranscriber:
    """
    Video/audio transcription service using Whisper API.

    Example:
        async with AIClient(settings) as client:
            transcriber = WhisperTranscriber(client, settings)
            transcript = await transcriber.transcribe(Path("video.mp4"))
            print(transcript.full_text)
    """

    def __init__(self, ai_client: AIClient, settings: Settings):
        """
        Initialize transcriber.

        Args:
            ai_client: AI client for API calls
            settings: Application settings
        """
        self.ai_client = ai_client
        self.settings = settings

    async def transcribe(self, video_path: Path) -> RawTranscript:
        """
        Transcribe video/audio file.

        Args:
            video_path: Path to video/audio file

        Returns:
            RawTranscript with segments and metadata

        Raises:
            FileNotFoundError: If file doesn't exist
            httpx.HTTPStatusError: If API returns error
        """
        video_path = Path(video_path)
        file_size_mb = video_path.stat().st_size / 1024 / 1024

        logger.info(f"Starting transcription: {video_path.name}")

        start_time = time.time()

        # Call Whisper API via AIClient
        response_data = await self.ai_client.transcribe(
            file_path=video_path,
            language=self.settings.whisper_language,
        )

        elapsed = time.time() - start_time

        # Parse response into models
        transcript = self._parse_response(response_data)

        logger.info(
            f"Transcription complete: {len(transcript.segments)} segments, "
            f"{transcript.duration_seconds:.1f}s duration"
        )

        # Performance metrics for progress estimation
        perf_logger.info(
            f"PERF | transcribe | "
            f"size={file_size_mb:.1f}MB | "
            f"duration={transcript.duration_seconds:.0f}s | "
            f"time={elapsed:.1f}s"
        )

        return transcript

    def _parse_response(self, data: dict) -> RawTranscript:
        """
        Parse Whisper API response into RawTranscript.

        Args:
            data: JSON response from Whisper API (verbose_json format)

        Returns:
            RawTranscript with parsed segments
        """
        # Parse segments
        segments = [
            TranscriptSegment(
                start=seg.get("start", 0.0),
                end=seg.get("end", 0.0),
                text=seg.get("text", "").strip(),
            )
            for seg in data.get("segments", [])
        ]

        # Build RawTranscript
        return RawTranscript(
            segments=segments,
            language=data.get("language", self.settings.whisper_language),
            duration_seconds=data.get("duration", 0.0),
            whisper_model="large-v3",
        )


if __name__ == "__main__":
    """Run tests when executed directly."""
    import asyncio
    import sys

    # Configure logging for tests
    logging.basicConfig(level=logging.INFO)

    async def run_tests():
        """Run all transcriber tests."""
        print("\nRunning transcriber tests...\n")

        # Test 1: Parse mock response
        print("Test 1: Parse mock response...", end=" ")
        try:
            settings = get_settings()
            # Create transcriber without real client for parsing test
            transcriber = WhisperTranscriber(None, settings)  # type: ignore

            mock_response = {
                "text": "Привет, это тестовая транскрипция. Всё работает отлично.",
                "segments": [
                    {"start": 0.0, "end": 2.5, "text": "Привет, это тестовая транскрипция."},
                    {"start": 2.5, "end": 5.0, "text": "Всё работает отлично."},
                ],
                "language": "ru",
                "duration": 5.0,
            }

            transcript = transcriber._parse_response(mock_response)

            assert len(transcript.segments) == 2, f"Expected 2 segments, got {len(transcript.segments)}"
            assert transcript.language == "ru", f"Expected 'ru', got {transcript.language}"
            assert transcript.duration_seconds == 5.0, f"Expected 5.0, got {transcript.duration_seconds}"
            assert transcript.whisper_model == "large-v3"
            assert "Привет" in transcript.full_text

            print("OK")
            print(f"  Segments: {len(transcript.segments)}")
            print(f"  Duration: {transcript.duration_seconds}s")
            print(f"  Full text: {transcript.full_text[:50]}...")

        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 2: Computed properties
        print("\nTest 2: Computed properties...", end=" ")
        try:
            seg = transcript.segments[0]
            assert seg.start_time == "00:00:00", f"Expected 00:00:00, got {seg.start_time}"
            assert seg.end_time == "00:00:02", f"Expected 00:00:02, got {seg.end_time}"

            # text_with_timestamps
            assert "[00:00:00]" in transcript.text_with_timestamps

            print("OK")
            print(f"  First segment: {seg.start_time} - {seg.end_time}")

        except Exception as e:
            print(f"FAILED: {e}")
            return 1

        # Test 3: Real transcription (optional)
        print("\nTest 3: Real transcription...", end=" ")
        async with AIClient(settings) as client:
            status = await client.check_services()

            if not status["whisper"]:
                print("SKIPPED (Whisper unavailable)")
            else:
                # Check if test file exists
                test_files = list(Path(".").glob("*.mp4")) + list(Path(".").glob("*.mp3"))
                if not test_files:
                    print("SKIPPED (no test file)")
                else:
                    try:
                        transcriber = WhisperTranscriber(client, settings)
                        transcript = await transcriber.transcribe(test_files[0])
                        print("OK")
                        print(f"  File: {test_files[0].name}")
                        print(f"  Segments: {len(transcript.segments)}")
                        print(f"  Duration: {transcript.duration_seconds:.1f}s")
                    except Exception as e:
                        print(f"FAILED: {e}")
                        return 1

        print("\n" + "=" * 40)
        print("All tests passed!")
        return 0

    sys.exit(asyncio.run(run_tests()))
