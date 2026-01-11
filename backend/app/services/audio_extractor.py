"""
Audio extraction service using ffmpeg.

Extracts audio from video files for Whisper transcription.
"""

import asyncio
import logging
import subprocess
from pathlib import Path

from app.config import Settings

logger = logging.getLogger(__name__)


class AudioExtractor:
    """
    Extracts audio from video files using ffmpeg.

    Example:
        extractor = AudioExtractor(settings)
        audio_path = await extractor.extract(video_path)
    """

    def __init__(self, settings: Settings):
        """
        Initialize audio extractor.

        Args:
            settings: Application settings
        """
        self.settings = settings

    async def extract(
        self,
        video_path: Path,
        output_dir: Path | None = None,
    ) -> Path:
        """
        Extract audio from video file.

        Args:
            video_path: Path to input video file
            output_dir: Output directory (default: settings.temp_dir)

        Returns:
            Path to extracted audio file (MP3)

        Raises:
            RuntimeError: If ffmpeg fails
            FileNotFoundError: If video file doesn't exist
        """
        video_path = Path(video_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if output_dir is None:
            output_dir = self.settings.temp_dir

        output_dir.mkdir(parents=True, exist_ok=True)

        # Use video stem + _audio.mp3 extension
        audio_path = output_dir / f"{video_path.stem}_audio.mp3"

        video_size_mb = video_path.stat().st_size / 1024 / 1024
        logger.info(
            f"Extracting audio: {video_path.name} ({video_size_mb:.1f} MB) -> {audio_path.name}"
        )

        # Run ffmpeg in thread pool to not block event loop
        await asyncio.to_thread(self._run_ffmpeg, video_path, audio_path)

        if not audio_path.exists():
            raise RuntimeError("Audio extraction failed: output file not created")

        audio_size_mb = audio_path.stat().st_size / 1024 / 1024
        logger.info(f"Audio extracted: {audio_path.name} ({audio_size_mb:.1f} MB)")

        return audio_path

    def _run_ffmpeg(self, video_path: Path, audio_path: Path) -> None:
        """
        Run ffmpeg to extract audio.

        Args:
            video_path: Input video path
            audio_path: Output audio path

        Raises:
            RuntimeError: If ffmpeg returns non-zero exit code
        """
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-vn",                    # No video
            "-acodec", "libmp3lame",  # MP3 codec
            "-ab", "128k",            # Bitrate 128kbps (good for speech)
            "-ar", "44100",           # Sample rate
            "-y",                     # Overwrite output
            str(audio_path),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 min timeout
        )

        if result.returncode != 0:
            logger.error(f"ffmpeg failed: {result.stderr[:500]}")
            raise RuntimeError(f"ffmpeg error (code {result.returncode})")


if __name__ == "__main__":
    """Run tests when executed directly."""
    import sys
    import tempfile

    # Configure logging for tests
    logging.basicConfig(level=logging.INFO)

    async def run_tests():
        """Run all audio extractor tests."""
        print("\nRunning audio extractor tests...\n")

        from app.config import get_settings

        settings = get_settings()

        # Test 1: Check ffmpeg availability
        print("Test 1: Check ffmpeg availability...", end=" ")
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                print("FAILED (ffmpeg not working)")
                return 1
            print("OK")
            # Extract version from first line
            version_line = result.stdout.split("\n")[0]
            print(f"  {version_line}")
        except FileNotFoundError:
            print("FAILED (ffmpeg not installed)")
            return 1

        # Test 2: Extract from test video (if available)
        print("\nTest 2: Extract audio from video...", end=" ")

        # Find any mp4 file for testing
        test_files = list(Path(".").glob("*.mp4"))
        if not test_files:
            test_files = list(settings.inbox_dir.glob("*.mp4")) if settings.inbox_dir.exists() else []

        if not test_files:
            print("SKIPPED (no test video found)")
        else:
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    extractor = AudioExtractor(settings)
                    audio_path = await extractor.extract(
                        test_files[0],
                        output_dir=Path(temp_dir),
                    )

                    assert audio_path.exists(), "Audio file not created"
                    assert audio_path.suffix == ".mp3", f"Wrong extension: {audio_path.suffix}"

                    audio_size_mb = audio_path.stat().st_size / 1024 / 1024
                    video_size_mb = test_files[0].stat().st_size / 1024 / 1024

                    print("OK")
                    print(f"  Video: {test_files[0].name} ({video_size_mb:.1f} MB)")
                    print(f"  Audio: {audio_path.name} ({audio_size_mb:.1f} MB)")
                    print(f"  Compression: {audio_size_mb / video_size_mb * 100:.1f}%")

            except Exception as e:
                print(f"FAILED: {e}")
                return 1

        # Test 3: Handle missing file
        print("\nTest 3: Handle missing file...", end=" ")
        try:
            extractor = AudioExtractor(settings)
            await extractor.extract(Path("/nonexistent/video.mp4"))
            print("FAILED (should have raised FileNotFoundError)")
            return 1
        except FileNotFoundError:
            print("OK (FileNotFoundError raised as expected)")

        print("\n" + "=" * 40)
        print("All tests passed!")
        return 0

    sys.exit(asyncio.run(run_tests()))
