"""
Cache models for pipeline stage results versioning.

Provides Pydantic models for tracking versions of intermediate pipeline results.
Each stage output can have multiple versions stored in the cache directory.

Example:
    archive/2025/01.09 ПШ/Video Title/
    ├── pipeline_results.json    # Current results
    └── .cache/
        ├── manifest.json        # Versions and metadata
        ├── transcription/v1.json
        ├── cleaning/v1.json
        ├── cleaning/v2.json     # Re-run with different model
        └── ...
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class CacheStageName(str, Enum):
    """Valid stage names for caching."""

    TRANSCRIPTION = "transcription"
    CLEANING = "cleaning"
    CHUNKING = "chunking"
    LONGREAD = "longread"
    SUMMARY = "summary"


class CacheEntry(BaseModel):
    """Single cached result entry for a pipeline stage.

    Represents one version of a stage's output. Multiple entries
    can exist for the same stage (re-runs with different models).

    Attributes:
        version: Version number (1-based, auto-incremented)
        stage: Stage name (transcription, cleaning, etc.)
        model_name: LLM/Whisper model used for this result
        created_at: When this version was created
        input_hash: SHA256 hash of input data (for cache invalidation)
        file_path: Relative path to cached JSON file
        is_current: Whether this is the current active version
        metadata: Additional metadata (prompt version, config, etc.)
    """

    version: int = Field(..., ge=1, description="Version number (1-based)")
    stage: CacheStageName = Field(..., description="Stage name")
    model_name: str = Field(..., description="Model used for generation")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When this version was created",
    )
    input_hash: str = Field(
        default="",
        description="SHA256 hash of input data",
    )
    file_path: str = Field(..., description="Relative path to cached file")
    is_current: bool = Field(
        default=True,
        description="Whether this is the active version",
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata (prompt version, config, etc.)",
    )


class CacheManifest(BaseModel):
    """Manifest tracking all cached stage results for a video.

    Stored as .cache/manifest.json in the video's archive directory.
    Contains entries for all stages and tracks current versions.

    Attributes:
        video_id: Unique video identifier
        created_at: When cache was first created
        updated_at: Last modification time
        entries: Mapping of stage -> list of CacheEntry
        pipeline_version: Pipeline version that created this cache

    Example:
        manifest = CacheManifest(video_id="2025-01-09_ПШ-SV_topic")
        manifest.add_entry(CacheEntry(
            version=1,
            stage=CacheStageName.CLEANING,
            model_name="gemma2:9b",
            file_path="cleaning/v1.json",
        ))
    """

    video_id: str = Field(..., description="Video identifier")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When cache was created",
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last modification time",
    )
    entries: dict[str, list[CacheEntry]] = Field(
        default_factory=dict,
        description="Stage name -> list of cached versions",
    )
    pipeline_version: str = Field(
        default="1.0.0",
        description="Pipeline version",
    )

    def get_current_entry(self, stage: CacheStageName) -> CacheEntry | None:
        """Get current active entry for a stage.

        Args:
            stage: Stage name

        Returns:
            Current CacheEntry or None if not cached
        """
        stage_key = stage.value
        if stage_key not in self.entries:
            return None

        for entry in self.entries[stage_key]:
            if entry.is_current:
                return entry
        return None

    def get_all_entries(self, stage: CacheStageName) -> list[CacheEntry]:
        """Get all cached entries for a stage.

        Args:
            stage: Stage name

        Returns:
            List of all CacheEntry versions (oldest first)
        """
        stage_key = stage.value
        return self.entries.get(stage_key, [])

    def get_latest_version(self, stage: CacheStageName) -> int:
        """Get latest version number for a stage.

        Args:
            stage: Stage name

        Returns:
            Latest version number (0 if no entries)
        """
        entries = self.get_all_entries(stage)
        if not entries:
            return 0
        return max(e.version for e in entries)

    def add_entry(self, entry: CacheEntry) -> None:
        """Add new cache entry and mark as current.

        Marks all previous entries for this stage as non-current.

        Args:
            entry: CacheEntry to add
        """
        stage_key = entry.stage.value

        if stage_key not in self.entries:
            self.entries[stage_key] = []

        # Mark all existing entries as non-current
        for existing in self.entries[stage_key]:
            existing.is_current = False

        # Add new entry
        self.entries[stage_key].append(entry)
        self.updated_at = datetime.now()

    def set_current_version(self, stage: CacheStageName, version: int) -> bool:
        """Set specific version as current.

        Args:
            stage: Stage name
            version: Version number to activate

        Returns:
            True if version was found and activated
        """
        stage_key = stage.value
        if stage_key not in self.entries:
            return False

        found = False
        for entry in self.entries[stage_key]:
            if entry.version == version:
                entry.is_current = True
                found = True
            else:
                entry.is_current = False

        if found:
            self.updated_at = datetime.now()
        return found


class StageVersionInfo(BaseModel):
    """Summary of a stage's cache versions (for API response).

    Provides a concise view of cached versions for display in UI.

    Attributes:
        stage: Stage name
        total_versions: Number of cached versions
        current_version: Currently active version number
        versions: List of version details
    """

    stage: str = Field(..., description="Stage name")
    total_versions: int = Field(..., ge=0, description="Number of versions")
    current_version: int | None = Field(
        default=None,
        description="Current active version (None if not cached)",
    )
    versions: list["VersionDetail"] = Field(
        default_factory=list,
        description="Details of each version",
    )


class VersionDetail(BaseModel):
    """Details of a single cached version.

    Attributes:
        version: Version number
        model_name: Model used
        created_at: Creation timestamp
        is_current: Whether this is active
    """

    version: int = Field(..., ge=1)
    model_name: str
    created_at: datetime
    is_current: bool = False


class CacheInfo(BaseModel):
    """Cache information for a video (API response).

    Attributes:
        video_id: Video identifier
        has_cache: Whether cache exists
        stages: Information about each cached stage
    """

    video_id: str
    has_cache: bool = False
    stages: list[StageVersionInfo] = Field(default_factory=list)


class RerunRequest(BaseModel):
    """Request to rerun a pipeline stage.

    Attributes:
        video_id: Video identifier
        stage: Stage to rerun
        model: Optional model override
        from_version: Version to use as input (None = use current)
    """

    video_id: str = Field(..., description="Video identifier")
    stage: CacheStageName = Field(..., description="Stage to rerun")
    model: str | None = Field(
        default=None,
        description="Model override (uses default if None)",
    )
    from_version: int | None = Field(
        default=None,
        description="Input version (None = use previous stage's current)",
    )


class RerunResponse(BaseModel):
    """Response from stage rerun.

    Attributes:
        video_id: Video identifier
        stage: Stage that was rerun
        new_version: Newly created version number
        model_name: Model that was used
    """

    video_id: str
    stage: str
    new_version: int
    model_name: str


# Self-reference resolution for Pydantic
StageVersionInfo.model_rebuild()


if __name__ == "__main__":
    """Run tests when executed directly."""
    import sys

    print("\nRunning cache models tests...\n")
    errors = []

    # Test 1: CacheEntry creation
    print("Test 1: CacheEntry creation...", end=" ")
    try:
        entry = CacheEntry(
            version=1,
            stage=CacheStageName.CLEANING,
            model_name="gemma2:9b",
            file_path="cleaning/v1.json",
            input_hash="abc123",
        )
        assert entry.version == 1
        assert entry.stage == CacheStageName.CLEANING
        assert entry.is_current is True
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(("CacheEntry", e))

    # Test 2: CacheManifest basic operations
    print("Test 2: CacheManifest basic operations...", end=" ")
    try:
        manifest = CacheManifest(video_id="test-video")
        assert manifest.video_id == "test-video"
        assert manifest.entries == {}
        assert manifest.get_latest_version(CacheStageName.CLEANING) == 0
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(("CacheManifest basic", e))

    # Test 3: Adding entries
    print("Test 3: Adding entries...", end=" ")
    try:
        manifest = CacheManifest(video_id="test-video")

        # Add first entry
        entry1 = CacheEntry(
            version=1,
            stage=CacheStageName.CLEANING,
            model_name="gemma2:9b",
            file_path="cleaning/v1.json",
        )
        manifest.add_entry(entry1)

        assert manifest.get_latest_version(CacheStageName.CLEANING) == 1
        current = manifest.get_current_entry(CacheStageName.CLEANING)
        assert current is not None
        assert current.version == 1
        assert current.is_current is True

        # Add second entry (should become current)
        entry2 = CacheEntry(
            version=2,
            stage=CacheStageName.CLEANING,
            model_name="qwen2.5:14b",
            file_path="cleaning/v2.json",
        )
        manifest.add_entry(entry2)

        assert manifest.get_latest_version(CacheStageName.CLEANING) == 2
        current = manifest.get_current_entry(CacheStageName.CLEANING)
        assert current is not None
        assert current.version == 2

        # Check first entry is no longer current
        entries = manifest.get_all_entries(CacheStageName.CLEANING)
        assert len(entries) == 2
        assert entries[0].is_current is False
        assert entries[1].is_current is True

        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(("Adding entries", e))

    # Test 4: Set current version
    print("Test 4: Set current version...", end=" ")
    try:
        manifest = CacheManifest(video_id="test-video")

        for v in range(1, 4):
            manifest.add_entry(CacheEntry(
                version=v,
                stage=CacheStageName.CHUNKING,
                model_name=f"model-v{v}",
                file_path=f"chunking/v{v}.json",
            ))

        # Set version 1 as current
        result = manifest.set_current_version(CacheStageName.CHUNKING, 1)
        assert result is True

        current = manifest.get_current_entry(CacheStageName.CHUNKING)
        assert current is not None
        assert current.version == 1

        # Non-existent version
        result = manifest.set_current_version(CacheStageName.CHUNKING, 99)
        assert result is False

        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(("Set current version", e))

    # Test 5: StageVersionInfo
    print("Test 5: StageVersionInfo...", end=" ")
    try:
        info = StageVersionInfo(
            stage="cleaning",
            total_versions=2,
            current_version=2,
            versions=[
                VersionDetail(
                    version=1,
                    model_name="gemma2:9b",
                    created_at=datetime.now(),
                    is_current=False,
                ),
                VersionDetail(
                    version=2,
                    model_name="qwen2.5:14b",
                    created_at=datetime.now(),
                    is_current=True,
                ),
            ],
        )
        assert info.total_versions == 2
        assert info.current_version == 2
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(("StageVersionInfo", e))

    # Test 6: CacheInfo
    print("Test 6: CacheInfo...", end=" ")
    try:
        cache_info = CacheInfo(
            video_id="test-video",
            has_cache=True,
            stages=[
                StageVersionInfo(
                    stage="cleaning",
                    total_versions=1,
                    current_version=1,
                ),
            ],
        )
        assert cache_info.has_cache is True
        assert len(cache_info.stages) == 1
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(("CacheInfo", e))

    # Test 7: RerunRequest validation
    print("Test 7: RerunRequest validation...", end=" ")
    try:
        request = RerunRequest(
            video_id="2025-01-09_ПШ-SV_topic",
            stage=CacheStageName.CLEANING,
            model="gemma2:9b",
        )
        assert request.from_version is None
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        errors.append(("RerunRequest", e))

    # Summary
    print("\n" + "=" * 40)
    if errors:
        print(f"FAILED: {len(errors)} test(s)")
        for name, err in errors:
            print(f"  - {name}: {err}")
        sys.exit(1)
    else:
        print("All tests passed!")
        sys.exit(0)
