"""Application version from VERSION file + BUILD_NUMBER from environment."""

import os
from pathlib import Path


def get_version() -> str:
    """Read version from VERSION file.

    Searches at different directory depths:
    - Local:  backend/app/version.py → parents[2] → project root
    - Docker: /app/app/version.py   → parents[1] → /app/ (WORKDIR)
    """
    for parents_up in (2, 1, 0):
        candidate = Path(__file__).parents[parents_up] / "VERSION"
        if candidate.exists():
            return candidate.read_text().strip()
    return "0.0.0-dev"


def get_build_number() -> int:
    """Read build number from BUILD_NUMBER environment variable."""
    return int(os.environ.get("BUILD_NUMBER", "0"))


__version__ = get_version()
__build__ = get_build_number()
