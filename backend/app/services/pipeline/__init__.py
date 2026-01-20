"""
Pipeline module for video processing.

This package contains the decomposed pipeline components:
- orchestrator: Main pipeline coordination
- progress_manager: Progress tracking and calculation
- fallback_factory: Fallback object creation
- config_resolver: Settings management with model overrides
- stage_cache: Versioned caching of intermediate results

Example:
    from app.services.pipeline import PipelineOrchestrator, PipelineError

    orchestrator = PipelineOrchestrator()
    result = await orchestrator.process(video_path)

    # With caching
    from app.services.pipeline import StageResultCache

    cache = StageResultCache(settings)
    await cache.save(archive_path, stage, result, model_name)
"""

from .orchestrator import (
    PipelineOrchestrator,
    PipelineError,
    get_video_duration,
)
from .progress_manager import ProgressManager, ProgressCallback
from .fallback_factory import FallbackFactory
from .config_resolver import ConfigResolver
from .stage_cache import StageResultCache

__all__ = [
    # Main orchestrator
    "PipelineOrchestrator",
    "PipelineError",
    "get_video_duration",
    # Supporting classes
    "ProgressManager",
    "ProgressCallback",
    "FallbackFactory",
    "ConfigResolver",
    "StageResultCache",
]
