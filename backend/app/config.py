"""
Application configuration and settings.
"""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # AI Services
    ollama_url: str = "http://192.168.1.152:11434"
    whisper_url: str = "http://192.168.1.152:9000"
    summarizer_model: str = "qwen2.5:14b"  # Model for summarization (конспект)
    longread_model: str = "qwen2.5:14b"  # Model for longread generation
    cleaner_model: str = "gemma2:9b"  # Stable model for transcript cleaning
    chunker_model: str = "gemma2:9b"  # Better chunk distribution than qwen
    whisper_model: str = "large-v3-turbo"  # Display name for Whisper model
    whisper_language: str = "ru"
    whisper_include_timestamps: bool = False  # Include [HH:MM:SS] in transcript_raw.txt
    llm_timeout: int = 300

    # Paths
    data_root: Path = Path("/data")
    inbox_dir: Path = Path("/data/inbox")
    archive_dir: Path = Path("/data/archive")
    temp_dir: Path = Path("/data/temp")
    config_dir: Path = Path("/app/config")

    # Logging
    log_level: str = "INFO"
    log_format: str = "structured"  # "simple" or "structured"

    # Per-module log levels (optional overrides)
    log_level_ai_client: str | None = None
    log_level_pipeline: str | None = None
    log_level_transcriber: str | None = None
    log_level_cleaner: str | None = None
    log_level_chunker: str | None = None
    log_level_summarizer: str | None = None

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def load_prompt(name: str, model: str | None = None, settings: Settings | None = None) -> str:
    """
    Load a prompt template with model-specific fallback.

    Lookup order:
    1. prompts/{name}_{model_family}.md (e.g., cleaner_system_gemma2.md)
    2. prompts/{name}.md (e.g., cleaner_system.md)

    Model family is extracted from model name:
    - "gemma2:9b" -> "gemma2"
    - "qwen2.5:14b" -> "qwen2"
    - "qwen3:14b" -> "qwen3"

    Args:
        name: Prompt name (without .md extension)
        model: Model name for model-specific prompts
        settings: Optional settings instance

    Returns:
        Prompt template content
    """
    if settings is None:
        settings = get_settings()

    # Try model-specific prompt first
    if model:
        model_family = model.split(":")[0].rstrip("0123456789.")
        specific_path = settings.config_dir / "prompts" / f"{name}_{model_family}.md"
        if specific_path.exists():
            return specific_path.read_text(encoding="utf-8")

    # Fallback to generic prompt
    generic_path = settings.config_dir / "prompts" / f"{name}.md"
    return generic_path.read_text(encoding="utf-8")


def load_glossary(settings: Settings | None = None) -> dict:
    """
    Load glossary from config/glossary.yaml.

    Args:
        settings: Optional settings instance

    Returns:
        Glossary dictionary with categories and terms
    """
    if settings is None:
        settings = get_settings()

    glossary_path = settings.config_dir / "glossary.yaml"
    with open(glossary_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_events_config(settings: Settings | None = None) -> dict:
    """
    Load events configuration from config/events.yaml.

    Args:
        settings: Optional settings instance

    Returns:
        Events configuration dictionary
    """
    if settings is None:
        settings = get_settings()

    events_path = settings.config_dir / "events.yaml"
    with open(events_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_performance_config(settings: Settings | None = None) -> dict:
    """
    Load performance coefficients from config/performance.yaml.

    Used by ProgressEstimator to calculate estimated processing time.

    Args:
        settings: Optional settings instance

    Returns:
        Performance configuration with stage coefficients
    """
    if settings is None:
        settings = get_settings()

    perf_path = settings.config_dir / "performance.yaml"
    with open(perf_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_models_config(settings: Settings | None = None) -> dict:
    """
    Load model configurations from config/models.yaml.

    Args:
        settings: Optional settings instance

    Returns:
        Models configuration dictionary with per-model settings
    """
    if settings is None:
        settings = get_settings()

    models_path = settings.config_dir / "models.yaml"
    with open(models_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_model_config(model: str, stage: str, settings: Settings | None = None) -> dict:
    """
    Load model-specific configuration for a pipeline stage.

    Extracts model family from model name and returns stage-specific settings.
    Falls back to defaults if model not found.

    Model family extraction:
    - "gemma2:9b" -> "gemma2"
    - "qwen2.5:14b" -> "qwen2"
    - "qwen3:14b" -> "qwen3"

    Args:
        model: Full model name (e.g., "gemma2:9b")
        stage: Pipeline stage ("cleaner", "chunker", "text_splitter")
        settings: Optional settings instance

    Returns:
        Configuration dictionary for the stage
    """
    config = load_models_config(settings)
    model_family = model.split(":")[0].rstrip("0123456789.")

    # Try model-specific config first
    if model_family in config.get("models", {}):
        stage_config = config["models"][model_family].get(stage, {})
        if stage_config:
            return stage_config

    # Fallback to defaults
    return config.get("defaults", {}).get(stage, {})


def get_model_config(model: str, settings: Settings | None = None) -> dict:
    """
    Get full model configuration for all stages.

    Extracts model family from model name and returns all settings.
    Falls back to defaults if model not found.

    Model family extraction:
    - "gemma2:9b" -> "gemma2"
    - "qwen2.5:14b" -> "qwen2"
    - "qwen3:14b" -> "qwen3"

    Args:
        model: Full model name (e.g., "gemma2:9b")
        settings: Optional settings instance

    Returns:
        Full configuration dictionary for the model
    """
    config = load_models_config(settings)
    model_family = model.split(":")[0].rstrip("0123456789.")

    # Try model-specific config first
    if model_family in config.get("models", {}):
        return config["models"][model_family]

    # Fallback to defaults
    return config.get("defaults", {})
