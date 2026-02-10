"""
API routes for model configuration.

Provides endpoints to get available models and their configurations.
"""

import logging

import httpx
from fastapi import APIRouter

from app.config import get_settings, load_models_config
from app.models.schemas import (
    AvailableModelsResponse,
    ClaudeModelConfig,
    DefaultModelsResponse,
    ProvidersInfo,
    ProviderStatus,
    WhisperModelConfig,
)
from app.services.pipeline import ProcessingStrategy
from app.services.pipeline.processing_strategy import ProviderType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("/available")
async def get_available_models() -> AvailableModelsResponse:
    """
    Get list of available models from Ollama, Claude API, and config.

    Whisper models are loaded from config/models.yaml (whisper_models section)
    to show only installed models with human-readable names.

    Claude models are shown only when ANTHROPIC_API_KEY is set and valid.

    Returns:
        AvailableModelsResponse with ollama_models, whisper_models, claude_models, and providers
    """
    settings = get_settings()
    ollama_models: list[str] = []

    # Check provider availability
    strategy = ProcessingStrategy(settings)
    availability = await strategy.check_availability()

    local_available = availability[ProviderType.LOCAL].available
    cloud_available = availability[ProviderType.CLOUD].available

    # Get Ollama models (only if local provider is available)
    if local_available:
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

    # Get Claude models from config (only if cloud provider is available)
    claude_models = []
    if cloud_available:
        claude_models = config.get("claude_models", [])
        logger.debug(f"Loaded {len(claude_models)} Claude models from config")

    return AvailableModelsResponse(
        ollama_models=sorted(ollama_models),
        whisper_models=[WhisperModelConfig(**m) for m in whisper_models],
        claude_models=[ClaudeModelConfig(**m) for m in claude_models],
        providers=ProvidersInfo(
            local=ProviderStatus(available=local_available, name="Ollama"),
            cloud=ProviderStatus(available=cloud_available, name="Claude API"),
        ),
    )


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
async def get_default_models() -> DefaultModelsResponse:
    """
    Get current default models from settings.

    Returns:
        DefaultModelsResponse with default model for each pipeline stage
    """
    settings = get_settings()
    config = load_models_config()

    # Resolve whisper model short name to full ID
    transcribe_model = _resolve_whisper_model_id(settings.whisper_model, config)

    return DefaultModelsResponse(
        transcribe=transcribe_model,
        clean=settings.cleaner_model,
        longread=settings.longread_model,
        summarize=settings.summarizer_model,
        describe=settings.describe_model,
    )


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
