"""Changelog API: parses CHANGELOG.md and returns structured JSON."""

import re
from pathlib import Path

from fastapi import APIRouter

from app.models.schemas import ChangelogEntry, ChangelogResponse, ChangelogVersion

router = APIRouter(prefix="/api", tags=["changelog"])

# Commitizen section headers → entry type
_TYPE_MAP: dict[str, str] = {
    "feat": "feat",
    "fix": "fix",
    "refactor": "refactor",
    "docs": "docs",
    "perf": "perf",
}

# Regex: ## 0.80.0 (2026-02-22) or ## v0.80.0 (2026-02-22)
_VERSION_RE = re.compile(r"^## v?(\d+\.\d+\.\d+) \((\d{4}-\d{2}-\d{2})\)")
# Regex: ### Feat, ### Fix, etc.
_SECTION_RE = re.compile(r"^### (\w+)")
# Regex: - description text
_ITEM_RE = re.compile(r"^- (.+)")


def _find_changelog() -> Path | None:
    """Find CHANGELOG.md by walking up from this file's directory.

    Supports both local dev and Docker:
    - Local:  backend/app/api/changelog_routes.py → parents[3] → project root
    - Docker: /app/app/api/changelog_routes.py   → parents[2] → /app/ (WORKDIR)
    """
    for parents_up in (3, 2, 1, 0):
        candidate = Path(__file__).parents[parents_up] / "CHANGELOG.md"
        if candidate.exists():
            return candidate
    return None


def parse_changelog(content: str) -> list[ChangelogVersion]:
    """Parse Commitizen-format CHANGELOG.md into structured versions."""
    versions: list[ChangelogVersion] = []
    current_version: ChangelogVersion | None = None
    current_type: str | None = None

    for line in content.splitlines():
        line = line.strip()

        # Version header
        version_match = _VERSION_RE.match(line)
        if version_match:
            current_version = ChangelogVersion(
                version=version_match.group(1),
                date=version_match.group(2),
                changes=[],
            )
            versions.append(current_version)
            current_type = None
            continue

        if current_version is None:
            continue

        # Section header (### Feat, ### Fix, etc.)
        section_match = _SECTION_RE.match(line)
        if section_match:
            section_name = section_match.group(1).lower()
            current_type = _TYPE_MAP.get(section_name)
            continue

        # Bullet item
        if current_type is not None:
            item_match = _ITEM_RE.match(line)
            if item_match:
                current_version.changes.append(
                    ChangelogEntry(type=current_type, description=item_match.group(1))
                )

    return versions


@router.get("/changelog")
async def get_changelog() -> ChangelogResponse:
    """Return parsed CHANGELOG.md as structured JSON."""
    changelog_path = _find_changelog()
    if changelog_path is None:
        return ChangelogResponse(versions=[])

    content = changelog_path.read_text(encoding="utf-8")
    versions = parse_changelog(content)
    return ChangelogResponse(versions=versions)
