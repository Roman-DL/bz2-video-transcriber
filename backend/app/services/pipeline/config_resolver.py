"""
Configuration resolver for pipeline stages.

Handles model overrides and settings management for step-by-step processing.
"""

import logging
from typing import Literal

from app.config import Settings

logger = logging.getLogger(__name__)

StageType = Literal["cleaner", "chunker", "summarizer", "longread"]


class ConfigResolver:
    """
    Resolves configuration for pipeline stages with optional overrides.

    Allows step-by-step mode to override specific models for testing
    different LLM configurations without changing global settings.

    Example:
        resolver = ConfigResolver(settings)

        # Get settings with chunker model override
        custom_settings = resolver.with_model("qwen2.5:14b", "chunker")

        # Use in service
        chunker = SemanticChunker(ai_client, custom_settings)
    """

    def __init__(self, settings: Settings):
        """
        Initialize config resolver.

        Args:
            settings: Base application settings
        """
        self.settings = settings

    def with_model(
        self,
        model: str | None,
        stage: StageType,
    ) -> Settings:
        """
        Get settings with optional model override.

        If model is None, returns original settings unchanged.
        Otherwise, creates a copy with the specified model override.

        Args:
            model: Optional model override (e.g., "qwen2.5:14b")
            stage: Stage name ("cleaner", "chunker", "summarizer", "longread")

        Returns:
            Settings instance (original or copy with override)

        Example:
            settings = resolver.with_model("gemma2:9b", "cleaner")
            # settings.cleaner_model == "gemma2:9b"
        """
        if not model:
            return self.settings

        logger.debug(f"Overriding {stage} model: {model}")

        # Create a copy with overridden model
        settings_dict = {
            "ollama_url": self.settings.ollama_url,
            "whisper_url": self.settings.whisper_url,
            "summarizer_model": self.settings.summarizer_model,
            "cleaner_model": self.settings.cleaner_model,
            "chunker_model": self.settings.chunker_model,
            "longread_model": self.settings.longread_model,
            "whisper_model": self.settings.whisper_model,
            "whisper_language": self.settings.whisper_language,
            "whisper_include_timestamps": self.settings.whisper_include_timestamps,
            "llm_timeout": self.settings.llm_timeout,
            "data_root": self.settings.data_root,
            "inbox_dir": self.settings.inbox_dir,
            "archive_dir": self.settings.archive_dir,
            "temp_dir": self.settings.temp_dir,
            "config_dir": self.settings.config_dir,
            "log_level": self.settings.log_level,
            "log_format": self.settings.log_format,
        }

        # Override the specific model
        model_field = self._get_model_field(stage)
        settings_dict[model_field] = model

        return Settings(**settings_dict)

    def _get_model_field(self, stage: StageType) -> str:
        """
        Get settings field name for stage model.

        Args:
            stage: Stage name

        Returns:
            Settings field name (e.g., "cleaner_model")
        """
        field_map = {
            "cleaner": "cleaner_model",
            "chunker": "chunker_model",
            "summarizer": "summarizer_model",
            "longread": "longread_model",
        }
        return field_map.get(stage, f"{stage}_model")

    def get_model_for_stage(self, stage: StageType) -> str:
        """
        Get current model for a stage.

        Args:
            stage: Stage name

        Returns:
            Model name from settings
        """
        model_map = {
            "cleaner": self.settings.cleaner_model,
            "chunker": self.settings.chunker_model,
            "summarizer": self.settings.summarizer_model,
            "longread": self.settings.longread_model,
        }
        return model_map.get(stage, "")


if __name__ == "__main__":
    """Run tests when executed directly."""
    from app.config import get_settings

    print("\nRunning ConfigResolver tests...\n")

    settings = get_settings()
    resolver = ConfigResolver(settings)

    # Test 1: No override returns original settings
    print("Test 1: No override returns original settings...", end=" ")
    result = resolver.with_model(None, "cleaner")
    assert result is settings, "Expected same settings instance"
    print("OK")

    # Test 2: Override cleaner model
    print("Test 2: Override cleaner model...", end=" ")
    result = resolver.with_model("test-model:7b", "cleaner")
    assert result is not settings, "Expected new settings instance"
    assert result.cleaner_model == "test-model:7b"
    assert result.chunker_model == settings.chunker_model  # Unchanged
    print("OK")

    # Test 3: Override chunker model
    print("Test 3: Override chunker model...", end=" ")
    result = resolver.with_model("another-model:14b", "chunker")
    assert result.chunker_model == "another-model:14b"
    assert result.cleaner_model == settings.cleaner_model  # Unchanged
    print("OK")

    # Test 4: Override summarizer model
    print("Test 4: Override summarizer model...", end=" ")
    result = resolver.with_model("summary-model:32b", "summarizer")
    assert result.summarizer_model == "summary-model:32b"
    print("OK")

    # Test 5: Override longread model
    print("Test 5: Override longread model...", end=" ")
    result = resolver.with_model("longread-model:14b", "longread")
    assert result.longread_model == "longread-model:14b"
    print("OK")

    # Test 6: Get model for stage
    print("Test 6: Get model for stage...", end=" ")
    cleaner_model = resolver.get_model_for_stage("cleaner")
    assert cleaner_model == settings.cleaner_model
    print("OK")

    # Test 7: All other settings preserved
    print("Test 7: All other settings preserved...", end=" ")
    result = resolver.with_model("test:1b", "cleaner")
    assert result.ollama_url == settings.ollama_url
    assert result.whisper_url == settings.whisper_url
    assert result.llm_timeout == settings.llm_timeout
    assert result.data_root == settings.data_root
    print("OK")

    print("\n" + "=" * 40)
    print("All ConfigResolver tests passed!")
