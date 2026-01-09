"""
AI client for Ollama and Whisper APIs.

Provides async HTTP client with retry logic for:
- Ollama: text generation and chat completions
- Whisper: audio/video transcription
"""

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

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Retry configuration for transient errors
RETRY_DECORATOR = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
)


class AIClient:
    """
    Async HTTP client for Ollama and Whisper AI services.

    Example:
        async with AIClient(settings) as client:
            status = await client.check_services()
            response = await client.generate("Hello!")
    """

    def __init__(self, settings: Settings):
        """
        Initialize AI client.

        Args:
            settings: Application settings with AI service URLs
        """
        self.settings = settings
        self.http_client = httpx.AsyncClient(timeout=settings.llm_timeout)

    async def __aenter__(self) -> "AIClient":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.http_client.aclose()

    async def check_services(self) -> dict:
        """
        Check availability of Ollama and Whisper services.

        Returns:
            Dict with service status:
            {
                "ollama": bool,
                "whisper": bool,
                "ollama_version": str | None
            }
        """
        ollama_available = False
        ollama_version = None
        whisper_available = False

        # Check Ollama
        try:
            response = await self.http_client.get(
                f"{self.settings.ollama_url}/api/version",
                timeout=5.0,
            )
            if response.status_code == 200:
                ollama_available = True
                data = response.json()
                ollama_version = data.get("version")
                logger.debug(f"Ollama available, version: {ollama_version}")
        except Exception as e:
            logger.debug(f"Ollama not available: {e}")

        # Check Whisper
        try:
            response = await self.http_client.get(
                f"{self.settings.whisper_url}/health",
                timeout=5.0,
            )
            if response.status_code == 200 and response.text == "OK":
                whisper_available = True
                logger.debug("Whisper available")
        except Exception as e:
            logger.debug(f"Whisper not available: {e}")

        return {
            "ollama": ollama_available,
            "whisper": whisper_available,
            "ollama_version": ollama_version,
        }

    @RETRY_DECORATOR
    async def transcribe(
        self,
        file_path: Path,
        language: str | None = None,
    ) -> dict:
        """
        Transcribe audio/video file using Whisper API.

        Args:
            file_path: Path to audio/video file
            language: Language code (default: from settings)

        Returns:
            Dict with transcription result including segments

        Raises:
            httpx.HTTPStatusError: If API returns error status
            FileNotFoundError: If file doesn't exist
        """
        if language is None:
            language = self.settings.whisper_language

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size_mb = file_path.stat().st_size / 1024 / 1024
        logger.info(f"Transcribing: {file_path.name} ({file_size_mb:.1f} MB)")
        logger.debug(f"Whisper URL: {self.settings.whisper_url}, language: {language}")

        start_time = time.time()

        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f, "application/octet-stream")}
                data = {
                    "language": language,
                    "response_format": "verbose_json",
                }

                response = await self.http_client.post(
                    f"{self.settings.whisper_url}/v1/audio/transcriptions",
                    files=files,
                    data=data,
                    timeout=7200.0,  # 2 hours for long videos
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
            raise

        except httpx.HTTPStatusError as e:
            elapsed = time.time() - start_time
            logger.error(
                f"Transcription HTTP error after {elapsed:.1f}s: "
                f"{e.response.status_code} - {e.response.text[:200]}"
            )
            raise

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Transcription failed after {elapsed:.1f}s: {type(e).__name__}: {e}")
            raise

    @RETRY_DECORATOR
    async def generate(
        self,
        prompt: str,
        model: str | None = None,
    ) -> str:
        """
        Generate text using Ollama /api/generate endpoint.

        Args:
            prompt: Text prompt for generation
            model: Model name (default: from settings)

        Returns:
            Generated text response

        Raises:
            httpx.HTTPStatusError: If API returns error status
        """
        if model is None:
            model = self.settings.llm_model

        logger.debug(f"Generating with {model}, prompt length: {len(prompt)}")

        response = await self.http_client.post(
            f"{self.settings.ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
            },
        )

        response.raise_for_status()
        result = response.json()

        response_text = result.get("response", "")
        logger.debug(f"Generated {len(response_text)} chars")

        return response_text

    @RETRY_DECORATOR
    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """
        Chat completion using Ollama OpenAI-compatible endpoint.

        Args:
            messages: List of chat messages [{"role": "user", "content": "..."}]
            model: Model name (default: from settings)
            temperature: Sampling temperature (default: 0.7)

        Returns:
            Assistant's response content

        Raises:
            httpx.HTTPStatusError: If API returns error status
        """
        if model is None:
            model = self.settings.llm_model

        logger.debug(f"Chat with {model}, {len(messages)} messages")

        response = await self.http_client.post(
            f"{self.settings.ollama_url}/v1/chat/completions",
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
            },
        )

        response.raise_for_status()
        result = response.json()

        content = result["choices"][0]["message"]["content"]
        logger.debug(f"Chat response: {len(content)} chars")

        return content


if __name__ == "__main__":
    """Run tests when executed directly."""
    import asyncio
    import sys

    # Configure logging for tests
    logging.basicConfig(level=logging.INFO)

    async def run_tests():
        """Run all AI client tests."""
        print("\nRunning AI client tests...\n")

        settings = get_settings()
        print(f"Ollama URL: {settings.ollama_url}")
        print(f"Whisper URL: {settings.whisper_url}")
        print(f"LLM Model: {settings.llm_model}")
        print()

        async with AIClient(settings) as client:
            # Test 1: Check services
            print("Test 1: Checking services...", end=" ")
            try:
                status = await client.check_services()
                print("OK")
                print(f"  Ollama: {'available' if status['ollama'] else 'unavailable'}")
                if status['ollama_version']:
                    print(f"  Ollama version: {status['ollama_version']}")
                print(f"  Whisper: {'available' if status['whisper'] else 'unavailable'}")
            except Exception as e:
                print(f"FAILED: {e}")
                return 1

            # Test 2: Generate (only if Ollama available)
            print("\nTest 2: Generate text...", end=" ")
            if status['ollama']:
                try:
                    response = await client.generate("Say 'Hello' in Russian. Reply with just the word.")
                    print("OK")
                    print(f"  Response: {response.strip()}")
                except Exception as e:
                    print(f"FAILED: {e}")
                    return 1
            else:
                print("SKIPPED (Ollama unavailable)")

            # Test 3: Chat (only if Ollama available)
            print("\nTest 3: Chat completion...", end=" ")
            if status['ollama']:
                try:
                    messages = [
                        {"role": "system", "content": "You are a helpful assistant. Reply briefly."},
                        {"role": "user", "content": "What is 2+2?"},
                    ]
                    response = await client.chat(messages)
                    print("OK")
                    print(f"  Response: {response.strip()[:100]}")
                except Exception as e:
                    print(f"FAILED: {e}")
                    return 1
            else:
                print("SKIPPED (Ollama unavailable)")

            # Test 4: Transcribe would require a real file
            print("\nTest 4: Transcribe (file required)...", end=" ")
            print("SKIPPED (no test file)")

        print("\n" + "=" * 40)
        print("All tests passed!")
        return 0

    sys.exit(asyncio.run(run_tests()))
