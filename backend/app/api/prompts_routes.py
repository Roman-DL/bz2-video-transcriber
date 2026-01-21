"""
API routes for prompt management.

Provides endpoints to list available prompt variants for each pipeline stage.
"""

from collections import defaultdict

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.models.schemas import (
    ComponentPrompts,
    PromptVariantInfo,
    StagePromptsResponse,
)

router = APIRouter(prefix="/api/prompts", tags=["prompts"])

# Valid pipeline stages with their expected components
STAGE_COMPONENTS: dict[str, list[str]] = {
    "cleaning": ["system", "user"],
    "longread": ["system", "instructions", "template"],
    "summary": ["system", "instructions", "template"],
    "story": ["system", "instructions", "template"],
}


def get_component_for_file(filename: str, expected_components: set[str]) -> str | None:
    """
    Determine which component a prompt file belongs to based on filename.

    Files are matched if the component name appears in the filename.
    For example, "system_v2.md" matches "system" component.

    Args:
        filename: Prompt filename (e.g., "system_v2.md")
        expected_components: Set of valid component names for the stage

    Returns:
        Component name if matched, None otherwise
    """
    name = filename.removesuffix(".md").lower()
    for comp in expected_components:
        if comp in name:
            return comp
    return None


@router.get("/{stage}", response_model=StagePromptsResponse)
async def get_stage_prompts(stage: str) -> StagePromptsResponse:
    """
    Get available prompt variants for a pipeline stage.

    Scans both external (prompts_dir) and built-in (config_dir/prompts)
    directories for prompt files. External prompts take precedence.

    Args:
        stage: Pipeline stage name (cleaning, longread, summary, story)

    Returns:
        StagePromptsResponse with available components and their variants

    Raises:
        HTTPException: 400 if stage is invalid
    """
    if stage not in STAGE_COMPONENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage: {stage}. Valid stages: {list(STAGE_COMPONENTS.keys())}",
        )

    settings = get_settings()
    expected_components = set(STAGE_COMPONENTS[stage])
    variants_by_component: dict[str, list[PromptVariantInfo]] = defaultdict(list)
    seen_files: set[str] = set()

    # Directories to scan (external first for priority)
    dirs_to_scan: list[tuple] = []
    if settings.prompts_dir:
        dirs_to_scan.append((settings.prompts_dir / stage, "external"))
    dirs_to_scan.append((settings.config_dir / "prompts" / stage, "builtin"))

    # Scan directories for prompt files
    for prompt_dir, source in dirs_to_scan:
        if not prompt_dir.exists():
            continue
        for filepath in prompt_dir.glob("*.md"):
            # Skip already seen files (external takes precedence)
            if filepath.name in seen_files:
                continue
            seen_files.add(filepath.name)

            # Determine which component this file belongs to
            component = get_component_for_file(filepath.name, expected_components)
            if component:
                variants_by_component[component].append(
                    PromptVariantInfo(
                        name=filepath.name.removesuffix(".md"),
                        source=source,
                        filename=filepath.name,
                    )
                )

    # Build response with all expected components
    components = [
        ComponentPrompts(
            component=comp,
            default=comp,
            variants=variants_by_component.get(comp, []),
        )
        for comp in STAGE_COMPONENTS[stage]
    ]

    return StagePromptsResponse(stage=stage, components=components)
