"""
Ollama AI client implementation.

Provides async HTTP client for Ollama LLM API with retry logic.
Implements BaseAIClient protocol for text generation and chat completions.

v0.43+: All methods return tuple[str, ChatUsage] for unified interface.
Note: Ollama doesn't provide token usage, so ChatUsage(0, 0) is returned.

Note: Whisper transcription is handled by separate WhisperClient.
"""

import logging

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import Settings
from app.services.ai_clients.base import (
    AIClientConfig,
    AIClientConnectionError,
    AIClientResponseError,
    AIClientTimeoutError,
    BaseAIClientImpl,
    ChatUsage,
)

logger = logging.getLogger(__name__)

# Retry configuration for transient errors
RETRY_DECORATOR = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
)


class OllamaClient(BaseAIClientImpl):
    """
    Async HTTP client for Ollama LLM API.

    Implements BaseAIClient protocol for LLM operations (generate, chat).
    For transcription, use WhisperClient instead.

    Example:
        async with OllamaClient.from_settings(settings) as client:
            status = await client.check_services()
            response = await client.generate("Hello!")
    """

    def __init__(
        self,
        config: AIClientConfig,
        default_model: str = "gemma2:9b",
        llm_timeout: float = 300.0,
    ):
        """
        Initialize Ollama client.

        Args:
            config: AI client configuration with Ollama URL
            default_model: Default model for generation
            llm_timeout: Timeout for LLM requests in seconds
        """
        super().__init__(config)
        self.default_model = default_model
        self.llm_timeout = llm_timeout

        # No global timeout - each request sets its own timeout explicitly
        self.http_client = httpx.AsyncClient(timeout=None)

    @classmethod
    def from_settings(cls, settings: Settings) -> "OllamaClient":
        """
        Create OllamaClient from application settings.

        Args:
            settings: Application settings

        Returns:
            Configured OllamaClient instance
        """
        config = AIClientConfig(
            base_url=settings.ollama_url,
            timeout=settings.llm_timeout,
        )
        return cls(
            config=config,
            default_model=settings.summarizer_model,
            llm_timeout=settings.llm_timeout,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.http_client.aclose()

    async def check_services(self) -> dict:
        """
        Check availability of Ollama service.

        Returns:
            Dict with service status:
            {
                "ollama": bool,
                "ollama_version": str | None
            }
        """
        ollama_available = False
        ollama_version = None

        try:
            response = await self.http_client.get(
                f"{self.config.base_url}/api/version",
                timeout=5.0,
            )
            if response.status_code == 200:
                ollama_available = True
                data = response.json()
                ollama_version = data.get("version")
                logger.debug(f"Ollama available, version: {ollama_version}")
        except Exception as e:
            logger.debug(f"Ollama not available: {e}")

        return {
            "ollama": ollama_available,
            "ollama_version": ollama_version,
        }

    @RETRY_DECORATOR
    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        num_predict: int | None = None,
    ) -> tuple[str, ChatUsage]:
        """
        Generate text using Ollama /api/generate endpoint.

        Args:
            prompt: Text prompt for generation
            model: Model name (default: from settings)
            num_predict: Max tokens to generate (default: None = model default)

        Returns:
            Tuple of (generated_text, ChatUsage).
            Note: ChatUsage(0, 0) as Ollama doesn't provide token usage.

        Raises:
            AIClientError: If generation fails
        """
        if model is None:
            model = self.default_model

        logger.debug(f"Generating with {model}, prompt length: {len(prompt)}")

        request_body: dict = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }

        if num_predict is not None:
            request_body["options"] = {"num_predict": num_predict}

        try:
            response = await self.http_client.post(
                f"{self.config.base_url}/api/generate",
                json=request_body,
                timeout=self.llm_timeout,
            )

            response.raise_for_status()
            result = response.json()

            response_text = result.get("response", "")

            # Diagnostics for empty responses
            if not response_text.strip():
                logger.error(
                    f"Empty response from LLM! Model: {model}, "
                    f"prompt_length: {len(prompt)} chars"
                )

            logger.debug(f"Generated {len(response_text)} chars")

            return response_text, ChatUsage()

        except httpx.TimeoutException as e:
            logger.error(f"Generation timeout with {model}: {e}")
            raise AIClientTimeoutError(
                f"Generation timeout",
                provider="ollama",
                model=model,
                original_error=e,
            ) from e

        except httpx.HTTPStatusError as e:
            logger.error(f"Generation HTTP error: {e.response.status_code}")
            raise AIClientResponseError(
                f"Generation failed: HTTP {e.response.status_code}",
                provider="ollama",
                model=model,
                status_code=e.response.status_code,
                response_body=e.response.text[:500],
                original_error=e,
            ) from e

        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Ollama: {e}")
            raise AIClientConnectionError(
                f"Cannot connect to Ollama at {self.config.base_url}",
                provider="ollama",
                original_error=e,
            ) from e

    @RETRY_DECORATOR
    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        num_predict: int | None = None,
    ) -> tuple[str, ChatUsage]:
        """
        Chat completion using Ollama OpenAI-compatible endpoint.

        Args:
            messages: List of chat messages [{"role": "user", "content": "..."}]
            model: Model name (default: from settings)
            temperature: Sampling temperature (default: 0.7)
            num_predict: Max tokens to generate (default: None = model default)

        Returns:
            Tuple of (response_content, ChatUsage).
            Note: ChatUsage(0, 0) as Ollama doesn't provide token usage.

        Raises:
            AIClientError: If chat completion fails
        """
        if model is None:
            model = self.default_model

        logger.debug(f"Chat with {model}, {len(messages)} messages")

        request_body: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        if num_predict is not None:
            request_body["max_tokens"] = num_predict

        try:
            response = await self.http_client.post(
                f"{self.config.base_url}/v1/chat/completions",
                json=request_body,
                timeout=self.llm_timeout,
            )

            response.raise_for_status()
            result = response.json()

            content = result["choices"][0]["message"]["content"]
            logger.debug(f"Chat response: {len(content)} chars")

            return content, ChatUsage()

        except httpx.TimeoutException as e:
            logger.error(f"Chat timeout with {model}: {e}")
            raise AIClientTimeoutError(
                f"Chat timeout",
                provider="ollama",
                model=model,
                original_error=e,
            ) from e

        except httpx.HTTPStatusError as e:
            logger.error(f"Chat HTTP error: {e.response.status_code}")
            raise AIClientResponseError(
                f"Chat failed: HTTP {e.response.status_code}",
                provider="ollama",
                model=model,
                status_code=e.response.status_code,
                response_body=e.response.text[:500],
                original_error=e,
            ) from e

        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Ollama: {e}")
            raise AIClientConnectionError(
                f"Cannot connect to Ollama at {self.config.base_url}",
                provider="ollama",
                original_error=e,
            ) from e


