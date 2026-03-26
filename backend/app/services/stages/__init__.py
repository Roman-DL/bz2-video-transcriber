"""
Pipeline stages for video processing.

This module provides a stage abstraction for the processing pipeline.
Each stage is a self-contained unit that can be composed into pipelines.

Usage:
    from app.services.stages import (
        BaseStage,
        StageContext,
        StageRegistry,
        get_registry,
        create_default_stages,
    )

    # Get default registry with all stages
    registry = get_registry()
    create_default_stages(settings)

    # Build and run pipeline
    stages = registry.build_pipeline(["parse", "transcribe", "clean", ...])
    context = StageContext().with_metadata("video_path", Path("video.mp4"))

    for stage in stages:
        result = await stage.execute(context)
        context = context.with_result(stage.name, result)

Adding new stages:
    See docs/pipeline/stages.md for detailed guide.

    1. Create a new file: stages/my_stage.py
    2. Define your stage class:

        class MyStage(BaseStage):
            name = "my_stage"
            depends_on = ["longread"]
            optional = True

            async def execute(self, context: StageContext) -> MyResult:
                longread = context.get_result("longread")
                # Process...
                return MyResult(...)

    3. Register in create_default_stages() or use register_stage()
"""

from app.services.stages.base import (
    BaseStage,
    StageContext,
    StageError,
    StageRegistry,
    get_registry,
    register_stage,
)
from app.services.stages.parse_stage import ParseStage
from app.services.stages.transcribe_stage import TranscribeStage
from app.services.stages.clean_stage import CleanStage
from app.services.stages.chunk_stage import ChunkStage
from app.services.stages.longread_stage import LongreadStage
from app.services.stages.summarize_stage import SummarizeStage
from app.services.stages.story_stage import StoryStage
from app.services.stages.save_stage import SaveStage
from app.services.stages.slides_stage import SlidesStage


__all__ = [
    # Base classes
    "BaseStage",
    "StageContext",
    "StageError",
    "StageRegistry",
    "get_registry",
    "register_stage",
    # Stage implementations
    "ParseStage",
    "TranscribeStage",
    "CleanStage",
    "ChunkStage",
    "LongreadStage",
    "SummarizeStage",
    "StoryStage",
    "SaveStage",
    "SlidesStage",
    # Factory function
    "create_default_stages",
]


def create_default_stages(
    settings,
    config_resolver=None,
    processing_strategy=None,
    registry: StageRegistry | None = None,
) -> StageRegistry:
    """Create and register all default pipeline stages.

    Args:
        settings: Application settings
        config_resolver: ConfigResolver for model overrides (created if None)
        processing_strategy: ProcessingStrategy for AI client creation (created if None)
        registry: Optional registry to use (creates new if None)

    Returns:
        Registry with all stages registered

    Example:
        registry = create_default_stages(settings)
        stages = registry.build_pipeline(["parse", "transcribe", ...])
    """
    if registry is None:
        registry = StageRegistry()

    # Register stages in dependency order
    registry.register(ParseStage(settings))
    registry.register(TranscribeStage(settings))
    registry.register(CleanStage(settings, config_resolver, processing_strategy))
    registry.register(SlidesStage(settings, config_resolver, processing_strategy))
    registry.register(ChunkStage(settings))
    registry.register(LongreadStage(settings, config_resolver, processing_strategy))
    registry.register(SummarizeStage(settings, config_resolver, processing_strategy))
    registry.register(StoryStage(settings, config_resolver, processing_strategy))
    registry.register(SaveStage(settings))

    return registry


# Default stage names for full pipeline
# Note: story stage is conditional based on content_type
# v0.25+: chunk moved AFTER longread/story (deterministic H2 parsing)
DEFAULT_PIPELINE_STAGES = [
    "parse",
    "transcribe",
    "clean",
    "slides",      # v0.84+: Optional, skipped when no slides
    "longread",    # Skipped for LEADERSHIP
    "summarize",   # Skipped for LEADERSHIP
    "story",       # Skipped for EDUCATIONAL
    "chunk",       # v0.25+: H2 chunking from longread/story
    "save",
]
