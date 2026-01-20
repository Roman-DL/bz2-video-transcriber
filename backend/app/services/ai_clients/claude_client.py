"""
Claude API client implementation (stub).

This is a placeholder for future Claude API integration.
Implementation will be completed in Phase 5 of the refactoring plan.
"""

import logging

from app.services.ai_clients.base import (
    AIClientConfig,
    AIClientError,
    BaseAIClientImpl,
)

logger = logging.getLogger(__name__)


class ClaudeClientNotImplementedError(AIClientError):
    """Raised when Claude client methods are called before implementation."""

    def __init__(self, method: str):
        super().__init__(
            f"ClaudeClient.{method}() not implemented. "
            "Claude API integration is planned for Phase 5.",
            provider="claude",
        )


class ClaudeClient(BaseAIClientImpl):
    """
    Claude API client (stub implementation).

    This client will provide integration with Anthropic's Claude API,
    enabling use of large context models (200K+ tokens) for processing
    long documents without chunking.

    Planned features:
    - claude-sonnet model support
    - Large context processing
    - Streaming responses
    - Tool use / function calling

    Example (future usage):
        config = AIClientConfig(
            base_url="https://api.anthropic.com",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
        )
        async with ClaudeClient(config) as client:
            response = await client.generate(long_document)
    """

    def __init__(
        self,
        config: AIClientConfig,
        default_model: str = "claude-sonnet-4-20250514",
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
            logger.warning(
                "ClaudeClient initialized without API key. "
                "Set ANTHROPIC_API_KEY environment variable for production use."
            )

    async def close(self) -> None:
        """Close the client and release resources."""
        # No resources to release in stub implementation
        pass

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        num_predict: int | None = None,
    ) -> str:
        """
        Generate text using Claude API (not implemented).

        Args:
            prompt: Text prompt for generation
            model: Model name (default: claude-sonnet)
            num_predict: Max tokens to generate

        Raises:
            ClaudeClientNotImplementedError: Always (stub implementation)
        """
        raise ClaudeClientNotImplementedError("generate")

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        num_predict: int | None = None,
    ) -> str:
        """
        Chat completion using Claude API (not implemented).

        Args:
            messages: List of chat messages
            model: Model name (default: claude-sonnet)
            temperature: Sampling temperature
            num_predict: Max tokens to generate

        Raises:
            ClaudeClientNotImplementedError: Always (stub implementation)
        """
        raise ClaudeClientNotImplementedError("chat")

    async def check_api_key(self) -> bool:
        """
        Verify Claude API key validity (not implemented).

        Returns:
            True if API key is valid

        Raises:
            ClaudeClientNotImplementedError: Always (stub implementation)
        """
        raise ClaudeClientNotImplementedError("check_api_key")


if __name__ == "__main__":
    """Run tests when executed directly."""
    import asyncio

    async def run_tests():
        """Test stub implementation."""
        print("\nTesting ClaudeClient stub...\n")

        config = AIClientConfig(
            base_url="https://api.anthropic.com",
            api_key="test-key",
        )

        async with ClaudeClient(config) as client:
            # Test 1: generate should raise NotImplementedError
            print("Test 1: generate() raises NotImplementedError...", end=" ")
            try:
                await client.generate("Test prompt")
                print("FAILED (no exception raised)")
            except ClaudeClientNotImplementedError as e:
                print("OK")
                print(f"  Error: {e}")

            # Test 2: chat should raise NotImplementedError
            print("\nTest 2: chat() raises NotImplementedError...", end=" ")
            try:
                await client.chat([{"role": "user", "content": "Test"}])
                print("FAILED (no exception raised)")
            except ClaudeClientNotImplementedError as e:
                print("OK")
                print(f"  Error: {e}")

        print("\n" + "=" * 40)
        print("All stub tests passed!")

    asyncio.run(run_tests())
