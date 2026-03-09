"""Lockfile read/write and hashing services."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from pyskills.models import (
    LocalSkillLockEntry,
    LocalSkillLockFile,
    SkillLockEntry,
    SkillLockFile,
)
from pyskills.shared import GLOBAL_LOCK_FILE, LOCAL_LOCK_FILE

GLOBAL_LOCK_VERSION = 2


def read_global_lock() -> SkillLockFile:
    """Read the global lock file.

    Returns
    -------
    SkillLockFile
        Parsed lock contents or an empty default structure.
    """

    path = Path.home() / ".agents" / GLOBAL_LOCK_FILE
    if not path.exists():
        return SkillLockFile(version=GLOBAL_LOCK_VERSION)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        migrated = _migrate_global_lock_data(data)
        return SkillLockFile.model_validate(migrated)
    except Exception:
        return SkillLockFile(version=GLOBAL_LOCK_VERSION)


def write_global_lock(lock: SkillLockFile) -> Path:
    """Write the global lock file.

    Parameters
    ----------
    lock : SkillLockFile
        Lock content to persist.

    Returns
    -------
    pathlib.Path
        Path to the written lock file.
    """

    path = Path.home() / ".agents" / GLOBAL_LOCK_FILE
    lock.version = GLOBAL_LOCK_VERSION
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(lock.model_dump_json(indent=2), encoding="utf-8")
    return path


def add_skill_to_global_lock(
    skill_name: str,
    *,
    source: str,
    source_type: str,
    source_url: str,
    skill_path: str | None = None,
    skill_folder_hash: str = "",
    plugin_name: str | None = None,
    source_id: str | None = None,
    agents: list[str] | None = None,
    install_mode: str = "symlink",
) -> None:
    """Add or update a skill in the global lock.

    Parameters
    ----------
    skill_name : str
        Skill key.
    source : str
        Source identifier for the skill.
    source_type : str
        Source type label (for example ``local`` or ``github``).
    source_url : str
        Canonical source URL or path.
    skill_path : str or None, optional
        Relative path to ``SKILL.md`` inside source.
    skill_folder_hash : str, optional
        Content hash for skill directory.
    plugin_name : str or None, optional
        Optional plugin grouping metadata.
    source_id : str or None, optional
        Canonical source identifier for grouping and telemetry.
    agents : list of str or None, optional
        Agents targeted for this installation.
    install_mode : str, optional
        Install mode used for the skill (``symlink`` or ``copy``).

    Returns
    -------
    None
    """

    lock = read_global_lock()
    now = datetime.now(UTC).isoformat()
    existing = lock.skills.get(skill_name)

    previous_agents = existing.agents if existing else []
    merged_agents = sorted(set(previous_agents + (agents or [])))

    merged = SkillLockEntry(
        source=source,
        source_type=source_type,
        source_url=source_url,
        skill_path=skill_path,
        skill_folder_hash=skill_folder_hash,
        installed_at=existing.installed_at if existing else now,
        updated_at=now,
        plugin_name=plugin_name,
        source_id=source_id
        or existing.source_id
        if existing
        else _default_source_id(source_type, source, source_url),
        agents=merged_agents,
        install_mode=install_mode,
    )
    lock.skills[skill_name] = merged
    write_global_lock(lock)


def compute_skill_folder_hash(skill_dir: Path) -> str:
    """Compute a deterministic hash for all files in a skill directory.

    Parameters
    ----------
    skill_dir : pathlib.Path
        Skill directory root.

    Returns
    -------
    str
        SHA-256 hash of sorted relative path and file content pairs.
    """

    files: list[Path] = [p for p in skill_dir.rglob("*") if p.is_file()]
    files.sort(key=lambda p: p.relative_to(skill_dir).as_posix())

    h = hashlib.sha256()
    for file in files:
        rel = file.relative_to(skill_dir).as_posix().encode("utf-8")
        h.update(rel)
        h.update(file.read_bytes())
    return h.hexdigest()


def read_local_lock(cwd: Path | None = None) -> LocalSkillLockFile:
    """Read the local project lock file.

    Parameters
    ----------
    cwd : pathlib.Path or None, optional
        Project root path.

    Returns
    -------
    LocalSkillLockFile
        Parsed lock contents or an empty default structure.
    """

    path = (cwd or Path.cwd()) / LOCAL_LOCK_FILE
    if not path.exists():
        return LocalSkillLockFile(version=1)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return LocalSkillLockFile.model_validate(data)
    except Exception:
        return LocalSkillLockFile(version=1)


def write_local_lock(
    lock: LocalSkillLockFile, cwd: Path | None = None
) -> Path:
    """Write the local project lock file.

    Parameters
    ----------
    lock : LocalSkillLockFile
        Lock content to persist.
    cwd : pathlib.Path or None, optional
        Project root path.

    Returns
    -------
    pathlib.Path
        Path to the written lock file.
    """

    path = (cwd or Path.cwd()) / LOCAL_LOCK_FILE
    ordered = dict(sorted(lock.skills.items(), key=lambda item: item[0]))
    lock.skills = ordered
    path.write_text(lock.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def add_skill_to_local_lock(
    skill_name: str,
    entry: LocalSkillLockEntry,
    cwd: Path | None = None,
) -> None:
    """Add or update a skill in the local lock.

    Parameters
    ----------
    skill_name : str
        Skill key.
    entry : LocalSkillLockEntry
        Entry payload to store.
    cwd : pathlib.Path or None, optional
        Project root path.

    Returns
    -------
    None
    """

    lock = read_local_lock(cwd)
    lock.skills[skill_name] = entry
    write_local_lock(lock, cwd)


def remove_skill_from_local_lock(
    skill_name: str,
    cwd: Path | None = None,
) -> bool:
    """Remove a skill from the local lock.

    Parameters
    ----------
    skill_name : str
        Skill key to remove.
    cwd : pathlib.Path or None, optional
        Project root path.

    Returns
    -------
    bool
        ``True`` when an entry existed and was removed.
    """

    lock = read_local_lock(cwd)
    if skill_name not in lock.skills:
        return False
    del lock.skills[skill_name]
    write_local_lock(lock, cwd)
    return True


def remove_skill_from_global_lock(skill_name: str) -> bool:
    """Remove a skill from the global lock.

    Parameters
    ----------
    skill_name : str
        Skill key to remove.

    Returns
    -------
    bool
        ``True`` when an entry existed and was removed.
    """

    lock = read_global_lock()
    if skill_name not in lock.skills:
        return False
    del lock.skills[skill_name]
    write_global_lock(lock)
    return True


def remove_skill_agents_from_global_lock(
    skill_name: str,
    agents: list[str],
) -> bool:
    """Remove agent targets for a skill from the global lock.

    Parameters
    ----------
    skill_name : str
        Skill key to update.
    agents : list of str
        Agents removed from installation targets.

    Returns
    -------
    bool
        ``True`` when the lock was modified.
    """

    lock = read_global_lock()
    entry = lock.skills.get(skill_name)
    if entry is None:
        return False

    if not entry.agents:
        del lock.skills[skill_name]
        write_global_lock(lock)
        return True

    remaining = sorted(set(entry.agents) - set(agents))
    if not remaining:
        del lock.skills[skill_name]
        write_global_lock(lock)
        return True

    entry.agents = remaining
    entry.updated_at = datetime.now(UTC).isoformat()
    lock.skills[skill_name] = entry
    write_global_lock(lock)
    return True


def _migrate_global_lock_data(data: object) -> dict[str, object]:
    """Migrate raw global lock payload to v2 schema."""

    if not isinstance(data, dict):
        return {"version": GLOBAL_LOCK_VERSION, "skills": {}}

    raw_skills = data.get("skills")
    skills_dict = raw_skills if isinstance(raw_skills, dict) else {}

    now = datetime.now(UTC).isoformat()
    migrated_skills: dict[str, dict[str, object]] = {}
    for name, raw_entry in skills_dict.items():
        if not isinstance(name, str) or not isinstance(raw_entry, dict):
            continue

        source = raw_entry.get("source")
        source_type = raw_entry.get("source_type")
        source_url = raw_entry.get("source_url")
        if not isinstance(source, str) or not source:
            source = ""
        if not isinstance(source_type, str) or not source_type:
            source_type = "unknown"
        if not isinstance(source_url, str) or not source_url:
            source_url = source

        agents = raw_entry.get("agents")
        if not isinstance(agents, list):
            agents = []
        normalized_agents = [a for a in agents if isinstance(a, str)]

        install_mode = raw_entry.get("install_mode")
        if install_mode not in {"symlink", "copy"}:
            install_mode = "symlink"

        source_id = raw_entry.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            source_id = _default_source_id(source_type, source, source_url)

        migrated_skills[name] = {
            "source": source,
            "source_type": source_type,
            "source_url": source_url,
            "skill_path": raw_entry.get("skill_path"),
            "skill_folder_hash": raw_entry.get("skill_folder_hash", ""),
            "installed_at": raw_entry.get("installed_at") or now,
            "updated_at": raw_entry.get("updated_at") or now,
            "plugin_name": raw_entry.get("plugin_name"),
            "source_id": source_id,
            "agents": normalized_agents,
            "install_mode": install_mode,
        }

    dismissed = data.get("dismissed")
    if not isinstance(dismissed, dict):
        dismissed = {}

    return {
        "version": GLOBAL_LOCK_VERSION,
        "skills": migrated_skills,
        "dismissed": dismissed,
        "last_selected_agents": data.get("last_selected_agents"),
    }


def _default_source_id(source_type: str, source: str, source_url: str) -> str:
    """Build a canonical source id for lock fidelity."""

    if source_type == "github":
        candidate = source_url or source
        if candidate.startswith("https://github.com/"):
            tail = candidate.removeprefix("https://github.com/")
            tail = tail.removesuffix(".git").strip("/")
            parts = tail.split("/")
            if len(parts) >= 2:
                return f"{parts[0]}/{parts[1]}"
        if "/" in source and source.count("/") == 1:
            return source

    if source_type == "well-known":
        try:
            parsed = urlparse(source_url or source)
            host = parsed.hostname or "unknown"
            path = parsed.path.strip("/")
            return f"{host}/{path}" if path else host
        except Exception:
            return source_url or source

    if source_type == "local":
        return str(Path(source_url or source).expanduser())

    return source or source_url
