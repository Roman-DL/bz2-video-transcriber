"""
API routes for model configuration.

Provides endpoints to get available models and their configurations.
"""

import logging

import httpx
from fastapi import APIRouter

from app.config import get_settings, load_models_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("/available")
async def get_available_models() -> dict:
    """
    Get list of available models from Ollama and Whisper.

    Returns:
        Dict with ollama_models and whisper_models lists
    """
    settings = get_settings()
    ollama_models: list[str] = []
    whisper_models: list[str] = []

    # Get Ollama models
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings.ollama_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                ollama_models = [model["name"] for model in data.get("models", [])]
                logger.debug(f"Found {len(ollama_models)} Ollama models")
    except Exception as e:
        logger.warning(f"Failed to get Ollama models: {e}")

    # Get Whisper models from faster-whisper-server
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings.whisper_url}/v1/models")
            if response.status_code == 200:
                data = response.json()
                whisper_models = [model["id"] for model in data.get("data", [])]
                logger.debug(f"Found {len(whisper_models)} Whisper models")
    except Exception as e:
        logger.warning(f"Failed to get Whisper models: {e}")

    return {
        "ollama_models": sorted(ollama_models),
        "whisper_models": sorted(whisper_models),
    }


@router.get("/default")
async def get_default_models() -> dict:
    """
    Get current default models from settings.

    Returns:
        Dict with default model for each pipeline stage
    """
    settings = get_settings()
    return {
        "transcribe": settings.whisper_model,
        "clean": settings.cleaner_model,
        "chunk": settings.chunker_model,
        "summarize": settings.summarizer_model,
    }


@router.get("/config")
async def get_models_config() -> dict:
    """
    Get model configurations from models.yaml.

    Returns full configuration for each model family including
    context_tokens and stage-specific parameters.

    Returns:
        Dict with model configurations
    """
    config = load_models_config()
    return config.get("models", {})
