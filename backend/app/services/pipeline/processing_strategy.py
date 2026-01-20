"""
Processing strategy for selecting between local and cloud AI providers.

Determines which AI client to use based on model name and availability.
Supports automatic fallback from cloud to local when needed.
"""

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import AsyncContextManager

from app.config import Settings
from app.services.ai_clients import (
    AIClientConnectionError,
    BaseAIClient,
    ClaudeClient,
    OllamaClient,
)

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """AI provider types."""

    LOCAL = "local"  # Ollama
    CLOUD = "cloud"  # Claude API


@dataclass
class ProviderInfo:
    """
    Information about AI provider.

    Attributes:
        type: Provider type (local/cloud)
        name: Human-readable name
        available: Whether provider is currently available
    """

    type: ProviderType
    name: str
    available: bool = False


class ProcessingStrategy:
    """
    Strategy for selecting AI providers based on model and availability.

    Determines whether to use local (Ollama) or cloud (Claude) processing.
    Supports automatic fallback from cloud to local when cloud is unavailable.

    Model naming convention:
    - Models starting with "claude" use Claude API
    - All other models use Ollama

    Example:
        strategy = ProcessingStrategy(settings)

        # Check availability
        await strategy.check_availability()

        # Get client for specific model
        async with strategy.get_client("claude-sonnet-4-5") as client:
            response = await client.generate("...")

        # Get client with fallback
        async with strategy.get_client_with_fallback(
            preferred="claude-sonnet",
            fallback="qwen2.5:14b"
        ) as client:
            response = await client.generate("...")
    """

    # Known cloud models (prefix-based matching)
    CLOUD_MODEL_PREFIXES = ("claude",)

    def __init__(self, settings: Settings):
        """
        Initialize processing strategy.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self._ollama_available: bool | None = None
        self._claude_available: bool | None = None

    def get_provider_type(self, model: str) -> ProviderType:
        """
        Determine provider type for a model.

        Args:
            model: Model name (e.g., "claude-sonnet-4-5", "gemma2:9b")

        Returns:
            ProviderType.CLOUD for Claude models, ProviderType.LOCAL otherwise
        """
        model_lower = model.lower()
        for prefix in self.CLOUD_MODEL_PREFIXES:
            if model_lower.startswith(prefix):
                return ProviderType.CLOUD
        return ProviderType.LOCAL

    async def check_availability(self) -> dict[ProviderType, ProviderInfo]:
        """
        Check availability of all providers.

        Returns:
            Dict mapping provider type to availability info
        """
        results = {}

        # Check Ollama
        ollama_available = await self._check_ollama()
        self._ollama_available = ollama_available
        results[ProviderType.LOCAL] = ProviderInfo(
            type=ProviderType.LOCAL,
            name="Ollama",
            available=ollama_available,
        )

        # Check Claude (only if API key is set)
        claude_available = await self._check_claude()
        self._claude_available = claude_available
        results[ProviderType.CLOUD] = ProviderInfo(
            type=ProviderType.CLOUD,
            name="Claude API",
            available=claude_available,
        )

        return results

    async def _check_ollama(self) -> bool:
        """Check if Ollama is available."""
        try:
            async with OllamaClient.from_settings(self.settings) as client:
                status = await client.check_services()
                return status.get("ollama", False)
        except Exception as e:
            logger.debug(f"Ollama check failed: {e}")
            return False

    async def _check_claude(self) -> bool:
        """Check if Claude API is available."""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.debug("Claude check skipped: no API key")
            return False

        try:
            async with ClaudeClient.from_settings(self.settings) as client:
                await client.check_api_key()
                return True
        except Exception as e:
            logger.debug(f"Claude check failed: {e}")
            return False

    def is_available(self, provider: ProviderType) -> bool:
        """
        Check if provider is available (using cached status).

        Call check_availability() first to populate cache.

        Args:
            provider: Provider type to check

        Returns:
            True if provider is available
        """
        if provider == ProviderType.LOCAL:
            return self._ollama_available or False
        elif provider == ProviderType.CLOUD:
            return self._claude_available or False
        return False

    def create_client(self, model: str) -> AsyncContextManager[BaseAIClient]:
        """
        Create AI client for specified model.

        Args:
            model: Model name (determines provider type)

        Returns:
            Context manager yielding appropriate AI client

        Raises:
            ValueError: If cloud model requested but no API key set
        """
        provider = self.get_provider_type(model)

        if provider == ProviderType.CLOUD:
            return ClaudeClient.from_settings(self.settings)
        else:
            return OllamaClient.from_settings(self.settings)

    async def get_client_with_fallback(
        self,
        preferred_model: str,
        fallback_model: str,
    ) -> tuple[BaseAIClient, str]:
        """
        Get AI client with automatic fallback.

        Tries preferred model first, falls back if unavailable.

        Args:
            preferred_model: First choice model (e.g., "claude-sonnet")
            fallback_model: Fallback model (e.g., "qwen2.5:14b")

        Returns:
            Tuple of (client, actual_model) - client is NOT in context manager,
            caller must call close() when done

        Example:
            client, model = await strategy.get_client_with_fallback(
                "claude-sonnet", "qwen2.5:14b"
            )
            try:
                response = await client.generate("...")
            finally:
                await client.close()
        """
        preferred_provider = self.get_provider_type(preferred_model)

        # Try preferred provider
        if preferred_provider == ProviderType.CLOUD:
            try:
                client = ClaudeClient.from_settings(self.settings)
                await client.check_api_key()
                logger.info(f"Using cloud provider with model: {preferred_model}")
                return client, preferred_model
            except (ValueError, AIClientConnectionError) as e:
                logger.warning(f"Cloud provider unavailable ({e}), falling back to local")
        else:
            try:
                client = OllamaClient.from_settings(self.settings)
                status = await client.check_services()
                if status.get("ollama"):
                    logger.info(f"Using local provider with model: {preferred_model}")
                    return client, preferred_model
                await client.close()
                logger.warning("Local Ollama unavailable, trying fallback")
            except Exception as e:
                logger.warning(f"Local provider unavailable ({e}), trying fallback")

        # Use fallback
        fallback_provider = self.get_provider_type(fallback_model)

        if fallback_provider == ProviderType.CLOUD:
            client = ClaudeClient.from_settings(self.settings)
        else:
            client = OllamaClient.from_settings(self.settings)

        logger.info(f"Using fallback model: {fallback_model}")
        return client, fallback_model


if __name__ == "__main__":
    """Run tests when executed directly."""
    import asyncio
    import sys

    from app.config import get_settings

    async def run_tests():
        """Test processing strategy."""
        print("\nTesting ProcessingStrategy...\n")

        settings = get_settings()
        strategy = ProcessingStrategy(settings)

        # Test 1: Provider type detection
        print("Test 1: Provider type detection...", end=" ")
        assert strategy.get_provider_type("gemma2:9b") == ProviderType.LOCAL
        assert strategy.get_provider_type("qwen2.5:14b") == ProviderType.LOCAL
        assert strategy.get_provider_type("claude-sonnet-4-5") == ProviderType.CLOUD
        assert strategy.get_provider_type("claude-3-opus") == ProviderType.CLOUD
        assert strategy.get_provider_type("Claude-Sonnet") == ProviderType.CLOUD  # Case insensitive
        print("OK")

        # Test 2: Check availability
        print("\nTest 2: Checking provider availability...")
        availability = await strategy.check_availability()

        for provider_type, info in availability.items():
            status = "available" if info.available else "unavailable"
            print(f"  {info.name}: {status}")

        # Test 3: Create clients
        print("\nTest 3: Create clients for different models...")

        # Test local client creation
        print("  Creating Ollama client for gemma2:9b...", end=" ")
        try:
            async with strategy.create_client("gemma2:9b") as client:
                print("OK (client created)")
        except Exception as e:
            print(f"FAILED: {e}")

        # Test cloud client creation (may fail without API key)
        print("  Creating Claude client for claude-sonnet...", end=" ")
        try:
            async with strategy.create_client("claude-sonnet-4-5") as client:
                print("OK (client created)")
        except ValueError as e:
            print(f"SKIPPED (no API key)")
        except Exception as e:
            print(f"FAILED: {e}")

        print("\n" + "=" * 40)
        print("ProcessingStrategy tests completed!")
        return 0

    sys.exit(asyncio.run(run_tests()))