if __name__ == "__main__":
    """Run tests when executed directly."""
    import asyncio
    import sys

    from app.config import get_settings

    # Configure logging for tests
    logging.basicConfig(level=logging.INFO)

    async def run_tests():
        """Run all Ollama client tests."""
        print("\nRunning Ollama client tests...\n")

        settings = get_settings()
        print(f"Ollama URL: {settings.ollama_url}")
        print(f"Summarizer Model: {settings.summarizer_model}")
        print()

        async with OllamaClient.from_settings(settings) as client:
            # Test 1: Check services
            print("Test 1: Checking Ollama...", end=" ")
            try:
                status = await client.check_services()
                print("OK")
                print(f"  Ollama: {'available' if status['ollama'] else 'unavailable'}")
                if status["ollama_version"]:
                    print(f"  Ollama version: {status['ollama_version']}")
            except Exception as e:
                print(f"FAILED: {e}")
                return 1

            # Test 2: Generate (only if Ollama available)
            print("\nTest 2: Generate text...", end=" ")
            if status["ollama"]:
                try:
                    response, usage = await client.generate(
                        "Say 'Hello' in Russian. Reply with just the word."
                    )
                    print("OK")
                    print(f"  Response: {response.strip()}")
                    print(f"  Usage: {usage.total_tokens} tokens (Ollama doesn't track)")
                except Exception as e:
                    print(f"FAILED: {e}")
                    return 1
            else:
                print("SKIPPED (Ollama unavailable)")

            # Test 3: Chat (only if Ollama available)
            print("\nTest 3: Chat completion...", end=" ")
            if status["ollama"]:
                try:
                    messages = [
                        {
                            "role": "system",
                            "content": "You are a helpful assistant. Reply briefly.",
                        },
                        {"role": "user", "content": "What is 2+2?"},
                    ]
                    response, usage = await client.chat(messages)
                    print("OK")
                    print(f"  Response: {response.strip()[:100]}")
                    print(f"  Usage: {usage.total_tokens} tokens (Ollama doesn't track)")
                except Exception as e:
                    print(f"FAILED: {e}")
                    return 1
            else:
                print("SKIPPED (Ollama unavailable)")

        print("\n" + "=" * 40)
        print("All tests passed!")
        return 0

    sys.exit(asyncio.run(run_tests()))
