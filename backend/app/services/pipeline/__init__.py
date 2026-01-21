"""
Pipeline module for video processing.

This package contains the decomposed pipeline components:
- orchestrator: Main pipeline coordination
- progress_manager: Progress tracking and calculation
- fallback_factory: Fallback object creation
- config_resolver: Settings management with model overrides
- stage_cache: Versioned caching of intermediate results
- processing_strategy: AI provider selection (local/cloud)

Example:
    from app.services.pipeline import PipelineOrchestrator, PipelineError

    orchestrator = PipelineOrchestrator()
    result = await orchestrator.process(video_path)

    # With caching
    from app.services.pipeline import StageResultCache

    cache = StageResultCache(settings)
    await cache.save(archive_path, stage, result, model_name)

    # With provider selection
    from app.services.pipeline import ProcessingStrategy

    strategy = ProcessingStrategy(settings)
    async with strategy.create_client("claude-sonnet") as client:
        response = await client.generate("...")
"""

from .orchestrator import (
    PipelineOrchestrator,
    PipelineError,
)
from .progress_manager import ProgressManager, ProgressCallback
from .fallback_factory import FallbackFactory
from .config_resolver import ConfigResolver
from .stage_cache import StageResultCache
from .processing_strategy import ProcessingStrategy, ProviderType, ProviderInfo

__all__ = [
    # Main orchestrator
    "PipelineOrchestrator",
    "PipelineError",
    # Supporting classes
    "ProgressManager",
    "ProgressCallback",
    "FallbackFactory",
    "ConfigResolver",
    "StageResultCache",
    # Provider selection
    "ProcessingStrategy",
    "ProviderType",
    "ProviderInfo",
]
