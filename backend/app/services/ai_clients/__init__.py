"""
AI Clients package for LLM providers.

This package provides a unified interface for different AI/LLM providers:
- OllamaClient: Local Ollama + Whisper (production)
- ClaudeClient: Anthropic Claude API (cloud, large context)

Usage:
    from app.services.ai_clients import OllamaClient, ClaudeClient, BaseAIClient

    # Type hint for any AI client
    async def process(client: BaseAIClient) -> str:
        return await client.generate("Hello")

    # Create Ollama client (local)
    async with OllamaClient.from_settings(settings) as client:
        response = await client.generate("Hello")

    # Create Claude client (cloud)
    async with ClaudeClient.from_settings(settings) as client:
        response = await client.generate("Analyze this document...")
"""

from app.services.ai_clients.base import (
    AIClientConfig,
    AIClientConnectionError,
    AIClientError,
    AIClientResponseError,
    AIClientTimeoutError,
    BaseAIClient,
    BaseAIClientImpl,
    GenerationOptions,
)
from app.services.ai_clients.claude_client import ClaudeClient
from app.services.ai_clients.ollama_client import OllamaClient

__all__ = [
    # Protocol and base classes
    "BaseAIClient",
    "BaseAIClientImpl",
    "AIClientConfig",
    "GenerationOptions",
    # Errors
    "AIClientError",
    "AIClientTimeoutError",
    "AIClientConnectionError",
    "AIClientResponseError",
    # Implementations
    "OllamaClient",
    "ClaudeClient",
]
