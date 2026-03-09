"""Lock health diagnostics services."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pyskills.shared import GLOBAL_LOCK_FILE, LOCAL_LOCK_FILE

from .locks import GLOBAL_LOCK_VERSION


@dataclass
class LockFileHealth:
    """Health summary for one lock file."""

    path: Path
    exists: bool
    version: int | None
    entries: int
    warnings: list[str] = field(default_factory=list)


@dataclass
class LockHealthReport:
    """Combined lock health report for project and global scope."""

    global_lock: LockFileHealth
    local_lock: LockFileHealth

    @property
    def warning_count(self) -> int:
        """Return total warning count across lock files."""

        return len(self.global_lock.warnings) + len(self.local_lock.warnings)


def diagnose_locks(cwd: Path | None = None) -> LockHealthReport:
    """Diagnose lock file health for local and global lock files.

    Parameters
    ----------
    cwd : pathlib.Path or None, optional
        Project working directory. Defaults to current working directory.

    Returns
    -------
    LockHealthReport
        Structured diagnostics for both lock files.
    """

    root = cwd or Path.cwd()
    global_path = Path.home() / ".agents" / GLOBAL_LOCK_FILE
    local_path = root / LOCAL_LOCK_FILE

    global_health = _diagnose_global_lock(global_path)
    local_health = _diagnose_local_lock(local_path)

    return LockHealthReport(global_lock=global_health, local_lock=local_health)


def _diagnose_global_lock(path: Path) -> LockFileHealth:
    """Diagnose global lock file health."""

    raw = _read_raw_json(path)
    if raw is None:
        return LockFileHealth(
            path=path,
            exists=False,
            version=None,
            entries=0,
            warnings=["Global lock file not found."],
        )

    version = raw.get("version") if isinstance(raw, dict) else None
    skills = raw.get("skills") if isinstance(raw, dict) else None
    entries = len(skills) if isinstance(skills, dict) else 0

    warnings: list[str] = []
    if not isinstance(version, int):
        warnings.append("Global lock has invalid or missing version.")
    elif version < GLOBAL_LOCK_VERSION:
        warnings.append(
            "Global lock version is outdated: "
            f"v{version} < v{GLOBAL_LOCK_VERSION}."
        )

    if isinstance(skills, dict):
        missing_source_id = 0
        missing_agents = 0
        missing_install_mode = 0

        for entry in skills.values():
            if not isinstance(entry, dict):
                continue

            source_id = entry.get("source_id")
            if not isinstance(source_id, str) or not source_id:
                missing_source_id += 1

            agents = entry.get("agents")
            if not isinstance(agents, list):
                missing_agents += 1

            install_mode = entry.get("install_mode")
            if install_mode not in {"symlink", "copy"}:
                missing_install_mode += 1

        if missing_source_id:
            warnings.append(
                "Global lock entries missing source_id: "
                f"{missing_source_id}"
            )
        if missing_agents:
            warnings.append(
                "Global lock entries missing agents metadata: "
                f"{missing_agents}"
            )
        if missing_install_mode:
            warnings.append(
                "Global lock entries missing install_mode: "
                f"{missing_install_mode}"
            )

    return LockFileHealth(
        path=path,
        exists=True,
        version=version if isinstance(version, int) else None,
        entries=entries,
        warnings=warnings,
    )


def _diagnose_local_lock(path: Path) -> LockFileHealth:
    """Diagnose local lock file health."""

    raw = _read_raw_json(path)
    if raw is None:
        return LockFileHealth(
            path=path,
            exists=False,
            version=None,
            entries=0,
            warnings=["Local lock file not found."],
        )

    version = raw.get("version") if isinstance(raw, dict) else None
    skills = raw.get("skills") if isinstance(raw, dict) else None
    entries = len(skills) if isinstance(skills, dict) else 0

    warnings: list[str] = []
    if not isinstance(version, int):
        warnings.append("Local lock has invalid or missing version.")

    return LockFileHealth(
        path=path,
        exists=True,
        version=version if isinstance(version, int) else None,
        entries=entries,
        warnings=warnings,
    )


def _read_raw_json(path: Path) -> dict[str, Any] | None:
    """Read raw JSON object from file path."""

    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    return payload
