"""
Pipeline module for video processing.

This package contains the decomposed pipeline components:
- orchestrator: Main pipeline coordination
- progress_manager: Progress tracking and calculation
- fallback_factory: Fallback object creation
- config_resolver: Settings management with model overrides

Example:
    from app.services.pipeline import PipelineOrchestrator, PipelineError

    orchestrator = PipelineOrchestrator()
    result = await orchestrator.process(video_path)
"""

from .orchestrator import (
    PipelineOrchestrator,
    PipelineError,
    get_video_duration,
)
from .progress_manager import ProgressManager, ProgressCallback
from .fallback_factory import FallbackFactory
from .config_resolver import ConfigResolver

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
]
