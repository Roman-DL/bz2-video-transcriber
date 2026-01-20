"""
Stage result caching service.

Provides persistent caching of pipeline stage results with versioning.
Allows re-running stages with different models while preserving history.

Example:
    cache = StageResultCache(settings)

    # Save stage result
    entry = await cache.save(
        archive_path=Path("/data/archive/2025/01.09 ПШ/Video"),
        stage=CacheStageName.CLEANING,
        result=cleaned_transcript,
        model_name="gemma2:9b",
        input_hash=cache.compute_hash(raw_transcript),
    )

    # Load cached result
    result = await cache.load(
        archive_path=archive_path,
        stage=CacheStageName.CLEANING,
        version=1,  # Optional, loads current if None
    )

    # Get cache info
    info = await cache.get_info(archive_path)
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.config import Settings
from app.models.cache import (
    CacheEntry,
    CacheInfo,
    CacheManifest,
    CacheStageName,
    StageVersionInfo,
    VersionDetail,
)

logger = logging.getLogger(__name__)

# Cache directory name (hidden)
CACHE_DIR = ".cache"
MANIFEST_FILE = "manifest.json"


class StageResultCache:
    """Service for caching pipeline stage results.

    Manages versioned cache of intermediate results in the archive directory.
    Each stage result is stored as a JSON file with version tracking.

    Directory structure:
        archive/2025/01.09 ПШ/Video Title/
        ├── pipeline_results.json    # Current results
        └── .cache/
            ├── manifest.json        # Versions and metadata
            ├── transcription/v1.json
            ├── cleaning/v1.json
            ├── cleaning/v2.json     # Re-run with different model
            └── ...

    Attributes:
        settings: Application settings
    """

    def __init__(self, settings: Settings):
        """Initialize cache service.

        Args:
            settings: Application settings
        """
        self.settings = settings

    def _get_cache_dir(self, archive_path: Path) -> Path:
        """Get cache directory path for archive.

        Args:
            archive_path: Archive directory path

        Returns:
            Path to cache directory
        """
        return archive_path / CACHE_DIR

    def _get_manifest_path(self, archive_path: Path) -> Path:
        """Get manifest file path.

        Args:
            archive_path: Archive directory path

        Returns:
            Path to manifest.json
        """
        return self._get_cache_dir(archive_path) / MANIFEST_FILE

    def _get_stage_dir(self, archive_path: Path, stage: CacheStageName) -> Path:
        """Get stage directory path.

        Args:
            archive_path: Archive directory path
            stage: Stage name

        Returns:
            Path to stage directory
        """
        return self._get_cache_dir(archive_path) / stage.value

    async def load_manifest(self, archive_path: Path) -> CacheManifest | None:
        """Load cache manifest from archive.

        Args:
            archive_path: Archive directory path

        Returns:
            CacheManifest or None if not exists
        """
        manifest_path = self._get_manifest_path(archive_path)

        if not manifest_path.exists():
            return None

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return CacheManifest.model_validate(data)
        except Exception as e:
            logger.warning(f"Failed to load cache manifest: {e}")
            return None

    async def save_manifest(
        self,
        archive_path: Path,
        manifest: CacheManifest,
    ) -> None:
        """Save cache manifest to archive.

        Args:
            archive_path: Archive directory path
            manifest: CacheManifest to save
        """
        cache_dir = self._get_cache_dir(archive_path)
        cache_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = self._get_manifest_path(archive_path)

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(
                manifest.model_dump(mode="json"),
                f,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

        logger.debug(f"Saved cache manifest: {manifest_path}")

    async def save(
        self,
        archive_path: Path,
        stage: CacheStageName,
        result: BaseModel,
        model_name: str,
        input_hash: str = "",
        metadata: dict | None = None,
    ) -> CacheEntry:
        """Save stage result to cache.

        Creates new version entry and stores result as JSON file.

        Args:
            archive_path: Archive directory path
            stage: Stage name
            result: Pydantic model result to cache
            model_name: Model used for this result
            input_hash: Hash of input data (for cache invalidation)
            metadata: Additional metadata to store

        Returns:
            Created CacheEntry
        """
        # Load or create manifest
        manifest = await self.load_manifest(archive_path)
        video_id = archive_path.name

        if manifest is None:
            manifest = CacheManifest(video_id=video_id)

        # Get next version number
        next_version = manifest.get_latest_version(stage) + 1

        # Create stage directory
        stage_dir = self._get_stage_dir(archive_path, stage)
        stage_dir.mkdir(parents=True, exist_ok=True)

        # Save result file
        file_name = f"v{next_version}.json"
        file_path = stage_dir / file_name
        relative_path = f"{stage.value}/{file_name}"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(
                result.model_dump(mode="json"),
                f,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

        # Create cache entry
        entry = CacheEntry(
            version=next_version,
            stage=stage,
            model_name=model_name,
            input_hash=input_hash,
            file_path=relative_path,
            is_current=True,
            metadata=metadata or {},
        )

        # Add to manifest
        manifest.add_entry(entry)
        await self.save_manifest(archive_path, manifest)

        logger.info(
            f"Cached {stage.value} v{next_version}: {file_path.name} "
            f"(model: {model_name})"
        )

        return entry

    async def load(
        self,
        archive_path: Path,
        stage: CacheStageName,
        version: int | None = None,
        model_class: type[BaseModel] | None = None,
    ) -> dict | BaseModel | None:
        """Load cached stage result.

        Args:
            archive_path: Archive directory path
            stage: Stage name
            version: Version to load (None = current)
            model_class: Pydantic model class to parse result into

        Returns:
            Cached result as dict or Pydantic model, None if not found
        """
        manifest = await self.load_manifest(archive_path)
        if manifest is None:
            return None

        # Get entry
        if version is None:
            entry = manifest.get_current_entry(stage)
        else:
            entries = manifest.get_all_entries(stage)
            entry = next((e for e in entries if e.version == version), None)

        if entry is None:
            return None

        # Load file
        file_path = self._get_cache_dir(archive_path) / entry.file_path

        if not file_path.exists():
            logger.warning(f"Cache file not found: {file_path}")
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if model_class is not None:
                return model_class.model_validate(data)
            return data

        except Exception as e:
            logger.error(f"Failed to load cache file {file_path}: {e}")
            return None

    async def get_info(self, archive_path: Path) -> CacheInfo:
        """Get cache information for a video.

        Args:
            archive_path: Archive directory path

        Returns:
            CacheInfo with all stage versions
        """
        video_id = archive_path.name
        manifest = await self.load_manifest(archive_path)

        if manifest is None:
            return CacheInfo(video_id=video_id, has_cache=False)

        stages: list[StageVersionInfo] = []

        for stage in CacheStageName:
            entries = manifest.get_all_entries(stage)
            if not entries:
                continue

            current = manifest.get_current_entry(stage)
            current_version = current.version if current else None

            versions = [
                VersionDetail(
                    version=e.version,
                    model_name=e.model_name,
                    created_at=e.created_at,
                    is_current=e.is_current,
                )
                for e in entries
            ]

            stages.append(
                StageVersionInfo(
                    stage=stage.value,
                    total_versions=len(entries),
                    current_version=current_version,
                    versions=versions,
                )
            )

        return CacheInfo(
            video_id=video_id,
            has_cache=len(stages) > 0,
            stages=stages,
        )

    async def set_current_version(
        self,
        archive_path: Path,
        stage: CacheStageName,
        version: int,
    ) -> bool:
        """Set specific version as current.

        Args:
            archive_path: Archive directory path
            stage: Stage name
            version: Version number to activate

        Returns:
            True if version was found and activated
        """
        manifest = await self.load_manifest(archive_path)
        if manifest is None:
            return False

        result = manifest.set_current_version(stage, version)
        if result:
            await self.save_manifest(archive_path, manifest)

        return result

    async def has_cache(self, archive_path: Path, stage: CacheStageName) -> bool:
        """Check if cache exists for a stage.

        Args:
            archive_path: Archive directory path
            stage: Stage name

        Returns:
            True if at least one cached version exists
        """
        manifest = await self.load_manifest(archive_path)
        if manifest is None:
            return False

        return len(manifest.get_all_entries(stage)) > 0

    async def invalidate(
        self,
        archive_path: Path,
        stage: CacheStageName,
        input_hash: str,
    ) -> bool:
        """Check if cache is invalidated by input change.

        Compares stored input_hash with provided hash to determine
        if cached result is still valid.

        Args:
            archive_path: Archive directory path
            stage: Stage name
            input_hash: Current input hash

        Returns:
            True if cache is invalidated (hash mismatch)
        """
        manifest = await self.load_manifest(archive_path)
        if manifest is None:
            return True

        current = manifest.get_current_entry(stage)
        if current is None:
            return True

        # Empty stored hash means never validated
        if not current.input_hash:
            return False

        return current.input_hash != input_hash

    @staticmethod
    def compute_hash(data: Any) -> str:
        """Compute SHA256 hash of data.

        Works with Pydantic models, dicts, and strings.

        Args:
            data: Data to hash

        Returns:
            Hex-encoded SHA256 hash
        """
        if isinstance(data, BaseModel):
            content = data.model_dump_json()
        elif isinstance(data, dict):
            content = json.dumps(data, sort_keys=True, ensure_ascii=False)
        else:
            content = str(data)

        return hashlib.sha256(content.encode()).hexdigest()


if __name__ == "__main__":
    """Run tests when executed directly."""
    import asyncio
    import sys
    import tempfile
    from datetime import datetime

    from pydantic import BaseModel as PydanticBaseModel

    print("\nRunning StageResultCache tests...\n")
    errors = []

    class MockResult(PydanticBaseModel):
        """Mock result for testing."""

        text: str
        value: int

    async def run_tests():
        from app.config import get_settings

        settings = get_settings()
        cache = StageResultCache(settings)

        # Test 1: compute_hash
        print("Test 1: compute_hash...", end=" ")
        try:
            hash1 = cache.compute_hash({"a": 1, "b": 2})
            hash2 = cache.compute_hash({"b": 2, "a": 1})  # Same content, different order
            hash3 = cache.compute_hash({"a": 1, "b": 3})  # Different content

            assert hash1 == hash2, "Same content should produce same hash"
            assert hash1 != hash3, "Different content should produce different hash"

            model_hash = cache.compute_hash(MockResult(text="hello", value=42))
            assert len(model_hash) == 64, "SHA256 should be 64 hex chars"

            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            errors.append(("compute_hash", e))

        # Test 2: Save and load manifest
        print("Test 2: Save and load manifest...", end=" ")
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                archive_path = Path(temp_dir) / "test_video"
                archive_path.mkdir()

                # Create and save manifest
                manifest = CacheManifest(video_id="test-video")
                await cache.save_manifest(archive_path, manifest)

                # Load manifest
                loaded = await cache.load_manifest(archive_path)
                assert loaded is not None
                assert loaded.video_id == "test-video"

                print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            errors.append(("Save/load manifest", e))

        # Test 3: Save and load result
        print("Test 3: Save and load result...", end=" ")
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                archive_path = Path(temp_dir) / "test_video"
                archive_path.mkdir()

                result = MockResult(text="test content", value=42)

                # Save result
                entry = await cache.save(
                    archive_path=archive_path,
                    stage=CacheStageName.CLEANING,
                    result=result,
                    model_name="test-model",
                    input_hash="abc123",
                )

                assert entry.version == 1
                assert entry.is_current is True

                # Load result
                loaded = await cache.load(
                    archive_path=archive_path,
                    stage=CacheStageName.CLEANING,
                    model_class=MockResult,
                )

                assert loaded is not None
                assert isinstance(loaded, MockResult)
                assert loaded.text == "test content"
                assert loaded.value == 42

                print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            errors.append(("Save/load result", e))

        # Test 4: Multiple versions
        print("Test 4: Multiple versions...", end=" ")
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                archive_path = Path(temp_dir) / "test_video"
                archive_path.mkdir()

                # Save v1
                result1 = MockResult(text="version 1", value=1)
                entry1 = await cache.save(
                    archive_path=archive_path,
                    stage=CacheStageName.CHUNKING,
                    result=result1,
                    model_name="model-v1",
                )
                assert entry1.version == 1

                # Save v2
                result2 = MockResult(text="version 2", value=2)
                entry2 = await cache.save(
                    archive_path=archive_path,
                    stage=CacheStageName.CHUNKING,
                    result=result2,
                    model_name="model-v2",
                )
                assert entry2.version == 2

                # Current should be v2
                loaded = await cache.load(
                    archive_path=archive_path,
                    stage=CacheStageName.CHUNKING,
                    model_class=MockResult,
                )
                assert loaded is not None
                assert loaded.value == 2

                # Load v1 explicitly
                loaded_v1 = await cache.load(
                    archive_path=archive_path,
                    stage=CacheStageName.CHUNKING,
                    version=1,
                    model_class=MockResult,
                )
                assert loaded_v1 is not None
                assert loaded_v1.value == 1

                print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            errors.append(("Multiple versions", e))

        # Test 5: get_info
        print("Test 5: get_info...", end=" ")
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                archive_path = Path(temp_dir) / "test_video"
                archive_path.mkdir()

                # Empty cache
                info = await cache.get_info(archive_path)
                assert info.has_cache is False

                # Add some results
                await cache.save(
                    archive_path=archive_path,
                    stage=CacheStageName.CLEANING,
                    result=MockResult(text="clean", value=1),
                    model_name="model-1",
                )
                await cache.save(
                    archive_path=archive_path,
                    stage=CacheStageName.CLEANING,
                    result=MockResult(text="clean2", value=2),
                    model_name="model-2",
                )

                info = await cache.get_info(archive_path)
                assert info.has_cache is True
                assert len(info.stages) == 1
                assert info.stages[0].total_versions == 2
                assert info.stages[0].current_version == 2

                print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            errors.append(("get_info", e))

        # Test 6: set_current_version
        print("Test 6: set_current_version...", end=" ")
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                archive_path = Path(temp_dir) / "test_video"
                archive_path.mkdir()

                # Create 3 versions
                for i in range(1, 4):
                    await cache.save(
                        archive_path=archive_path,
                        stage=CacheStageName.LONGREAD,
                        result=MockResult(text=f"v{i}", value=i),
                        model_name=f"model-{i}",
                    )

                # Set v1 as current
                result = await cache.set_current_version(
                    archive_path=archive_path,
                    stage=CacheStageName.LONGREAD,
                    version=1,
                )
                assert result is True

                # Verify
                loaded = await cache.load(
                    archive_path=archive_path,
                    stage=CacheStageName.LONGREAD,
                    model_class=MockResult,
                )
                assert loaded is not None
                assert loaded.value == 1

                print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            errors.append(("set_current_version", e))

        # Test 7: invalidate
        print("Test 7: invalidate...", end=" ")
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                archive_path = Path(temp_dir) / "test_video"
                archive_path.mkdir()

                # No cache - always invalidated
                is_invalid = await cache.invalidate(
                    archive_path=archive_path,
                    stage=CacheStageName.SUMMARY,
                    input_hash="hash1",
                )
                assert is_invalid is True

                # Save with hash
                await cache.save(
                    archive_path=archive_path,
                    stage=CacheStageName.SUMMARY,
                    result=MockResult(text="summary", value=1),
                    model_name="model",
                    input_hash="hash1",
                )

                # Same hash - not invalidated
                is_invalid = await cache.invalidate(
                    archive_path=archive_path,
                    stage=CacheStageName.SUMMARY,
                    input_hash="hash1",
                )
                assert is_invalid is False

                # Different hash - invalidated
                is_invalid = await cache.invalidate(
                    archive_path=archive_path,
                    stage=CacheStageName.SUMMARY,
                    input_hash="hash2",
                )
                assert is_invalid is True

                print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            errors.append(("invalidate", e))

        return errors

    errors = asyncio.run(run_tests())

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
