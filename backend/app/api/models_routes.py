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
    Get list of available models from Ollama and config.

    Whisper models are loaded from config/models.yaml (whisper_models section)
    to show only installed models with human-readable names.

    Returns:
        Dict with ollama_models and whisper_models lists
    """
    settings = get_settings()
    ollama_models: list[str] = []

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

    # Get Whisper models from config (only installed models)
    config = load_models_config()
    whisper_models = config.get("whisper_models", [])
    logger.debug(f"Loaded {len(whisper_models)} Whisper models from config")

    return {
        "ollama_models": sorted(ollama_models),
        "whisper_models": whisper_models,
    }


def _resolve_whisper_model_id(short_name: str, config: dict) -> str:
    """
    Resolve whisper model short name to full ID.

    Matches by short name or partial ID match.

    Args:
        short_name: Short model name (e.g. 'large-v3-turbo')
        config: Loaded models config

    Returns:
        Full model ID if found, otherwise original short_name
    """
    whisper_models = config.get("whisper_models", [])
    for model in whisper_models:
        # Match by name or by ID containing the short name
        if model["name"] == short_name or short_name in model["id"]:
            return model["id"]
    return short_name


@router.get("/default")
async def get_default_models() -> dict:
    """
    Get current default models from settings.

    Returns:
        Dict with default model for each pipeline stage
    """
    settings = get_settings()
    config = load_models_config()

    # Resolve whisper model short name to full ID
    transcribe_model = _resolve_whisper_model_id(settings.whisper_model, config)

    return {
        "transcribe": transcribe_model,
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
