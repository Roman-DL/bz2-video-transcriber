"""
Whisper transcription service.

Transcribes video/audio files via Whisper HTTP API.
Extracts audio from video before sending to Whisper for better reliability.

v0.42+: Added confidence and processing_time_sec metrics.
"""

import logging
import math
import time
from pathlib import Path

from app.config import Settings, get_settings
from app.models.schemas import RawTranscript, TranscriptSegment
from app.services.ai_clients import WhisperClient
from app.services.audio_extractor import AudioExtractor

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("app.perf")


class WhisperTranscriber:
    """
    Video/audio transcription service using Whisper API.

    Example:
        async with WhisperClient.from_settings(settings) as client:
            transcriber = WhisperTranscriber(client, settings)
            transcript = await transcriber.transcribe(Path("video.mp4"))
            print(transcript.full_text)
    """

    def __init__(self, whisper_client: WhisperClient, settings: Settings):
        """
        Initialize transcriber.

        Args:
            whisper_client: Whisper client for transcription API calls
            settings: Application settings
        """
        self.whisper_client = whisper_client
        self.settings = settings

    async def transcribe(
        self,
        video_path: Path,
        temp_dir: Path | None = None,
    ) -> tuple[RawTranscript, Path]:
        """
        Transcribe video file by extracting audio first.

        Extracts audio from video using ffmpeg, then sends audio to Whisper API.
        This approach is more reliable for long videos (55+ min).

        Args:
            video_path: Path to video file
            temp_dir: Directory for temporary audio file (default: settings.temp_dir)

        Returns:
            Tuple of (RawTranscript, audio_path)

        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If audio extraction fails
            httpx.HTTPStatusError: If API returns error
        """
        video_path = Path(video_path)
        video_size_mb = video_path.stat().st_size / 1024 / 1024

        logger.info(f"Starting transcription: {video_path.name} ({video_size_mb:.1f} MB)")

        start_time = time.time()

        # Step 1: Extract audio from video
        extractor = AudioExtractor(self.settings)
        audio_path = await extractor.extract(
            video_path,
            output_dir=temp_dir or self.settings.temp_dir,
        )

        extract_time = time.time() - start_time
        logger.info(f"Audio extraction took {extract_time:.1f}s")

        # Step 2: Send audio to Whisper API (not video!)
        whisper_start = time.time()
        response_data = await self.whisper_client.transcribe(
            file_path=audio_path,
            language=self.settings.whisper_language,
        )

        whisper_time = time.time() - whisper_start
        total_time = time.time() - start_time

        # Parse response into models with processing time
        transcript = self._parse_response(response_data, processing_time=total_time)

        conf_str = f", confidence={transcript.confidence:.2%}" if transcript.confidence else ""
        logger.info(
            f"Transcription complete: {len(transcript.segments)} segments, "
            f"{transcript.duration_seconds:.1f}s duration{conf_str}"
        )

        # Performance metrics for progress estimation
        perf_logger.info(
            f"PERF | transcribe | "
            f"size={video_size_mb:.1f}MB | "
            f"duration={transcript.duration_seconds:.0f}s | "
            f"extract={extract_time:.1f}s | "
            f"whisper={whisper_time:.1f}s | "
            f"total={total_time:.1f}s"
        )

        return transcript, audio_path

    def _parse_response(
        self,
        data: dict,
        processing_time: float | None = None,
    ) -> RawTranscript:
        """
        Parse Whisper API response into RawTranscript.

        Args:
            data: JSON response from Whisper API (verbose_json format)
            processing_time: Total processing time in seconds (v0.42+)

        Returns:
            RawTranscript with parsed segments and metrics
        """
        raw_segments = data.get("segments", [])

        # Parse segments
        segments = [
            TranscriptSegment(
                start=seg.get("start", 0.0),
                end=seg.get("end", 0.0),
                text=seg.get("text", "").strip(),
            )
            for seg in raw_segments
        ]

        # Calculate confidence from avg_logprob (v0.42+)
        # Whisper segments contain avg_logprob which is log probability
        # confidence = exp(avg_logprob), clamped to [0, 1]
        confidence = self._calculate_confidence(raw_segments)

        # Build RawTranscript with metrics
        return RawTranscript(
            segments=segments,
            language=data.get("language", self.settings.whisper_language),
            duration_seconds=data.get("duration", 0.0),
            whisper_model=self.settings.whisper_model,
            confidence=confidence,
            processing_time_sec=processing_time,
        )

    def _calculate_confidence(self, segments: list[dict]) -> float | None:
        """
        Calculate average confidence from Whisper segments.

        Uses avg_logprob from segments and converts to probability.
        confidence = exp(mean(avg_logprob))

        Args:
            segments: Raw segment data from Whisper API

        Returns:
            Confidence score 0-1, or None if not available
        """
        logprobs = []
        for seg in segments:
            logprob = seg.get("avg_logprob")
            if logprob is not None:
                logprobs.append(logprob)

        if not logprobs:
            return None

        avg_logprob = sum(logprobs) / len(logprobs)
        # Convert log probability to probability, clamp to [0, 1]
        confidence = min(1.0, max(0.0, math.exp(avg_logprob)))

        return round(confidence, 4)


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
            assert transcript.whisper_model == settings.whisper_model
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
        async with WhisperClient.from_settings(settings) as whisper:
            available = await whisper.check_health()

            if not available:
                print("SKIPPED (Whisper unavailable)")
            else:
                # Check if test file exists (only mp4 - we extract audio from video)
                test_files = list(Path(".").glob("*.mp4"))
                if not test_files:
                    print("SKIPPED (no test video)")
                else:
                    try:
                        transcriber = WhisperTranscriber(whisper, settings)
                        transcript, audio_path = await transcriber.transcribe(test_files[0])
                        print("OK")
                        print(f"  Video: {test_files[0].name}")
                        print(f"  Audio: {audio_path.name}")
                        print(f"  Segments: {len(transcript.segments)}")
                        print(f"  Duration: {transcript.duration_seconds:.1f}s")
                        # Clean up temp audio file
                        audio_path.unlink(missing_ok=True)
                    except Exception as e:
                        print(f"FAILED: {e}")
                        return 1

        print("\n" + "=" * 40)
        print("All tests passed!")
        return 0

    sys.exit(asyncio.run(run_tests()))
