"""Skill discovery and parsing services."""

from __future__ import annotations

from pathlib import Path

from pyskills.models import Skill
from pyskills.shared import is_subpath_safe

SKIP_DIRS = {"node_modules", ".git", "dist", "build", "__pycache__"}


def parse_skill_md(skill_md_path: Path) -> Skill | None:
    """Parse ``SKILL.md`` frontmatter into a ``Skill`` model.

    Parameters
    ----------
    skill_md_path : pathlib.Path
        Path to a ``SKILL.md`` file.

    Returns
    -------
    Skill or None
        Parsed skill when required fields are present; otherwise ``None``.
    """

    try:
        content = skill_md_path.read_text(encoding="utf-8")
    except OSError:
        return None

    if not content.startswith("---"):
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    frontmatter = parts[1]
    fields: dict[str, str] = {}
    for raw_line in frontmatter.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()

    name = fields.get("name")
    description = fields.get("description")
    if not name or not description:
        return None

    return Skill(
        name=name,
        description=description,
        path=skill_md_path.parent,
        raw_content=content,
    )


def discover_skills(
    base_path: Path, subpath: str | None = None
) -> list[Skill]:
    """Discover skills from a base directory.

    Parameters
    ----------
    base_path : pathlib.Path
        Root search directory.
    subpath : str or None, optional
        Optional subdirectory constraint relative to ``base_path``.

    Returns
    -------
    list of Skill
        Unique discovered skills.

    Raises
    ------
    ValueError
        Raised when ``subpath`` resolves outside ``base_path``.
    """

    search_path = base_path / subpath if subpath else base_path
    if not is_subpath_safe(base_path, search_path):
        raise ValueError("Subpath escapes base path")

    skills: list[Skill] = []
    seen: set[str] = set()

    for skill_md in search_path.rglob("SKILL.md"):
        if any(part in SKIP_DIRS for part in skill_md.parts):
            continue
        skill = parse_skill_md(skill_md)
        if not skill or skill.name in seen:
            continue
        seen.add(skill.name)
        skills.append(skill)

    return skills
