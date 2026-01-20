"""
Base AI client protocol for LLM providers.

Defines the interface that all AI clients must implement,
allowing interchangeable use of Ollama, Claude, and future providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class AIClientConfig:
    """
    Configuration for AI client instances.

    Attributes:
        base_url: API endpoint URL
        timeout: Request timeout in seconds
        api_key: Optional API key for authenticated services
        max_retries: Number of retry attempts for transient errors
    """

    base_url: str
    timeout: float = 300.0
    api_key: str | None = None
    max_retries: int = 3


@dataclass
class GenerationOptions:
    """
    Options for text generation requests.

    Attributes:
        model: Model name to use
        num_predict: Maximum tokens to generate (None = model default)
        temperature: Sampling temperature (0.0 = deterministic)
        stop: Stop sequences to end generation
    """

    model: str
    num_predict: int | None = None
    temperature: float = 0.7
    stop: list[str] = field(default_factory=list)


@runtime_checkable
class BaseAIClient(Protocol):
    """
    Protocol defining the interface for AI/LLM clients.

    All AI client implementations must provide these methods.
    This enables dependency injection and easy swapping between
    local (Ollama) and cloud (Claude API) providers.

    Example:
        async def process_text(client: BaseAIClient, text: str) -> str:
            return await client.generate(text)

        # Works with any implementation
        ollama = OllamaClient(config)
        claude = ClaudeClient(config)
        result = await process_text(ollama, "Hello")
        result = await process_text(claude, "Hello")
    """

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        num_predict: int | None = None,
    ) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: Text prompt for generation
            model: Model name (uses default if None)
            num_predict: Max tokens to generate (model default if None)

        Returns:
            Generated text response

        Raises:
            AIClientError: If generation fails
        """
        ...

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        num_predict: int | None = None,
    ) -> str:
        """
        Chat completion with message history.

        Args:
            messages: List of messages [{"role": "user", "content": "..."}]
            model: Model name (uses default if None)
            temperature: Sampling temperature
            num_predict: Max tokens to generate (model default if None)

        Returns:
            Assistant's response content

        Raises:
            AIClientError: If chat completion fails
        """
        ...

    async def close(self) -> None:
        """Close the client and release resources."""
        ...

    async def __aenter__(self) -> "BaseAIClient":
        """Context manager entry."""
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        ...


class AIClientError(Exception):
    """
    Base exception for AI client errors.

    Attributes:
        message: Error description
        provider: AI provider name (ollama, claude, etc.)
        model: Model that caused the error
        original_error: Underlying exception if available
    """

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        model: str | None = None,
        original_error: Exception | None = None,
    ):
        self.message = message
        self.provider = provider
        self.model = model
        self.original_error = original_error
        super().__init__(message)

    def __str__(self) -> str:
        parts = [self.message]
        if self.provider:
            parts.append(f"provider={self.provider}")
        if self.model:
            parts.append(f"model={self.model}")
        return " | ".join(parts)


class AIClientTimeoutError(AIClientError):
    """Raised when a request times out."""

    pass


class AIClientConnectionError(AIClientError):
    """Raised when connection to AI service fails."""

    pass


class AIClientResponseError(AIClientError):
    """
    Raised when AI service returns an error response.

    Attributes:
        status_code: HTTP status code if available
        response_body: Response body if available
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.response_body = response_body


class BaseAIClientImpl(ABC):
    """
    Abstract base class for AI client implementations.

    Provides common functionality for context manager protocol
    and can be extended with shared helper methods.

    Subclasses must implement:
        - generate()
        - chat()
        - close()
    """

    def __init__(self, config: AIClientConfig):
        """
        Initialize AI client with configuration.

        Args:
            config: Client configuration with URL, timeout, etc.
        """
        self.config = config

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        num_predict: int | None = None,
    ) -> str:
        """Generate text from a prompt."""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        num_predict: int | None = None,
    ) -> str:
        """Chat completion with message history."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the client and release resources."""
        pass

    async def __aenter__(self) -> "BaseAIClientImpl":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()


if __name__ == "__main__":
    """Run tests when executed directly."""

    def test_protocol_compliance():
        """Verify that classes properly implement the protocol."""
        print("Testing BaseAIClient protocol...")

        # Test that BaseAIClientImpl is recognized as implementing Protocol
        # This is a compile-time check, but we verify the structure
        assert hasattr(BaseAIClientImpl, "generate")
        assert hasattr(BaseAIClientImpl, "chat")
        assert hasattr(BaseAIClientImpl, "close")
        assert hasattr(BaseAIClientImpl, "__aenter__")
        assert hasattr(BaseAIClientImpl, "__aexit__")
        print("  Methods defined: OK")

        # Test AIClientError
        error = AIClientError("Test error", provider="test", model="test-model")
        assert str(error) == "Test error | provider=test | model=test-model"
        print("  AIClientError: OK")

        # Test AIClientConfig
        config = AIClientConfig(base_url="http://localhost:11434")
        assert config.timeout == 300.0
        assert config.max_retries == 3
        print("  AIClientConfig defaults: OK")

        print("\nAll protocol tests passed!")

    test_protocol_compliance()
