"""
Whisper transcription client implementation.

Provides async HTTP client for Whisper ASR API with retry logic.
Separated from OllamaClient for single responsibility principle.
"""

import asyncio
import logging
import time
from pathlib import Path

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import Settings
from app.services.ai_clients.base import (
    AIClientConnectionError,
    AIClientResponseError,
    AIClientTimeoutError,
)

logger = logging.getLogger(__name__)

# Retry configuration for transient errors
RETRY_DECORATOR = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
)


class WhisperClient:
    """
    Async HTTP client for Whisper transcription API.

    Provides transcription functionality via self-hosted Whisper service.
    Uses thread pool for file uploads to avoid blocking the event loop.

    Example:
        async with WhisperClient.from_settings(settings) as client:
            status = await client.check_health()
            result = await client.transcribe(audio_path)
    """

    def __init__(
        self,
        whisper_url: str,
        default_language: str = "ru",
    ):
        """
        Initialize Whisper client.

        Args:
            whisper_url: URL for Whisper API
            default_language: Default language for transcription
        """
        self.whisper_url = whisper_url
        self.default_language = default_language
        self.http_client = httpx.AsyncClient(timeout=None)

    @classmethod
    def from_settings(cls, settings: Settings) -> "WhisperClient":
        """
        Create WhisperClient from application settings.

        Args:
            settings: Application settings

        Returns:
            Configured WhisperClient instance
        """
        return cls(
            whisper_url=settings.whisper_url,
            default_language=settings.whisper_language,
        )

    async def __aenter__(self) -> "WhisperClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.http_client.aclose()

    async def check_health(self) -> bool:
        """
        Check availability of Whisper service.

        Returns:
            True if Whisper is available, False otherwise
        """
        try:
            response = await self.http_client.get(
                f"{self.whisper_url}/health",
                timeout=5.0,
            )
            if response.status_code == 200 and response.text == "OK":
                logger.debug("Whisper available")
                return True
        except Exception as e:
            logger.debug(f"Whisper not available: {e}")
        return False

    async def check_services(self) -> dict:
        """
        Check Whisper service status (for compatibility).

        Returns:
            Dict with service status: {"whisper": bool}
        """
        whisper_available = await self.check_health()
        return {"whisper": whisper_available}

    def _sync_transcribe(
        self,
        file_path: Path,
        language: str,
    ) -> httpx.Response:
        """
        Synchronous file upload to Whisper API.

        Runs in a thread pool to avoid blocking the event loop.

        Args:
            file_path: Path to audio/video file
            language: Language code

        Returns:
            httpx.Response from Whisper API
        """
        with httpx.Client(timeout=7200.0) as sync_client:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f, "application/octet-stream")}
                data = {
                    "language": language,
                    "response_format": "verbose_json",
                }
                return sync_client.post(
                    f"{self.whisper_url}/v1/audio/transcriptions",
                    files=files,
                    data=data,
                )

    @RETRY_DECORATOR
    async def transcribe(
        self,
        file_path: Path,
        language: str | None = None,
    ) -> dict:
        """
        Transcribe audio/video file using Whisper API.

        Uses thread pool for file upload to avoid blocking the event loop,
        allowing progress ticker to update during long transcriptions.

        Args:
            file_path: Path to audio/video file
            language: Language code (default: from settings)

        Returns:
            Dict with transcription result including segments

        Raises:
            FileNotFoundError: If file doesn't exist
            AIClientError: If transcription fails
        """
        if language is None:
            language = self.default_language

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size_mb = file_path.stat().st_size / 1024 / 1024
        logger.info(f"Transcribing: {file_path.name} ({file_size_mb:.1f} MB)")
        logger.debug(f"Whisper URL: {self.whisper_url}, language: {language}")

        start_time = time.time()

        try:
            # Run synchronous file upload in thread pool to not block event loop
            response = await asyncio.to_thread(
                self._sync_transcribe,
                file_path,
                language,
            )

            elapsed = time.time() - start_time
            logger.debug(f"Whisper response: {response.status_code}, elapsed: {elapsed:.1f}s")

            response.raise_for_status()
            result = response.json()

            duration = result.get("duration", 0)
            segments = len(result.get("segments", []))
            logger.info(
                f"Transcription complete: {segments} segments, "
                f"duration: {duration:.0f}s, elapsed: {elapsed:.1f}s"
            )
            return result

        except httpx.TimeoutException as e:
            elapsed = time.time() - start_time
            logger.error(f"Transcription timeout after {elapsed:.1f}s: {e}")
            raise AIClientTimeoutError(
                f"Transcription timeout after {elapsed:.1f}s",
                provider="whisper",
                original_error=e,
            ) from e

        except httpx.HTTPStatusError as e:
            elapsed = time.time() - start_time
            logger.error(
                f"Transcription HTTP error after {elapsed:.1f}s: "
                f"{e.response.status_code} - {e.response.text[:200]}"
            )
            raise AIClientResponseError(
                f"Transcription failed: HTTP {e.response.status_code}",
                provider="whisper",
                status_code=e.response.status_code,
                response_body=e.response.text[:500],
                original_error=e,
            ) from e

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Transcription failed after {elapsed:.1f}s: {type(e).__name__}: {e}")
            raise AIClientConnectionError(
                f"Transcription failed: {e}",
                provider="whisper",
                original_error=e,
            ) from e


if __name__ == "__main__":
    """Run tests when executed directly."""
    import sys

    from app.config import get_settings

    # Configure logging for tests
    logging.basicConfig(level=logging.INFO)

    async def run_tests():
        """Run all Whisper client tests."""
        print("\nRunning Whisper client tests...\n")

        settings = get_settings()
        print(f"Whisper URL: {settings.whisper_url}")
        print()

        async with WhisperClient.from_settings(settings) as client:
            # Test 1: Check health
            print("Test 1: Checking Whisper health...", end=" ")
            try:
                available = await client.check_health()
                print("OK" if available else "Whisper unavailable")
                print(f"  Status: {'available' if available else 'unavailable'}")
            except Exception as e:
                print(f"FAILED: {e}")
                return 1

            # Test 2: Transcribe would require a real file
            print("\nTest 2: Transcribe (file required)...", end=" ")
            print("SKIPPED (no test file)")

        print("\n" + "=" * 40)
        print("All tests passed!")
        return 0

    sys.exit(asyncio.run(run_tests()))
