"""
AI Clients package for LLM and transcription providers.

This package provides a unified interface for different AI services:
- OllamaClient: Local Ollama LLM (text generation, chat)
- ClaudeClient: Anthropic Claude API (cloud, large context)
- WhisperClient: Whisper ASR for transcription (separate service)

Usage:
    from app.services.ai_clients import OllamaClient, ClaudeClient, WhisperClient

    # Create Ollama client for LLM (local)
    async with OllamaClient.from_settings(settings) as client:
        response = await client.generate("Hello")

    # Create Claude client for LLM (cloud)
    async with ClaudeClient.from_settings(settings) as client:
        response = await client.generate("Analyze this document...")

    # Create Whisper client for transcription
    async with WhisperClient.from_settings(settings) as client:
        result = await client.transcribe(audio_path)
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
from app.services.ai_clients.whisper_client import WhisperClient

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
    # LLM Implementations
    "OllamaClient",
    "ClaudeClient",
    # Transcription
    "WhisperClient",
]
