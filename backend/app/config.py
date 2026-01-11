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
    llm_model: str = "qwen2.5:14b"
    cleaner_model: str = "gemma2:9b"  # Stable model for transcript cleaning
    chunker_model: str = "gemma2:9b"  # Better chunk distribution than qwen
    whisper_model: str = "large-v3-turbo"  # Display name for Whisper model
    whisper_language: str = "ru"
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


def load_prompt(name: str, settings: Settings | None = None) -> str:
    """
    Load a prompt template from config/prompts/{name}.md.

    Args:
        name: Prompt name (without .md extension)
        settings: Optional settings instance

    Returns:
        Prompt template content
    """
    if settings is None:
        settings = get_settings()

    prompt_path = settings.config_dir / "prompts" / f"{name}.md"
    return prompt_path.read_text(encoding="utf-8")


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
