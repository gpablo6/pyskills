"""Installed skills inventory services."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .agents import AGENTS
from .discovery import parse_skill_md
from .installer import get_agent_base_dir, get_canonical_skills_dir
from .locks import read_global_lock, read_local_lock


@dataclass
class InstalledSkillInfo:
    """Represents one installed skill in a given scope.

    Attributes
    ----------
    name : str
        Skill display name.
    description : str
        Skill description from ``SKILL.md`` frontmatter.
    path : pathlib.Path
        Canonical path used for display.
    scope : str
        Installation scope (``project`` or ``global``).
    agents : set of str
        Agent identifiers where the skill is linked or copied.
    source : str or None
        Lockfile source identifier when available.
    source_type : str or None
        Lockfile source type when available.
    plugin_name : str or None
        Optional plugin grouping metadata from global lock.
    """

    name: str
    description: str
    path: Path
    scope: str
    agents: set[str] = field(default_factory=set)
    source: str | None = None
    source_type: str | None = None
    plugin_name: str | None = None


def list_installed_skills(
    *,
    global_install: bool,
    cwd: Path | None = None,
    agent_filter: list[str] | None = None,
) -> list[InstalledSkillInfo]:
    """List installed skills for the selected scope.

    Parameters
    ----------
    global_install : bool
        Whether to read global install directories.
    cwd : pathlib.Path or None, optional
        Project root path for project-scoped listing.
    agent_filter : list of str or None, optional
        Optional subset of agents to attribute during scanning.

    Returns
    -------
    list of InstalledSkillInfo
        Sorted installed skills for the selected scope.
    """

    root = cwd or Path.cwd()
    scope = "global" if global_install else "project"

    skills_by_name: dict[str, InstalledSkillInfo] = {}
    lock_meta = _load_lock_metadata(global_install=global_install, cwd=root)

    canonical_dir = get_canonical_skills_dir(global_install, cwd=root)
    for skill in _scan_skill_dir(canonical_dir):
        skills_by_name[skill.name] = InstalledSkillInfo(
            name=skill.name,
            description=skill.description,
            path=skill.path,
            scope=scope,
            source=lock_meta.get(skill.name, {}).get("source"),
            source_type=lock_meta.get(skill.name, {}).get("source_type"),
            plugin_name=lock_meta.get(skill.name, {}).get("plugin_name"),
        )

    agents_to_scan = agent_filter or list(AGENTS.keys())
    for agent in agents_to_scan:
        if agent not in AGENTS:
            continue

        try:
            base_dir = get_agent_base_dir(agent, global_install, cwd=root)
        except ValueError:
            continue

        for skill in _scan_skill_dir(base_dir):
            existing = skills_by_name.get(skill.name)
            if existing is None:
                existing = InstalledSkillInfo(
                    name=skill.name,
                    description=skill.description,
                    path=skill.path,
                    scope=scope,
                    source=lock_meta.get(skill.name, {}).get("source"),
                    source_type=lock_meta.get(skill.name, {}).get(
                        "source_type"
                    ),
                    plugin_name=lock_meta.get(skill.name, {}).get(
                        "plugin_name"
                    ),
                )
                skills_by_name[skill.name] = existing
            existing.agents.add(agent)

    return sorted(skills_by_name.values(), key=lambda s: s.name.lower())


def _scan_skill_dir(base_dir: Path) -> list[InstalledSkillInfo]:
    """Scan direct children of ``base_dir`` for valid skill directories."""

    if not base_dir.exists():
        return []

    found: list[InstalledSkillInfo] = []
    for child in base_dir.iterdir():
        if not (child.is_dir() or child.is_symlink()):
            continue

        parsed = parse_skill_md(child / "SKILL.md")
        if not parsed:
            continue

        found.append(
            InstalledSkillInfo(
                name=parsed.name,
                description=parsed.description,
                path=parsed.path,
                scope="project",
            )
        )

    return found


def _load_lock_metadata(
    *,
    global_install: bool,
    cwd: Path,
) -> dict[str, dict[str, str]]:
    """Load lock metadata keyed by skill name."""

    if global_install:
        lock = read_global_lock()
        return {
            name: {
                "source": entry.source,
                "source_type": entry.source_type,
                "plugin_name": entry.plugin_name or "",
            }
            for name, entry in lock.skills.items()
        }

    lock = read_local_lock(cwd=cwd)
    return {
        name: {
            "source": entry.source,
            "source_type": entry.source_type,
            "plugin_name": "",
        }
        for name, entry in lock.skills.items()
    }
