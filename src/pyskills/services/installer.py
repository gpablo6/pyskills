"""Skill installation services."""

from __future__ import annotations

import shutil
from pathlib import Path

from pyskills.models import InstallMode, InstallResult, Skill
from pyskills.shared import (
    AGENTS_DIR,
    SKILLS_SUBDIR,
    is_subpath_safe,
    sanitize_name,
)

from .agents import AGENTS, is_universal_agent


def get_canonical_skills_dir(
    global_install: bool, cwd: Path | None = None
) -> Path:
    """Return the canonical skills directory for a scope.

    Parameters
    ----------
    global_install : bool
        Whether the installation is global.
    cwd : pathlib.Path or None, optional
        Project directory when not global.

    Returns
    -------
    pathlib.Path
        Canonical ``.agents/skills`` directory for the selected scope.
    """

    base = Path.home() if global_install else (cwd or Path.cwd())
    return base / AGENTS_DIR / SKILLS_SUBDIR


def get_agent_base_dir(
    agent: str, global_install: bool, cwd: Path | None = None
) -> Path:
    """Resolve an agent's base skill directory.

    Parameters
    ----------
    agent : str
        Agent identifier.
    global_install : bool
        Whether the installation is global.
    cwd : pathlib.Path or None, optional
        Project directory when not global.

    Returns
    -------
    pathlib.Path
        Agent base directory for installation.

    Raises
    ------
    ValueError
        Raised when global installation is requested for an unsupported agent.
    """

    cfg = AGENTS[agent]
    if is_universal_agent(agent):
        return get_canonical_skills_dir(global_install, cwd)

    if global_install:
        if cfg.global_skills_dir is None:
            raise ValueError(
                f"{cfg.display_name} does not support "
                "global skill installation"
            )
        return cfg.global_skills_dir

    return (cwd or Path.cwd()) / cfg.skills_dir


def _clean_dir(path: Path) -> None:
    """Delete and recreate a directory path.

    Parameters
    ----------
    path : pathlib.Path
        Directory to clean.

    Returns
    -------
    None
    """

    if path.exists() or path.is_symlink():
        shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)


def _copy_directory(src: Path, dst: Path) -> None:
    """Recursively copy skill files, excluding unsupported entries.

    Parameters
    ----------
    src : pathlib.Path
        Source directory.
    dst : pathlib.Path
        Destination directory.

    Returns
    -------
    None
    """

    for entry in src.iterdir():
        if entry.name in {"metadata.json", ".git"} or entry.name.startswith(
            "_"
        ):
            continue
        target = dst / entry.name
        if entry.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            _copy_directory(entry, target)
        else:
            shutil.copy2(entry, target)


def install_skill_for_agent(
    skill: Skill,
    agent: str,
    *,
    global_install: bool = False,
    cwd: Path | None = None,
    mode: InstallMode = "symlink",
) -> InstallResult:
    """Install one skill for one target agent.

    Parameters
    ----------
    skill : Skill
        Skill to install.
    agent : str
        Agent identifier.
    global_install : bool, optional
        Whether to install globally.
    cwd : pathlib.Path or None, optional
        Project directory used for project-scoped installs.
    mode : {"symlink", "copy"}, optional
        Installation strategy.

    Returns
    -------
    InstallResult
        Structured installation outcome for the agent.
    """

    cwd = cwd or Path.cwd()
    skill_name = sanitize_name(skill.name)

    canonical_base = get_canonical_skills_dir(global_install, cwd)
    canonical_dir = canonical_base / skill_name

    agent_base = get_agent_base_dir(agent, global_install, cwd)
    agent_dir = agent_base / skill_name

    if not is_subpath_safe(canonical_base, canonical_dir):
        return InstallResult(
            success=False,
            path=agent_dir,
            mode=mode,
            error="unsafe canonical path",
        )

    if not is_subpath_safe(agent_base, agent_dir):
        return InstallResult(
            success=False, path=agent_dir, mode=mode, error="unsafe agent path"
        )

    try:
        if mode == "copy":
            _clean_dir(agent_dir)
            _copy_directory(skill.path, agent_dir)
            return InstallResult(success=True, path=agent_dir, mode="copy")

        _clean_dir(canonical_dir)
        _copy_directory(skill.path, canonical_dir)

        if global_install and is_universal_agent(agent):
            return InstallResult(
                success=True,
                path=canonical_dir,
                mode="symlink",
                canonical_path=canonical_dir,
            )

        if agent_dir.exists() or agent_dir.is_symlink():
            shutil.rmtree(agent_dir, ignore_errors=True)

        try:
            agent_dir.parent.mkdir(parents=True, exist_ok=True)
            agent_dir.symlink_to(canonical_dir, target_is_directory=True)
            return InstallResult(
                success=True,
                path=agent_dir,
                mode="symlink",
                canonical_path=canonical_dir,
            )
        except OSError:
            _clean_dir(agent_dir)
            _copy_directory(skill.path, agent_dir)
            return InstallResult(
                success=True,
                path=agent_dir,
                mode="symlink",
                canonical_path=canonical_dir,
                symlink_failed=True,
            )

    except Exception as exc:
        return InstallResult(
            success=False, path=agent_dir, mode=mode, error=str(exc)
        )
