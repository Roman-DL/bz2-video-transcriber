"""
Claude API client implementation.

Provides async client for Anthropic's Claude API with retry logic.
Implements BaseAIClient protocol for text generation and chat completions.

v0.42+: Added chat_with_usage() method for token tracking.
"""

import logging
import os
from dataclasses import dataclass

from anthropic import AsyncAnthropic, APIConnectionError, APIStatusError, APITimeoutError

from app.config import Settings
from app.services.ai_clients.base import (
    AIClientConfig,
    AIClientConnectionError,
    AIClientResponseError,
    AIClientTimeoutError,
    BaseAIClientImpl,
)

logger = logging.getLogger(__name__)

# Default Claude model (using alias for auto-updates)
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-5"


@dataclass
class ChatUsage:
    """Token usage from Claude API response.

    Attributes:
        input_tokens: Tokens in the input prompt
        output_tokens: Tokens generated in response
    """

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.input_tokens + self.output_tokens


class ClaudeClient(BaseAIClientImpl):
    """
    Async client for Anthropic's Claude API.

    Implements BaseAIClient protocol for LLM operations.
    Designed for large context processing (200K+ tokens) without chunking.

    Features:
    - claude-sonnet model support
    - Large context processing
    - Automatic retry on transient errors
    - Cost-aware logging

    Example:
        async with ClaudeClient.from_settings(settings) as client:
            response = await client.generate("Analyze this document...")

        # Or with explicit config
        config = AIClientConfig(api_key=os.getenv("ANTHROPIC_API_KEY"))
        async with ClaudeClient(config) as client:
            response = await client.chat([
                {"role": "user", "content": "Hello!"}
            ])
    """

    def __init__(
        self,
        config: AIClientConfig,
        default_model: str = DEFAULT_CLAUDE_MODEL,
    ):
        """
        Initialize Claude client.

        Args:
            config: AI client configuration with API key
            default_model: Default Claude model to use

        Raises:
            ValueError: If API key is not provided
        """
        super().__init__(config)
        self.default_model = default_model

        if not config.api_key:
            raise ValueError(
                "ClaudeClient requires API key. "
                "Set ANTHROPIC_API_KEY environment variable."
            )

        self.client = AsyncAnthropic(
            api_key=config.api_key,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )

        logger.info(f"ClaudeClient initialized, model: {default_model}")

    @classmethod
    def from_settings(cls, settings: Settings) -> "ClaudeClient":
        """
        Create ClaudeClient from application settings.

        Args:
            settings: Application settings

        Returns:
            Configured ClaudeClient instance

        Raises:
            ValueError: If ANTHROPIC_API_KEY not set
        """
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable not set. "
                "Claude API requires authentication."
            )

        config = AIClientConfig(
            base_url="https://api.anthropic.com",
            api_key=api_key,
            timeout=settings.llm_timeout,
            max_retries=3,
        )

        return cls(config=config)

    async def close(self) -> None:
        """Close the client and release resources."""
        await self.client.close()
        logger.debug("ClaudeClient closed")

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        num_predict: int | None = None,
    ) -> str:
        """
        Generate text using Claude API.

        Internally uses the messages API with a single user message.

        Args:
            prompt: Text prompt for generation
            model: Model name (default: claude-sonnet)
            num_predict: Max tokens to generate (default: 4096)

        Returns:
            Generated text response

        Raises:
            AIClientError: If generation fails
        """
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(
            messages=messages,
            model=model,
            temperature=0.7,
            num_predict=num_predict,
        )

    async def generate_with_usage(
        self,
        prompt: str,
        model: str | None = None,
        num_predict: int | None = None,
    ) -> tuple[str, ChatUsage]:
        """
        Generate text with token usage tracking.

        Same as generate() but also returns token usage statistics.

        Args:
            prompt: Text prompt for generation
            model: Model name (default: claude-sonnet)
            num_predict: Max tokens to generate (default: 4096)

        Returns:
            Tuple of (generated_text, ChatUsage)

        Example:
            text, usage = await client.generate_with_usage("Hello!")
            print(f"Used {usage.total_tokens} tokens")
        """
        messages = [{"role": "user", "content": prompt}]
        return await self.chat_with_usage(
            messages=messages,
            model=model,
            temperature=0.7,
            num_predict=num_predict,
        )

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        num_predict: int | None = None,
    ) -> str:
        """
        Chat completion using Claude Messages API.

        Converts Ollama-style messages to Claude format:
        - "system" messages become system parameter
        - "user" and "assistant" messages are passed as-is

        Args:
            messages: List of chat messages [{"role": "user", "content": "..."}]
            model: Model name (default: claude-sonnet)
            temperature: Sampling temperature (default: 0.7)
            num_predict: Max tokens to generate (default: 4096)

        Returns:
            Assistant's response content

        Raises:
            AIClientError: If chat completion fails
        """
        if model is None:
            model = self.default_model

        if num_predict is None:
            num_predict = 4096

        # Extract system message if present
        system_content = None
        chat_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                chat_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

        logger.debug(
            f"Claude chat: model={model}, messages={len(chat_messages)}, "
            f"system={'yes' if system_content else 'no'}, max_tokens={num_predict}"
        )

        try:
            # Build request kwargs
            kwargs = {
                "model": model,
                "max_tokens": num_predict,
                "temperature": temperature,
                "messages": chat_messages,
            }

            if system_content:
                kwargs["system"] = system_content

            response = await self.client.messages.create(**kwargs)

            # Extract text from response
            content = response.content[0].text

            # Log usage for cost monitoring
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            logger.info(
                f"Claude response: {len(content)} chars, "
                f"tokens: {input_tokens} in / {output_tokens} out"
            )

            return content

        except APITimeoutError as e:
            logger.error(f"Claude timeout: {e}")
            raise AIClientTimeoutError(
                f"Claude request timeout",
                provider="claude",
                model=model,
                original_error=e,
            ) from e

        except APIConnectionError as e:
            logger.error(f"Claude connection error: {e}")
            raise AIClientConnectionError(
                f"Cannot connect to Claude API: {e}",
                provider="claude",
                original_error=e,
            ) from e

        except APIStatusError as e:
            logger.error(f"Claude API error: {e.status_code} - {e.message}")
            raise AIClientResponseError(
                f"Claude API error: {e.message}",
                provider="claude",
                model=model,
                status_code=e.status_code,
                response_body=str(e.body) if e.body else None,
                original_error=e,
            ) from e

    async def chat_with_usage(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        num_predict: int | None = None,
    ) -> tuple[str, ChatUsage]:
        """
        Chat completion with token usage tracking.

        Same as chat() but also returns token usage statistics.
        Use this when you need to track costs or debug prompts.

        Args:
            messages: List of chat messages [{"role": "user", "content": "..."}]
            model: Model name (default: claude-sonnet)
            temperature: Sampling temperature (default: 0.7)
            num_predict: Max tokens to generate (default: 4096)

        Returns:
            Tuple of (response_content, ChatUsage)

        Raises:
            AIClientError: If chat completion fails

        Example:
            content, usage = await client.chat_with_usage(messages)
            print(f"Used {usage.input_tokens} in, {usage.output_tokens} out")
        """
        if model is None:
            model = self.default_model

        if num_predict is None:
            num_predict = 4096

        # Extract system message if present
        system_content = None
        chat_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                chat_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

        logger.debug(
            f"Claude chat_with_usage: model={model}, messages={len(chat_messages)}, "
            f"system={'yes' if system_content else 'no'}, max_tokens={num_predict}"
        )

        try:
            # Build request kwargs
            kwargs = {
                "model": model,
                "max_tokens": num_predict,
                "temperature": temperature,
                "messages": chat_messages,
            }

            if system_content:
                kwargs["system"] = system_content

            response = await self.client.messages.create(**kwargs)

            # Extract text and usage from response
            content = response.content[0].text
            usage = ChatUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

            logger.info(
                f"Claude response: {len(content)} chars, "
                f"tokens: {usage.input_tokens} in / {usage.output_tokens} out"
            )

            return content, usage

        except APITimeoutError as e:
            logger.error(f"Claude timeout: {e}")
            raise AIClientTimeoutError(
                f"Claude request timeout",
                provider="claude",
                model=model,
                original_error=e,
            ) from e

        except APIConnectionError as e:
            logger.error(f"Claude connection error: {e}")
            raise AIClientConnectionError(
                f"Cannot connect to Claude API: {e}",
                provider="claude",
                original_error=e,
            ) from e

        except APIStatusError as e:
            logger.error(f"Claude API error: {e.status_code} - {e.message}")
            raise AIClientResponseError(
                f"Claude API error: {e.message}",
                provider="claude",
                model=model,
                status_code=e.status_code,
                response_body=str(e.body) if e.body else None,
                original_error=e,
            ) from e

    async def check_api_key(self) -> bool:
        """
        Verify Claude API key validity.

        Makes a minimal API call to check authentication.

        Returns:
            True if API key is valid

        Raises:
            AIClientResponseError: If API key is invalid
        """
        try:
            # Minimal request to verify auth
            await self.client.messages.create(
                model=self.default_model,
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}],
            )
            return True
        except APIStatusError as e:
            if e.status_code == 401:
                raise AIClientResponseError(
                    "Invalid Claude API key",
                    provider="claude",
                    status_code=401,
                    original_error=e,
                ) from e
            raise


