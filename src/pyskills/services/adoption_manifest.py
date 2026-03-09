"""Adoption manifest persistence and rollback helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import shutil

from pyskills.models import AdoptionManifest


@dataclass
class UndoResult:
    """Summary for one adoption undo operation."""

    restored_paths: int = 0
    removed_created_paths: int = 0
    skipped_paths: int = 0


def write_adoption_manifest(
    *,
    manifest: AdoptionManifest,
    base_dir: Path,
) -> Path:
    """Write an adoption manifest to disk.

    Parameters
    ----------
    manifest : AdoptionManifest
        Manifest to persist.
    base_dir : pathlib.Path
        Directory where manifest files are stored.

    Returns
    -------
    pathlib.Path
        Written manifest path.
    """

    base_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    path = base_dir / f"adopt-{stamp}.json"
    suffix = 1
    while path.exists():
        path = base_dir / f"adopt-{stamp}-{suffix}.json"
        suffix += 1

    path.write_text(
        manifest.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def undo_adoption(*, manifest_path: Path) -> UndoResult:
    """Undo one adoption apply operation.

    Parameters
    ----------
    manifest_path : pathlib.Path
        Path to a previously generated manifest.

    Returns
    -------
    UndoResult
        Summary of restored and skipped paths.
    """

    manifest = AdoptionManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    result = UndoResult()

    for created in manifest.created_paths:
        created_path = Path(created)
        if not (created_path.exists() or created_path.is_symlink()):
            result.skipped_paths += 1
            continue
        if created_path.is_symlink() or created_path.is_file():
            created_path.unlink(missing_ok=True)
        else:
            shutil.rmtree(created_path, ignore_errors=True)
        result.removed_created_paths += 1

    # Undo replacements in reverse order to preserve dependency order.
    for entry in reversed(manifest.backup_entries):
        original = Path(entry.original_path)
        backup = Path(entry.backup_path)
        if not (backup.exists() or backup.is_symlink()):
            result.skipped_paths += 1
            continue
        if original.exists() or original.is_symlink():
            if original.is_symlink() or original.is_file():
                original.unlink(missing_ok=True)
            else:
                shutil.rmtree(original, ignore_errors=True)
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(backup), str(original))
        result.restored_paths += 1

    return result
