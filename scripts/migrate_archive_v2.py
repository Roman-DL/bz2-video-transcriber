#!/usr/bin/env python3
"""Migrate archive from 4-level to 3-level structure.

4-level (old):
  Regular: archive/{year}/{event_type}/{MM.DD}/{stream title (speaker)}/
  Offsite: archive/{year}/Выездные/{event_type}/{title (speaker)}/

3-level (new):
  Regular: archive/{year}/{event_type}/{MM.DD stream. title (speaker)}/
  Offsite: archive/{year}/{MM event_type}/{title (speaker)}/

Usage:
  python3 scripts/migrate_archive_v2.py --dry-run    # Preview changes
  python3 scripts/migrate_archive_v2.py               # Execute migration

The script:
1. Scans the archive directory for 4-level folders
2. Builds old→new path mapping
3. Saves rollback JSON before making changes
4. Moves folders to new structure
5. Updates metadata.archivePath in pipeline_results.json
6. Removes empty intermediate folders (MM.DD, Выездные)
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


ARCHIVE_DIR = Path("/data/archive")
ROLLBACK_FILE = ARCHIVE_DIR / "migration_rollback.json"


def find_regular_4level(archive_dir: Path) -> list[dict]:
    """Find regular events with 4-level structure: year/event_type/MM.DD/topic/."""
    migrations = []

    for year_dir in sorted(archive_dir.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue

        for event_type_dir in sorted(year_dir.iterdir()):
            if not event_type_dir.is_dir() or event_type_dir.name == "Выездные":
                continue

            event_type = event_type_dir.name

            for mid_dir in sorted(event_type_dir.iterdir()):
                if not mid_dir.is_dir():
                    continue

                # Check if mid_dir matches MM.DD pattern (date folder)
                if not re.match(r"^\d{2}\.\d{2}$", mid_dir.name):
                    # Already 3-level (topic folder directly under event_type)
                    continue

                date_prefix = mid_dir.name  # "08.04"

                for topic_dir in sorted(mid_dir.iterdir()):
                    if not topic_dir.is_dir():
                        continue

                    # Old: year/event_type/MM.DD/stream title (speaker)/
                    # New: year/event_type/MM.DD stream. title (speaker)/
                    # But we need to figure out if there's a stream prefix
                    old_name = topic_dir.name
                    # Topic format: "SV Контент (Пепелина Инга)" or "Контент (Пепелина Инга)"
                    # Check if first word is a stream (uppercase latin/cyrillic short code)
                    parts = old_name.split(" ", 1)
                    if len(parts) == 2 and re.match(r"^[A-ZА-Я]{2,}", parts[0]):
                        # Has stream: "SV Контент (speaker)" -> "08.04 SV. Контент (speaker)"
                        stream = parts[0]
                        rest = parts[1]
                        new_name = f"{date_prefix} {stream}. {rest}"
                    else:
                        # No stream: "Контент (speaker)" -> "08.04 Контент (speaker)"
                        new_name = f"{date_prefix} {old_name}"

                    new_path = event_type_dir / new_name

                    migrations.append({
                        "old_path": str(topic_dir),
                        "new_path": str(new_path),
                        "type": "regular",
                        "empty_after": str(mid_dir),
                    })

    return migrations


def find_offsite_4level(archive_dir: Path) -> list[dict]:
    """Find offsite events: year/Выездные/event_type/topic/."""
    migrations = []

    for year_dir in sorted(archive_dir.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue

        vyezdnye_dir = year_dir / "Выездные"
        if not vyezdnye_dir.is_dir():
            continue

        for event_type_dir in sorted(vyezdnye_dir.iterdir()):
            if not event_type_dir.is_dir():
                continue

            event_type = event_type_dir.name

            for topic_dir in sorted(event_type_dir.iterdir()):
                if not topic_dir.is_dir():
                    continue

                # Get month from pipeline_results.json
                results_file = topic_dir / "pipeline_results.json"
                month = None

                if results_file.exists():
                    try:
                        with open(results_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        date_str = data.get("metadata", {}).get("date")
                        if date_str:
                            # date format: "YYYY-MM-DD"
                            month = date_str.split("-")[1]
                    except (json.JSONDecodeError, IOError, IndexError):
                        pass

                if month is None:
                    print(f"  WARNING: Cannot determine month for {topic_dir}, skipping")
                    continue

                # Old: year/Выездные/event_type/topic/
                # New: year/MM event_type/topic/
                new_event_group = f"{month} {event_type}"
                new_parent = year_dir / new_event_group
                new_path = new_parent / topic_dir.name

                migrations.append({
                    "old_path": str(topic_dir),
                    "new_path": str(new_path),
                    "type": "offsite",
                    "empty_after": str(event_type_dir),
                    "vyezdnye_dir": str(vyezdnye_dir),
                })

    return migrations


def update_pipeline_results(path: Path, new_archive_path: str) -> bool:
    """Update metadata.archivePath in pipeline_results.json."""
    results_file = path / "pipeline_results.json"
    if not results_file.exists():
        return False

    try:
        with open(results_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "metadata" in data and "archivePath" in data["metadata"]:
            data["metadata"]["archivePath"] = new_archive_path
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
    except (json.JSONDecodeError, IOError) as e:
        print(f"  WARNING: Failed to update {results_file}: {e}")

    return False


def run_migration(dry_run: bool = True):
    """Execute archive migration."""
    if not ARCHIVE_DIR.exists():
        print(f"Archive directory not found: {ARCHIVE_DIR}")
        sys.exit(1)

    print(f"Scanning archive: {ARCHIVE_DIR}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}\n")

    # Find all migrations
    regular = find_regular_4level(ARCHIVE_DIR)
    offsite = find_offsite_4level(ARCHIVE_DIR)
    migrations = regular + offsite

    if not migrations:
        print("No 4-level folders found. Archive is already migrated.")
        return

    print(f"Found {len(migrations)} folders to migrate:")
    print(f"  Regular: {len(regular)}")
    print(f"  Offsite: {len(offsite)}\n")

    for m in migrations:
        old = Path(m["old_path"]).relative_to(ARCHIVE_DIR)
        new = Path(m["new_path"]).relative_to(ARCHIVE_DIR)
        print(f"  [{m['type']:7s}] {old}")
        print(f"         → {new}\n")

    if dry_run:
        print("Dry run complete. Use without --dry-run to execute.")
        return

    # Save rollback mapping
    print(f"Saving rollback mapping to {ROLLBACK_FILE}...")
    rollback = {
        "created_at": datetime.now().isoformat(),
        "migrations": migrations,
    }
    with open(ROLLBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(rollback, f, ensure_ascii=False, indent=2)

    # Execute moves
    empty_dirs = set()
    for m in migrations:
        old_path = Path(m["old_path"])
        new_path = Path(m["new_path"])

        # Create parent if needed
        new_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"  Moving: {old_path.name} → {new_path.parent.name}/{new_path.name}")
        old_path.rename(new_path)

        # Update pipeline_results.json
        update_pipeline_results(new_path, str(new_path))

        # Track empty dirs for cleanup
        if "empty_after" in m:
            empty_dirs.add(m["empty_after"])
        if "vyezdnye_dir" in m:
            empty_dirs.add(m["vyezdnye_dir"])

    # Remove empty directories
    print("\nCleaning up empty directories...")
    for dir_path in sorted(empty_dirs, reverse=True):
        p = Path(dir_path)
        if p.exists() and p.is_dir():
            remaining = list(p.iterdir())
            if not remaining:
                print(f"  Removing empty: {p.relative_to(ARCHIVE_DIR)}")
                p.rmdir()
            else:
                print(f"  Keeping (not empty): {p.relative_to(ARCHIVE_DIR)} ({len(remaining)} items)")

    print(f"\nMigration complete. {len(migrations)} folders moved.")
    print(f"Rollback mapping saved to {ROLLBACK_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate archive from 4-level to 3-level structure")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without executing")
    args = parser.parse_args()

    run_migration(dry_run=args.dry_run)