if __name__ == "__main__":
    """Run tests when executed directly."""
    import asyncio
    import sys

    async def run_tests():
        """Test Claude client implementation."""
        print("\nTesting ClaudeClient...\n")

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("ANTHROPIC_API_KEY not set, skipping tests")
            return 0

        config = AIClientConfig(
            base_url="https://api.anthropic.com",
            api_key=api_key,
            timeout=60.0,
        )

        async with ClaudeClient(config) as client:
            # Test 1: API key validation
            print("Test 1: Checking API key...", end=" ")
            try:
                valid = await client.check_api_key()
                print("OK" if valid else "FAILED")
            except Exception as e:
                print(f"FAILED: {e}")
                return 1

            # Test 2: Generate
            print("\nTest 2: Generate text...", end=" ")
            try:
                response = await client.generate(
                    "Say 'Hello' in Russian. Reply with just the word.",
                    num_predict=10,
                )
                print("OK")
                print(f"  Response: {response.strip()}")
            except Exception as e:
                print(f"FAILED: {e}")
                return 1

            # Test 3: Chat with system message
            print("\nTest 3: Chat with system message...", end=" ")
            try:
                messages = [
                    {"role": "system", "content": "You are a helpful assistant. Be brief."},
                    {"role": "user", "content": "What is 2+2?"},
                ]
                response = await client.chat(messages, num_predict=20)
                print("OK")
                print(f"  Response: {response.strip()[:100]}")
            except Exception as e:
                print(f"FAILED: {e}")
                return 1

        print("\n" + "=" * 40)
        print("All tests passed!")
        return 0

    sys.exit(asyncio.run(run_tests()))
